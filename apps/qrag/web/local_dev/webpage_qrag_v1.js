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

function displayHTMLResponse(htmlContent, sender) {
    var messagesArea = document.getElementById('messagesArea');
    var messageElement = document.createElement('div');
    messageElement.innerHTML = htmlContent; // Set innerHTML to display HTML content
    messageElement.className = sender; // Use this to style messages differently based on the sender
    messagesArea.appendChild(messageElement);
}

// Function to submit user input and display response
function submitInput() {
    var userInput = document.getElementById('userInput').value;
    fetch('http://127.0.0.1:5000/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({question: userInput})  // Update key to question
    })
    .then(response => response.json())
    .then(data => {
        if (data.status) {
            displayHTMLResponse(data.status, 'bot'); // Display status response from the API
        } else if (data.error) {
            displayMessage(data.error, 'bot'); // Display error message
        } else {
            displayMessage('No response received.', 'bot');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        displayMessage('Sorry, there was an error in the reply-bot submit user input.', 'bot');
    });
    document.getElementById('userInput').value = ''; // Clear input field after sending
}

// Optional: Automatically call getHelloworldMessage when the page loads and setup submit button event listener
document.addEventListener("DOMContentLoaded", function() {
    displayMessage('This is the JavaScript file load message - running local dev from file path: webpage_qrag_loc.js', 'bot');
    // getHelloworldMessage();
    var submitButton = document.getElementById('submitButton');
    submitButton.addEventListener('click', submitInput);

    // Clear the content of the fields just in the browser but does not change the actual html file which will still have text in those fields that will show on reload
    var clearButton = document.getElementById('clearButton');
    clearButton.addEventListener('click', function() {
        document.getElementById('userQuestion').textContent = '';
        document.getElementById('routePreamble').textContent = '';
        document.getElementById('quotedQA').textContent = '';
        document.getElementById('aiAnswer').textContent = '';
    });
});

