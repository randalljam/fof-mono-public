import { buttonParamsMapping, SHOW_EMAIL_LIST_SIGNUP } from './demo-config.js';
import { ragFunctions } from './qrag-client.js';
import {
  adjustTextareaHeight,
  createAccordionItem,
  displayTempMessage,
  downloadMarkdown,
  replaceAccordionItem,
  resetButtonToInitialState,
  setButtonToStopState,
} from './qrag-ui.js';
import { checkPrivacyConsent, showConsentError } from './privacy-consent.js';
import {
  callHashStore,
  getStoredJWT,
  getUserContext,
  maxQuestionLength,
  validateAndSanitizeInput,
  waitForAuthReady,
} from './validation.js';
import { notifySecurityAction, notifyUserAction, sendEmail, toggleEmailInputVisibility } from './share-email.js';
import { saveQragChatIfSignedIn } from './qrag-persist.js';
import { API_ENDPOINTS } from './api-endpoints.js';
import { getAuthHeaders } from './validation.js';

function getElementIDTrailingString(elementId) {
  const underscoreIndex = elementId.indexOf('_');
  if (underscoreIndex === -1 || underscoreIndex === elementId.length - 1) return null;
  return elementId.substring(underscoreIndex + 1);
}

async function fetchIPAddress() {
  try {
    const response = await fetch('https://api.ipify.org?format=json');
    const data = await response.json();
    return data.ip;
  } catch (error) {
    console.error('Error fetching IP address:', error);
    return null;
  }
}

function logErrorToMonitoring(error, context) {
  const errorData = {
    timestamp: new Date().toISOString(),
    error: error.message,
    context,
    userAgent: navigator.userAgent,
    url: window.location.href,
  };
  fetch(API_ENDPOINTS.sendEmail, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      to_address: 'contact@focusonfoundations.org',
      email_subject: `Error in ${context}`,
      from_address: 'contact@focusonfoundations.org',
      email_body_plain: `An error occurred:\n\n${JSON.stringify(errorData, null, 2)}`,
      email_body_html: `<p>An error occurred:</p><pre>${JSON.stringify(errorData, null, 2)}</pre>`,
    }),
  }).catch((err) => console.error('Failed to send error email:', err));
}

function initDateRange(qragInputComponent, demo) {
  const dateRangeContainer = qragInputComponent.querySelector('.date-range-container');
  const startDate = qragInputComponent.querySelector('#start-date');
  const endDate = qragInputComponent.querySelector('#end-date');

  if (!demo.dateRange?.show) {
    if (dateRangeContainer) dateRangeContainer.style.display = 'none';
    sessionStorage.removeItem('qrag-start-date');
    sessionStorage.removeItem('qrag-end-date');
    return;
  }

  const { min, max } = demo.dateRange;
  startDate.min = min;
  startDate.max = max;
  endDate.min = min;
  endDate.max = max;
  sessionStorage.setItem('qrag-start-date', min);
  sessionStorage.setItem('qrag-end-date', max);
  startDate.value = min;
  endDate.value = max;

  startDate.addEventListener('change', function onStartChange() {
    endDate.min = this.value;
    if (endDate.value && endDate.value < this.value) endDate.value = this.value;
    sessionStorage.setItem('qrag-start-date', this.value);
    sessionStorage.setItem('qrag-end-date', endDate.value);
  });

  endDate.addEventListener('change', function onEndChange() {
    startDate.max = this.value;
    if (startDate.value && startDate.value > this.value) startDate.value = this.value;
    sessionStorage.setItem('qrag-start-date', startDate.value);
    sessionStorage.setItem('qrag-end-date', this.value);
  });
}

function initNumChunks(qragInputComponent) {
  const numChunksOptions = qragInputComponent.querySelectorAll('.num-chunks-option');
  const defaultNumChunksValue = '10';

  if (!sessionStorage.getItem('num-chunks')) {
    sessionStorage.setItem('num-chunks', defaultNumChunksValue);
  }

  function updateSelectedOption(selectedElement) {
    numChunksOptions.forEach((option) => option.classList.remove('selected'));
    selectedElement.classList.add('selected');
    sessionStorage.setItem('num-chunks', selectedElement.getAttribute('data-value'));
  }

  numChunksOptions.forEach((option) => {
    if (option.getAttribute('data-value') === sessionStorage.getItem('num-chunks')) {
      updateSelectedOption(option);
    }
    option.addEventListener('click', () => updateSelectedOption(option));
  });

  window.getSelectedNumChunksValue = () => sessionStorage.getItem('num-chunks') || defaultNumChunksValue;
}

// Accounts/auth replaced the old "nice name" identification: guests only accept
// the terms + privacy statement (no name entry). Accepting consent bootstraps
// the demo session — the hash-store call logs the consent event and returns the
// JWT the QRAG backends require.
function initGuestSession(botContainer) {
  let pending = null;
  window.ensureQragSession = async function ensureQragSession() {
    if (!checkPrivacyConsent()) return false;
    if (getStoredJWT()) return true;
    if (!pending) {
      pending = (async () => {
        let ipAddress = sessionStorage.getItem('userIPAddress');
        if (!ipAddress) {
          ipAddress = await fetchIPAddress();
          if (ipAddress) sessionStorage.setItem('userIPAddress', ipAddress);
        }
        await callHashStore(
          'guest',
          ipAddress,
          sessionStorage.getItem('inputUserEmail') || '',
          sessionStorage.getItem('emailListSignupChecked'),
          'accept_privacy_consent',
          sessionStorage.getItem('privacyConsent') || ''
        );
        return true;
      })().catch((error) => {
        console.error('ensureQragSession - Error:', error);
        pending = null;
        const errorElement = botContainer.querySelector('.botsubmit-error');
        if (errorElement) {
          errorElement.textContent = 'There was an error starting your session. Please try again.';
          errorElement.style.display = 'block';
          setTimeout(() => { errorElement.style.display = 'none'; }, 3000);
        }
        return false;
      });
    }
    return pending;
  };
  // Returning visitor with consent already stored: fetch the session token now
  // so the first question doesn't have to wait for it.
  if (checkPrivacyConsent() && !getStoredJWT()) window.ensureQragSession();
}

function submitInputRag(event, botContainer) {
  event.preventDefault();
  let submissionSucceeded = false;

  if (!checkPrivacyConsent()) {
    showConsentError(botContainer);
    return false;
  }

  // The guest-session bootstrap (consent event + QRAG token) must complete
  // before the request goes out; the submit chain awaits it below.
  const sessionReady = window.ensureQragSession ? window.ensureQragSession() : Promise.resolve(true);

  const submitButtonId = event.currentTarget.id;
  const trailingId = getElementIDTrailingString(submitButtonId);
  const userInputId = `inputText_${trailingId}`;
  const submitIconId = `submitIcon_${trailingId}`;
  const errorElement = document.getElementById(`submitError_${trailingId}`);
  const userInputField = document.getElementById(userInputId);
  const rawUserQuestion = userInputField.value;
  const questionCheck = validateAndSanitizeInput(rawUserQuestion, maxQuestionLength, 'Question', 'INPUT_TYPE_PARAGRAPH');

  if (questionCheck.success && questionCheck.messages.length > 0) {
    displayTempMessage(questionCheck.messages.join(' '), 'info', 3000, event.currentTarget);
  } else if (!questionCheck.success) {
    if (questionCheck.suspicious) {
      notifySecurityAction('Suspicious Input', questionCheck.rawInput, questionCheck.fieldLabel);
    }
    if (errorElement) {
      errorElement.style.display = 'block';
      errorElement.innerHTML = questionCheck.messages.join(' ');
      setTimeout(() => { errorElement.style.display = 'none'; }, 3000);
    }
    userInputField.value = rawUserQuestion;
    return;
  }

  const sanitizedQuestion = questionCheck.value;
  const numChunksValue = window.getSelectedNumChunksValue?.();
  const numChunksInteger = numChunksValue !== undefined ? parseInt(numChunksValue, 10) : undefined;
  const userEmailHmacHash = sessionStorage.getItem('userEmailHmacHash') || 'NA';

  const submitButton = document.getElementById(submitButtonId);
  const submitIcon = document.getElementById(submitIconId);
  setButtonToStopState(submitButton, submitIcon);

  const params = buttonParamsMapping[submitButtonId];
  const ragFunctionNames = params.ragFunction.split(',').map((func) => func.trim());

  const firstRagFunction = ragFunctions[ragFunctionNames[0]];
  Promise.resolve(sessionReady)
    .then(() => waitForAuthReady())
    .then(() => firstRagFunction(
      sanitizedQuestion,
      params.vector_index_name,
      params.route_dict_name,
      numChunksInteger,
      userEmailHmacHash,
      getUserContext()
    ))
    .then((firstJsonData) => {
      if (params.displayType === 'quoted-qa-then-ai-answer') {
        createAccordionItem(firstJsonData, submitButtonId, buttonParamsMapping);
      }
      if (ragFunctionNames.length === 2) {
        return ragFunctions[ragFunctionNames[1]](
          firstJsonData,
          params.large_context_filename,
          (retryResponse) => replaceAccordionItem(retryResponse, submitButtonId, buttonParamsMapping)
        );
      }
      return firstJsonData;
    })
    .then((finalJsonData) => {
      submissionSucceeded = true;
      if (finalJsonData.status === 'Error') {
        if (errorElement) {
          errorElement.style.display = 'block';
          errorElement.innerHTML = finalJsonData.message;
        }
        replaceAccordionItem(finalJsonData.response, submitButtonId, buttonParamsMapping);
      } else {
        replaceAccordionItem(finalJsonData, submitButtonId, buttonParamsMapping);
        saveQragChatIfSignedIn(submitButtonId, sanitizedQuestion, finalJsonData);
      }
    })
    .catch((error) => {
      console.error('submitInputRag - Fetch error:', error);
      logErrorToMonitoring(error, 'qrag-routing API call');
      if (errorElement) {
        let errorMessage = 'Apologies - an error occurred. We have been notified and will look into it. Please try again later or email contact@focusonfoundations.org if you would like to be notified when it is fixed.';
        if (error.message.includes('NETWORK_CHANGED_OR_UNREACHABLE')) {
          errorMessage = 'Your network connection changed while the request was being sent. Please try again.';
        } else if (error.message.includes('401') || error.message.includes('JWT')) {
          errorMessage = 'Your session token is missing or expired. Please refresh the page and try again.';
        }
        errorElement.style.display = 'block';
        errorElement.innerHTML = errorMessage;
        setTimeout(() => { errorElement.style.display = 'none'; }, 10000);
      }
      userInputField.value = rawUserQuestion;
    })
    .finally(() => {
      resetButtonToInitialState(submitButton, submitIcon);
      if (submissionSucceeded) {
        userInputField.value = '';
        adjustTextareaHeight(userInputField, 1, 20);
        userInputField.style.height = '';
      }
      adjustTextareaHeight(userInputField, 8, 20);
    });
}

function initShareActions(botContainer) {
  botContainer.addEventListener('click', (event) => {
    const button = event.target.closest('[data-action]');
    if (!button) return;
    if (button.dataset.action === 'download') {
      downloadMarkdown(botContainer, (actionType, content) => notifyUserAction(actionType, content, botContainer));
    }
    if (button.dataset.action === 'email') {
      toggleEmailInputVisibility(button, botContainer);
    }
    if (button.dataset.action === 'email-send') {
      sendEmail(botContainer);
    }
  });

  botContainer.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && event.target.classList.contains('email-input-address')) {
      event.preventDefault();
      sendEmail(botContainer);
    }
  });
}

export function initQragDemo(demo) {
  const botContainer = document.getElementById(demo.containerId);
  if (!botContainer) return;

  const qragInputComponent = botContainer.querySelector('.qrag-input-component');
  initDateRange(qragInputComponent, demo);
  initNumChunks(qragInputComponent);
  initGuestSession(botContainer);
  initShareActions(botContainer);

  const trailingId = demo.id;
  const textarea = qragInputComponent.querySelector('.botsubmit-textarea');
  const button = qragInputComponent.querySelector('.botsubmit-button');
  const icon = button.querySelector('.botsubmit-button-icon');
  const error = qragInputComponent.querySelector('.botsubmit-error');

  textarea.id = `inputText_${trailingId}`;
  button.id = demo.submitButtonId;
  if (icon) icon.id = `submitIcon_${trailingId}`;
  if (error) error.id = `submitError_${trailingId}`;

  textarea.addEventListener('input', () => adjustTextareaHeight(textarea, 8, 20));
  textarea.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      button.click();
    }
  });
  button.addEventListener('click', (event) => {
    submitInputRag(event, botContainer);
    button.blur();
  });

  if (!SHOW_EMAIL_LIST_SIGNUP) {
    botContainer.querySelectorAll('.email-checkbox-container').forEach((el) => {
      el.style.display = 'none';
    });
  }
}
