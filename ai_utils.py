import os
import openai
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import requests
from tenacity import retry, wait_random_exponential, stop_after_attempt
import logging
import urllib.parse
import re
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')
DEFAULT_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')

logger.info(f"OpenAI API Key configured: {'Yes' if openai.api_key else 'No'}")
logger.info(f"Using model: {DEFAULT_MODEL}")

def clean_foundation_name(name):
    """Clean up foundation name for better search results."""
    if not name:
        return ""
        
    # Remove extra quotes and spaces
    name = name.strip().strip('"').strip("'").strip()
    
    # Remove common suffixes that might interfere with search
    suffixes = [' Inc', ' LLC', ' Corporation', ' Corp', ' Foundation', ' Founda', ' Trust', ' Private']
    for suffix in suffixes:
        if name.lower().endswith(suffix.lower()):
            name = name[:-len(suffix)]
            
    # Fix common issues with apostrophes and special characters
    name = name.replace("'S", "'s").replace("'", "'")
    
    # Remove any remaining special characters but preserve & and -
    name = re.sub(r'[^\w\s&\'-]', ' ', name)
    
    # Clean up extra spaces
    name = ' '.join(name.split())
    
    return name.strip()

def extract_text_from_html(html_content):
    """Extract meaningful text from HTML content."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        # Get text
        text = soup.get_text()
        
        # Break into lines and remove leading and trailing space on each
        lines = (line.strip() for line in text.splitlines())
        
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        
        # Drop blank lines
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    except Exception as e:
        logger.error(f"Error extracting text from HTML: {str(e)}")
        return ""

def get_search_results(foundation_name):
    """Get search results from multiple sources."""
    search_results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }
    
    # Reduced number of search queries to avoid rate limiting
    search_queries = [
        # Try exact name first
        f'"{foundation_name}"',
        
        # Try most important site-specific search
        f'site:charitynavigator.org "{foundation_name}"',
        
        # Try with specific information
        f'"{foundation_name}" mission statement'
    ]
    
    logger.info(f"Searching for foundation: {foundation_name}")
    
    retry_delay = 2  # Start with 2 second delay
    max_retries = 3
    
    for query in search_queries:
        retries = 0
        while retries < max_retries:
            try:
                logger.info(f"Trying search query: {query}")
                
                # Google search
                search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&num=10"
                response = requests.get(search_url, headers=headers, timeout=10)
                
                if response.status_code == 429:
                    retries += 1
                    wait_time = retry_delay * (2 ** retries)  # Exponential backoff
                    logger.warning(f"Rate limited. Waiting {wait_time} seconds before retry {retries}/{max_retries}")
                    time.sleep(wait_time)
                    continue
                    
                if response.status_code != 200:
                    logger.warning(f"Got status code {response.status_code} for query: {query}")
                    break  # Move to next query
                    
                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract text from various HTML elements that might contain useful information
                selectors = [
                    # Main search result divs
                    ('div', ['g']),  # Main result container
                    ('div', ['VwiC3b', 'yXK7lf']),  # Snippet container
                    ('div', ['MUxGbd', 'yDYNvb', 'lyLwlc']),  # Description
                    
                    # Featured snippet elements
                    ('div', ['IZ6rdc']),  # Featured snippet
                    
                    # Knowledge graph elements
                    ('div', ['kno-rdesc'])  # Knowledge graph description
                ]
                
                results_found = False
                for tag, classes in selectors:
                    elements = soup.find_all(tag, class_=classes)
                    for element in elements:
                        # Get text and clean it
                        text = element.get_text().strip()
                        
                        # Remove duplicate whitespace and newlines
                        text = ' '.join(text.split())
                        
                        # Only keep substantial text
                        if text and len(text) > 50 and not any(x in text.lower() for x in ['javascript', 'cookies', 'browser']):
                            # Check if this text is substantially different from what we already have
                            is_duplicate = any(similar_text in text or text in similar_text for similar_text in search_results)
                            
                            if not is_duplicate:
                                search_results.append(text)
                                results_found = True
                                logger.info(f"Found result ({len(text)} chars): {text[:100]}...")
                
                if not results_found:
                    logger.warning(f"No results found with selectors for query: {query}")
                
                # If we found good results, no need to try more queries
                if len(search_results) >= 2:  # Reduced from 3 to 2
                    logger.info(f"Found {len(search_results)} good results, stopping search")
                    return search_results
                    
                # Add a longer delay between requests
                time.sleep(3)  # Increased from 1 to 3 seconds
                break  # Success, move to next query
                    
            except requests.RequestException as e:
                logger.error(f"Request error for query '{query}': {str(e)}")
                break  # Move to next query
            except Exception as e:
                logger.error(f"Unexpected error for query '{query}': {str(e)}")
                break  # Move to next query
    
    # If we still don't have results, try to extract from URLs
    if not search_results:
        try:
            # Get URLs from search results
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if 'http' in href and 'charitynavigator.org' in href:  # Only try CharityNavigator to reduce load
                    try:
                        response = requests.get(href, headers=headers, timeout=10)
                        if response.status_code == 200:
                            text = extract_text_from_html(response.text)
                            if text and len(text) > 50:
                                search_results.append(text)
                                logger.info(f"Found result from URL {href}")
                                return search_results  # Return immediately if we found something
                    except:
                        continue
        except Exception as e:
            logger.error(f"Error extracting from URLs: {str(e)}")
    
    logger.info(f"Total search results found: {len(search_results)}")
    return search_results

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
def get_foundation_summary(foundation_name):
    """
    Generate a summary of a foundation using web search results and OpenAI.
    """
    if not foundation_name:
        return {
            'success': False,
            'error': 'No foundation name provided',
            'summary': 'Unable to generate summary: No foundation name provided.'
        }
    
    logger.info(f"Generating summary for: {foundation_name}")
    
    # Clean up the foundation name
    clean_name = clean_foundation_name(foundation_name)
    logger.info(f"Cleaned foundation name: {clean_name}")
    
    try:
        # Get search results
        search_results = get_search_results(clean_name)
        logger.info(f"Found {len(search_results)} search results")
        
        # Combine search results
        context = "\n\n".join(search_results[:5])  # Take first 5 results
        
        if not context:
            logger.warning(f"No search results found for {clean_name}, using fallback context")
            context = f"This appears to be a foundation named {clean_name}. Please provide a general summary based on the foundation's name and any patterns you observe in similar foundations."
        
        logger.info("Generating OpenAI summary")
        # Generate summary using OpenAI
        prompt = f"""Based on the following information about {clean_name}, create a concise one-paragraph summary that includes:
        - Their main focus areas and priorities (if known)
        - Typical grant sizes or ranges (if available)
        - Geographic focus (if mentioned)
        - Any unique characteristics or requirements
        
        Information:
        {context}
        
        Please provide a factual summary without speculation. If certain information is not available, focus on what can be reasonably inferred from the foundation's name and any available information. If very little information is available, acknowledge this in the summary."""

        response = openai.ChatCompletion.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates concise, accurate summaries of charitable foundations based on available information. When information is limited, acknowledge this fact but still provide useful insights based on the foundation's name and any patterns you observe in similar foundations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=300
        )
        
        summary = response.choices[0].message.content.strip()
        logger.info(f"Successfully generated summary: {summary[:100]}...")
        
        return {
            'success': True,
            'summary': summary,
            'source': 'Web search and AI analysis'
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error generating summary: {error_msg}")
        return {
            'success': False,
            'error': error_msg,
            'summary': f"Unable to generate summary for {clean_name}. Error: {error_msg}"
        }
