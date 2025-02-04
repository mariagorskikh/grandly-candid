from flask import Flask, render_template, request, jsonify
import requests
import os
from dotenv import load_dotenv
import json
from ai_utils import get_foundation_summary
import logging

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static')
API_KEY = os.getenv('CANDID_API_KEY')

@app.route('/')
def index():
    logger.info('Index page requested')
    return render_template('index.html')

@app.route('/search_grants', methods=['POST'])
def search_grants():
    logger.info('Search funders endpoint called')
    data = request.get_json()
    logger.info(f'Received data: {json.dumps(data, indent=2)}')
    
    url = "https://api.candid.org/grants/v1/funders"
    
    headers = {
        "accept": "application/json",
        "Subscription-Key": API_KEY
    }
    
    try:
        # Build query parameters
        params = {}
        
        # Add query parameter if provided
        if data.get('query'):
            params['query'] = data['query'].strip()
            logger.info(f'Search query: {params["query"]}')
        
        logger.info(f'Making API request to: {url}')
        logger.info(f'With params: {json.dumps(params, indent=2)}')
        
        response = requests.get(url, headers=headers, params=params)
        logger.info(f'Response status code: {response.status_code}')
        
        try:
            response_data = response.json()
            logger.info(f'Response data: {json.dumps(response_data, indent=2)}')
        except json.JSONDecodeError:
            logger.error(f'Failed to decode JSON. Raw response: {response.text}')
            return jsonify({
                'error': 'Invalid API response',
                'details': 'The API response was not valid JSON'
            }), 500
        
        if response.status_code == 400:
            logger.error(f'API error response: {response_data}')
            return jsonify({
                'error': 'Invalid search parameters',
                'details': response_data.get('message', 'Unknown error')
            }), 400
        
        response.raise_for_status()
        
        # Return the funders data with AI summaries
        if response_data.get('data'):
            funders = response_data['data'].get('rows', [])
            
            # Add AI summaries and process each funder
            for funder in funders:
                # Add website URL if available
                if funder.get('website_url'):
                    funder['url'] = funder['website_url']
                    logger.info(f"Found website URL for {funder.get('funder_name')}: {funder['url']}")
                
                # Generate AI summary
                if funder.get('funder_name'):
                    logger.info(f"Generating summary for: {funder['funder_name']}")
                    summary_result = get_foundation_summary(funder['funder_name'])
                    funder['ai_summary'] = summary_result.get('summary', '')
                    funder['summary_source'] = summary_result.get('source', '')
                    logger.info(f"Generated summary: {funder['ai_summary'][:100]}...")
            
            return jsonify({
                'funders': funders,
                'meta': {
                    'total_hits': response_data['data'].get('total_hits', 0),
                    'num_pages': response_data['data'].get('num_pages', 0)
                }
            })
        else:
            return jsonify({
                'error': 'No funders found',
                'details': 'The API response did not contain any funder data'
            }), 404
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Candid API: {str(e)}")
        error_details = {
            'error': 'Failed to fetch funders data',
            'details': str(e),
            'status_code': getattr(e.response, 'status_code', None),
            'response_text': getattr(e.response, 'text', None) if hasattr(e, 'response') else None
        }
        logger.error(f"Error details: {json.dumps(error_details, indent=2)}")
        return jsonify(error_details), 500

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=8080)
