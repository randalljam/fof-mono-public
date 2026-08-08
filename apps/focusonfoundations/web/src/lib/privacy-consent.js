import { PRIVACY_CONSENT_VERSION_DATE } from './demo-config.js';

export function checkPrivacyConsent() {
  return sessionStorage.getItem('privacyConsent') === PRIVACY_CONSENT_VERSION_DATE;
}

export function setPrivacyConsent() {
  sessionStorage.setItem('privacyConsent', PRIVACY_CONSENT_VERSION_DATE);
  document.querySelectorAll('.privacy-consent-box').forEach((el) => {
    el.style.display = 'none';
  });
}

export function showConsentError(container) {
  const errorElement = container?.querySelector('.botsubmit-error') || container?.querySelector('.consent-error');
  if (errorElement) {
    errorElement.textContent = 'Please review and accept the Privacy Policy and Terms of Service to continue.';
    errorElement.style.display = 'block';
    setTimeout(() => { errorElement.style.display = 'none'; }, 3000);
  }
}

export function initPrivacyConsent(root = document) {
  const consentBox = root.querySelector('.privacy-consent-box');
  if (!consentBox) return;

  if (checkPrivacyConsent()) {
    consentBox.style.display = 'none';
    return;
  }

  const checkbox = consentBox.querySelector('#privacy-consent');
  if (checkbox) {
    checkbox.addEventListener('change', () => {
      if (checkbox.checked) {
        setPrivacyConsent();
        // Accepting consent starts the guest session (fetches the QRAG token).
        if (typeof window.ensureQragSession === 'function') {
          window.ensureQragSession();
        }
      }
    });
  }
}
