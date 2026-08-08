# ===== START OF FILE hash-store/app.py =====
# file_path: web/aws_chalice/hash-store/app.py
# contains: python code for AWS Lambda Function 
#           deployed with Chalice using chalicelib_mirror_deploy.sh bash script

from chalice import Chalice, Response
import boto3
import csv
from io import StringIO
import tempfile
import os

from chalicelib.fileops import get_current_datetime_filefriendly
from chalicelib.aws import USERS_HMAC_SECRET_KEY, generate_hmac_hash, generate_jwt
from chalicelib.aws import upload_file_to_s3, get_s3_object


app = Chalice(app_name='hash-store')
app.api.cors = True

# Define allowed origins as a set
ALLOWED_ORIGINS = {
    'https://www.focusonfoundations.org',
    'https://focusonfoundations.org',
    'https://staging.focusonfoundations.org',
    'https://floodlamp-8c9d00d6ef3e90c375de806594d04.webflow.io',
    'http://localhost:3000',
    'http://localhost:4321',
}

# Add S3 client
s3 = boto3.client('s3')

@app.route('/hash-store', methods=['POST'], cors=True)
def handle_generate_hashes_and_store():
    print("hash-store lambda func - last updated 12-20-24 RT ")
    
    # Get the origin and set up CORS headers as before
    request_origin = app.current_request.headers.get('origin', '')
    cors_headers = {
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    }

    # Only add the origin if it's in our allowed list
    if request_origin in ALLOWED_ORIGINS:
        cors_headers['Access-Control-Allow-Origin'] = request_origin

    try:
        received_request_data = app.current_request.json_body
        print("Received request data:", received_request_data)
        
        # Extract required parameters
        key = received_request_data.get('key')
        s3_path = received_request_data.get('s3_path')
        user_nice_name = received_request_data.get('userNiceName')
        user_ip_address = received_request_data.get('userIPAddress')
        input_user_email = received_request_data.get('inputUserEmail', '')  # Default to empty string
        emailListSignupChecked = received_request_data.get('emailListSignupChecked')
        event_type = received_request_data.get('eventType', '')
        privacy_consent = received_request_data.get('privacyConsent', '')
        
        # Validate required fields - check if they exist in request, allow empty strings
        required_fields = {
            'key': key is not None,
            'userNiceName': user_nice_name is not None,
            'userIPAddress': user_ip_address is not None,
            'eventType': event_type is not None,
            'privacyConsent': privacy_consent is not None
        }
        
        missing_fields = [field for field, present in required_fields.items() if not present]
        if missing_fields:
            return Response(
                body={'error': f'Missing required parameters: {", ".join(missing_fields)}'},
                status_code=400,
                headers=cors_headers
            )

        # Ensure s3_path is at least an empty string
        s3_path = s3_path if s3_path is not None else ""

        # Use hardcoded bucket name
        bucket_name = '[S3-BUCKET]'

        # Check if file exists using get_s3_object
        existing_content = get_s3_object(bucket_name, key, s3_path, parse_json=False)
        if existing_content is None:
            return Response(
                body={'error': 'S3 file not found'},
                status_code=404,
                headers=cors_headers
            )

        # Generate hashes
        hashed_user_nice_name = generate_hmac_hash(user_nice_name, USERS_HMAC_SECRET_KEY)
        hashed_user_ip_address = generate_hmac_hash(user_ip_address, USERS_HMAC_SECRET_KEY)
        hashed_input_user_email = generate_hmac_hash(input_user_email, USERS_HMAC_SECRET_KEY)
        
        # Get current timestamp
        timestamp = get_current_datetime_filefriendly(location='America/Los_Angeles', include_utc=True)

        # Create a temporary file to store the CSV data
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.csv') as temp_file:
            csv_writer = csv.writer(temp_file)
            
            try:
                # Read existing CSV from S3
                response = s3.get_object(Bucket=bucket_name, Key=key)
                existing_csv = response['Body'].read().decode('utf-8')
                
                # Write header and existing content
                lines = existing_csv.splitlines()
                header = lines[0]
                temp_file.write(header + '\n')
                
                # Write new row with both original and hashed values
                new_row = [
                    timestamp,
                    user_nice_name,
                    hashed_user_nice_name,
                    user_ip_address,
                    hashed_user_ip_address,
                    input_user_email,
                    hashed_input_user_email,
                    emailListSignupChecked,
                    event_type,
                    privacy_consent
                ]
                csv_writer.writerow(new_row)
                
                # Write remaining rows
                for line in lines[1:]:
                    temp_file.write(line + '\n')
                    
            except Exception as e:
                print(f"Error processing CSV: {e}")
                return Response(
                    body={'error': 'Failed to process CSV file'},
                    status_code=500,
                    headers=cors_headers
                )

        # Upload the updated file back to S3
        try:
            upload_result = upload_file_to_s3(
                file_path=temp_file.name,
                bucket=bucket_name,
                object_name=key
            )
            
            if not upload_result:
                raise Exception("Failed to upload file to S3")
                
        finally:
            # Clean up temporary file
            os.unlink(temp_file.name)

        # Generate JWT token using the user's IP address
        jwt_token = generate_jwt(
            subject_claim=user_ip_address,
            expiry_days=30
        )

        # Return success response with hashed values and JWT
        return Response(
            body={
                'status': 'Success',
                'hashed_values': {
                    'hashedUserNiceName': hashed_user_nice_name,
                    'hashedUserIPAddress': hashed_user_ip_address,
                    'hashedInputUserEmail': hashed_input_user_email
                },
                'jwtToken': jwt_token  # Add JWT to response
            },
            status_code=200,
            headers=cors_headers
        )
    
    except Exception as e:
        print("Error while processing request:", e)
        return Response(body={'error': str(e)}, status_code=500, headers=cors_headers)

# TO REDEPLOY WITH MIRROR SCRIPT
'''
cd /Users/randytrue/Documents/Code/corpus-tools/web-shared/aws_chalice/hash-store
../chalicelib_mirror_deploy.sh
'''

#   - Lambda ARN: arn:aws:lambda:us-west-2:[AWS-ACCOUNT-ID]:function:hash-store-dev
#   - Rest API URL: https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/

# OLD ONE BEFORE GIT PROBLEM - Make sure doesn't work
#   - Rest API URL: https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/


# TEST WITH CURL WITHOUT API KEY
# curl -X POST https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/hash-store -H "Content-Type: application/json" -d '{"key": "user_hash_log_2024-12-09.csv", "s3_path": "", "userNiceName": "Curl Test User", "userIPAddress": "192.168.1.1", "inputUserEmail": "curl-test@example.com", "emailListSignupChecked": false, "eventType": "curl_test", "privacyConsent": "2024-12-17"}'

# TEST WITH CURL WITH API KEY  
# curl -X POST https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/hash-store -H "Content-Type: application/json" -H "x-api-key: Fhhs7..." -d '{"key": "user_hash_log_2024-12-17.csv", "s3_path": "", "userNiceName": "Curl Test User", "userIPAddress": "192.168.1.1", "inputUserEmail": "curl-test@example.com", "emailListSignupChecked": false, "eventType": "curl_test", "privacyConsent": "2024-12-17"}'


# TEST WITH PORTAL API GATEWAY (NOT IN LAMBDA FUNCTION VIEW)
# Headers:
'''
Content-Type:application/json
Origin:https://www.focusonfoundations.org
'''

# Request body:
'''
{
  "key": "user_hash_log_2024-12-09.csv",
  "s3_path": "",
  "userNiceName": "Portal Test User",
  "userIPAddress": "192.168.1.1",
  "inputUserEmail": "portal-test@example.com",
  "emailListSignupChecked": true,
  "eventType": "portal_test",
  "privacyConsent": "2024-12-17"
}
'''

# ===== END OF FILE hash-store/app.py =====


