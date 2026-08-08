# ===== START OF FILE qrag-llm/app.py =====
# in AWS Chalice for Lambda Function

from chalice import Chalice, Response
import json
import traceback
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
    'https://focusonfoundations.org',
    'https://staging.focusonfoundations.org',
    'https://floodlamp-8c9d00d6ef3e90c375de806594d04.webflow.io',
    'http://localhost:4321',
}

# Define the server-side models and timing
FIRST_MODEL = "gpt-5.4"
FALLBACK_MODEL = "gpt-5.4"
REASONING_EFFORT = "low"  # 'low', 'medium', or 'high'
FALLBACK_REASONING_EFFORT = None  # None = no reasoning
RETRY_TIME = 23  # single retry time in seconds for both first and fallback model calls
SAMPLING_INTERVAL = 1
FIRST_INTENTIONAL_DELAY = 0  # seconds, for testing 17
FALLBACK_INTENTIONAL_DELAY = 0  # seconds, for testing 21


@app.route('/qrag-llm', methods=['POST'], cors=True)
def handle_qrag_llm():
    start_time = time.time()
    print(f"qrag-llm lambda func - last updated 3-22 model gpt-5.4 reasoning low, fallback none")
    
    # Log initial execution time immediately
    elapsed_time = time.time() - start_time
    print(f"Initial execution time: {elapsed_time:.1f}s")
    
    # Check if this is a retry attempt
    received_request_data = app.current_request.json_body
    is_retry = received_request_data.get('metadata', {}).get('is_retry', False)
    
    # Set model and reasoning effort based on whether this is a retry
    current_model = FALLBACK_MODEL if is_retry else FIRST_MODEL
    current_reasoning_effort = FALLBACK_REASONING_EFFORT if is_retry else REASONING_EFFORT
    print(f"Using LLM model: {current_model} reasoning_effort: {current_reasoning_effort} (retry: {is_retry})")
    
    # Inject LLM config into metadata early so it appears in both timeout/retry and success responses
    if 'metadata' in received_request_data:
        received_request_data['metadata']['llm_model'] = current_model
        received_request_data['metadata']['reasoning_effort'] = current_reasoning_effort if current_reasoning_effort else 'none'
    
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

        # Start monitoring thread for execution time
        monitoring_active = threading.Event()
        monitoring_active.set()
        elapsed_time = 0
        
        def monitor_execution_time():
            nonlocal elapsed_time
            while monitoring_active.is_set():
                elapsed_time = time.time() - start_time
                print(f"Execution time: {elapsed_time:.1f}s, is_retry: {is_retry}, current_model: {current_model}")
                # Force flush stdout to ensure logs are captured
                import sys
                sys.stdout.flush()
                time.sleep(SAMPLING_INTERVAL)
        
        # Start monitoring thread with higher priority
        monitor_thread = threading.Thread(target=monitor_execution_time, daemon=True)
        monitor_thread.start()

        # Log time before starting LLM worker
        elapsed_time = time.time() - start_time
        print(f"  *** Pre-LLM execution time: {elapsed_time:.1f}s")

        # Create an Event to signal completion
        completion_event = threading.Event()
        result = {'response': None, 'error': None}
        
        def llm_worker():
            try:
                # Add intentional delay for testing (isolated)
                if not is_retry:
                    print(f"Adding {FIRST_INTENTIONAL_DELAY} seconds for first intentional delay to test timeout...")
                    time.sleep(FIRST_INTENTIONAL_DELAY)
                    elapsed = time.time() - start_time
                    print(f"First intentional delay complete at {elapsed:.1f}s")
                else:
                    print(f"Adding {FALLBACK_INTENTIONAL_DELAY} seconds for fallback intentional delay to test timeout...")
                    time.sleep(FALLBACK_INTENTIONAL_DELAY)
                    elapsed = time.time() - start_time
                    print(f"Fallback intentional delay complete at {elapsed:.1f}s")
                    
                elapsed = time.time() - start_time
                print(f"Starting LLM call with model {current_model} at {elapsed:.1f}s")
                    
                result['response'] = qrag_llm_call(
                    received_request_data,
                    llm_model=current_model,
                    large_context=large_context,
                    large_context_filename=large_context_filename,
                    reasoning_effort=current_reasoning_effort
                )
                elapsed = time.time() - start_time
                print(f"LLM call completed successfully at {elapsed:.1f}s")
            except Exception as e:
                elapsed = time.time() - start_time
                print(f"LLM call failed with error at {elapsed:.1f}s: {str(e)}")
                result['error'] = e
            finally:
                completion_event.set()
        
        # Start LLM call in separate thread
        thread = threading.Thread(target=llm_worker)
        thread.start()
        
        # Wait for completion or timeout
        while not completion_event.wait(timeout=SAMPLING_INTERVAL):
            if elapsed_time >= RETRY_TIME:
                monitoring_active.clear()
                print(f"Execution time exceeded {RETRY_TIME}s, initiating retry...")
                
                return Response(
                    body=json.dumps({
                        'status': 'Retry',
                        'message': f'Model ({current_model}) timed out after {elapsed_time:.1f}s. Doing retry.',
                        'response': {
                            'metadata': received_request_data['metadata'],
                            'content': {
                                **received_request_data['content'],
                                'ai_answer': f'STILL WAITING FOR AI ANSWER - Model ({current_model}) timed out after {elapsed_time:.1f}s. Retrying...'
                            }
                        }
                    }),
                    status_code=200,
                    headers=cors_headers
                )

        # Process completion
        if completion_event.is_set():
            if result['error']:
                raise result['error']
            response_json_object = result['response']
        
        # Clean up monitoring thread
        monitoring_active.clear()
        monitor_thread.join(timeout=1.0)

        print("\nPrinting JSON object with pretty_print_json_data...")
        pretty_print_json_data(response_json_object, print_values=True)

        print("\nWriting JSON to file...")
        json_prefix = 'qrag-exch_'
        json_file_path = '/tmp/' + json_prefix + get_current_datetime_filefriendly() + '.json'
        write_json_file_from_json_data(response_json_object, json_file_path, overwrite="yes")

        # Determine S3 path based on index name from response metadata
        metadata = response_json_object.get("metadata", {})
        vector_index_name = metadata.get("vector_index_name", "NOT_FOUND")
        if vector_index_name.startswith("deutsch"):
            s3_path = "s3-qrag-deutsch"
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



