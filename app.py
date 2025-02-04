from flask import Flask, render_template, request, jsonify
import requests
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static')
API_KEY = os.getenv('CANDID_API_KEY')

@app.route('/')
def index():
    app.logger.info('Index page requested')
    return render_template('index.html')

@app.route('/search_grants', methods=['POST'])
def search_grants():
    app.logger.info('Search funders endpoint called')
    data = request.get_json()
    app.logger.info(f'Received data: {json.dumps(data, indent=2)}')
    
    url = "https://api.candid.org/grants/v1/funders"
    
    headers = {
        "accept": "application/json",
        "Subscription-Key": API_KEY
    }
    
    try:
        # Build query parameters - keep it simple
        params = {}
        
        # Add query parameter if provided
        if data.get('query'):
            params['query'] = data['query'].strip()
            app.logger.info(f'Search query: {params["query"]}')
        
        app.logger.info(f'Making API request to: {url}')
        app.logger.info(f'With params: {json.dumps(params, indent=2)}')
        
        response = requests.get(url, headers=headers, params=params)
        app.logger.info(f'Response status code: {response.status_code}')
        
        try:
            response_data = response.json()
            app.logger.info(f'Response data: {json.dumps(response_data, indent=2)}')
        except json.JSONDecodeError:
            app.logger.error(f'Failed to decode JSON. Raw response: {response.text}')
            return jsonify({
                'error': 'Invalid API response',
                'details': 'The API response was not valid JSON'
            }), 500
        
        if response.status_code == 400:
            app.logger.error(f'API error response: {response_data}')
            return jsonify({
                'error': 'Invalid search parameters',
                'details': response_data.get('message', 'Unknown error')
            }), 400
        
        response.raise_for_status()
        
        # Return the funders data
        if response_data.get('data'):
            return jsonify({
                'funders': response_data['data'].get('rows', []),
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
        app.logger.error(f"Error calling Candid API: {str(e)}")
        error_details = {
            'error': 'Failed to fetch funders data',
            'details': str(e),
            'status_code': getattr(e.response, 'status_code', None),
            'response_text': getattr(e.response, 'text', None) if hasattr(e, 'response') else None
        }
        app.logger.error(f"Error details: {json.dumps(error_details, indent=2)}")
        return jsonify(error_details), 500

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=8080)
