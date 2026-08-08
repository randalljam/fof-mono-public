from chalice import Chalice, Response

from chalicelib.rag_bots import qrag_sim_routed, write_json_file_from_object, print_qrag_display_text 
from chalicelib.rag_prompts_routes import ROUTES_DICT_DEUTSCH_V3
from chalicelib.vectordb import generate_embedding  # leave in even through grayed out because it's called by pinecone_retreiver which is called by qrag_sim_routed
from chalicelib.aws_s3 import upload_file_to_s3
from chalicelib.fileops import get_current_datetime_filefriendly

app = Chalice(app_name='qrag-deutsch-v3')
app.api.cors = True  # Enable CORS for all routes

@app.route('/qrag', methods=['POST'], cors=True)
def qrag():

    # for fixed question test
    # qrag_object = qrag_sim_routed('What is a good explanation?',ROUTES_DICT_DEUTSCH_V1,'qragnospace')
    # return Response(body={'status': 'Success', 'message': qrag_object}, status_code=200)

    try:
        data = app.current_request.json_body
        print("Received request data:", data)  # Log incoming request data
        user_question = data.get('question')

        if not user_question:
            return Response(body={'error': 'No question provided'}, status_code=400)
        
        # Create a static debug response
        # static_response = {
        #     'user_question': 'This is a static user question for debug.',
        #     'route_preamble': 'This is a static route preamble for debug.',
        #     'quoted_qa': 'This is a static quoted QA for debug.',
        #     'ai_answer': 'This is a static AI answer for debug.'
        # }
        # print("Returning static debug JSON response...")
        # return Response(body={'status': 'Success', 'response': static_response}, status_code=200)

        # Define paths
        json_prefix = 'qrag-exch_'
        json_file_path = '/tmp/' + json_prefix + get_current_datetime_filefriendly() + '.json'
        
        # Call your custom multi-route retrieval augmented generation pipeline
        print("\nCalling qrag_sim_routed...")
        response_json_object = qrag_sim_routed(user_question, ROUTES_DICT_DEUTSCH_V3, 'deutsch-transcript-qrag')

        print("\nPrinting json object with print_qrag_display_text...")
        print_qrag_display_text(response_json_object)

        print("\nWriting JSON to file...")
        write_json_file_from_object(response_json_object, json_file_path)

        print("\nUploading JSON to S3...")
        upload_file_to_s3(json_file_path, bucket='[S3-BUCKET]', s3_path='s3-qrag-deutsch-v3')

        print("Returning JSON response...")
        return Response(body={'status': 'Success', 'response': response_json_object}, status_code=200)
    
    except Exception as e:
        print("Error while processing request:", e)  # Log any exceptions
        return Response(body={'error': str(e)}, status_code=500)

# TO UPDATE
# cd /Users/randytrue/Documents/Code/corpus-tools/web/aws_chalice/qrag-deutsch-v3
# ../chalicelib_mirror_deploy.sh

# API ENDPOINT: https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/qrag

# TEST WITH CURL
# curl -X POST https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/qrag -H "Content-Type: application/json" -d '{"question": "What do you think about using curl commands to test AWS lambda functions?"}'

# TEST WITH PORTAL API GATEWAY (NOT IN LAMBDA FUNCTION VIEW)
# Headers:
'''
Content-Type:application/json
'''

# Request body:
'''
{
  "question": "Is this working from thew Portal API Gateway Test tab"
}
'''
