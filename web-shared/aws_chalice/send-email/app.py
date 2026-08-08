# START OF FILE send-email/app.py
# in AWS Chalice for Lambda Function

from chalice import Chalice, Response
import boto3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import json
import base64
from chalicelib.aws import verify_jwt  # Add JWT verification import

app = Chalice(app_name='send-email')
app.api.cors = True

ses_client = boto3.client('ses')

# Replace the CORS_HEADERS constant with ALLOWED_ORIGINS
ALLOWED_ORIGINS = {
    'https://www.focusonfoundations.org',
    'https://focusonfoundations.org',
    'https://staging.focusonfoundations.org',
    'https://floodlamp-8c9d00d6ef3e90c375de806594d04.webflow.io',
    'http://localhost:4321',
}

@app.route('/send-email', methods=['POST'], cors=True)
def send_email():
    print("send-email lambda func - last updated 12-20 0719 with JWT verification")
    # Get the origin from the request
    request_origin = app.current_request.headers.get('origin', '')
    
    # Set the CORS headers based on the request origin
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
        request = app.current_request
        json_body = request.json_body

        to_address = json_body['to_address']
        email_subject = json_body['email_subject']
        from_address = json_body['from_address']
        email_body_plain = json_body.get('email_body_plain', '')
        email_body_html = json_body.get('email_body_html', '')
        attachments = json_body.get('attachments', [])

        # Create MIME message
        msg = MIMEMultipart('mixed')
        msg['Subject'] = email_subject
        msg['From'] = from_address
        msg['To'] = to_address

        # Create a MIME part for the email body
        if email_body_html:
            msg_alternative = MIMEMultipart('alternative')
            msg.attach(msg_alternative)
            part1 = MIMEText(email_body_plain, 'plain')
            part2 = MIMEText(email_body_html, 'html')
            msg_alternative.attach(part1)
            msg_alternative.attach(part2)
        else:
            part1 = MIMEText(email_body_plain, 'plain')
            msg.attach(part1)

        # Attach files
        for attachment in attachments:
            filename = attachment['filename']
            file_content = base64.b64decode(attachment['content'])
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(file_content)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={filename}')
            msg.attach(part)

        response = ses_client.send_raw_email(
            Source=msg['From'],
            Destinations=[msg['To']],
            RawMessage={
                'Data': msg.as_string()
            }
        )

        return Response(
            body=json.dumps({
                'status': 'Success',
                'message': 'Email sent successfully!'
            }),
            status_code=200,
            headers=cors_headers
        )

    except Exception as e:
        print("Error while processing request:", e)
        return Response(
            body=json.dumps({'error': str(e)}),
            status_code=500,
            headers=cors_headers
        )

# TO DEPLOY WITHOUT USING MIRROR SCRIPT WHICH IS NOT NECESARY
'''
cd /Users/randytrue/Documents/Code/corpus-tools/web-shared/aws_chalice/send-email
chalice deploy
'''

# API ENDPOINT: 
'''
  - LambdaARN: arn:aws:lambda:us-west-2:[AWS-ACCOUNT-ID]:function:send-email-dev
  - Rest API URL: https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/
'''

# TEST WITH CURL WITHOUT API KEY
# curl -X POST https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/send-email -H "Content-Type: application/json" -d '{"to_address": "[REDACTED-EMAIL]", "email_subject": "CURL TEST of Lambda Function with SES Email", "from_address": "randy@floodlamp.bio", "email_body_plain": "Here is the plain text content of the email with headings, bold, italics, and a link.", "email_body_html": "<h1>Heading Level 1</h1><h2>Heading Level 2</h2><p>This is a <strong>bold</strong> text and this is an <em>italic</em> text.</p><p>Here is a link to <a href=\"https://example.com\">example.com</a>.</p>"}'

# TEST WITH CURL WITH API KEY
# curl -X POST https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/send-email -H "Content-Type: application/json" -H "x-api-key: efgh2..." -d '{"to_address": "[REDACTED-EMAIL]", "email_subject": "CURL TEST of Lambda Function with SES Email", "from_address": "randy@floodlamp.bio", "email_body_plain": "Here is the plain text content of the email with headings, bold, italics, and a link.", "email_body_html": "<h1>Heading Level 1</h1><h2>Heading Level 2</h2><p>This is a <strong>bold</strong> text and this is an <em>italic</em> text.</p><p>Here is a link to <a href=\"https://example.com\">example.com</a>.</p>"}'

# TEST WITH CURL WITH JWT
# curl -X POST https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/send-email -H "Content-Type: application/json" -H "Authorization: Bearer eyJh..." -d '{"to_address": "[REDACTED-EMAIL]", "email_subject": "CURL TEST of Lambda Function with SES Email", "from_address": "randy@floodlamp.bio", "email_body_plain": "Here is the plain text content of the email with headings, bold, italics, and a link.", "email_body_html": "<h1>Heading Level 1</h1><h2>Heading Level 2</h2><p>This is a <strong>bold</strong> text and this is an <em>italic</em> text.</p><p>Here is a link to <a href=\"https://example.com\">example.com</a>.</p>"}'

# TO TEST 5XX ERRORS FOR CLOUDWATCH ALARM - ADD THIS BELOW DEF LINE
'''
    # Test error - remove after testing
    raise Exception("Test 5XX error")
'''

# END OF FILE send-email/app.py