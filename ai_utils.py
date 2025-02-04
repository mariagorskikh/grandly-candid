import os
import openai
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import requests
from tenacity import retry, wait_random_exponential, stop_after_attempt

# Load environment variables
load_dotenv()

# Configure OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')
DEFAULT_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4-0125-preview')

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(3))
def get_foundation_summary(foundation_name):
    """
    Generate a summary of a foundation using web search results and OpenAI.
    """
    # Search query to find information about the foundation
    search_query = f"{foundation_name} foundation grants mission about"
    
    # Get search results (placeholder - we'll implement web search later)
    # For now, we'll use a direct approach with a simple Google search
    search_url = f"https://www.google.com/search?q={search_query}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(search_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract text from search results
        search_results = []
        for result in soup.find_all(['h3', 'div'], class_=['r', 'VwiC3b']):
            if result.get_text().strip():
                search_results.append(result.get_text().strip())
        
        # Combine search results
        context = "\n".join(search_results[:5])  # Take first 5 results
        
        # Generate summary using OpenAI
        prompt = f"""Based on the following information about {foundation_name}, create a concise one-paragraph summary that includes:
        - Their main focus areas and priorities
        - Typical grant sizes or ranges (if available)
        - Geographic focus
        - Any unique characteristics or requirements
        
        Information:
        {context}
        
        Please provide a factual summary without speculation. If certain information is not available, don't include it rather than guessing."""

        response = openai.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates concise, accurate summaries of charitable foundations based on available information."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=300
        )
        
        return {
            'success': True,
            'summary': response.choices[0].message.content.strip(),
            'source': 'Web search and AI analysis'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'summary': f"Unable to generate summary for {foundation_name}. Please try again later."
        }
