# Local dev implementation of qrag and web page display, with real OpenAI API call with user input question, and upload of json to s3

from flask import Flask, request, jsonify  # pip install Flask
from flask_cors import CORS  # pip install -U flask-cors
from bs4 import BeautifulSoup  # pip install beautifulsoup4
# import os
# import json
# import boto3
# from datetime import datetime

# Import your custom functions using regular imports
from bots.rag_bots import qrag_sim_routed, write_json_file_from_object, create_html_page_from_json_file, print_qrag_display_text
from bots.rag_bots import ROUTES_DICT_DEUTSCH_V1
from bots.vectordb import generate_embedding
from core.aws import upload_file_to_s3
from core.fileops import get_current_datetime_filefriendly

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    print("Received request data:", data)  # Log incoming request data
    user_question = data.get('question')
    
    if not user_question:
        return jsonify({'error': 'No question provided'}), 400

    # Define paths
    json_prefix = 'qrag-exch_'
    json_file_path = 'bots/locstore/' + json_prefix + get_current_datetime_filefriendly() + '.json'
    html_file_path = 'apps/qrag/web/local_dev/index.html'

    try:
        # Call your custom multi-route retrieval augmented generation pipeline
        print("\nCalling qrag_sim_routed...")
        response_json_object = qrag_sim_routed(user_question, ROUTES_DICT_DEUTSCH_V1, 'qragnospace')
        
        print("\nPrinting json object with print_qrag_display_text...")
        print_qrag_display_text(response_json_object)
        
        print("\nWriting JSON to file...")
        write_json_file_from_object(response_json_object, json_file_path)

        print("\nUploading JSON to S3...")
        upload_file_to_s3(json_file_path, bucket='[S3-BUCKET]', s3_path='deutsch_qrag_demo_v1')

        print("\nUpdating HTML file...")
        create_html_page_from_json_file(json_file_path, html_file_path)

        return jsonify({'status': 'Successfully updated HTML file', 'response': response_json_object})
    except Exception as e:
        print("Error while processing request:", e)  # Log any exceptions
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

