// ========= START OF FILE webflow-fof-site-body.js =========
// deploy: copy to Site Settings > Custom Code > Body section between script tags
// contains: Email sending, hash storage, user data management, validation, security alerts,
//           UI helpers, and text processing functions for the QRAG application

var fileInfo = `webflow-fof-site-body.js 9-23-25 moved button params mapping here from webflow-rag-devpage.js`;
const SEND_EMAIL_API_ENDPOINT_URL = 'https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/prod/send-email';
const HASH_STORE_API_ENDPOINT_URL = 'https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/prod/hash-store';
const HASH_STORE_LOG_FILE_KEY = 'pii_user_hash_log_2024-12-17.csv';
const HASH_STORE_LOG_FILE_PATH = '';
const PRIVACY_CONSENT_VERSION_DATE = '2024-12-17';

// Add new constant for JWT storage key
const JWT_STORAGE_KEY = 'jwtToken';

document.addEventListener("DOMContentLoaded", function() {
  console.log('Loading JavaScript for Site Body: ', fileInfo);

  // Ensure the Webflow object exists
  window.Webflow ||= [];

  // Use Webflow's push method to run code after the page and Webflow scripts have loaded
  window.Webflow.push(function () {
      console.log('Webflow scripts have loaded.');
  });
});

// Maps submit button IDs to their corresponding RAG parameters and configuration
const buttonParamsMapping = {
    'submitButton_deutsch-demo_qrag': {  // Bot container id=container_deutsch-demo_qrag
        displayType: 'quoted-qa-then-ai-answer',
        ragFunction: 'qragRouting, qragLLM', 
        vector_index_name: 'deutsch-transcript-qrag-95f-20250923', 
        route_dict_name: 'ROUTES_DICT_DEUTSCH_M1',
        large_context_filename: 'deutsch_large_context_v1.md',
        botTitle: 'QRAG demo over David Deutsch Interview Corpus'
    },
    'submitButton_deutsch-demo_vrag': { 
        displayType: 'ai-answer-only',
        ragFunction: 'vragLLM', 
        vector_index_name: 'dd-transcripts-vrag-80f-20240727',
        large_context_filename: 'deutsch_large_context_v1.md',
        botTitle: 'VRAG demo over David Deutsch Interview Corpus'
    },
    'submitButton_pv-evac-demo_qrag': {  // Bot container id=container_pv-evac-demo_qrag
        displayType: 'quoted-qa-then-ai-answer',
        ragFunction: 'qragRouting, qragLLM', 
        vector_index_name: 'pv-evac-qrag-3f-20250202', 
        route_dict_name: 'ROUTES_DICT_PV_EVAC_M1',
        large_context_filename: null,  // Explicitly set to null
        botTitle: 'QRAG demo over PVSD Evacuation Preparedness Meeting'
    },
    'submitButton_fda-townhalls-demo_qrag': {  // Bot container id=container_fda-townhalls-demo_qrag
        displayType: 'quoted-qa-then-ai-answer',
        ragFunction: 'qragRouting, qragLLM', 
        vector_index_name: 'fda-townhalls-qrag-100f-20250114', 
        route_dict_name: 'ROUTES_DICT_FDA_TOWNHALLS_M1',
        large_context_filename: null,  // Explicitly set to null
        botTitle: 'QRAG demo over 100 FDA COVID-19 Diagnostics Virtual Town Halls'
    },
    'submitButton_sovereign-child-demo_qrag': {  // Bot container id=container_sovereign-child-demo_qrag
        displayType: 'quoted-qa-then-ai-answer',
        ragFunction: 'qragRouting, qragLLM', 
        vector_index_name: 'sovereign-child-qrag-7f-20250805', // was sovereign-child-qrag-2f-20250208
        route_dict_name: 'ROUTES_DICT_SOVEREIGN_CHILD_M1',
        large_context_filename: '2025-01-13_Book - The Sovereign Child by Dr Aaron Stupple.md',
        botTitle: 'QRAG demo over The Sovereign Child book'
    }
};

//// SHARE FUNCTIONS
async function sendEmail(event) {
  event.preventDefault();
  const displayDuration = 3000;

  // Access the email input field relative to the event target
  var emailInput = event.currentTarget;
  var parentNode = emailInput.parentNode;
  var emailInputAddress = parentNode.querySelector('input[type="email"]');
  var emailInputAddressValue = emailInputAddress.value;

  // Validate email using validateAndSanitizeInput
  const emailCheck = validateAndSanitizeInput(
      emailInputAddressValue,
      null, // Use default max length from INPUT_TYPE_EMAIL
      'Email Address',
      'INPUT_TYPE_EMAIL'
  );

  if (!emailCheck.success) {
      console.error("Invalid or empty email address.");
      displayTempMessage(emailCheck.messages.join(' '), 'error', displayDuration, emailInput);
      return;
  }

  // Use the sanitized email value
  const sanitizedEmail = emailCheck.value;

  try {
      // Store sanitized email in sessionStorage
      sessionStorage.setItem('inputUserEmail', sanitizedEmail);
      console.log('Email stored in sessionStorage:', sanitizedEmail);

      // Get stored user info for hash-store call
      const userNiceName = sessionStorage.getItem('userNiceName') || '';
      const userIPAddress = sessionStorage.getItem('userIPAddress') || '';
      const emailListSignupChecked = sessionStorage.getItem('emailListSignupChecked') === 'true';
      const privacyConsent = sessionStorage.getItem('privacyConsent') || '';

      // Call hash-store API
      console.log('sendEmail - Calling hash-store with:', {
          userNiceName,
          userIPAddress,
          inputUserEmail: sanitizedEmail,
          emailListSignupChecked,
          eventType: 'submit_user_email',
          privacyConsent
      });

      const hashedValues = await callHashStore(
          userNiceName,
          userIPAddress,
          sanitizedEmail,
          emailListSignupChecked,
          'submit_user_email',
          privacyConsent
      );

      console.log('sendEmail - Received hashed values:', hashedValues);

      // Access the hidden div to get the Markdown content
      var hiddenDiv = emailInput.closest('.bot-container').querySelector('.hidden-div');
      var hiddenDivMarkdown = hiddenDiv.textContent;

      // Convert Markdown content to HTML and plain text
      var emailContent = processMarkdownToTextAndHtml(hiddenDivMarkdown);

      // Rest of the existing email sending logic...
      var emailPrelude = 'Below is the requested content. If you did not request this content, please reply to this email stating that, and let us know if you would like to prevent this email address from receiving any further messages.';
      var emailBodyPlain = `${emailPrelude}\n\n${emailContent.plainText}`;
      var emailBodyHtml = `<p>${emailPrelude.replace(/\n/g, '<br>')}</p><br>${emailContent.html}`;

      var payload = {
          to_address: sanitizedEmail,
          email_subject: "Your Deutsch QRAG Demo Questions and Answers - from focusonfoundations.org",
          from_address: "contact@focusonfoundations.org",
          email_body_plain: emailBodyPlain,
          email_body_html: emailBodyHtml
      };

      const response = await fetch(SEND_EMAIL_API_ENDPOINT_URL, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify(payload)
      });

      if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log("Received data:", data);
      displayTempMessage('Email sent successfully!', 'success', displayDuration, emailInput);
      
      // Notify about the email action with content
      await notifyUserAction('Email', hiddenDivMarkdown);

      // Use parentNode reference to find elements
      const emailInputElement = parentNode.querySelector('.email-input-address');
      const emailCheckboxContainer = parentNode.querySelector('.email-checkbox-container');
      
      // Delay hiding the elements to match the message duration
      setTimeout(() => {
          if (emailInputElement) emailInputElement.style.display = 'none';
          if (emailCheckboxContainer) emailCheckboxContainer.style.display = 'none';
      }, displayDuration);

  } catch (error) {
      console.error('sendEmail - Error:', error);
      displayTempMessage('Failed to send email.', 'error', displayDuration, emailInput);
  }
}

function displayTempMessage(message, type, duration, targetElement) {
    if (!targetElement) {
        console.warn('displayTempMessage: Target element is null');
        return; // Gracefully handle missing target element
    }

    const botContainer = targetElement.closest('.bot-container');
    if (!botContainer) {
        console.warn('displayTempMessage: Could not find bot container');
        return;
    }

    // Create or find message div
    let messageDiv = botContainer.querySelector('.temp-message');
    if (!messageDiv) {
        messageDiv = document.createElement('div');
        messageDiv.className = 'temp-message';
        // Insert at the top of the bot container
        botContainer.insertBefore(messageDiv, botContainer.firstChild);
    }

    // Set message and styling
    messageDiv.textContent = message;
    messageDiv.style.display = 'block';
    messageDiv.style.color = type === 'error' ? 'red' : (type === 'info' ? 'blue' : 'green');

    // Clear previous timeout if it exists
    if (messageDiv.timeout) {
        clearTimeout(messageDiv.timeout);
    }

    // Set new timeout to hide message
    messageDiv.timeout = setTimeout(() => {
        messageDiv.style.display = 'none';
    }, duration);
}

async function callHashStore(userNiceName, userIPAddress, inputUserEmail = '', emailListSignupChecked = null, eventType, privacyConsent) {
    const payload = {
        key: HASH_STORE_LOG_FILE_KEY,
        s3_path: HASH_STORE_LOG_FILE_PATH || "",
        userNiceName: userNiceName,
        userIPAddress: userIPAddress,
        inputUserEmail: inputUserEmail || "",
        emailListSignupChecked: emailListSignupChecked,
        eventType: eventType,
        privacyConsent: privacyConsent
    };

    console.log('callHashStore - Calling hash-store API with:', payload);

    try {
        const response = await fetch(HASH_STORE_API_ENDPOINT_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Error response:', errorText);
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('callHashStore - Received response:', data);

        // Store JWT token if received
        if (data.jwtToken) {
            sessionStorage.setItem(JWT_STORAGE_KEY, data.jwtToken);
            console.log('JWT token stored in sessionStorage');
        }

        if (data.hashed_values) {
            sessionStorage.setItem('hashedUserNiceName', data.hashed_values.hashedUserNiceName);
            sessionStorage.setItem('hashedUserIPAddress', data.hashed_values.hashedUserIPAddress);
            if (inputUserEmail) {
                sessionStorage.setItem('hashedInputUserEmail', data.hashed_values.hashedInputUserEmail);
            }
        }

        return data.hashed_values;

    } catch (error) {
        console.error('callHashStore - Error:', error);
        throw error;
    }
}

// Add helper function to get JWT token
function getStoredJWT() {
    return sessionStorage.getItem(JWT_STORAGE_KEY);
}

// Add helper function to add JWT to headers
function getAuthHeaders() {
    const jwt = getStoredJWT();
    const headers = {
        'Content-Type': 'application/json'
    };
    
    if (jwt) {
        headers['Authorization'] = `Bearer ${jwt}`;
    }
    
    return headers;
}

async function notifyUserAction(actionType, actionContent) {
    try {
        // Get stored user info - both raw and hashed values
        const userNiceName = sessionStorage.getItem('userNiceName') || '';
        const hashedUserNiceName = sessionStorage.getItem('hashedUserNiceName') || '';
        const hashedUserIPAddress = sessionStorage.getItem('hashedUserIPAddress') || '';
        const hashedInputUserEmail = sessionStorage.getItem('hashedInputUserEmail') || '';
        const emailListSignupChecked = sessionStorage.getItem('emailListSignupChecked') === 'true';

        // Get the current page's bot container and its title
        const botContainer = document.querySelector('.bot-container');
        const submitButtonId = botContainer.querySelector('button[id^="submitButton_"]').id;
        const actionSource = buttonParamsMapping[submitButtonId].botTitle;

        // Convert the action content to formatted text and HTML
        const formattedContent = processMarkdownToTextAndHtml(actionContent);

        // Prepare the email payload
        const payload = {
            to_address: "contact@focusonfoundations.org",
            email_subject: `User ${actionType} Action - ${actionSource}`,
            from_address: "contact@focusonfoundations.org",
            email_body_plain: `
User Action Details:
- Action Type: ${actionType}
- Action Source: ${actionSource}
- Hashed User Nice Name: ${hashedUserNiceName}
- Hashed User IP Address: ${hashedUserIPAddress}
- Hashed User Email: ${hashedInputUserEmail}
- Email List Signup: ${emailListSignupChecked}

User Action Content:
${formattedContent.plainText}`,
            email_body_html: `
<h3>User Action Details:</h3>
<ul>
    <li><strong>Action Type:</strong> ${actionType}</li>
    <li><strong>Action Source:</strong> ${actionSource}</li>
    <li><strong>Hashed User Nice Name:</strong> ${hashedUserNiceName}</li>
    <li><strong>Hashed User IP Address:</strong> ${hashedUserIPAddress}</li>
    <li><strong>Hashed User Email:</strong> ${hashedInputUserEmail}</li>
    <li><strong>Email List Signup:</strong> ${emailListSignupChecked}</li>
</ul>

<h3>User Action Content:</h3>
${formattedContent.html}`
        };

        const response = await fetch(SEND_EMAIL_API_ENDPOINT_URL, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        console.log(`Notification sent for user ${actionType} action`);

    } catch (error) {
        console.error('Error sending notification:', error);
        // Don't throw the error - we don't want to interrupt the user's action
    }
}

// Sends an email alert about suspicious input.
async function notifySecurityAction(actionType, suspiciousContent, inputField = '') {
    try {
        // Get stored user info - both raw and hashed values
        const userNiceName = sessionStorage.getItem('userNiceName') || '';
        const hashedUserNiceName = sessionStorage.getItem('hashedUserNiceName') || '';
        const userIPAddress = sessionStorage.getItem('userIPAddress') || '';
        const hashedUserIPAddress = sessionStorage.getItem('hashedUserIPAddress') || '';
        const inputUserEmail = sessionStorage.getItem('inputUserEmail') || '';
        const hashedInputUserEmail = sessionStorage.getItem('hashedInputUserEmail') || '';
        const emailListSignupChecked = sessionStorage.getItem('emailListSignupChecked') === 'true';

        // Get page information
        const fullUrl = window.location.href;
        const urlSlug = window.location.pathname.split('/').pop() || 'home';

        // Safely encode suspicious content
        const encodedContent = suspiciousContent
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');

        // Prepare email payload
        const payload = {
            to_address: "contact@focusonfoundations.org",
            email_subject: `[SECURITY ALERT] ${actionType} Detected on ${urlSlug}`,
            from_address: "contact@focusonfoundations.org",
            email_body_plain: `
Security Alert Details:
- Action Type: ${actionType}
- Page URL: ${fullUrl}
- Page Slug: ${urlSlug}
- Input Field: ${inputField}
- Flagged Input: ${suspiciousContent}
- User Nice Name: ${userNiceName}
- Hashed User Nice Name: ${hashedUserNiceName}
- User IP Address: ${userIPAddress}
- Hashed User IP Address: ${hashedUserIPAddress}
- User Email: ${inputUserEmail}
- Hashed User Email: ${hashedInputUserEmail}
- Email List Signup: ${emailListSignupChecked}

Raw Suspicious Content (Base64 encoded for safety):
${btoa(suspiciousContent)}`,
            email_body_html: `
<h3>Security Alert Details:</h3>
<ul>
    <li><strong>Action Type:</strong> ${actionType}</li>
    <li><strong>Page URL:</strong> ${fullUrl}</li>
    <li><strong>Page Slug:</strong> ${urlSlug}</li>
    <li><strong>Input Field:</strong> ${inputField}</li>
    <li><strong>User Nice Name:</strong> ${userNiceName}</li>
    <li><strong>Hashed User Nice Name:</strong> ${hashedUserNiceName}</li>
    <li><strong>User IP Address:</strong> ${userIPAddress}</li>
    <li><strong>Hashed User IP Address:</strong> ${hashedUserIPAddress}</li>
    <li><strong>User Email:</strong> ${inputUserEmail}</li>
    <li><strong>Hashed User Email:</strong> ${hashedInputUserEmail}</li>
    <li><strong>Email List Signup:</strong> ${emailListSignupChecked}</li>
</ul>

<h3>Flagged Input (HTML Encoded):</h3>
<pre style="background-color: #f8f8f8; padding: 10px; border: 1px solid #ddd;">${encodedContent}</pre>

<h3>Raw Suspicious Content (Base64):</h3>
<pre style="background-color: #f8f8f8; padding: 10px; border: 1px solid #ddd;">${btoa(suspiciousContent)}</pre>`
        };

        const response = await fetch(SEND_EMAIL_API_ENDPOINT_URL, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            console.error('Failed to send security alert email:', await response.text());
        } else {
            console.log('Security alert email sent successfully.');
        }
    } catch (error) {
        console.error('Error in notifySecurityAction sending security alert email:', error);
    }
}

//// USER FUNCTIONS
// Function to log user info
function consoleLogUserInfo() {
  const userEmail = sessionStorage.getItem('userEmail');
  const userName = sessionStorage.getItem('userName');
  const userIdAlt = sessionStorage.getItem('userIdAlt');
  const userEmailHmacHash = sessionStorage.getItem('userEmailHmacHash');
  const privacyConsent = sessionStorage.getItem('privacyConsent');
  const userNiceName = sessionStorage.getItem('userNiceName');
  const userIPAddress = sessionStorage.getItem('userIPAddress');
  const inputUserEmail = sessionStorage.getItem('inputUserEmail');
  const emailListSignupChecked = sessionStorage.getItem('emailListSignupChecked');
  const hashedUserNiceName = sessionStorage.getItem('hashedUserNiceName');
  const hashedUserIPAddress = sessionStorage.getItem('hashedUserIPAddress');
  const hashedInputUserEmail = sessionStorage.getItem('hashedInputUserEmail');
  const jwtToken = sessionStorage.getItem(JWT_STORAGE_KEY);
  
    console.log('Session Storage - Webflow Account User items:\n' +
        '  Webflow Email: ' + (userEmail || 'null') + '\n' +
        '  Webflow Name: ' + (userName || 'Not set') + '\n' +
        '  Webflow ID: ' + (userIdAlt || 'Not set') + '\n' +
        '  Webflow Email HMAC Hash: ' + (userEmailHmacHash || 'Not set') + '\n' +
        '\nSession Storage - Open Access User items:\n' +
        '  Privacy Consent: ' + (privacyConsent || 'Not set') + '\n' +
        '  Nice Name: ' + (userNiceName || 'Not set') + '\n' +
        '  IP Address: ' + (userIPAddress || 'Not set') + '\n' +
        '  Input Email: ' + (inputUserEmail || 'Not set') + '\n' +
        '  Email List Signup: ' + (emailListSignupChecked || 'Not set') + '\n' +
        '  Hashed Nice Name: ' + (hashedUserNiceName || 'Not set') + '\n' +
        '  Hashed IP Address: ' + (hashedUserIPAddress || 'Not set') + '\n' +
        '  Hashed Input Email: ' + (hashedInputUserEmail || 'Not set') + '\n' +
        '  JWT Token: ' + (jwtToken || 'Not set'));

}

function consoleLogSessionStorage() {
    // Log user info first
    consoleLogUserInfo();
    
    // Log additional items
    const numChunks = sessionStorage.getItem('num-chunks');
    const startDate = sessionStorage.getItem('qrag-start-date');
    const endDate = sessionStorage.getItem('qrag-end-date');
    
    console.log('Session Storage - Non user info items:\n' +
        '  Num Chunks: ' + (numChunks || 'Not set') + '\n' +
        '  Start Date: ' + (startDate || 'Not set') + '\n' +
        '  End Date: ' + (endDate || 'Not set') + '\n');
}

function clearSiteSessionStorage() {
    // Webflow Account User info
    sessionStorage.removeItem('userEmail');
    sessionStorage.removeItem('userName');
    sessionStorage.removeItem('userIdAlt');
    sessionStorage.removeItem('userEmailHmacHash');
    
    // Open Access User info
    sessionStorage.removeItem('privacyConsent');
    sessionStorage.removeItem('userNiceName');
    sessionStorage.removeItem('userIPAddress');
    sessionStorage.removeItem('inputUserEmail');
    sessionStorage.removeItem('emailListSignupChecked');
    sessionStorage.removeItem('hashedUserNiceName');
    sessionStorage.removeItem('hashedUserIPAddress');
    sessionStorage.removeItem('hashedInputUserEmail');
    sessionStorage.removeItem(JWT_STORAGE_KEY);
    sessionStorage.removeItem('num-chunks');
    sessionStorage.removeItem('qrag-start-date');
    sessionStorage.removeItem('qrag-end-date');
    
    console.log('Application session storage cleared');
}

function getUserContext() {
    return {
        hashedUserNiceName: sessionStorage.getItem('hashedUserNiceName') || 'NA',
        hashedUserIPAddress: sessionStorage.getItem('hashedUserIPAddress') || 'NA',
        hashedInputUserEmail: sessionStorage.getItem('hashedInputUserEmail') || 'NA'
    };
}

function logErrorToMonitoring(error, context) {
  const errorData = {
      timestamp: new Date().toISOString(),
      error: error.message,
      context: context,
      userAgent: navigator.userAgent,
      url: window.location.href
  };

  // Prepare the email payload
  const payload = {
      to_address: "contact@focusonfoundations.org",
      email_subject: `Error in ${context}`,
      from_address: "contact@focusonfoundations.org",
      email_body_plain: `An error occurred:\n\n${JSON.stringify(errorData, null, 2)}`,
      email_body_html: `<p>An error occurred:</p><pre>${JSON.stringify(errorData, null, 2)}</pre>`
  };

  // Can add a monitoring endpoint here if needed

  // Send the email notification
  fetch(SEND_EMAIL_API_ENDPOINT_URL, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload)
  }).catch(err => console.error('Failed to send error email:', err));
}

// Function to check privacy consent status
function checkPrivacyConsent() {
    const consent = sessionStorage.getItem('privacyConsent');
    return consent === PRIVACY_CONSENT_VERSION_DATE;
}

// Function to set privacy consent
function setPrivacyConsent() {
    sessionStorage.setItem('privacyConsent', PRIVACY_CONSENT_VERSION_DATE);
    console.log('Privacy consent set:', PRIVACY_CONSENT_VERSION_DATE);
    
    document.querySelectorAll('.privacy-consent-box').forEach(el => {
        el.style.display = 'none';
    });
    
    // Restore the timeout but add sessionStorage check
    setTimeout(() => {
        const nicenameTextarea = document.querySelector('.nicename-textarea');
        const currentName = nicenameTextarea?.value.trim() || '';
        const storedName = sessionStorage.getItem('userNiceName');
        
        // Only submit if we have a name in the textarea and it's not already in sessionStorage
        if (currentName && !storedName) {
            handleNiceNameSubmission();
            console.log('Processing name submission after consent - name was entered but not stored');
        }
    }, 100);
}

// Function to show consent error
function showConsentError() {
    const errorElement = document.querySelector('.botsubmit-error');
    if (errorElement) {
        errorElement.textContent = "Please review and accept the Privacy Policy and Terms of Service  to continue.";
        errorElement.style.display = 'block';
        setTimeout(() => { errorElement.style.display = 'none'; }, 3000);
    }
}


//// TEXT PROCESSING
function processJsonToMarkdown(jsonData) {
  const metadata = jsonData.metadata;
  const content = jsonData.content;
  const userQuestion = content.user_question;
  const routePreamble = content.route_preamble;
  const aiAnswer = content.ai_answer;

  let markdownString = `\n\n\n## ${userQuestion}\n`;  // add markdown heading level 2
  markdownString += `${routePreamble}\n\n`;

  if (content.quoted_qa) {
      const quotedQaLines = content.quoted_qa.split('\n');
      let formattedQa = '';

      quotedQaLines.forEach(line => {
          if (line.trim().startsWith('QUESTION') && !line.trim().startsWith('QUESTION SIMILARITY SCORE')) {
              formattedQa += `### ${line.trim()}\n`;
          } else {
              formattedQa += `${line}\n`;
          }
      });

      markdownString += formattedQa;
  }

  markdownString += `### AI ANSWER:\n${aiAnswer}`;

  return markdownString;
}

function simpleMarkdownToHtml(markdownString) {
  // Convert headings
  let htmlContent = markdownString
      .replace(/^###### (.*$)/gim, '<span style="font-size: 0.67em;">$1</span>')
      .replace(/^##### (.*$)/gim, '<span style="font-size: 0.83em;">$1</span>')
      .replace(/^#### (.*$)/gim, '<span style="font-size: 1em;">$1</span>')
      .replace(/^### (.*$)/gim, '<span style="font-size: 1.17em;"><strong>$1</strong></span>')
      .replace(/^## (.*$)/gim, '<span style="font-size: 1.5em;"><strong>$1</strong></span>')
      .replace(/^# (.*$)/gim, '<span style="font-size: 2em;"><strong>$1</strong></span>');

  // Convert bold and italic
  htmlContent = htmlContent
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')  // Convert double asterisks to bold
      .replace(/__(.*?)__/g, '<strong>$1</strong>')      // Convert double underscores to bold
      .replace(/\*(.*?)\*/g, '<em>$1</em>');      // Convert single asterisk to italic

  htmlContent = htmlContent
      .split('\n')
      .map(line => {
          if (line.startsWith('TOPICS: [')) {
              return line.replace(/\['|'\]|'/g, ''); // Remove ['...'] and single quotes
          }
          if (line.startsWith('SOURCE:')) {
              return line; // Skip markdown processing for SOURCE lines
          }
          return line.replace(/_(.*?)_/g, '<em>$1</em>');
      })
      .join('\n');
  
  // Convert links to open in new tab
  htmlContent = htmlContent.replace(/\[(.*?)\]\((.*?)\)/gim, '<a href="$2" target="_blank">$1</a>');

  // Convert newlines to <br> tags
  htmlContent = htmlContent.replace(/\n/g, '<br>');

  return htmlContent.trim();
}

// Returns HTML and plain text for an email
function processMarkdownToTextAndHtml(markdownString) {
  // Convert Markdown to HTML using the simple conversion function
  const htmlContent = simpleMarkdownToHtml(markdownString);
  
  // Extract the first line and make it a title tag
  const firstLine = htmlContent.split('<br>')[0];
  const titleTag = `<span style="font-size: 2em; font-weight: bold;">${firstLine}</span>`;
  const modHtmlContent = htmlContent.replace(firstLine, titleTag);
  
  // Remove Markdown syntax to get plain text
  const plainTextContent = markdownString
  .replace(/[*_]/g, '')  // Remove asterisks and underscores used for bold and italic
  .replace(/#/g, '')     // Remove hash symbols used for headings
  .replace(/\n/g, ' ');  // Replace newlines with spaces

  return {
      plainText: plainTextContent,
      html: modHtmlContent
  };
}


//// STYLING
function setButtonToStopState(button, icon) {
  button.classList.add('button-processing');
  button.classList.remove('button-initial');
  icon.textContent = 'stop_circle';
  icon.classList.add('icon-stop');
}

function resetButtonToInitialState(button, icon) {
  button.classList.remove('button-processing');
  button.classList.add('button-initial');
  icon.textContent = 'arrow_upward';
  icon.classList.remove('icon-stop');
  icon.classList.add('icon-arrow-up');
}


/// VALIDATION  - webflow-fof-site-body.js   12-14 0449 updated max lengths PREV 12-13 1707 email using validator library
// Sync with API Gateway Validation Rules in primary/aws_valid.py
var maxUserNameLength = 64;
var maxQuestionLength = 500;
var maxEmailLength = 254;
var maxFileNameLength = 255;

// Suspicious patterns to detect potential XSS or malicious input
const suspiciousPatterns = [
    /<script/i,
    /javascript:/i,
    /onerror=/i,
    /onclick=/i,
    /eval\(/i
];

// Input type validation rules
const INPUT_TYPES = {
    INPUT_TYPE_NAME: {
        allowedPattern: /[^\w\s.'\-()/]/g,  // Only letters, numbers, underscore, spaces, and hyphen the backslash is an escape character
        maxLength: maxUserNameLength,
        allowNewlines: false,
        description: 'letters, numbers, spaces, periods, hyphens, parentheses, and forward slashes'
    },
    INPUT_TYPE_PARAGRAPH: {
        allowedPattern: /[^\w\s.,!?@#'":;\-()[\]{}/\*_\p{Emoji}]/gu, // Added _ and * for markdown formatting
        maxLength: maxQuestionLength,
        allowNewlines: true,
        description: 'text with basic punctuation, markdown formatting (*, _), forward slashes, emojis, and formatting'
    },
    INPUT_TYPE_EMAIL: {
        // 12-13 1636 RT change to validator.js
        //allowedPattern: /[^a-zA-Z0-9.!#$%&'*+/=?^_{|}~@-]/g,  // Email-specific allowed chars (no spaces)
        maxLength: maxEmailLength,
        allowNewlines: false,
        description: 'valid email address characters'
    },
    INPUT_TYPE_FILENAME: {  // Add this new input type
        allowedPattern: /[^\w\s.'-]/g,  // Only letters, numbers, underscore, spaces, dots, and hyphen
        maxLength: maxFileNameLength,
        allowNewlines: false,
        description: 'letters, numbers, spaces, dots, and hyphens'
    }
};

function validateAndSanitizeInput(input, maxLength, fieldLabel, inputType = 'INPUT_TYPE_PARAGRAPH') {
    let messages = [];
    const rules = INPUT_TYPES[inputType] || INPUT_TYPES.INPUT_TYPE_PARAGRAPH;
    let wasModified = false;

    if (!input) {
        return {
            success: false,
            value: '',
            messages: [`${fieldLabel} cannot be empty.`]
        };
    }

    // 1. Check suspicious patterns
    for (const pattern of suspiciousPatterns) {
        if (pattern.test(input)) {
            notifySecurityAction('Suspicious Input', input);
            return {
                success: false,
                value: '',
                messages: [`Suspicious input detected in ${fieldLabel}. Please remove characters such as <, >, &, etc.`]
            };
        }
    }

    // 2. Trim and sanitize
    const beforeTrim = input;
    let sanitized = input.trim();
    const wasTrimmed = beforeTrim !== sanitized;

    // Special handling for email type
    if (inputType === 'INPUT_TYPE_EMAIL') {
        // Use validator.js for email validation
        if (!validator.isEmail(sanitized)) {
            return {
                success: false,
                value: sanitized,
                messages: [`Please enter a valid email address.`]
            };
        }
        // If valid email, no further character sanitization needed
        wasModified = wasTrimmed;
    } else {
        // For non-email types, track removed characters
        const beforeCharSanitize = sanitized;
        let removedChars = new Set();
        sanitized = sanitized.replace(rules.allowedPattern, (char) => {
            removedChars.add(char);
            return '';
        });
        
        const charChanges = beforeCharSanitize !== sanitized;
        wasModified = wasModified || charChanges;

        if (charChanges) {
            const removedCharsArray = Array.from(removedChars);
            console.log(`Removed characters:`, removedCharsArray);
            messages.push(`Removed invalid characters from ${fieldLabel}: ${removedCharsArray.join(' ')}`);
        }
        
        // Handle whitespace based on input type rules
        if (rules.allowNewlines) {
            const beforeWhitespace = sanitized;
            sanitized = sanitized.replace(/\r\n/g, '\n');
            const whitespaceChanges = beforeWhitespace !== sanitized;
            wasModified = wasModified || whitespaceChanges;
        } else {
            const beforeWhitespace = sanitized;
            sanitized = sanitized.replace(/[\n\r]+/g, ' ');
            const whitespaceChanges = beforeWhitespace !== sanitized;
            wasModified = wasModified || whitespaceChanges;
        }
    }

    // Log changes
    if (wasTrimmed || wasModified) {
        console.log(`validateAndSanitizeInput on ${fieldLabel} (${inputType}) - Changes detected:`);
        if (wasTrimmed) {
            console.log(`- Trimmed input`);
        }
        if (inputType !== 'INPUT_TYPE_EMAIL' && wasModified) {
            console.log(`- Removed invalid characters (only ${rules.description} allowed)`);
            messages.push(`Some invalid characters were removed from ${fieldLabel}.`);
        }
    } else {
        console.log(`validateAndSanitizeInput on ${fieldLabel} (${inputType}) - OK`);
    }

    // Enforce maxLength from rules
    const effectiveMaxLength = maxLength || rules.maxLength;
    if (effectiveMaxLength && sanitized.length > effectiveMaxLength) {
        sanitized = sanitized.substring(0, effectiveMaxLength);
        messages.push(`${fieldLabel} truncated to ${effectiveMaxLength} characters.`);
    }

    // Check if the result is empty after sanitization
    if (!sanitized) {
        messages.push(`${fieldLabel} cannot be empty after sanitization.`);
        return { success: false, value: '', messages };
    }

    return { success: true, value: sanitized, messages };
}

// ===== END OF FILE webflow-fof-site-body.js =====