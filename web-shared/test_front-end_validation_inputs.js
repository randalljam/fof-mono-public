/// VALIDATION  - webflow-fof-site-body.js   12-14 0449 updated max lengths PREV 12-13 1707 email using validator library
var maxUserNameLength = 64;
var maxQuestionLength = 500;

/////////////////////////////////////////////////////////////////////
// IMPORTANT - REMOVE THIS FROM WEBFLOW-FOW-SITE-BODY.JS
/////////////////////////////////////////////////////////////////////
const validator = require('validator');

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
        allowedPattern: /[^\w\s.'-()]/g,  // Only letters, numbers, underscore, spaces, and hyphen
        maxLength: maxUserNameLength,
        allowNewlines: false,
        description: 'letters, numbers, spaces, and hyphens'
    },
    INPUT_TYPE_PARAGRAPH: {
        allowedPattern: /[^\w\s.,!?@#'":;\-()[\]{}\p{Emoji}]/gu,  // More permissive
        maxLength: maxQuestionLength,
        allowNewlines: true,
        description: 'text with basic punctuation, emojis, and formatting'
    },
    INPUT_TYPE_EMAIL: {
        // 12-13 1636 RT change to validator.js
        //allowedPattern: /[^a-zA-Z0-9.!#$%&'*+/=?^_{|}~@-]/g,  // Email-specific allowed chars (no spaces)
        maxLength: 254,
        allowNewlines: false,
        description: 'valid email address characters'
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
        // For non-email types, continue with existing character sanitization
        const beforeCharSanitize = sanitized;
        sanitized = sanitized.replace(rules.allowedPattern, '');
        const charChanges = beforeCharSanitize !== sanitized;
        wasModified = wasModified || charChanges;
        
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

/////////////////////////////////////////////////////////////////////
////// DO NOT COPY BELOW TEST CODE TO WEBFLOW-FOW-SITE-BODY.JS //////
/////////////////////////////////////////////////////////////////////

// Test version of security notification function
function notifySecurityAction(type, content) {
    console.log('\x1b[33m%s\x1b[0m', `[SECURITY ALERT] ${type}: Suspicious input detected`);
    console.log('\x1b[33m%s\x1b[0m', `[SECURITY ALERT] Content sample: ${content.substring(0, 50)}${content.length > 50 ? '...' : ''}`);
}

// Enhanced test framework
function assert(condition, message, expected, actual) {
    const result = condition ? '\x1b[32m✓\x1b[0m' : '\x1b[31m✗\x1b[0m';
    // Add detailed input/output logging
    console.log('\n=== Test: ' + message + ' ===');
    if (actual.input) console.log('Input:           ', JSON.stringify(actual.input));
    if (actual.value !== undefined) console.log('Sanitized output:', JSON.stringify(actual.value));
    if (actual.messages && actual.messages.length) console.log('Messages:', actual.messages);
    console.log('Result:', `${result} ${message}`);
    
    if (!condition && expected !== undefined) {
        console.log('  Expected:', JSON.stringify(expected));
        console.log('  Actual:  ', JSON.stringify(actual));
    }
    console.log('-------------------');
    return condition;
}

function runTests() {
    console.log('\nRunning validation tests...\n');
    let failedTests = 0;

    // ==== COMMON TESTS (ALL INPUT TYPES) ====
    console.log('=== Testing Common Validations (All Input Types) ===\n');

    // Test empty input (for each type)
    ['INPUT_TYPE_NAME', 'INPUT_TYPE_PARAGRAPH', 'INPUT_TYPE_EMAIL'].forEach(inputType => {
        let input = '';
        let result = validateAndSanitizeInput(input, null, 'Field', inputType);
        assert(
            result.success === false && 
            result.messages[0].includes('cannot be empty'),
            `[${inputType}] Should reject empty input`,
            result,
            { ...result, input }
        ) || failedTests++;
    });

    // Test trimming (for each type except email)
    ['INPUT_TYPE_NAME', 'INPUT_TYPE_PARAGRAPH'].forEach(inputType => {
        let input = '  Test Value  \n\n';
        let result = validateAndSanitizeInput(input, null, 'Field', inputType);
        assert(
            result.success === true && 
            !result.value.startsWith(' ') && 
            !result.value.endsWith(' '),
            `[${inputType}] Should trim leading/trailing whitespace`,
            result,
            { ...result, input }
        ) || failedTests++;
    });

    // Test suspicious patterns (for each type)
    ['INPUT_TYPE_NAME', 'INPUT_TYPE_PARAGRAPH', 'INPUT_TYPE_EMAIL'].forEach(inputType => {
        let input = '<script>alert("XSS")</script>';
        let result = validateAndSanitizeInput(input, null, 'Field', inputType);
        assert(
            result.success === false && 
            result.messages[0].includes('Suspicious input detected'),
            `[${inputType}] Should detect and reject suspicious input`,
            result,
            { ...result, input }
        ) || failedTests++;
    });

    // ==== INPUT_TYPE_NAME SPECIFIC TESTS ====
    console.log('\n=== Testing INPUT_TYPE_NAME Specific Validations ===\n');

    // Test valid name
    let input = 'John Doe';
    let result = validateAndSanitizeInput(input, null, 'Name', 'INPUT_TYPE_NAME');
    assert(
        result.success === true && 
        result.value === 'John Doe',
        '[INPUT_TYPE_NAME] Should accept valid name',
        result,
        { ...result, input }
    ) || failedTests++;

    // Test name with invalid characters
    input = 'John$$$Doe@';
    result = validateAndSanitizeInput(input, null, 'Name', 'INPUT_TYPE_NAME');
    assert(
        result.success === true && 
        result.value === 'JohnDoe' && 
        result.messages[0].includes('invalid characters were removed'),
        '[INPUT_TYPE_NAME] Should remove invalid characters',
        { success: true, value: 'JohnDoe', messages: ['Some invalid characters were removed from Name.'], input: 'John$$$Doe@' },
        { ...result, input }
    ) || failedTests++;

    // Test name with newlines
    input = 'John\nDoe\nSmith';
    result = validateAndSanitizeInput(input, null, 'Name', 'INPUT_TYPE_NAME');
    assert(
        result.success === true && 
        result.value === 'John Doe Smith',
        '[INPUT_TYPE_NAME] Should replace newlines with spaces',
        result,
        { ...result, input }
    ) || failedTests++;

    // ==== INPUT_TYPE_PARAGRAPH SPECIFIC TESTS ====
    console.log('\n=== Testing INPUT_TYPE_PARAGRAPH Specific Validations ===\n');

    // Test paragraph with preserved formatting
    input = 'Line one\n  Line two\n    Line three';
    result = validateAndSanitizeInput(input, null, 'Paragraph', 'INPUT_TYPE_PARAGRAPH');
    assert(
        result.success === true && 
        result.value === 'Line one\n  Line two\n    Line three',
        '[INPUT_TYPE_PARAGRAPH] Should preserve interior whitespace and newlines',
        result,
        { ...result, input }
    ) || failedTests++;

    // Test paragraph with emojis
    input = 'Hello 👋 World 🌍!';
    result = validateAndSanitizeInput(input, null, 'Paragraph', 'INPUT_TYPE_PARAGRAPH');
    assert(
        result.success === true && 
        result.value === 'Hello 👋 World 🌍!',
        '[INPUT_TYPE_PARAGRAPH] Should preserve emojis',
        result,
        { ...result, input }
    ) || failedTests++;

    // ==== INPUT_TYPE_EMAIL SPECIFIC TESTS ====
    console.log('\n=== Testing INPUT_TYPE_EMAIL Specific Validations ===\n');

    // Test email with dots
    input = 'test.dot@example.com';
    result = validateAndSanitizeInput(input, null, 'Email', 'INPUT_TYPE_EMAIL');
    assert(
        result.success === true && 
        result.value === 'test.dot@example.com',
        '[INPUT_TYPE_EMAIL] Should accept email with dots',
        result,
        { ...result, input }
    ) || failedTests++;

    // Test email with plus
    input = 'name+test@mydomain.com';
    result = validateAndSanitizeInput(input, null, 'Email', 'INPUT_TYPE_EMAIL');
    assert(
        result.success === true && 
        result.value === 'name+test@mydomain.com',
        '[INPUT_TYPE_EMAIL] Should accept email with plus',
        result,
        { ...result, input }
    ) || failedTests++;

    // Test email with hyphen and subdomain
    input = 'name.with-hyphen@site.co.uk';
    result = validateAndSanitizeInput(input, null, 'Email', 'INPUT_TYPE_EMAIL');
    assert(
        result.success === true && 
        result.value === 'name.with-hyphen@site.co.uk',
        '[INPUT_TYPE_EMAIL] Should accept email with hyphen and subdomain',
        result,
        { ...result, input }
    ) || failedTests++;

    // Test email with special characters
    input = 'complex!#$%&\'*+-/=?^_`{|}~@weird.email';
    result = validateAndSanitizeInput(input, null, 'Email', 'INPUT_TYPE_EMAIL');
    assert(
        result.success === true && 
        result.value === 'complex!#$%&\'*+-/=?^_`{|}~@weird.email',
        '[INPUT_TYPE_EMAIL] Should accept email with special characters',
        result,
        { ...result, input }
    ) || failedTests++;
    // Test email with spaces
    input = 'no@spaces allowed@email.com';
    result = validateAndSanitizeInput(input, null, 'Email', 'INPUT_TYPE_EMAIL');
    assert(
        result.success === false,
        '[INPUT_TYPE_EMAIL] Should reject email with spaces',
        result,
        { ...result, input }
    ) || failedTests++;

    // Test email missing domain
    input = 'missing@';
    result = validateAndSanitizeInput(input, null, 'Email', 'INPUT_TYPE_EMAIL');
    assert(
        result.success === false,
        '[INPUT_TYPE_EMAIL] Should reject email missing domain',
        result,
        { ...result, input }
    ) || failedTests++;

    // Test email missing local part
    input = '@nodomain.com';
    result = validateAndSanitizeInput(input, null, 'Email', 'INPUT_TYPE_EMAIL');
    assert(
        result.success === false,
        '[INPUT_TYPE_EMAIL] Should reject email missing local part',
        result,
        { ...result, input }
    ) || failedTests++;

    // Test email with consecutive dots
    input = 'double..dots@domain.com';
    result = validateAndSanitizeInput(input, null, 'Email', 'INPUT_TYPE_EMAIL');
    assert(
        result.success === false,
        '[INPUT_TYPE_EMAIL] Should reject email with consecutive dots',
        result,
        { ...result, input }
    ) || failedTests++;

    // Test email with invalid special chars
    input = 'too<many>special@chars.com';
    result = validateAndSanitizeInput(input, null, 'Email', 'INPUT_TYPE_EMAIL');
    assert(
        result.success === false,
        '[INPUT_TYPE_EMAIL] Should reject email with invalid special characters',
        result,
        { ...result, input }
    ) || failedTests++;

    // Test very long email
    input = 'verylongemailaddressmorethan254charactersisnotallowedbyemailstandardsverylongemailaddressmorethan254charactersisnotallowedbyemailstandardsverylongemailaddressmorethan254charactersisnotallowedbyemailstandardsverylongemailaddressmorethan254charactersisnotallowed@domain.com';
    result = validateAndSanitizeInput(input, null, 'Email', 'INPUT_TYPE_EMAIL');
    assert(
        result.success === false,
        '[INPUT_TYPE_EMAIL] Should reject email longer than 254 characters',
        result,
        { ...result, input }
    ) || failedTests++;

    // Test maximum username length
    input = 'a'.repeat(maxUserNameLength + 1);  // One character over limit
    result = validateAndSanitizeInput(input, null, 'Name', 'INPUT_TYPE_NAME');
    assert(
        result.success === true && 
        result.value.length === maxUserNameLength &&
        result.messages[0].includes('truncated'),
        '[INPUT_TYPE_NAME] Should truncate username longer than maxUserNameLength',
        result,
        { ...result, input }
    ) || failedTests++;

    // Test maximum question length
    input = 'a'.repeat(maxQuestionLength + 1);  // One character over limit
    result = validateAndSanitizeInput(input, null, 'Question', 'INPUT_TYPE_PARAGRAPH');
    assert(
        result.success === true && 
        result.value.length === maxQuestionLength &&
        result.messages[0].includes('truncated'),
        '[INPUT_TYPE_PARAGRAPH] Should truncate text longer than maxQuestionLength',
        result,
        { ...result, input }
    ) || failedTests++;

    console.log(`\nTests completed. ${failedTests} tests failed.\n`);
}

runTests();