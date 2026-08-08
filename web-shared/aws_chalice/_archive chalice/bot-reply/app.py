from chalice import Chalice, Response
import markdown2

app = Chalice(app_name='bot-reply')
app.api.cors = True  # Enable CORS for all routes


@app.route('/reply', methods=['POST'], cors=True)
def reply_static():
    data = app.current_request.json_body  # Get JSON data from request
    user_message = data.get('message')
    
    if not user_message:
        return Response(body={'error': 'No message provided'},
                        status_code=400,
                        headers={'Content-Type': 'application/json'})

    # Processing the user message
    response_message = f"Look TL! This is from AWS Lambda function, using Chalice. It is the bot-reply app using a POST method. You said: {user_message}"
    
    md_sample = f"""
    ## Sample Heading Two
    This is some AMAZING sample text under heading two.

    ### Sample Heading Three
    This is some additional text under heading three.
    You said: {user_message}
    """
    html_response = markdown2.markdown(md_sample)
    #return {'response': html_response}
    return {'response': response_message}

# TO EXECUTE
# cd /Users/randytrue/Documents/Code/corpus-tools/web/aws_chalice/bot-reply
# chalice deploy

# CURL TEST - THIS IS WORKING!
# curl -X POST https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/reply -H "Content-Type: application/json" -d '{"message": "hello from curl Test of bot-reply"}'


# TEST WITH PORTAL API GATEWAY
# Headers:
# Content-Type:application/json

# Request body:
# {
#   "message": "test message from API Gateway"
# }
