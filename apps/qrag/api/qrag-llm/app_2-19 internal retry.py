# ===== START OF FILE qrag-llm/app.py =====
# in AWS Chalice for Lambda Function

from chalice import Chalice, Response
import json
import os
import traceback
import boto3
import time
import threading

from chalicelib.rag import qrag_llm_call
from chalicelib.aws import upload_file_to_s3, verify_jwt, get_large_context_from_s3
from chalicelib.rag_prompts_routes import *
from chalicelib.fileops import get_current_datetime_filefriendly, write_json_file_from_json_data, pretty_print_json_data

app = Chalice(app_name='qrag-llm')
app.api.cors = True

# Define allowed origins as a set
ALLOWED_ORIGINS = {
    'https://www.focusonfoundations.org',
    'https://floodlamp-8c9d00d6ef3e90c375de806594d04.webflow.io',
    'http://localhost:8000'
}

# Define the server-side models and timing
SERVER_SIDE_LLM_MODEL = "o3-mini"
FALLBACK_MODEL = "gpt-4o"
RETRY_INITIATION_TIME = 10  # seconds - time to initiate retry
RETRY_TIMEOUT_TIME = 26  # seconds - time to return from retry so that API gateway doesn't kill the lambda
INTENTIONAL_DELAY = 0  # seconds
RETRY_FLAG_PARAM = "is_retry"
SAMPLING_INTERVAL = 1  # seconds
FUNCTION_NAME = "qrag-llm-dev"

@app.route('/qrag-llm', methods=['POST'], cors=True)
def handle_qrag_llm():
    start_time = time.time()
    print("qrag-llm lambda func - last updated 2-19 0919 with retry")
    
    # Check if this is a retry attempt
    received_request_data = app.current_request.json_body
    is_retry = received_request_data.get('metadata', {}).get(RETRY_FLAG_PARAM, False)
    
    # If it's a retry, use the fallback model
    current_model = FALLBACK_MODEL if is_retry else SERVER_SIDE_LLM_MODEL
    print(f"Using LLM model: {current_model} (retry: {is_retry})")
    
    # Get the origin from the request
    request_origin = app.current_request.headers.get('origin', '')
    
    # Set the CORS headers based on the request origin
    cors_headers = {
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization'
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

        # Override model with our server-side choice
        received_request_data['metadata']['llm_model'] = current_model
        
        # Get large context filename from metadata
        large_context_filename = received_request_data.get('metadata', {}).get('large_context_filename')
        large_context = None
        
        if large_context_filename:
            print(f"Getting large context from S3 for file: {large_context_filename}")
            large_context = get_large_context_from_s3(large_context_filename)
            if not large_context:
                error_msg = f"Failed to load required large context from {large_context_filename}"
                print(f"Error: {error_msg}")
                return Response(
                    body=json.dumps({
                        'error': error_msg,
                        'error_type': 'LargeContextLoadError',
                        'vector_index': received_request_data.get('metadata', {}).get('vector_index_name', 'unknown')
                    }),
                    status_code=500,
                    headers=cors_headers
                )
            else:
                print(f"Successfully loaded large context from file: {large_context_filename}")
        else:
            print("No large context filename provided")

        # Start the LLM call
        try:
            # Check if this is a retry attempt
            received_request_data = app.current_request.json_body
            is_retry = received_request_data.get('metadata', {}).get(RETRY_FLAG_PARAM, False)
            
            # If it's a retry, use the fallback model
            current_model = FALLBACK_MODEL if is_retry else SERVER_SIDE_LLM_MODEL
            print(f"Using LLM model: {current_model} (retry: {is_retry})")

            # Start monitoring thread for execution time
            monitoring_active = threading.Event()
            monitoring_active.set()
            elapsed_time = 0  # Shared variable for tracking time
            retry_elapsed_time = 0  # Shared variable for retry tracking
            retry_start_time = None
            
            def monitor_execution_time():
                while monitoring_active.is_set():
                    nonlocal elapsed_time, retry_elapsed_time
                    elapsed_time = time.time() - start_time
                    if retry_start_time:
                        retry_elapsed_time = time.time() - retry_start_time
                        print(f"Execution time: {elapsed_time:.2f}s (overall), {retry_elapsed_time:.2f}s (retry), is_retry: {is_retry}, current_model: {current_model}")
                    else:
                        print(f"Execution time: {elapsed_time:.2f}s, is_retry: {is_retry}, current_model: {current_model}")
                    time.sleep(SAMPLING_INTERVAL)
            
            monitor_thread = threading.Thread(target=monitor_execution_time)
            monitor_thread.daemon = True
            monitor_thread.start()

            # Add intentional delay for testing (isolated)
            if not is_retry:
                print(f"Adding {INTENTIONAL_DELAY} second intentional delay to test timeout...")
                time.sleep(INTENTIONAL_DELAY)
            
            # Create an Event to signal completion
            completion_event = threading.Event()
            result = {'response': None, 'error': None}
            
            def llm_worker():
                try:
                    result['response'] = qrag_llm_call(
                        received_request_data,
                        llm_model=current_model,
                        large_context=large_context,
                        large_context_filename=large_context_filename
                    )
                except Exception as e:
                    result['error'] = e
                finally:
                    completion_event.set()
            
            # Start LLM call in separate thread
            thread = threading.Thread(target=llm_worker)
            thread.start()
            
            # Wait for completion or timeout
            while not completion_event.wait(timeout=SAMPLING_INTERVAL):
                if not is_retry and elapsed_time >= RETRY_INITIATION_TIME:
                    monitoring_active.clear()
                    print(f"Execution time exceeded {RETRY_INITIATION_TIME}s, initiating retry...")
                    
                    print("=== RETRY PROCESS STARTING ===")
                    print(f"Original request execution time: {elapsed_time:.2f}s")
                    print(f"Original model used: {current_model}")
                    print(f"Switching to fallback model: {FALLBACK_MODEL}")
                    
                    retry_start_time = time.time()
                    received_request_data['metadata'][RETRY_FLAG_PARAM] = True
                    received_request_data['metadata']['llm_model'] = FALLBACK_MODEL
                    
                    # Get the original authorization header
                    original_auth = app.current_request.headers.get('Authorization')
                    
                    # Create API Gateway style event
                    retry_event = {
                        'body': json.dumps(received_request_data),
                        'requestContext': {
                            'resourcePath': '/qrag-llm',
                            'httpMethod': 'POST',
                            'path': '/api/qrag-llm',
                            'protocol': 'HTTP/1.1',
                            'stage': 'api'
                        },
                        'headers': {
                            'Content-Type': 'application/json',
                            'Authorization': original_auth  # Forward the original auth header
                        },
                        'multiValueQueryStringParameters': None,
                        'queryStringParameters': None,
                        'pathParameters': None,
                        'stageVariables': None,
                        'isBase64Encoded': False
                    }
                    
                    print("Invoking Lambda with retry request...")
                    lambda_client = boto3.client('lambda')
                    response = lambda_client.invoke(
                        FunctionName=FUNCTION_NAME,
                        InvocationType='RequestResponse',
                        Payload=json.dumps(retry_event)
                    )
                    
                    retry_response = json.loads(response['Payload'].read())
                    print(f"Retry response received: {retry_response}")
                    
                    return Response(
                        body=retry_response.get('body', json.dumps({'error': 'Retry failed'})),
                        status_code=retry_response.get('statusCode', 500),
                        headers=cors_headers
                    )
                
                elif is_retry and retry_elapsed_time >= RETRY_TIMEOUT_TIME:
                    monitoring_active.clear()
                    print(f"Retry execution time exceeded {RETRY_TIMEOUT_TIME}s")
                    raise Exception("Retry attempt also timed out")
            
            # Process completion
            if completion_event.is_set():
                if result['error']:
                    raise result['error']
                response_json_object = result['response']
            
            # Clean up monitoring thread
            monitoring_active.clear()
            monitor_thread.join(timeout=1.0)

        except Exception as e:
            print(f"Error occurred: {str(e)}")
            raise

        print("Writing JSON to file...")
        json_prefix = 'qrag-exch_'
        json_file_path = '/tmp/' + json_prefix + get_current_datetime_filefriendly() + '.json'
        write_json_file_from_json_data(response_json_object, json_file_path, overwrite="yes")

        # Determine S3 path based on index name from response metadata
        metadata = response_json_object.get("metadata", {})
        vector_index_name = metadata.get("vector_index_name", "NOT_FOUND")
        if vector_index_name.startswith("deutsch"):
            s3_path = "s3-qrag-deutsch-v3"
        elif vector_index_name.startswith("pv-evac"):
            s3_path = "s3-qrag-pv-evac"
        elif vector_index_name.startswith("fda-townhalls"):
            s3_path = "s3-qrag-fda-townhalls"
        elif vector_index_name.startswith("sovereign-child"):
            s3_path = "s3-qrag-sovereign-child"
        else:
            s3_path = "s3-qrag-default"

        print(f"Extracted index name: {vector_index_name}")
        print(f"Uploading JSON to S3 path: {s3_path}")
        upload_file_to_s3(json_file_path, bucket='[S3-BUCKET]', s3_path=s3_path)

        print("Returning JSON response...")
        return Response(
            body=json.dumps({'status': 'Success', 'response': response_json_object}),
            status_code=200,
            headers=cors_headers
        )
    
    except Exception as e:
        error_details = {
            'error': str(e),
            'error_type': type(e).__name__,
            'traceback': traceback.format_exc()
        }
        print("Error details:", error_details)
        return Response(
            body=json.dumps(error_details),
            status_code=500,
            headers=cors_headers
        )

# TO REDEPLOY WITH MIRROR SCRIPT
'''
cd /Users/randytrue/Documents/Code/corpus-tools/web/aws_chalice/qrag-llm
../chalicelib_mirror_deploy.sh
'''

# API ENDPOINT: https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/qrag-llm

# SKIP CURL TEST BECAUSE JSON IS BIG

# TEST WITH PORTAL API GATEWAY (NOT IN LAMBDA FUNCTION VIEW)
# Headers:
'''
Content-Type:application/json
Origin:https://www.focusonfoundations.org
Authorization:Bearer your_jwt_token_here
'''

# Request body:
{
    "metadata": {
        "timestamp": "2024-06-13T11:46:33.651753",
        "user_id": "default",
        "vector_index_name": "deutsch-transcript-qrag-83f-20250202",
        "bot_version": "2.0",
        "llm_model": "gpt-4o",
        "routes_info": {
            "routes_flow_name": "3 routes, sim-star double, separate prompts",
            "upper_sim_bound": 0.9,
            "lower_sim_bound": 0.3,
            "max_sim": "0.216",
            "max_stars": 5,
            "routes_dict_content": {
                "routes_dict_name": "ROUTES_DICT_DEUTSCH_M1",
                "prompt_initial_good_match": "Given your knowledge of David Deutsch and his philosophy of deep optimism, as well as the QUOTED QUESTIONS AND ANSWERS from Deutsch below, to answer the USER QUESTION below.\n",
                "route_preamble_good_match": "There is a good match of your question in David Deutsch's interviews. See his QUOTED QUESTIONS AND ANSWERS below followed by an AI ANSWER that synthesizes these quotes with David Deutsch's philosophy and your exact question.",
                "prompt_initial_partial_match": "Given your knowledge of David Deutsch and his philosophy of deep optimism, as well as the QUOTED QUESTIONS AND ANSWERS from Deutsch below, to answer the USER QUESTION below.\n",
                "route_preamble_partial_match": "There is a partial match of your question in David Deutsch's interviews. See his QUOTED QUESTIONS AND ANSWERS below followed by an AI ANSWER that synthesizes these quotes with David Deutsch's philosophy and your exact question.",
                "prompt_initial_no_match": "Given your knowledge of David Deutsch and his philosophy of deep optimism, answer the USER QUESTION below.\n",
                "route_preamble_no_match": "Your question is not addressed in David Deutsch's interviews. No QUOTED QUESTIONS AND ANSWERS are therefore provided but here is an AI ANSWER that synthesizes David Deutsch's philosophy and your question.",
                "quoted_qa_single": "QUOTED QUESTION: {top_sim_question}\nQUOTED SOURCE: {top_sim_source}\nQUOTED TIMESTAMP: {top_sim_timestamp}\nQUOTED ANSWER: {top_sim_answer}\n{top_sim_display}\n\n",
                "quoted_qa_double": "QUOTED QUESTION 1: {top_stars_question}\nQUOTED SOURCE 1: {top_stars_source}\nQUOTED TIMESTAMP 1: {top_stars_timestamp}\nQUOTED ANSWER 1: {top_stars_answer}\n{top_stars_display}\n\nQUOTED QUESTION 2: {top_sim_question}\nQUOTED SOURCE 2: {top_sim_source}\nQUOTED TIMESTAMP 2: {top_sim_timestamp}\nQUOTED ANSWER 2: {top_sim_answer}\n{top_sim_display}\n\n",
                "user_ai_qa": "USER QUESTION: {user_question}\n\nAI ANSWER: "
            }
        }
    },
    "content": {
        "user_question": "What should I eat for lunch?",
        "route_preamble": "Your question is not addressed in David Deutsch's interviews. No QUOTED QUESTIONS AND ANSWERS are therefore provided but here is an AI ANSWER that synthesizes David Deutsch's philosophy and your question.",
        "prompt_initial": "Given your knowledge of David Deutsch and his philosophy of deep optimism, answer the USER QUESTION below.\n",
        "quoted_qa": "",
        "ai_answer": "WAITING FOR LLM RESPONSE",
        "large_context": "Sample context",
        "large_context_filename": "Sample context filename",
        "chunks": {
            "max_sim": "0.216",
            "max_stars": 5,
            "chunks": [
                {
                    "question": "How should one think about choices to pursue what one finds interesting and fun versus helping the world?",
                    "source": "2021-01-09_Knowledge and Reality OurKarlPopper - Meeting David Deutsch_qafixed.md",
                    "timestamp": "[1:12:40](https://www.youtube.com/watch?v=Qrt0XXg0QKM&t=4360)",
                    "answer": "__I don't think it's a good idea to try and save the world in the sense of subordinating one's own values to what one thinks the world's values are.__",
                    "stars": 5,
                    "sim": "0.216"
                },
                {
                    "question": "What is your advice on advice?",
                    "source": "2022-01-30_Lunar Society podcast - AI America Fun and Bayes_qafixed.md",
                    "timestamp": "[1:20:19](https://www.youtube.com/watch?v=EVwjofV5TgU&t=4819)",
                    "answer": "I try very hard not to give advice. Because it's not a good relationship to be with somebody to give them advice. ",
                    "stars": 5,
                    "sim": "0.196"
                }
            ]
        }
    }
}

# Request body from aws_valid.py
{
    "metadata": {
        "timestamp": "2024-06-13T11:46:33.651753",
        "user_id": "default", 
        "vector_index_name": "deutsch-transcript-qrag-83f-20250202",
        "bot_version": "2.0",
        "llm_model": "gpt-4o-mini",
        "routes_info": {
            "routes_flow_name": "3 routes, separate route prompts",
            "upper_sim_bound": 0.9,
            "lower_sim_bound": 0.3,
            "max_sim": "0.216",
            "max_stars": 5,
            "routes_dict_content": {
                "routes_dict_name": "ROUTES_DICT_DEUTSCH_M1"
            }
        }
    },
    "content": {
        "user_question": "What should I eat for lunch?",
        "route_preamble": "Your question is not addressed in David Deutsch's interviews.",
        "prompt_initial": "Given your knowledge of David Deutsch and his philosophy...",
        "quoted_qa": "",
        "ai_answer": "WAITING FOR LLM RESPONSE",
        "large_context": "Sample context",
        "large_context_filename": "Sample context filename",
        "chunks": {
            "max_sim": "0.216",
            "max_stars": 5,
            "chunks": []
        }
    }
}

# ===== END OF FILE qrag-llm/app.py =====



