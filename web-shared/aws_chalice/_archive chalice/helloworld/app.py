from chalice import Chalice

app = Chalice(app_name='helloworld')
app.api.cors = True  # Enable CORS for all routes

@app.route('/')
def index():
    return {'message': 'Hello Sat User! This is from AWS Lambda function, using Chalice. It is the helloworld app using a GET method'}

# TO EXECUTE
# cd bot_prod/aws_chalice/helloworld
# chalice deploy

# The view function above will return {"...": "..."}
# whenever you make an HTTP GET request to '/'.
#
# Here are a few more examples:
#
# @app.route('/hello/{name}')
# def hello_name(name):
#    # '/hello/james' -> {"hello": "james"}
#    return {'hello': name}
#
# @app.route('/users', methods=['POST'])
# def create_user():
#     # This is the JSON body the user sent in their POST request.
#     user_as_json = app.current_request.json_body
#     # We'll echo the json body back to the user in a 'user' key.
#     return {'user': user_as_json}
#
# See the README documentation for more examples.
#
