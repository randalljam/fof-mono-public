# Mon 4-8 simple from chatgpt response on 4-7 after pasting stackoverflow thread
# AWS LAMBDA FUNCTION CODE
exports.handler = async (event) => {
    return {
        statusCode: 200,
        headers: {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*", // Adjust according to your CORS policy
        },
        body: JSON.stringify({ message: "Mon 4-8 Simple Hello from Lambda!" }),
    };
};

# WEBFLOW CUSTOM CODE


# version Sun Apr 7 618pm
import json

def lambda_handler(event, context):
    # Parse the request body from the event
    try:
        body = json.loads(event.get('body', '{}'))
        user_message = body.get('message')
    except (KeyError, TypeError, ValueError):
        # Return a 400 error if something goes wrong with parsing the message
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': 'https://www.floodlamp.bio'
            },
            'body': json.dumps({'error': 'Bad request'})
        }
    
    if not user_message:
        # No message provided
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': 'https://www.floodlamp.bio'
            },
            'body': json.dumps({'error': 'No message provided'})
        }
    
    # Process the message (in this case, just echoing it back)
    response_message = f"Look DSP! I'm running a AWS Lambda function. You said '{user_message}'"
    
    # Return a 200 response with the processed message
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': 'https://www.floodlamp.bio'
        },
        'body': json.dumps({'response': response_message})
    }


# initial version
import json

def lambda_handler(event, context):
    # Parse the request body from the event
    try:
        body = json.loads(event['body'])
        user_message = body.get('message')
    except (KeyError, TypeError, ValueError):
        # Return a 400 error if something goes wrong with parsing the message
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Bad request'})
        }
    
    if not user_message:
        # No message provided
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'No message provided'})
        }
    
    # Process the message (in this case, just echoing it back)
    response_message = f"Look DSP! I'm running a AWS Lambda function. You said '{user_message}'"
    
    # Return a 200 response with the processed message
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'response': response_message})
    }
