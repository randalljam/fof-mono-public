# Development function to create the test qrag routed display html from a input json file path

from flask import Flask, request, jsonify  # pip install Flask
from flask_cors import CORS  # pip install -U flask-cors
import os
import json
from bs4 import BeautifulSoup
from bots.rag_bots import create_html_page_from_json_file

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    print("Received request data:", data)  # Log incoming request data
    json_file_name = data.get('json_file_name')
    
    if not json_file_name:
        return jsonify({'error': 'No JSON file name provided'}), 400
    
    html_file_path = 'apps/qrag/web/local_dev/index.html'  # Define the path to your HTML file

    if not os.path.exists(json_file_name):
        return jsonify({'error': f"Error: File '{json_file_name}' does not exist."}), 400

    try:
        # Attempt to update the HTML with the given JSON file
        create_html_page_from_json_file(json_file_name, html_file_path)
        return jsonify({'status': 'Successfully updated HTML file'})
    except Exception as e:
        print("Error while updating HTML:", e)  # Log any exceptions
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)


