# ===== START OF FILE hmac-hash/app.py =====
# file_path: web/aws_chalice/hmac-hash/app.py
# contains: python code for AWS Lambda Function 
#           deployed with Chalice using chalicelib_mirror_deploy.sh bash script

import sys
import os
from chalice import Chalice, Response, CORSConfig
from chalicelib.aws import USERS_HMAC_SECRET_KEY, generate_hmac_hash


# Define allowed origins as a list (previously it was a set but o1-pro suggested list)
CORS_ALLOWED_ORIGINS = [
    'https://www.focusonfoundations.org',
    'https://floodlamp-8c9d00d6ef3e90c375de806594d04.webflow.io',
    'http://localhost:3000'
]

cors_config = CORSConfig(
    allow_origin=CORS_ALLOWED_ORIGINS,
    allow_headers=['Content-Type', 'Authorization'],
    max_age=None,              # Optional: how long the browser can cache preflight responses
    expose_headers=None,       # Optional: which headers can be exposed to the browser
    allow_credentials=False    # Optional: set True if you need cookies/credentials
)

app = Chalice(app_name='hmac-hash')
app.api.cors = cors_config

@app.route('/generate-hash', methods=['POST'], cors=True)
def handle_generate_hash():
    print("hmac-hash lambda func")
    print("last updated: 4-3 1136 dev test - was 4-2 0602 script updates mid fixing CORS config (last non-test change 12-20-24 RT removed API key)")
    
    try:
        received_request_data = app.current_request.json_body
        print("Received request data:", received_request_data)
        
        # Extract input text from the request
        input_text = received_request_data.get('input_text')

        if not input_text:
            return Response(body={'error': 'Missing input_text parameter'}, status_code=400)
        
        # Generate HMAC hash
        hash_string = generate_hmac_hash(input_text, USERS_HMAC_SECRET_KEY)

        print("Returning JSON response...")
        return Response(body={'status': 'Success', 'hash': hash_string}, status_code=200)
    
    except Exception as e:
        print("Error while processing request:", e)
        return Response(body={'error': str(e)}, status_code=500)

# TO REDEPLOY WITH MIRROR SCRIPT
'''
cd /Users/randytrue/Documents/Code/corpus-tools/web/aws_chalice/hmac-hash
../chalicelib_mirror_deploy.sh
../chalicelib_mirror_deploy.sh prod
'''

# TEST WITH CURL WITHOUT API KEY
# curl -X POST https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/generate-hash -H "Content-Type: application/json" -d '{"input_text": "test@example.com"}'

# TEST WITH CURL WITH API KEY
# curl -X POST https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/generate-hash -H "Content-Type: application/json" -H "x-api-key: bfua9..." -d '{"input_text": "test@example.com"}'

'''
# Test with allowed origin
curl -v -X POST https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/dev/generate-hash \
  -H "Content-Type: application/json" \
  -H "Origin: https://www.focusonfoundations.org" \
  -d '{"input_text": "test@example.com"}'

# Test with disallowed origin
curl -v -X POST https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/dev/generate-hash \
  -H "Content-Type: application/json" \
  -H "Origin: https://example.com" \
  -d '{"input_text": "test@example.com"}'
'''

# TEST WITH PORTAL API GATEWAY (NOT IN LAMBDA FUNCTION VIEW)
# Headers:
'''
Content-Type:application/json
Origin:https://www.focusonfoundations.org
'''

# Request body:
'''
{
  "input_text": "test@example.com"
}
'''

# ===== END OF FILE hmac-hash/app.py =====
