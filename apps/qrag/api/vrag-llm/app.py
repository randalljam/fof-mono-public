# ===== START OF FILE vrag-llm/app.py =====
# in AWS Chalice for Lambda Function

from chalice import Chalice, Response
import json
import os
import traceback

from chalicelib.rag import vrag_llm_call, print_vrag_display_text
from chalicelib.aws import verify_jwt, upload_file_to_s3
from chalicelib.llm import simple_openai_chat_completion_request
from chalicelib.rag_prompts_routes import *
from chalicelib.vectordb import generate_embedding
from chalicelib.fileops import get_current_datetime_filefriendly


app = Chalice(app_name='vrag-llm')
app.api.cors = True

# Define allowed origins as a set
ALLOWED_ORIGINS = {
    'https://www.focusonfoundations.org',
    'https://focusonfoundations.org',
    'https://staging.focusonfoundations.org',
    'https://floodlamp-8c9d00d6ef3e90c375de806594d04.webflow.io',
    'http://localhost:4321',
}

@app.route('/vrag-llm', methods=['POST'], cors=True)
def handle_vrag_llm():
    print("vrag-llm lambda func")
    print("last updated: 4-11 0818 dev troubleshooting PREV 12-21 0646 with JWT verification")
    
    # Get the origin and set up CORS headers
    request_origin = app.current_request.headers.get('origin', '')
    cors_headers = {
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization'  # Added Authorization
    }
    
    # Only add the origin if it's in our allowed list
    if request_origin in ALLOWED_ORIGINS:
        cors_headers['Access-Control-Allow-Origin'] = request_origin

    raw_request_data = app.current_request.raw_body.decode('utf-8')
    print("Raw request data:", raw_request_data)
    try:
        # Verify JWT token
        auth_header = app.current_request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return Response(
                body={'error': 'Missing or invalid Authorization header'},
                status_code=401,
                headers=cors_headers
            )

        token = auth_header.split(' ')[1]
        claims = verify_jwt(token)
        if not claims:
            return Response(
                body={'error': 'Invalid or expired JWT token'},
                status_code=401,
                headers=cors_headers
            )

        # Continue with existing functionality
        raw_request_data = app.current_request.raw_body.decode('utf-8')
        print("Raw request data:", raw_request_data)
        
        received_request_data = app.current_request.json_body
        print("Received request data:", received_request_data)
        
        # Extract parameters from the request
        user_question = received_request_data['user_question']
        vector_index_name = received_request_data['vector_index_name']
        vrag_preamble = received_request_data.get('vrag_preamble', 'VRAG_PREAMBLE_V1')  # Default to this prompt if not provided
        llm_model = received_request_data.get('llm_model', 'gpt-4o')  # Default to gpt-4o if not provided
        user_id = received_request_data.get('user_id', 'default')  # Default to 'default' if not provided
        vrag_version = received_request_data.get('vrag_version', '1.0')  # Default to '1.0' if not provided
        num_chunks = received_request_data.get('num_chunks', 3)  # Default to 3 if not provided

        # Define paths
        json_prefix = 'vrag-exch_'
        json_file_path = '/tmp/' + json_prefix + get_current_datetime_filefriendly() + '.json'

        # Call the function to get the AI response
        print("\nCalling vrag_llm...")
        response_json_object = vrag_llm_call(user_question, vector_index_name, int(num_chunks), vrag_preamble, llm_model, user_id, vrag_version)

        print("\nPrinting JSON object with print_vrag_display_text...")
        print_vrag_display_text(response_json_object)

        print("\nWriting JSON to file...")
        os.makedirs(os.path.dirname(json_file_path), exist_ok=True)
        with open(json_file_path, 'w') as json_file:
            json.dump(response_json_object, json_file, indent=4)

        print("\nUploading JSON to S3...")
        upload_file_to_s3(json_file_path, bucket='[S3-BUCKET]', s3_path='s3-deutsch-vrag-20240728')

        print("Returning JSON response...")
        return Response(
            body=json.dumps({'status': 'Success', 'response': response_json_object}),
            status_code=200,
            headers=cors_headers
        )
    
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return Response(
            body=json.dumps({'error': str(e), 'traceback': traceback.format_exc()}),
            status_code=500,
            headers=cors_headers
        )

# TO REDEPLOY WITH MIRROR SCRIPT
'''
cd /Users/randytrue/Documents/Code/corpus-tools/web/aws_chalice/vrag-llm
../chalicelib_mirror_deploy.sh
'''

#   - Rest API URL: https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/vrag-llm
#   - Lambda ARN: arn:aws:lambda:us-west-2:[AWS-ACCOUNT-ID]:function:vrag-llm-dev

# SKIP CURL TEST BECAUSE JSON IS BIG

# TEST WITH PORTAL API GATEWAY (NOT IN LAMBDA FUNCTION VIEW)
# Headers:
'''
Content-Type:application/json
Origin:https://www.focusonfoundations.org
'''

# Request body with only 2 fields because the others have defaults:
{
  "user_question": "What is David Deutsch's view on artificial intelligence?",
  "vector_index_name": "dd-transcripts-vrag-80f-20240727"
}
# Request body with all fields:
{
  "user_question": "What is David Deutsch's view on artificial intelligence?",
  "vector_index_name": "dd-transcripts-vrag-80f-20240727",
  "vrag_preamble": "Given your knowledge of David Deutsch and his philosophy of deep optimism, as well as the QUOTED TEXT from Deutsch below, answer the USER QUESTION.",
  "num_chunks": 5,
  "llm_model": "gpt-4o",
  "user_id": "test_user",
  "bot_version": "1.0"
}
# ===== END OF FILE vrag-llm/app.py =====



