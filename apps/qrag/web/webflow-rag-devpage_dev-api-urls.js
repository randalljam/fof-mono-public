// ========= START OF FILE web/webflow-rag-devpage.js =========
// deploy: copy to all QRAG pages > Settings > Custom Code > Body section between script tags
// contains: Core RAG functionality for Q&A interface, including user input handling,
//           API calls to AWS Lambda endpoints, dynamic UI updates, 
//           markdown processing, and sharing features (download/email)

var fileInfo = 'webflow-rag-devpage_dev-api-urls.js  2026-03-21 update to dev API URLs';
const showEmailListSignup = true;  // Set this to true to enable the email list signup option

const QRAG_ROUTING_API_URL = 'https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/qrag-routing';
const QRAG_LLM_API_URL = 'https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/qrag-llm';
const VRAG_LLM_API_URL = 'https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/vrag-llm';

// Moved buttonParamsMapping to webflow-fof-site-body.js 9-23-25

document.addEventListener("DOMContentLoaded", function() {
    console.log('Loading JavaScript for Page Body: ', fileInfo);

    // Use Webflow's push method to run code after the page and Webflow scripts have loaded
    window.Webflow.push(function () {
        console.log('Webflow scripts have loaded.');
    });

    // Check for user email and hash in session storage
    console.log('Current sessionStorage on RAG page load:');
    consoleLogSessionStorage();

    initializeDynamicIdAssignments();

    document.querySelectorAll('[id^="inputText_"], [id^="submitButton_"]').forEach(element => {
        if (element.tagName.toLowerCase() === 'textarea') {
            element.addEventListener('keydown', function(event) {
                if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault(); // Prevent the default newline behavior
                    const trailingId = getElementIDTrailingString(element.id);
                    const buttonId = `submitButton_${trailingId}`;
                    const buttonElement = document.getElementById(buttonId);
                    if (buttonElement) {
                        console.log('Enter pressed, triggering button click for:', buttonId);
                        buttonElement.click(); // Trigger the button click associated with this textarea
                    } else {
                        console.error('Button not found for ID:', buttonId);
                    }
                }
            });
        } else if (element.tagName.toLowerCase() === 'button') {
            element.addEventListener('click', function(event) {
                console.log(`Click event on element with ID ${event.target.id}`);
                console.log(`Event currentTarget ID: ${event.currentTarget.id}`);
                try {
                    submitInputRag(event); // Pass the event directly
                } catch (error) {
                    console.error('Error in submitInputRag:', error);
                }
                this.blur(); // Add this line to remove focus after click
            });
        }
    });

    // Flag to control validation on blur
    const validateOnBlur = false;
    document.querySelectorAll('[id^="inputText_"]').forEach(textarea => {
        // Add blur event handler for validation only if enabled
        if (validateOnBlur) {
            textarea.addEventListener('blur', function() {
                const questionCheck = validateAndSanitizeInput(
                    this.value, 
                    maxQuestionLength, 
                    'Question',
                    'INPUT_TYPE_PARAGRAPH'
                );
                
                // Update textarea with sanitized value if valid
                if (questionCheck.success) {
                    this.value = questionCheck.value;
                }
                
                // Show any messages
                if (questionCheck.messages.length > 0) {
                    const trailingId = getElementIDTrailingString(this.id);
                    const errorId = `submitError_${trailingId}`;
                    const errorElement = document.getElementById(errorId);
                    if (errorElement) {
                        errorElement.style.display = 'block';
                        errorElement.innerHTML = questionCheck.messages.join(' ');
                        setTimeout(() => { 
                            errorElement.style.display = 'none'; 
                        }, 3000);
                    }
                }
            });
        }
    });
});


//// DYNAMIC ELEMENT ID ASSIGNMENTS
function initializeDynamicIdAssignments() {
    const botContainers = document.querySelectorAll('.w-layout-blockcontainer.bot-container.w-container'); // Use a class that wraps your bot containers

    botContainers.forEach((botContainer) => {
        // Print the ID of each container to the console
        console.log(`Selected Container ID: ${botContainer.id}`);
        assignUserInputContainerIds(botContainer);
        // Add calls to other ID assignment functions for different components here if needed
    });
}

// Adjusts the textarea height based on its content with configurable max rows and line height
function adjustTextareaHeight(textarea, maxRows, lineHeight) {
    textarea.style.height = ''; // Reset height to shrink if text is deleted
    const scrollHeight = textarea.scrollHeight;
    const maxHeight = lineHeight * maxRows;
    if (scrollHeight > maxHeight) {
        textarea.style.height = maxHeight + 'px';
        textarea.style.overflowY = 'auto'; // Enable scrolling
    } else {
        textarea.style.height = scrollHeight + 'px';
        textarea.style.overflowY = 'hidden'; // Hide scrollbar when not needed
    }
}

// Helper function to assign IDs to user input components including the icon within the button and an error display element
function assignUserInputContainerIds(botContainer) {
    const userInputContainer = botContainer.querySelector('.qrag-input-component');
    if (!userInputContainer) {
        console.error('User input container not found in bot container:', botContainer.id);
        return;
    }

    const textarea = userInputContainer.querySelector('.botsubmit-textarea');
    const button = userInputContainer.querySelector('.botsubmit-button');
    const icon = button?.querySelector('.botsubmit-button-icon');
    const error = userInputContainer.querySelector('.botsubmit-error');

    const trailingIdString = getElementIDTrailingString(botContainer.id);

    if (trailingIdString) {
        textarea.id = `inputText_${trailingIdString}`;
        button.id = `submitButton_${trailingIdString}`;
        if (icon) icon.id = `submitIcon_${trailingIdString}`;
        if (error) error.id = `submitError_${trailingIdString}`;
        
        console.log(`  - Assigned User Input ContainerIDs: ${textarea.id}, ${button.id}, ${icon ? icon.id : 'icon missing'}, ${error ? error.id : 'error missing'}`);
    
        // Add event listener for resizing the textarea
        textarea.addEventListener('input', function() {
            adjustTextareaHeight(textarea, 8, 20);
        });
    
        // Validate the newly assigned button ID
        validateButtonIdInParamsMapping(button.id);
    } else {
        console.error('Failed to get trailing ID string for:', botContainer.id);
    }
}

function initializeNumChunksComponent(component) {  // Don't think this is used
    if (!component) return;

    const buttons = component.querySelectorAll('button');
    let selectedButton = null;

    buttons.forEach(button => {
        button.addEventListener('click', function() {
            if (selectedButton) {
                selectedButton.classList.remove('selected');
            }
            this.classList.add('selected');
            selectedButton = this;
            window.numChunks = parseInt(this.textContent, 10);
            console.log('Number of chunks set to:', window.numChunks);
        });
    });

    // Set default selection
    const defaultButton = buttons[1]; // Selecting the second button as default (need to coordinate with value which is currently 10)
    if (defaultButton) {
        defaultButton.click();
    }
}

function validateButtonIdInParamsMapping(buttonId) {
    const validButtonIds = Object.keys(buttonParamsMapping);
    // console.log(`DEBUG Validating button ID by looking for '${buttonId}' in list from mapping:`, validButtonIds);
    if (!buttonParamsMapping.hasOwnProperty(buttonId)) {
        const trailingId = getElementIDTrailingString(buttonId);
        const errorId = `submitError_${trailingId}`;
        const errorContainer = document.getElementById(errorId);
        if (errorContainer) {
            errorContainer.style.display = 'block';
            errorContainer.innerHTML = `This functionality is disabled - contact support at our domain for assistance.`;
            console.error(`Configuration Error: No parameters found for dynamically generated button ID: ${buttonId}`);
        } else {
            console.error(`Error display element not found for ID: ${errorId}`);
        }
    } else {
        const ragFunctionNames = buttonParamsMapping[buttonId].ragFunction.split(',').map(func => func.trim());
        const allFunctionsExist = ragFunctionNames.every(funcName => typeof window[funcName] === 'function');
        const allFunctionsValid = ragFunctionNames.every(funcName => funcName !== '');

        if (allFunctionsExist && allFunctionsValid) {
            console.log(`Validation of button ID passes for ${buttonId} found in buttonParamsMapping, all rag functions are valid.`);
        } else {
            console.error(`Mapping Validation Error: One or more functions specified for ${buttonId} do not exist or are empty.`);
        }
    }
}

// Utility function to get trailing string from an element ID after the first underscore
function getElementIDTrailingString(elementId) {
    const underscoreIndex = elementId.indexOf('_');
    if (underscoreIndex === -1 || underscoreIndex === elementId.length - 1) {
        console.error('Invalid element ID format:', elementId);
        return null;
    }
    return elementId.substring(underscoreIndex + 1);
}

function checkBotElementsExist(submitButtonId) {
    const submitButton = document.getElementById(submitButtonId);
    if (!submitButton) {
        console.error("checkBotElementsExist - Submit button not found.");
        return false;
    }

    let botContainer = submitButton.closest('.bot-container');
    if (!botContainer) {
        console.error("checkBotElementsExist - Bot container not found.");
        return false;
    }

    let accordionContainer = botContainer.querySelector('.accordion-container');
    if (!accordionContainer) {
        console.error("checkBotElementsExist - Accordion container not found.");
        return false;
    }

    let accordionCard = accordionContainer.querySelector('.accordion-card');
    if (!accordionCard) {
        console.error("checkBotElementsExist - Accordion card not found.");
        return false;
    }

    return true;
}

//// CORE FUNCTIONS
function getBotContainerFromSubmitButtonId(submitButtonId) {
    // Use dynamically assigned ID to access the bot container directly
    const trailingIdString = getElementIDTrailingString(submitButtonId);
    return document.getElementById(`container_${trailingIdString}`);
}

function submitInputRag(event) {
    event.preventDefault(); 

    // Add consent check at the start
    if (!checkPrivacyConsent()) {
        showConsentError();
        return false;
    }

    // Add nicename check right after consent check
    const userNiceName = sessionStorage.getItem('userNiceName');
    if (!userNiceName) {
        const errorElement = document.querySelector('.botsubmit-error');
        if (errorElement) {
            errorElement.style.display = 'block';
            errorElement.innerHTML = 'Please enter your name before submitting a question.';
            setTimeout(() => { errorElement.style.display = 'none'; }, 3000);
        }
        return false;
    }

    const submitButtonId = event.currentTarget.id;
    const trailingId = getElementIDTrailingString(submitButtonId);
    const userInputId = `inputText_${trailingId}`;
    const submitIconId = `submitIcon_${trailingId}`;
    const errorId = `submitError_${trailingId}`;
    const errorElement = document.getElementById(errorId);

    // Validate question from textarea
    const userInputField = document.getElementById(userInputId);
    const rawUserQuestion = userInputField.value;
    let questionCheck = validateAndSanitizeInput(rawUserQuestion, maxQuestionLength, 'Question', 'INPUT_TYPE_PARAGRAPH');
    
    // If validation succeeded but characters were removed, show info message but continue
    if (questionCheck.success && questionCheck.messages.length > 0) {
        try {
            displayTempMessage(questionCheck.messages.join(' '), 'info', 3000, document.getElementById(submitButtonId));
        } catch (error) {
            console.warn('Failed to display message about removed characters:', error);
            // Continue with submission even if message display fails
        }
    } else if (!questionCheck.success) {
        // Only stop submission if validation actually failed
        if (errorElement) {
            errorElement.style.display = 'block';
            errorElement.innerHTML = questionCheck.messages.join(' ');
            setTimeout(() => { errorElement.style.display = 'none'; }, 3000);
        }
        // Preserve the invalid input in the textarea
        userInputField.value = rawUserQuestion;
        return;
    }

    // Continue with the rest of the submission...
    const sanitizedQuestion = questionCheck.value;

    // Get num_chunks value using the global function
    const numChunksValue = window.getSelectedNumChunksValue ? window.getSelectedNumChunksValue() : undefined;
    const numChunksInteger = numChunksValue !== undefined ? parseInt(numChunksValue, 10) : undefined;
    
    // Get user hash from session storage
    const userEmailHmacHash = sessionStorage.getItem('userEmailHmacHash') || 'NA';

    // Change button text and color to indicate processing
    var submitButton = document.getElementById(submitButtonId);
    var submitIcon = document.getElementById(submitIconId);
    setButtonToStopState(submitButton, submitIcon);

    // Show info messages if any transformations were applied to question only
    if (questionCheck.messages.length > 0) {
        displayTempMessage(questionCheck.messages.join(' '), 'info', 3000, submitButton);
    }

    // Determine which RAG function(s) to call based on the button ID
    const params = buttonParamsMapping[submitButtonId];
    const ragFunctions = params.ragFunction.split(',').map(func => func.trim());
    const numberOfRagFunctions = ragFunctions.length;

    // Call the first RAG function dynamically with sanitized question
    const firstRagFunction = ragFunctions[0];
    window[firstRagFunction](
        sanitizedQuestion,
        params.vector_index_name,
        params.route_dict_name,
        numChunksInteger,
        userEmailHmacHash,  // Pass the user email hash as a user_id
        getUserContext()  // Encapsulate user-related data - currently the 3 hashed items (see getUserContext in site-body.js)
    )
    .then(firstJsonData => {
        console.log("submitInputRag - Received firstRagFunction json data:", firstJsonData);
        if (params.displayType === 'quoted-qa-then-ai-answer') {
            createAccordionItem(firstJsonData, submitButtonId);
        }
        if (numberOfRagFunctions === 2) {
            const secondRagFunction = ragFunctions[1];
            return window[secondRagFunction](firstJsonData, params.large_context_filename);
        } else {
            return firstJsonData; // For VRAG, we only have one function call
        }
    })
    .then(finalJsonData => {
        console.log("submitInputRag - Received final json data:", finalJsonData);
        
        // Handle both success and error cases
        if (finalJsonData.status === 'Error') {
            // Show error message at the top (permanently)
            if (errorElement) {
                errorElement.style.display = 'block';
                errorElement.innerHTML = finalJsonData.message;
            }
            // Use the response object which contains the content
            replaceAccordionItem(finalJsonData.response, submitButtonId);
        } else {
            // On success, show scroll message and update accordion
            if (errorElement) {
                errorElement.style.display = 'block';
                errorElement.innerHTML = '✨ AI answer ready - scroll down to view ✨';
            }
            // For success case, finalJsonData is already the response object
            replaceAccordionItem(finalJsonData, submitButtonId);
        }
    })
    .catch(error => {
        console.error('submitInputRag - Fetch error:', error);
        logErrorToMonitoring(error, 'qrag-routing API call');

        // Show appropriate error message to user
        if (errorElement) {
            let errorMessage = 'Apologies - an error occurred. We have been notified and will look into it. Please try again later or email contact@focusonfoundations.org if you would like to be notified when it is fixed.';
            
            errorElement.style.display = 'block';
            errorElement.innerHTML = errorMessage;
            
            // Hide error message after 10 seconds
            setTimeout(() => {
                errorElement.style.display = 'none';
            }, 10000);
        }

        // Preserve the user's input
        const userInputField = document.getElementById(userInputId);
        if (userInputField) {
            userInputField.value = rawUserQuestion;
        }
    })
    .finally(() => {
        resetButtonToInitialState(submitButton, submitIcon);
        const userInputField = document.getElementById(userInputId);

        // Reset the input field and button to initial state
        userInputField.value = ''; // Clear input field after sending
        
        // Temporarily reset the textarea height to a single line
        adjustTextareaHeight(userInputField, 1, 20);

        // Ensure the textarea can expand again on user input
        userInputField.style.height = ''; // Clear any inline height style
        adjustTextareaHeight(userInputField, 8, 20); // Reapply the initial maxRows setting
    });
}

// returns the routing json data if api call returns success
// processing start_date/end_date inside function instead of passing as parameters
function qragRouting(userInput, vector_index_name, route_dict_name, numChunksValue, userEmailHmacHash, userContext) {
    const errorElement = document.querySelector('.botsubmit-error');
    
    // Early return with error display if input is empty
    if (!userInput || userInput.trim() === '') {
        if (errorElement) {
            errorElement.textContent = 'Please enter a question before submitting.';
            errorElement.style.display = 'block';
            setTimeout(() => { errorElement.style.display = 'none'; }, 3000);
        }
        console.error('Empty input submitted');
        return;
    }

    // Continue with normal function flow...
    console.log("qrag-routing - Calling Lambda function with userInput:", userInput);
    console.log("   route_dict_name:", route_dict_name, "vector_index_name:", vector_index_name, "numChunksValue:", numChunksValue);
    console.log("   userEmailHmacHash as user_id:", userEmailHmacHash);
    console.log("   userContext:", userContext);

    // Get date values from sessionStorage
    const startDate = sessionStorage.getItem('qrag-start-date');
    const endDate = sessionStorage.getItem('qrag-end-date');
    
    console.log("   startDate:", startDate, "endDate:", endDate);

    // Validate that either both dates are present or neither is present
    if ((startDate && !endDate) || (!startDate && endDate)) {
        const errorMessage = 'Invalid date range: both start and end dates must be provided together';
        console.error(errorMessage);
        throw new Error(errorMessage);
    }

    // Create the base request body
    let requestBody = { 
        user_question: userInput, 
        vector_index_name: vector_index_name,
        num_chunks: numChunksValue,
        route_dict_name: route_dict_name,
        user_id: userEmailHmacHash,  // Pass the user email hash as a user_id
        ...userContext  // Spread the user context object into the request body
    };

    // Only add start_date/end_date if both dates are present
    if (startDate && endDate) {
        requestBody.start_date = startDate;
        requestBody.end_date = endDate;
    }

    console.log("qrag-routing - Full request body:", requestBody);

    return fetch(QRAG_ROUTING_API_URL, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(requestBody)
    })
    .then(httpResponse => {
        if (!httpResponse.ok) {
            const errorMessage = `qrag-routing - API Error (${httpResponse.status}): ${httpResponse.statusText}`;
            console.error(errorMessage);
            throw new Error(errorMessage);
        }
        return httpResponse.json();
    })
    .then(apiResponse => {
        console.log("qrag-routing - Received API Response:", apiResponse);
        if (!apiResponse.response) {
            throw new Error('qrag-routing - No data in API Response');
        }
        return apiResponse.response;
    });
}

// returns the complete json data if api call returns success
const MAX_QRAG_LLM_RETRIES = 3;
function qragLLM(routingJsonData, large_context_filename) {
    console.log("qrag-llm - Calling Lambda function with routing JSON data:", routingJsonData);
    console.log("qrag-llm - Using large context filename:", large_context_filename);

    // Initialize metadata if it doesn't exist
    if (!routingJsonData.metadata) {
        routingJsonData.metadata = {};
    }

    // Initialize retry count if not set
    if (routingJsonData.metadata.retry_count === undefined) {
        routingJsonData.metadata.retry_count = 0;
    }

    // Set is_retry based on retry count
    routingJsonData.metadata.is_retry = routingJsonData.metadata.retry_count > 0;

    // Show initial waiting message in error area
    const errorElement = document.querySelector(`[id^="submitError_"]`);
    if (errorElement && !routingJsonData.metadata.is_retry) {
        errorElement.style.display = 'block';
        errorElement.innerHTML = routingJsonData.content.ai_answer;
    }

    // Check if we've exceeded max retries (should only happen after a retry attempt)
    if (routingJsonData.metadata.retry_count > MAX_QRAG_LLM_RETRIES) {
        console.log(`qrag-llm - Both models timed out after ${MAX_QRAG_LLM_RETRIES + 1} attempts`);
        const timeoutMessage = `Sorry, the AI models failed to respond after ${MAX_QRAG_LLM_RETRIES + 1} attempts. We've been notified about this issue and will look into it. If you want to try again, copy your question, refresh the webpage, and paste your question back in.`;
        
        // Update the AI answer in the response data
        routingJsonData.content.ai_answer = timeoutMessage;

        // Notify about the retry failure
        notifyUserAction('Retry Failure', `Question: ${routingJsonData.content.user_question}\nError: ${timeoutMessage}`);
        
        return Promise.resolve({
            status: 'Error',
            message: timeoutMessage,
            response: routingJsonData
        });
    }

    // Add large_context_filename to metadata if provided
    if (large_context_filename) {
        routingJsonData.metadata.large_context_filename = large_context_filename;
    }

    return fetch(QRAG_LLM_API_URL, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(routingJsonData)
    })
    .then(httpResponse => {
        console.log("qrag-llm - HTTP response status:", httpResponse.status);
        if (!httpResponse.ok) {
            return httpResponse.json().then(errorData => {
                if (errorData.error_type === 'LargeContextLoadError') {
                    throw new Error(`Failed to load context data: ${errorData.error}`);
                }
                throw new Error(`HTTP error! status: ${httpResponse.status}, message: ${errorData.error}`);
            });
        }
        return httpResponse.json();
    })
    .then(apiResponse => {
        console.log("qrag-llm - Received API Response:", apiResponse);
        if (!apiResponse.response) {
            throw new Error('qrag-llm - No data in API Response');
        }
        
        // Check if this is a retry response and update UI
        if (apiResponse.status === 'Retry') {
            console.log("qrag-llm - Received retry response, updating UI and initiating retry with fallback model");
            
            // Show the timeout message in both error area and accordion
            const errorElement = document.querySelector(`[id^="submitError_"]`);
            if (errorElement) {
                errorElement.style.display = 'block';
                errorElement.innerHTML = apiResponse.response.content.ai_answer;
            }
            
            // Update the accordion
            replaceAccordionItem(apiResponse.response, document.querySelector('[id^="submitButton_"]').id);
            
            // Increment retry count and make new request
            routingJsonData.metadata.retry_count += 1;
            return qragLLM(routingJsonData, large_context_filename);
        }
        
        return apiResponse.response;
    });
}

function vragLLM(userInput, vector_index_name) {
    console.log("vrag-llm - Calling Lambda function with userInput:", userInput, "vector_index_name:", vector_index_name);
    return fetch(VRAG_LLM_API_URL, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ 
            user_question: userInput,
            vector_index_name: vector_index_name 
        })
    })
    .then(httpResponse => {  // Clearly indicates this is the HTTP response object
        if (!httpResponse.ok) {
            throw new Error(`vrag-routing - HTTP error! status: ${httpResponse.status}`);
        }
        return httpResponse.json();  // Parse JSON from the HTTP response
    })
    .then(apiResponse => {  // This is the full API response including status and data
        console.log("vrag-routing - Received API Response:", apiResponse);
        if (!apiResponse.response) {
            throw new Error('vrag-routing - No data in API Response');
        }
        return apiResponse.response;  // return the json data in the response field of apiResponse
    });
}

function generateDropdownContent(jsonData, displayType) {
    let dropdownContent = '';
    if (displayType === 'ai-answer-only') {
        if (jsonData.content.ai_answer && jsonData.content.ai_answer.startsWith("WAITING FOR AI ANSWER") || 
            jsonData.content.ai_answer && jsonData.content.ai_answer.startsWith("STILL WAITING FOR AI ANSWER")) {
            dropdownContent += `<div class="accordion-dropdown-text accordion-dropdown-text-waiting">${jsonData.content.ai_answer}</div>`;
        } else {
            dropdownContent += `<div class="accordion-dropdown-text" style="color: red;">AI ANSWER:<br>${simpleMarkdownToHtml(jsonData.content.ai_answer)}</div>`;
        }
    } else if (displayType === 'quoted-qa-then-ai-answer') {
        if (jsonData.content.route_preamble) {
            dropdownContent += `<div class="accordion-dropdown-text">${simpleMarkdownToHtml(jsonData.content.route_preamble)}</div>`;
        }
        if (jsonData.content.quoted_qa) {
            dropdownContent += `<div class="accordion-dropdown-text">${simpleMarkdownToHtml(jsonData.content.quoted_qa)}</div>`;
        }
        if (jsonData.content.ai_answer && (
            jsonData.content.ai_answer.startsWith("WAITING FOR AI ANSWER") || 
            jsonData.content.ai_answer.startsWith("STILL WAITING FOR AI ANSWER")
        )) {
            dropdownContent += `<div class="accordion-dropdown-text accordion-dropdown-text-waiting">${jsonData.content.ai_answer}</div>`;
        } else {
            dropdownContent += `<div class="accordion-dropdown-text accordion-dropdown-text-ai-answer">AI ANSWER:<br>${simpleMarkdownToHtml(jsonData.content.ai_answer)}</div>`;
        }
    }
    return dropdownContent;
}

function createAccordionItem(jsonData, submitButtonId) {
    // Check for necessary elements exist and if not throw error
    if (!checkBotElementsExist(submitButtonId)) {
        throw new Error("createAccordionItem - Required elements not found.");
    }

    const botContainer = getBotContainerFromSubmitButtonId(submitButtonId);
    
    // Check if the hidden-div already exists in the botContainer, if not, create the Hidden Div and Share Elements
    if (!botContainer.querySelector('.hidden-div')) {
        createHiddenDivAndShareElements(botContainer);
    }
    
    const accordionCard = botContainer.querySelector('.accordion-card');

    // Create the accordion item container
    var accordionItem = document.createElement('div');
    accordionItem.className = 'accordion-item w-dropdown';

    // Create the accordion toggle
    var accordionToggle = document.createElement('div');
    accordionToggle.className = 'accordion-toggle w-dropdown-toggle';
    
    // Set the title text using 'user_question' from jsonData and apply text clamping
    const user_question = jsonData.content.user_question.replace(/\n/g, '<br>');
    accordionToggle.innerHTML = `
        <div class="accordion-icon w-icon-dropdown-toggle"></div>
        <div class="accordion-title-text" style="user-select: text;">${user_question}</div>
    `;

    // Add toggle event - Update to only trigger on icon click
    const icon = accordionToggle.querySelector('.accordion-icon');
    icon.addEventListener('click', function (e) {
        e.stopPropagation(); // Prevent event from bubbling up
        var dropdownList = accordionToggle.nextElementSibling;
        var isCollapsed = dropdownList.style.display === 'none';
        dropdownList.style.display = isCollapsed ? 'block' : 'none';
        icon.style.transform = isCollapsed ? 'rotate(0deg)' : 'rotate(-90deg)';
    });

    const params = buttonParamsMapping[submitButtonId];
    const displayType = params.displayType;

    var dropdownList = document.createElement('nav');
    dropdownList.className = 'accordion-dropdown-list w-dropdown-list';
    dropdownList.style.display = 'block'; // Start visible

    dropdownList.innerHTML = generateDropdownContent(jsonData, displayType);

    // Convert JSON response to Markdown and append to the top of the hidden div with deleteTopHeadingFlag set to false
    writeMarkdownToHiddenDiv(jsonData, botContainer, false);

    // Append the toggle and dropdown to the accordion item
    accordionItem.appendChild(accordionToggle);
    accordionItem.appendChild(dropdownList);

    accordionCard.insertBefore(accordionItem, accordionCard.firstChild);
}

function replaceAccordionItem(jsonData, submitButtonId) {
    // Check for necessary elements exist and if not throw error
    if (!checkBotElementsExist(submitButtonId)) {
        throw new Error("replaceAccordionItem - Required elements not found.");
    }

    const botContainer = getBotContainerFromSubmitButtonId(submitButtonId);

    let accordionCard = botContainer.querySelector('.accordion-card');
    if (!accordionCard) {
        console.error("replaceAccordionItem - Accordion card not found.");
        return;
    }

    // Find the first accordion item to update - this method will always return the topmost one in the DOM
    let accordionItem = accordionCard.querySelector('.accordion-item');
    if (!accordionItem) {
        console.error("replaceAccordionItem - Accordion item not found.");
        return;
    }

    const accordionTitleText = accordionItem.querySelector('.accordion-title-text');
    const user_question = jsonData.content.user_question.replace(/\n/g, '<br>');
    accordionTitleText.innerHTML = user_question;

    const params = buttonParamsMapping[submitButtonId];
    const displayType = params.displayType;

    const dropdownList = accordionItem.querySelector('.accordion-dropdown-list');
    dropdownList.innerHTML = generateDropdownContent(jsonData, displayType);

    // Convert JSON response to Markdown and append to the hidden div with deletion of the top heading
    writeMarkdownToHiddenDiv(jsonData, botContainer, true);
}

function createHiddenDivAndShareElements(botContainer) {
    console.log('Creating hidden div and download button');
    
    // Get the bot title from the buttonParamsMapping
    const submitButtonId = botContainer.querySelector('button[id^="submitButton_"]').id;
    const botTitle = buttonParamsMapping[submitButtonId].botTitle;

    // Create a hidden div
    let hiddenDiv = document.createElement('div');
    hiddenDiv.className = 'hidden-div';
    hiddenDiv.style.display = 'none';
    hiddenDiv.textContent = `${botTitle}\nby Randy True of focusonfoundations.org`;

    // Create download and email buttons
    let downloadButton = createIconButton('download', 'material-symbols-rounded', () => downloadMarkdown(botContainer));
    let emailButton = createIconButton('mail', 'material-symbols-rounded', () => toggleEmailInputVisibility(emailButton));
    
    console.log('createHiddenDivAndShareElements - Hidden div, download button, and email button created and event listeners added');
    
    // Create an input text block for email address
    let emailInput = createInput('email', 'Enter your email to send the below exchanges', 'email-input-address');
    emailInput.style.display = 'none';
    emailInput.addEventListener('keypress', function(event) {
        if (event.key === 'Enter') {
            event.preventDefault(); // Prevent the default action to stop form submission
            sendEmail(event); // Call the sendEmail function
        }
    });

    // Create a checkbox for "add me to the email list for updates to this project" only if showEmailListSignup is true
    let emailCheckboxContainer;
    if (showEmailListSignup) {
        emailCheckboxContainer = createCheckboxWithLabel('Add me to the email list for updates to this project.');
    }

    // Create a block for download, email button, email input, and checkbox with label (if enabled)
    let shareDiv = document.createElement('div');
    shareDiv.className = 'share-div';
    shareDiv.appendChild(downloadButton);
    shareDiv.appendChild(emailButton);
    shareDiv.appendChild(emailInput);
    if (showEmailListSignup) {
        shareDiv.appendChild(emailCheckboxContainer);
    }

    // Find the accordion container and insert the hiddenDiv and shareDiv above it
    let accordionContainer = botContainer.querySelector('.accordion-container');
    botContainer.insertBefore(hiddenDiv, accordionContainer);
    botContainer.insertBefore(shareDiv, accordionContainer);
}
 
  
//// CHILD FUNCTIONS FOR createHiddenDivAndShareElements 
function createIconButton(iconText, iconClass, eventListener) {
    let button = document.createElement('button');
    let icon = document.createElement('span');
    icon.className = iconClass;
    icon.textContent = iconText;
    button.appendChild(icon);
    button.className = 'primary-button w-button icon-button'; // Add the new class here
    button.addEventListener('click', eventListener);
    return button;
}
  
function styleButton(button, styles) {
    Object.assign(button.style, styles);
}

function createInput(type, placeholder, className) {
    let input = document.createElement('input');
    input.type = type;
    input.placeholder = placeholder;
    input.className = className; // Assign the class name
    return input;
}

function createCheckboxWithLabel(labelText) {
    let container = document.createElement('div');
    container.className = 'email-checkbox-container';
    container.style.display = 'none';

    let checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'email-checkbox';

    let label = document.createElement('label');
    label.className = 'email-checkbox-label';
    label.textContent = labelText;

    container.appendChild(checkbox);
    container.appendChild(label);

    return container;
}
  
function toggleEmailInputVisibility(emailButton) {
    let emailInput = emailButton.parentElement.querySelector('.email-input-address');
    let emailCheckboxContainer = emailButton.parentElement.querySelector('.email-checkbox-container');
    
    // If the input is currently hidden, show it
    if (emailInput.style.display === 'none' || !emailInput.style.display) {
        emailInput.style.display = 'inline-block';
        
        // Check if we have a stored email
        const storedEmail = sessionStorage.getItem('inputUserEmail');
        if (storedEmail) {
            // If we have a stored email, populate it but don't show checkbox
            emailInput.value = storedEmail;
            if (emailCheckboxContainer) {
                emailCheckboxContainer.style.display = 'none';
            }
        } else {
            // First time user - show empty email field and checkbox
            emailInput.value = '';
            if (emailCheckboxContainer) {
                emailCheckboxContainer.style.display = 'inline-block';
                
                // Add change listener to checkbox if not already added
                const checkbox = emailCheckboxContainer.querySelector('.email-checkbox');
                if (checkbox) {
                    checkbox.addEventListener('change', function() {
                        if (this.checked) {
                            sessionStorage.setItem('emailListSignupChecked', 'true');
                        }
                    });
                }
            }
        }
    } else {
        // Hide both elements when toggling off
        emailInput.style.display = 'none';
        if (emailCheckboxContainer) {
            emailCheckboxContainer.style.display = 'none';
        }
    }
}

function writeMarkdownToHiddenDiv(jsonData, botContainer, deleteTopHeadingFlag) {
    const MARKDOWN_HEADING_LEVEL = '##'; // Set the Markdown heading level to be removed if needed

    if (!botContainer) {
        console.error('writeMarkdownToHiddenDiv - Error: botContainer is null.');
        return;
    }
    var markdownContent = processJsonToMarkdown(jsonData);
    var hiddenDiv = botContainer.querySelector('.hidden-div'); // Accessing the element with class='hidden-div' using the passed botContainer
    if (!hiddenDiv) {
        console.error('writeMarkdownToHiddenDiv - Error: hiddenDiv not found within the botContainer.');
        return;
    }
    let initialText = hiddenDiv.textContent;

    // Optionally remove the top Markdown heading and content below it until the next heading of the same level
    if (deleteTopHeadingFlag) {
        const firstHeadingIndex = initialText.indexOf('\n' + MARKDOWN_HEADING_LEVEL + ' ');
        //console.log('DEBUG - Next heading index:', firstHeadingIndex, 'text:', initialText.substring(firstHeadingIndex, firstHeadingIndex + 10));
            if (firstHeadingIndex !== -1) {
            let nextHeadingIndex = initialText.indexOf('\n' + MARKDOWN_HEADING_LEVEL + ' ', firstHeadingIndex + 1);
            let preHeadingText = initialText.substring(0, firstHeadingIndex); // Preserve text before the first heading
            //console.log('DEBUG - Next heading index:', nextHeadingIndex, 'text:', initialText.substring(nextHeadingIndex, nextHeadingIndex + 10));
            //console.log('DEBUG - Pre-heading text:', preHeadingText);
            if (nextHeadingIndex === -1) { // No next heading found, delete to the end
                initialText = preHeadingText; // Assign initialText to just the preHeadingText
            } else {
                let postHeadingText = initialText.substring(nextHeadingIndex); // Preserve text after the next heading
                //console.log('DEBUG - Post-heading text:', postHeadingText);
                initialText = preHeadingText + postHeadingText; // Combine the preserved parts
            }
        }
    }
    hiddenDiv.textContent = initialText; // Update the text content of hiddenDiv
    // console.log('DEBUG After deletion - Current total content of hiddenDiv:', {
    //     content: hiddenDiv.textContent
    // });

    // Insert the new markdown content
    const firstMarkdownHeaderIndex = initialText.search(/##\s/);
    let insertionPoint;
    if (firstMarkdownHeaderIndex !== -1) {
        insertionPoint = initialText.substring(0, firstMarkdownHeaderIndex).search(/\S\s*$/) + 1;
    } else {
        insertionPoint = initialText.search(/\S\s*$/) + 1;
    }
    hiddenDiv.textContent = initialText.substring(0, insertionPoint) + markdownContent + initialText.substring(insertionPoint);
    console.log('writeMarkdownToHiddenDiv - Markdown content updated in the hidden div');
    // console.log('DEBUG After insertion - Current total content of hiddenDiv:', {
    //     content: hiddenDiv.textContent
    // });
}

function appendMarkdownToHiddenDiv(jsonData, botContainer) {
    if (!botContainer) {
        console.error('appendMarkdownToHiddenDiv - Error: botContainer is null.');
        return;
    }
    var markdownContent = processJsonToMarkdown(jsonData);
    var hiddenDiv = botContainer.querySelector('.hidden-div'); // Accessing the element with class='hidden-div' using the passed botContainer
    if (!hiddenDiv) {
        console.error('appendMarkdownToHiddenDiv - Error: hiddenDiv not found within the botContainer.');
        return;
    }
    const initialText = hiddenDiv.textContent;
    const firstMarkdownHeaderIndex = initialText.search(/##\s/);
    let insertionPoint;
    if (firstMarkdownHeaderIndex !== -1) {
        insertionPoint = initialText.substring(0, firstMarkdownHeaderIndex).search(/\S\s*$/) + 1;
    } else {
        insertionPoint = initialText.search(/\S\s*$/) + 1;
    }
    hiddenDiv.textContent = initialText.substring(0, insertionPoint) + markdownContent + initialText.substring(insertionPoint);
    console.log('appendMarkdownToHiddenDiv - Markdown content inserted at the correct position in the hidden div');
}
function downloadMarkdown(botContainer) {
    // Get the markdown content from the hidden div within the specified bot container
    let hiddenDiv = botContainer.querySelector('.hidden-div');
    let markdownContent = hiddenDiv.textContent;

    // Get current date and time in Pacific Time
    const now = new Date();
    const options = { 
        timeZone: 'America/Los_Angeles',
        year: 'numeric', 
        month: '2-digit', 
        day: '2-digit',
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    };
    
    // Format the date and time parts
    const formatter = new Intl.DateTimeFormat('en-US', options);
    const parts = formatter.formatToParts(now);
    
    // Create a map for easy access to date parts
    const dateMap = {};
    parts.forEach(part => {
        dateMap[part.type] = part.value;
    });
    
    // Format date as YYYY-MM-DD_HHMMSS
    const dateStr = `${dateMap.year}-${dateMap.month}-${dateMap.day}_${dateMap.hour}${dateMap.minute}${dateMap.second}`;
    
    // Determine which bot/corpus is being used
    let botType = "QRag";
    const containerId = botContainer.id;
    
    if (containerId.includes('deutsch')) {
        botType = "QRAG-Deutsch";
    } else if (containerId.includes('pv-evac')) {
        botType = "QRAG-PV-EPC";
    } else if (containerId.includes('fda-townhalls')) {
        botType = "QRAG-FDATownHalls";
    } else if (containerId.includes('sovereign-child')) {
        botType = "QRAG-SovereignChild";
    }
    
    // Create filename with date, time and bot type
    const filename = `FOF_AI-Tool_${dateStr}_${botType}.md`;

    // Create a Blob from the markdown content with proper encoding
    let blob = new Blob([markdownContent], { type: 'text/markdown;charset=utf-8' });

    // Create a link element
    let link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;

    // Programmatically click the link to trigger the download
    link.click();
    
    // Notify about the download action with content
    notifyUserAction('Download', markdownContent);
}

console.log('End of script file: webflow-css_rag-devpage.js in page custom code body reached');

// ========= END OF FILE webflow-rag-devpage.js =========
