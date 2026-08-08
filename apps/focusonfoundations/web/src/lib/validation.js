import validator from 'validator';
import { API_ENDPOINTS } from './api-endpoints.js';
import { HASH_STORE_LOG_FILE_KEY, JWT_STORAGE_KEY } from './demo-config.js';

export const maxUserNameLength = 64;
export const maxQuestionLength = 500;
export const maxEmailLength = 254;
export const maxFileNameLength = 255;

const suspiciousPatterns = [
  /<script/i,
  /javascript:/i,
  /onerror=/i,
  /onclick=/i,
  /eval\(/i,
];

export const INPUT_TYPES = {
  INPUT_TYPE_NAME: {
    allowedPattern: /[^\w\s.'\-()/]/g,
    maxLength: maxUserNameLength,
    allowNewlines: false,
    description: 'letters, numbers, spaces, periods, hyphens, parentheses, and forward slashes',
  },
  INPUT_TYPE_PARAGRAPH: {
    allowedPattern: /[^\w\s.,!?@#'":;\-()[\]{}/\*_\p{Emoji}]/gu,
    maxLength: maxQuestionLength,
    allowNewlines: true,
    description: 'text with basic punctuation, markdown formatting (*, _), forward slashes, emojis, and formatting',
  },
  INPUT_TYPE_EMAIL: {
    maxLength: maxEmailLength,
    allowNewlines: false,
    description: 'valid email address characters',
  },
  INPUT_TYPE_FILENAME: {
    allowedPattern: /[^\w\s.'-]/g,
    maxLength: maxFileNameLength,
    allowNewlines: false,
    description: 'letters, numbers, spaces, dots, and hyphens',
  },
};

export function validateAndSanitizeInput(input, maxLength, fieldLabel, inputType = 'INPUT_TYPE_PARAGRAPH') {
  const messages = [];
  const rules = INPUT_TYPES[inputType] || INPUT_TYPES.INPUT_TYPE_PARAGRAPH;
  let wasModified = false;

  if (!input) {
    return {
      success: false,
      value: '',
      messages: [`${fieldLabel} cannot be empty.`],
    };
  }

  for (const pattern of suspiciousPatterns) {
    if (pattern.test(input)) {
      return {
        success: false,
        value: '',
        messages: [`Suspicious input detected in ${fieldLabel}. Please remove characters such as <, >, &, etc.`],
        suspicious: true,
        rawInput: input,
        fieldLabel,
      };
    }
  }

  const beforeTrim = input;
  let sanitized = input.trim();
  const wasTrimmed = beforeTrim !== sanitized;

  if (inputType === 'INPUT_TYPE_EMAIL') {
    if (!validator.isEmail(sanitized)) {
      return {
        success: false,
        value: sanitized,
        messages: ['Please enter a valid email address.'],
      };
    }
    wasModified = wasTrimmed;
  } else {
    const beforeCharSanitize = sanitized;
    const removedChars = new Set();
    sanitized = sanitized.replace(rules.allowedPattern, (char) => {
      removedChars.add(char);
      return '';
    });
    const charChanges = beforeCharSanitize !== sanitized;
    wasModified = wasModified || charChanges;
    if (charChanges) {
      messages.push(`Removed invalid characters from ${fieldLabel}: ${Array.from(removedChars).join(' ')}`);
    }
    if (rules.allowNewlines) {
      sanitized = sanitized.replace(/\r\n/g, '\n');
    } else {
      sanitized = sanitized.replace(/[\n\r]+/g, ' ');
    }
  }

  const effectiveMaxLength = maxLength || rules.maxLength;
  if (effectiveMaxLength && sanitized.length > effectiveMaxLength) {
    sanitized = sanitized.substring(0, effectiveMaxLength);
    messages.push(`${fieldLabel} truncated to ${effectiveMaxLength} characters.`);
  }

  if (!sanitized) {
    messages.push(`${fieldLabel} cannot be empty after sanitization.`);
    return { success: false, value: '', messages };
  }

  return { success: true, value: sanitized, messages, wasModified: wasModified || wasTrimmed };
}

export function getStoredJWT() {
  return sessionStorage.getItem(JWT_STORAGE_KEY);
}

export function getAuthHeaders() {
  const jwt = getStoredJWT();
  const headers = { 'Content-Type': 'application/json' };
  if (jwt) {
    headers.Authorization = `Bearer ${jwt}`;
  }
  return headers;
}

// In-flight hash-store call, so question submits can wait for the JWT it
// returns instead of racing it (a fast submit after consent+name otherwise
// goes out with no Authorization header and gets a 401).
let pendingHashStore = null;
export function waitForAuthReady() {
  return pendingHashStore ? pendingHashStore.catch(() => {}) : Promise.resolve();
}

export async function callHashStore(userNiceName, userIPAddress, inputUserEmail = '', emailListSignupChecked = null, eventType, privacyConsent) {
  const promise = callHashStoreInner(userNiceName, userIPAddress, inputUserEmail, emailListSignupChecked, eventType, privacyConsent);
  pendingHashStore = promise;
  try {
    return await promise;
  } finally {
    if (pendingHashStore === promise) pendingHashStore = null;
  }
}

async function callHashStoreInner(userNiceName, userIPAddress, inputUserEmail, emailListSignupChecked, eventType, privacyConsent) {
  const payload = {
    key: HASH_STORE_LOG_FILE_KEY,
    s3_path: '',
    userNiceName,
    userIPAddress,
    inputUserEmail: inputUserEmail || '',
    emailListSignupChecked,
    eventType,
    privacyConsent,
  };

  const response = await fetch(API_ENDPOINTS.hashStore, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const data = await response.json();
  if (data.jwtToken) {
    sessionStorage.setItem(JWT_STORAGE_KEY, data.jwtToken);
  }
  if (data.hashed_values) {
    sessionStorage.setItem('hashedUserNiceName', data.hashed_values.hashedUserNiceName);
    sessionStorage.setItem('hashedUserIPAddress', data.hashed_values.hashedUserIPAddress);
    if (inputUserEmail) {
      sessionStorage.setItem('hashedInputUserEmail', data.hashed_values.hashedInputUserEmail);
    }
  }
  return data.hashed_values;
}

export function getUserContext() {
  return {
    hashedUserNiceName: sessionStorage.getItem('hashedUserNiceName') || 'NA',
    hashedUserIPAddress: sessionStorage.getItem('hashedUserIPAddress') || 'NA',
    hashedInputUserEmail: sessionStorage.getItem('hashedInputUserEmail') || 'NA',
  };
}
