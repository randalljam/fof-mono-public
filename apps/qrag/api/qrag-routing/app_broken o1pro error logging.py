# ===== START OF FILE qrag-routing/app.py =====
# in AWS Chalice for Lambda Function

import os
import json
from chalice import Chalice, Response

from chalicelib.rag import qrag_routing_call, print_qrag_display_text
# from chalicelib.llm import simple_openai_chat_completion_request
from chalicelib.rag_prompts_routes import *
from chalicelib.vectordb import generate_embedding
from chalicelib.fileops import get_current_datetime_filefriendly
from chalicelib.aws import verify_jwt

# not currently used langchain-layer arn:aws:lambda:us-west-2:[AWS-ACCOUNT-ID]:layer:langchain-layer:1

app = Chalice(app_name='qrag-routing')
app.api.cors = True

# Define allowed origins as a set
ALLOWED_ORIGINS = {
    'https://www.focusonfoundations.org',
    'https://floodlamp-8c9d00d6ef3e90c375de806594d04.webflow.io',
    'http://localhost:8000'
}

@app.route('/qrag-routing', methods=['POST'], cors=True)
def handle_qrag_routing():
    print("qrag-routing lambda func - last updated 2025-01-21 with o1 pro enhanced logging")

    request_headers = app.current_request.headers
    request_origin = request_headers.get('origin', 'No origin provided')
    print(f"Request Origin: {request_origin}")
    print(f"Request Headers: {json.dumps(dict(request_headers), default=str)}")

    # Set up CORS headers
    cors_headers = {
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization'
    }

    # Check CORS origin
    if request_origin in ALLOWED_ORIGINS:
        cors_headers['Access-Control-Allow-Origin'] = request_origin
        print(f"Origin '{request_origin}' is allowed.")
    else:
        print(f"Origin '{request_origin}' is NOT in allowed list: {ALLOWED_ORIGINS}")
        # You can explicitly return 403 here if you want to enforce it strictly
        # but at a minimum log it. Usually, Chalice CORS is more permissive by default.

    # Get raw request body
    raw_request_data = app.current_request.raw_body.decode('utf-8', errors='replace')
    print("Raw request data:", raw_request_data)

    try:
        # 1. Authorization check
        auth_header = app.current_request.headers.get('Authorization')
        if not auth_header:
            error_msg = "ERROR: No Authorization header present"
            print(error_msg)
            return Response(
                body={'error': error_msg},
                status_code=401,
                headers=cors_headers
            )
        if not auth_header.startswith('Bearer '):
            error_msg = "ERROR: Authorization header does not start with 'Bearer '"
            print(error_msg)
            return Response(
                body={'error': error_msg},
                status_code=401,
                headers=cors_headers
            )

        token = auth_header.split(' ')[1]
        print("Attempting to verify JWT token...")

        # your custom verification
        claims = verify_jwt(token)  # presumably returns None or False if invalid

        if not claims:
            error_msg = "ERROR: JWT verification failed (Invalid or expired token)"
            print(error_msg)
            return Response(
                body={'error': error_msg},
                status_code=401,
                headers=cors_headers
            )
        print("JWT verification successful. Claims:", claims)

        # 2. Parse JSON body
        received_request_data = app.current_request.json_body
        if not received_request_data:
            error_msg = "ERROR: Empty JSON body"
            print(error_msg)
            return Response(
                body={'error': error_msg},
                status_code=400,
                headers=cors_headers
            )

        print("Parsed request data:", received_request_data)

        # 3. Check required fields
        required_fields = ['user_question', 'vector_index_name', 'route_dict_name']
        missing_fields = [field for field in required_fields if field not in received_request_data]
        if missing_fields:
            error_msg = f"ERROR: Missing required fields: {missing_fields}"
            print(error_msg)
            return Response(
                body={'error': error_msg},
                status_code=400,
                headers=cors_headers
            )

        # 4. Logging user_id check
        user_id = received_request_data.get('user_id')
        if not user_id:
            print("WARNING: No user_id provided in the request data")

        # ... do the rest of your logic (extract parameters, call your qrag_routing_call, etc.) ...

        # If everything is good, return a 200
        print("All validations passed. Calling qrag_routing_call...")
        
        # Extract parameters from received_request_data
        user_question = received_request_data['user_question']
        vector_index_name = received_request_data['vector_index_name']
        route_dict_name = received_request_data['route_dict_name']
        
        # Call the actual qrag_routing_call function
        response_data = qrag_routing_call(
            user_question=user_question,
            vector_index_name=vector_index_name,
            route_dict_name=route_dict_name
        )
        
        # Return the proper response format
        return Response(
            body=json.dumps({
                'status': 'Success',
                'content': {
                    'user_question': user_question,
                    'route_preamble': response_data.get('route_preamble', ''),
                    'quoted_qa': response_data.get('quoted_qa', ''),
                    'ai_answer': response_data.get('ai_answer', 'WAITING FOR AI ANSWER...')
                }
            }),
            status_code=200,
            headers=cors_headers
        )

    except json.JSONDecodeError as e:
        error_msg = f"ERROR: Invalid JSON in request body: {str(e)}"
        print(error_msg)
        return Response(
            body={'error': error_msg},
            status_code=400,
            headers=cors_headers
        )
    except Exception as e:
        # This covers anything unexpected
        error_type = type(e).__name__
        error_details = str(e)
        print(f"ERROR: Unexpected error: {error_details} (type: {error_type})")
        return Response(
            body={'error': f'Internal server error: {error_details}'},
            status_code=500,
            headers=cors_headers
        )
    
# TO REDEPLOY WITH MIRROR SCRIPT
'''
cd /Users/randytrue/Documents/Code/corpus-tools/web/aws_chalice/qrag-routing
../chalicelib_mirror_deploy.sh
'''

# API ENDPOINT: https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/qrag-routing

# TEST WITH CURL WITH JWT
# curl -X POST https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/qrag-routing -H "Content-Type: application/json" -H "Authorization: Bearer eyJh..." -d '{"user_question": "Is this test working with JWT?", "vector_index_name": "deutsch-transcript-qrag-78f-20240926", "num_chunks": 3, "route_dict_name": "ROUTES_DICT_DEUTSCH_V4", "routes_bounds": [0.3, 0.9], "llm_model": "gpt-4o", "user_id": "test_user", "qrag_version": "1.0"}'

# TEST WITH CURL WITHOUT API KEY OR JWT
# curl -X POST https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/qrag-routing -H "Content-Type: application/json" -d '{"user_question": "Is this test working from the Curl with API key?", "vector_index_name": "deutsch-transcript-qrag-78f-20240926", "num_chunks": 3, "route_dict_name": "ROUTES_DICT_DEUTSCH_V4", "routes_bounds": [0.3, 0.9], "llm_model": "gpt-4o", "user_id": "test_user", "qrag_version": "1.0"}'

# TEST WITH CURL WITH API KEY
# curl -X POST https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/qrag-routing -H "Content-Type: application/json" -H "x-api-key: Fhhs7..." -d '{"user_question": "Is this test working from the Curl with API key?", "vector_index_name": "deutsch-transcript-qrag-78f-20240926", "num_chunks": 3, "route_dict_name": "ROUTES_DICT_DEUTSCH_V4", "routes_bounds": [0.3, 0.9], "llm_model": "gpt-4o", "user_id": "test_user", "qrag_version": "1.0"}'

# TEST WITH PORTAL API GATEWAY (NOT IN LAMBDA FUNCTION VIEW)
# Headers:
'''
Content-Type:application/json,
Origin:https://www.focusonfoundations.org
'''

# Request body:
'''
{
  "user_question": "Is this PV Evac QRAG working from the Portal API Gateway Test tab with CORS restricted to fof domain?",
  "vector_index_name": "pv-evac-qrag-2f-20241024",
  "num_chunks": 3,
  "route_dict_name": "ROUTES_DICT_PV_EVAC_V1",
  "routes_bounds": [0.3, 0.9],
  "llm_model": "gpt-4o",
  "user_id": "test_user",
  "qrag_version": "1.0"
}
'''

'''
{
  "user_question": "Is this Deutsch QRAG working from the Portal API Gateway Test tab with CORS restricted to fof domain?",
  "vector_index_name": "deutsch-transcript-qrag-78f-20240926",
  "num_chunks": 3,
  "route_dict_name": "ROUTES_DICT_DEUTSCH_V4",
  "routes_bounds": [0.3, 0.9],
  "llm_model": "gpt-4o",
  "user_id": "test_user",
  "qrag_version": "1.0"
}
'''

# ===== END OF FILE qrag-routing/app.py =====



