from flask import Flask, request, jsonify  # pip install Flask
from flask_cors import CORS  # pip install -U flask-cors


app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Dummy function to simulate your chatbot's message processing
def process_message(message):
    # Here, you'd include the logic of your chatbot
    # For demonstration, it simply echoes the message
    return f"Look Ma! I'm running a local Flask python server thingymajig. You said '{message}'"

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json  # Assuming the message is sent as JSON
    user_message = data.get('message')
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    response = process_message(user_message)
    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(debug=True)
    #app.run(debug=True, host='0.0.0.0')  # added to try getting the server working on local network

