# ===== START OF FILE deepgram-callback/app.py =====
# in AWS Chalice for Lambda Function

from chalice import Chalice, Response
import json
import boto3
import os
import time
from botocore.exceptions import NoCredentialsError

app = Chalice(app_name='deepgram-callback')

# Read the expected dg-token from environment variables
EXPECTED_DG_TOKEN = os.environ.get('DEEPGRAM_API_KEY_ID')

@app.route('/transcription', methods=['POST'])
def dg_callback_handle_transcription():
    print("deepgram-callback lambda func - last updated ")
    request = app.current_request
    try:
        # Extract the dg-token from the headers
        dg_token = request.headers.get('dg-token')
        if dg_token != EXPECTED_DG_TOKEN:
            # Unauthorized access
            return Response(
                body=json.dumps({'message': 'Unauthorized'}),
                status_code=401,
                headers={'Content-Type': 'application/json'}
            )

        transcription_data = request.json_body
        
        # Extract request_id from the transcription data if available
        request_id = transcription_data.get('metadata', {}).get('request_id', 'default_request_id')
        
        # Save the transcription data to S3
        if transcription_data:
            object_name = f"{request_id}.json"
            file_name = dg_callback_save_to_s3(transcription_data, object_name)
            if file_name:
                response_message = f"Received and saved transcription successfully as {file_name}"
                status_code = 200
            else:
                response_message = "Failed to save transcription to S3"
                status_code = 500
        else:
            response_message = "No data received"
            status_code = 400
            
    except Exception as e:
        print(f"Error processing transcription: {str(e)}")
        response_message = "Error processing transcription"
        status_code = 500

    return Response(
        body=json.dumps({'message': response_message}, indent=4),
        status_code=status_code,
        headers={'Content-Type': 'application/json'}
    )

def dg_callback_save_to_s3(transcription_data, object_name, bucket_name='fofpublic', s3_path='deepgram-transcriptions/'):
    s3_client = boto3.client('s3')
    
    if s3_path:
        object_name = f"{s3_path}{object_name}"

    try:
        # Stream the JSON directly to S3 without saving to disk
        s3_client.put_object(
            Bucket=bucket_name,
            Key=object_name,
            Body=json.dumps(transcription_data, indent=4),
            ContentType='application/json'
        )
        print(f"Uploaded {object_name} to {bucket_name}")
        return object_name

    except Exception as e:
        print("Error uploading to S3:", str(e))
        return None

# https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/transcription

# TO EXECUTE
# cd apps/transcription/api/deepgram-callback
# ../chalicelib_mirror_deploy.sh

# TO CURL TEST BASIC GET REQUEST
# expected {"hello":"world"}"
# curl https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api


# TO CURL TEST ENDPOINT DIRECTLY (NOT REAL)
# expected {"statusCode":200,"body":"\"Received transcription successfully\""}(.venv) RTMac23:deepgram-callback randytrue$ 
# curl --request POST \
#   --header "Content-Type: application/json" \
#   --data '{"sample_key": "sample_value"}' \
#   --url https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/transcription

# TO CURL TEST WITH REAL DEEPGRAM TRANSCRIPTION
# NOT WORKING (RT 5-3 0331) - {"err_code":"INVALID_AUTH","err_msg":"Invalid credentials."
# curl \
#   --request POST \
#   --header 'Authorization: Token DEEPGRAM_API_KEY' \
#   --header 'Content-Type: audio/mp3' \
#   --data-binary @'tests/test_data_files/transcribe/synthetic_audio.mp3' \
#   --url 'https://api.deepgram.com/v1/listen?callback=https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/transcription'

# ===== END OF FILE deepgram-callback/app.py =====
