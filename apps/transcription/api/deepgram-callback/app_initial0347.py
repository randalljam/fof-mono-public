from chalice import Chalice
import json

from config import DEEPGRAM_API_KEY

app = Chalice(app_name='deepgram-callback')

@app.route('/')
def index():
    return {'hello': 'world'}

@app.route('/transcription', methods=['POST'])
def handle_transcription():
    # Retrieve the JSON data sent with the POST request
    request = app.current_request
    transcription_data = request.json_body

    # Log the received transcription data
    print("Received transcription data: ", json.dumps(transcription_data, indent=2))

    # Here you can process the transcription data as needed

    # Respond that the transcription was received successfully
    return {
        'statusCode': 200,
        'body': json.dumps('Received transcription successfully')
    }

# TO EXECUTE
# cd apps/transcription/api/deepgram-callback
# chalice deploy

# TO CURL TEST ENDPOINT DIRECTLY (NOT REAL)
# curl --request POST \
# >   --header "Content-Type: application/json" \
# >   --data '{"sample_key": "sample_value"}' \
# >   --url https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/transcription
# {"statusCode":200,"body":"\"Received transcription successfully\""}(.venv) RTMac23:deepgram-callback randytrue$ 

# TO CURL TEST WITH REAL DEEPGRAM TRANSCRIPTION
# NOT WORKING (RT 5-3 0331) - {"err_code":"INVALID_AUTH","err_msg":"Invalid credentials."
# curl \
#   --request POST \
#   --header 'Authorization: Token DEEPGRAM_API_KEY' \
#   --header 'Content-Type: audio/mp3' \
#   --data-binary @'tests/test_data_files/transcribe/synthetic_audio.mp3' \
#   --url 'https://api.deepgram.com/v1/listen?callback=https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/transcription'
