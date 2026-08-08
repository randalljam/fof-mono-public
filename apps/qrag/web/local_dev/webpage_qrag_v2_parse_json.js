// JavaScript file for local-dev that is called from index.html
// Load message at the bottom

// Function to fetch a static message from the helloworld API and display it
function getHelloworldMessage() {
    // Use the endpoint URL from the helloworld API Gateway
    fetch('https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api', { 
        method: 'GET', // Assuming the Chalice function is accessible via GET
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        // Assuming the API returns {"message": "Hello World or other text"}
        displayMessage(data.message, 'bot');
    })
    .catch(error => {
        console.error('Error:', error);
        displayMessage('Sorry, there was an error in helloworld.', 'bot');
    });
}

// Function to display the message in the 'messagesArea' element
function displayMessage(message, sender) {
    var messagesArea = document.getElementById('messagesArea');
    var messageElement = document.createElement('div');
    messageElement.textContent = message;
    messageElement.className = sender; // Use this to style messages differently based on the sender
    messagesArea.appendChild(messageElement);
}

function displayParsedJSON(response) {
    console.log("Displaying parsed JSON:", response);
    if (response.content)
        document.getElementById('displayUserQuestion').innerHTML = response.content.user_question.replace(/\n/g, '<br>')  || 'No user question';
        document.getElementById('displayRoutePreamble').innerHTML = response.content.route_preamble.replace(/\n/g, '<br>') || 'No Route Preamble';
        document.getElementById('displayQuotedQA').innerHTML = response.content.quoted_qa.replace(/\n/g, '<br>') || 'No Quoted QA';
        document.getElementById('displayAiAnswer').innerHTML = response.content.ai_answer.replace(/\n/g, '<br>') || 'No AI Answer';
}

function submitInput() {
    var userInput = document.getElementById('userInput').value;
    console.log("Submitting input:", userInput);
    fetch('https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/qrag', {
    //fetch('http://127.0.0.1:5000/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({question: userInput})
    })
    .then(response => {
        console.log("Fetch response status:", response.status); // Log response status
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log("Received data:", data); // Log the parsed JSON data
        if (data.status) {
            displayParsedJSON(data.response); // Parse and display the JSON response
        } else if (data.error) {
            displayMessage(data.error, 'bot');
        } else {
            displayMessage('No response received.', 'bot');
        }
    })
    .catch(error => {
        console.error('Fetch error:', error); // Log any errors in the catch block
        displayMessage('Sorry, there was an error in the user input.', 'bot');
    });
    document.getElementById('userInput').value = ''; // Clear input field after sending
}

document.addEventListener("DOMContentLoaded", function() {
    console.log('JavaScript file webpage_qrag_v2_parse_json.js loaded');
    displayMessage('This is the JavaScript file load message - running local dev from file path: webpage_qrag_v2_parse_json.js', 'bot');
    var submitButton = document.getElementById('submitButton');
    submitButton.addEventListener('click', submitInput);

    var clearButton = document.getElementById('clearButton');
    clearButton.addEventListener('click', function() {
        document.getElementById('displayUserQuestion').textContent = '';
        document.getElementById('displayRoutePreamble').textContent = '';
        document.getElementById('displayQuotedQA').textContent = '';
        document.getElementById('displayAiAnswer').textContent = '';
    });
});



