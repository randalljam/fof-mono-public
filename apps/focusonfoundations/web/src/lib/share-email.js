import { API_ENDPOINTS } from './api-endpoints.js';
import { buttonParamsMapping } from './demo-config.js';
import { getAuthHeaders, validateAndSanitizeInput } from './validation.js';
import { processMarkdownToTextAndHtml } from './qrag-ui.js';

function setSendButtonLoading(sendButton, loading) {
  if (!sendButton) return;
  const icon = sendButton.querySelector('.material-symbols-rounded');
  sendButton.disabled = loading;
  if (loading) {
    sendButton.classList.add('is-sending');
    if (icon) icon.textContent = 'progress_activity';
  } else {
    sendButton.classList.remove('is-sending');
    if (icon) icon.textContent = 'send';
  }
}

function showEmailStatus(statusEl, message, type, autoHideMs) {
  if (!statusEl) return;
  statusEl.textContent = message;
  statusEl.className = `email-status email-status--${type}`;
  statusEl.style.display = 'block';
  if (statusEl.hideTimeout) clearTimeout(statusEl.hideTimeout);
  if (autoHideMs) {
    statusEl.hideTimeout = setTimeout(() => {
      statusEl.style.display = 'none';
    }, autoHideMs);
  }
}

export async function sendEmail(botContainer) {
  const emailContainer = botContainer.querySelector('.email-send-container');
  if (!emailContainer) return;
  const emailInputAddress = emailContainer.querySelector('.email-input-address');
  const sendButton = emailContainer.querySelector('.email-send-button');
  const statusEl = botContainer.querySelector('.email-status');

  const emailCheck = validateAndSanitizeInput(
    emailInputAddress.value,
    null,
    'Email Address',
    'INPUT_TYPE_EMAIL'
  );

  if (!emailCheck.success) {
    showEmailStatus(statusEl, emailCheck.messages.join(' '), 'error');
    return;
  }

  const sanitizedEmail = emailCheck.value;
  setSendButtonLoading(sendButton, true);
  showEmailStatus(statusEl, 'Sending…', 'info');

  try {
    sessionStorage.setItem('inputUserEmail', sanitizedEmail);
    const userNiceName = sessionStorage.getItem('userNiceName') || '';
    const userIPAddress = sessionStorage.getItem('userIPAddress') || '';
    const emailListSignupChecked = sessionStorage.getItem('emailListSignupChecked') === 'true';
    const privacyConsent = sessionStorage.getItem('privacyConsent') || '';

    const { callHashStore } = await import('./validation.js');
    await callHashStore(
      userNiceName,
      userIPAddress,
      sanitizedEmail,
      emailListSignupChecked,
      'submit_user_email',
      privacyConsent
    );

    const hiddenDiv = botContainer.querySelector('.hidden-div');
    const emailContent = processMarkdownToTextAndHtml(hiddenDiv.textContent);
    const emailPrelude = 'Below is the requested content. If you did not request this content, please reply to this email stating that, and let us know if you would like to prevent this email address from receiving any further messages.';
    const payload = {
      to_address: sanitizedEmail,
      email_subject: 'Your Deutsch QRAG Demo Questions and Answers - from focusonfoundations.org',
      from_address: 'contact@focusonfoundations.org',
      email_body_plain: `${emailPrelude}\n\n${emailContent.plainText}`,
      email_body_html: `<p>${emailPrelude.replace(/\n/g, '<br>')}</p><br>${emailContent.html}`,
    };

    const response = await fetch(API_ENDPOINTS.sendEmail, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    setSendButtonLoading(sendButton, false);
    showEmailStatus(statusEl, 'Email sent successfully!', 'success', 5000);
    notifyUserAction('Email', hiddenDiv.textContent, botContainer);
  } catch (error) {
    console.error('sendEmail - Error:', error);
    setSendButtonLoading(sendButton, false);
    showEmailStatus(statusEl, 'Failed to send email. Please try again.', 'error');
  }
}

export async function notifyUserAction(actionType, actionContent, botContainer) {
  try {
    const submitButton = botContainer.querySelector('button[id^="submitButton_"]');
    const actionSource = buttonParamsMapping[submitButton.id].botTitle;
    const formattedContent = processMarkdownToTextAndHtml(actionContent);
    const payload = {
      to_address: 'contact@focusonfoundations.org',
      email_subject: `User ${actionType} Action - ${actionSource}`,
      from_address: 'contact@focusonfoundations.org',
      email_body_plain: `User Action Details:\n- Action Type: ${actionType}\n- Action Source: ${actionSource}\n\nUser Action Content:\n${formattedContent.plainText}`,
      email_body_html: `<h3>User Action Details:</h3><ul><li><strong>Action Type:</strong> ${actionType}</li><li><strong>Action Source:</strong> ${actionSource}</li></ul><h3>User Action Content:</h3>${formattedContent.html}`,
    };

    await fetch(API_ENDPOINTS.sendEmail, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });
  } catch (error) {
    console.error('Error sending notification:', error);
  }
}

export async function notifySecurityAction(actionType, suspiciousContent, inputField = '') {
  try {
    const payload = {
      to_address: 'contact@focusonfoundations.org',
      email_subject: `[SECURITY ALERT] ${actionType} Detected on ${window.location.pathname}`,
      from_address: 'contact@focusonfoundations.org',
      email_body_plain: `Security Alert: ${actionType}\nField: ${inputField}\nContent: ${suspiciousContent}`,
      email_body_html: `<p>Security Alert: ${actionType}</p><pre>${suspiciousContent}</pre>`,
    };
    await fetch(API_ENDPOINTS.sendEmail, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });
  } catch (error) {
    console.error('Error in notifySecurityAction:', error);
  }
}

export function toggleEmailInputVisibility(emailButton, botContainer) {
  const emailContainer = botContainer.querySelector('.email-send-container');
  if (!emailContainer) return;
  const emailInput = emailContainer.querySelector('.email-input-address');
  const emailCheckboxContainer = botContainer.querySelector('.email-checkbox-container');
  const statusEl = botContainer.querySelector('.email-status');

  const isHidden = emailContainer.style.display === 'none' || !emailContainer.style.display;
  if (isHidden) {
    emailContainer.style.display = 'inline-flex';
    if (statusEl) {
      statusEl.style.display = 'none';
      statusEl.textContent = '';
    }
    const storedEmail = sessionStorage.getItem('inputUserEmail');
    if (storedEmail) {
      emailInput.value = storedEmail;
      if (emailCheckboxContainer) emailCheckboxContainer.style.display = 'none';
    } else {
      emailInput.value = '';
      if (emailCheckboxContainer) {
        emailCheckboxContainer.style.display = 'flex';
        const checkbox = emailCheckboxContainer.querySelector('.email-checkbox');
        checkbox?.addEventListener('change', function onChange() {
          if (this.checked) {
            sessionStorage.setItem('emailListSignupChecked', 'true');
          }
        });
      }
    }
    emailInput.focus();
  } else {
    emailContainer.style.display = 'none';
    if (emailCheckboxContainer) emailCheckboxContainer.style.display = 'none';
  }
}
