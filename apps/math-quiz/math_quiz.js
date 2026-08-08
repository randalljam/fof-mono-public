// START OF FILE math_quiz.js

var fileInfo = `math_quiz.js 1-31-2025 fixed duplicate problem bug`;
console.log('JavaScript file loaded. ', fileInfo);

// Function to dynamically load external scripts
function loadScript(url) {
    return new Promise(function(resolve, reject) {
        let script = document.createElement('script');
        script.src = url;
        script.onload = function() {
            console.log(`${url} loaded successfully`);
            resolve();
        };
        script.onerror = function() {
            console.error(`Failed to load script ${url}`);
            reject(new Error(`Failed to load script ${url}`));
        };
        document.head.appendChild(script);
    });
}

// Load external libraries
async function loadExternalLibraries() {
    try {
        await loadScript('https://cdnjs.cloudflare.com/ajax/libs/blueimp-md5/2.19.0/js/md5.min.js');
        await loadScript('https://cdnjs.cloudflare.com/ajax/libs/jszip/3.7.1/jszip.min.js');
        await loadScript('https://cdn.jsdelivr.net/npm/canvas-confetti@1.5.1/dist/confetti.browser.min.js');

        // Check if confetti library loaded successfully
        if (typeof confetti !== 'undefined') {
            console.log("Confetti library loaded successfully");
        } else {
            console.error("Failed to load confetti library");
        }
    } catch (error) {
        console.error("Error loading external libraries:", error);
    }
}

// Global variables
let settings = {
    audioEnabled: false,
    speechDetectionEnabled: false,
    autoSubmitOnLength: true,
    problem_list: []
};
let sessionData = {};
let problemsAttempted = [];
let usedProblems = new Set();
let problemIndex = 0;
let startTime, endTime;
let problemData;
let uploadedProblemList = [];
let uploadedProblemListMetadata = null;

// Add these global variables near the top of your file
let recognition;
let isListening = false;
// Guards against double submission of the same problem (Enter key, auto-submit,
// and continuous speech recognition can all fire submitAnswer)
let answerSubmitted = true;

const FLAG_LABELS = {
    distracted: 'Distracted',
    interrupted: 'Interrupted',
    error: 'Input Error',
    stall: 'Stall',
    dontknow: "I Don't Know",  // Used by button only, not in dropdown
    other: 'Other'
};

const FLAG_OPTIONS = [
    { value: '', label: 'No flag' },
    { value: 'distracted', label: FLAG_LABELS.distracted },
    { value: 'interrupted', label: FLAG_LABELS.interrupted },
    { value: 'error', label: FLAG_LABELS.error },
    { value: 'stall', label: FLAG_LABELS.stall },
    { value: 'other', label: FLAG_LABELS.other }
];

function navigateToAnalysis() {
    console.log('Navigating to analysis page');
    let targetUrl = useLocalMathQuizPages() ? 'math_analysis.html' : 'https://www.focusonfoundations.org/math-analysis';
    console.log('Target URL:', targetUrl);
    window.location.href = targetUrl;
}

// Modify the setupAnalysisButtons function
function setupAnalysisButtons() {
    console.log('Setting up analysis buttons');
    document.body.addEventListener('click', function(event) {
        if (event.target.classList.contains('do-analysis-button')) {
            console.log('Analysis button clicked');
            navigateToAnalysis();
        }
    });
}

// Modify the runAssessment function to hide the initial analysis button
function runAssessment() {
    console.log("Starting assessment");
    problemsAttempted = [];
    usedProblems.clear();
    problemIndex = 0;
    if (!Array.isArray(settings.problem_list)) {
        settings.problem_list = [];
    }
    // Hide initial analysis button if it exists
    const initialAnalysisButton = document.getElementById('do-analysis-initial');
    if (initialAnalysisButton) {
        initialAnalysisButton.classList.add('hidden');
    }
    
    // Clear the welcome message
    document.getElementById('messages').innerHTML = '';

    // Hide user inputs and show quiz section
    const userInputs = document.getElementById('app-screens');
    const quizSection = document.getElementById('quiz-section');
    if (userInputs) userInputs.classList.add('hidden');
    if (quizSection) quizSection.classList.remove('hidden');

    // Add the end quiz button
    let endQuizBtn = document.getElementById('end-quiz-btn');
    if (!endQuizBtn) {
        endQuizBtn = document.createElement('button');
        endQuizBtn.id = 'end-quiz-btn';
        endQuizBtn.className = 'btn btn-end-quiz';
        endQuizBtn.textContent = 'End Quiz';
        endQuizBtn.addEventListener('click', handleEndQuizEarly);
        document.getElementById('container').appendChild(endQuizBtn);
    }

    // Initialize session data
    sessionData = {
        version: "1.1",
        user: {
            name: sessionData.user ? sessionData.user.name : "Unknown"
        },
        session: {
            id: generateUUID(),
            start_time: getCurrentDatetimeFileFriendly(),
            end_time: null,  // Will be set at the end of the assessment
            settings: settings
        }
    };

    // Start the first problem
    nextProblem();
}

// Initialize the quiz
async function initQuiz() {
    console.log("initQuiz function called");
    await loadExternalLibraries();
    setupSpeechRecognition();
    setupAnalysisButtons(); // Set up event handlers once
    getUsername();
}

// Add this function to set up speech recognition
function setupSpeechRecognition() {
    window.SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if ('SpeechRecognition' in window) {
        recognition = new window.SpeechRecognition();
        recognition.lang = 'en-US';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;
        recognition.continuous = true;

        recognition.onstart = function() {
            console.log('Speech recognition started. Microphone is now active.');
        };

        recognition.onend = function() {
            console.log('Speech recognition ended.');
            isListening = false;
            document.getElementById('start-listening').style.display = 'inline-block';
            document.getElementById('stop-listening').style.display = 'none';
        };

        recognition.onresult = function(event) {
            const transcript = event.results[event.results.length - 1][0].transcript;
            console.log('Speech recognized:', transcript);
            handleUserAnswer(transcript);
        };

        recognition.onerror = function(event) {
            console.log('Speech recognition error:', event.error);
            if (event.error === 'no-speech') {
                // Handle the no-speech error silently
                stopListening();
            } else {
                console.error('Speech recognition error:', event.error);
            }
        };

        console.log('Speech recognition set up successfully');
    } else {
        console.log('Speech recognition not supported');
    }

}

// Utility functions
function displayMessage(message) {
    const messagesEl = document.getElementById('messages');
    if (!messagesEl) {
        console.warn('displayMessage: messages element not found');
        return;
    }
    messagesEl.innerHTML = message;
}

function appendMessage(message) {
    const messagesEl = document.getElementById('messages');
    if (!messagesEl) {
        console.warn('appendMessage: messages element not found');
        return;
    }
    messagesEl.innerHTML += '<br>' + message;
}

function getUsername() {
    displayMessage('');

    const defaultNames = ['test', 'Kid1', 'Randy', 'TL'];
    
    // Retrieve names from localStorage or use default if empty
    let allNames = JSON.parse(localStorage.getItem('allNames') || 'null');
    
    // If allNames is null (first time load), initialize with defaultNames
    if (allNames === null) {
        allNames = [...defaultNames];
        localStorage.setItem('allNames', JSON.stringify(allNames));
    }
    
    console.log('Initial allNames:', allNames);

    const userInputs = document.getElementById('app-screens');  // Update ID
    userInputs.innerHTML = `
        <div class="welcome-screen">  <!-- New wrapper class -->
            <h2 class="welcome">Welcome to the Arithmetic Fluency Assessment Tool!</h2>
            <div class="name-selection">  <!-- New semantic class -->
                <label>Select a preset or choose 'Custom': </label>
                <br>
                <select id="username-select" class="input-select">
                    ${allNames.map(name => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('')}
                </select>
                <input type="text" id="username-input" class="input-text" placeholder="Enter new name here">
            </div>
            <div class="action-buttons">  <!-- New semantic class -->
                <button id="continue-button" class="btn btn-success">Continue</button>
                <button id="download-all-json-initial" class="btn btn-download">Download All Sessions Data</button>
                <button id="clear-all-sessions-initial" class="btn btn-clear">Clear All Sessions</button>
                <button id="do-analysis-initial" class="btn btn-primary do-analysis-button">Go To Analysis</button>
            </div>
        </div>
    `;

    // Ensure the initial analysis button is visible
    document.getElementById('do-analysis-initial').classList.remove('hidden');

    const usernameSelect = document.getElementById('username-select');
    const usernameInput = document.getElementById('username-input');
    const continueButton = document.getElementById('continue-button');

    usernameSelect.addEventListener('change', function() {
        if (this.value !== "") {
            usernameInput.value = '';
        }
    });

    usernameInput.addEventListener('input', function() {
        usernameSelect.value = '';
    });

    function updateNameList(username) {
        console.log('Updating name list with:', username);
        
        // Remove the selected username from the list if it already exists
        allNames = allNames.filter(name => name !== username);
        
        // Add the selected username to the front of the list
        allNames.unshift(username);
        
        // Remove duplicates while preserving order
        allNames = [...new Set(allNames)];
        
        localStorage.setItem('allNames', JSON.stringify(allNames));
        console.log('Updated and saved allNames:', allNames);
    }

    continueButton.addEventListener('click', function() {
        const username = usernameInput.value || usernameSelect.value || 'test';
        console.log('Selected username:', username);
        sessionData.user = { name: username };
        
        updateNameList(username);
        
        getSettings();
    });

    usernameInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            continueButton.click();
        }
    });

    // Replace with this:
    if (allNames.length > 0) {
        usernameSelect.value = allNames[0];
    }

    // Add event listeners for the buttons
    document.getElementById('download-all-json-initial').addEventListener('click', downloadAllSessionsData);
    document.getElementById('clear-all-sessions-initial').addEventListener('click', clearAllSessions);
    document.getElementById('do-analysis-initial').addEventListener('click', navigateToAnalysis);

    // Print out current sessions
    listCurrentJsonFiles();
}

function getPresets() {
    return {
          "t1": {
            "preset": "t1",
            "description": "1 question adding numbers 0 to 5",
            "note": "",
            "num_problems": 1,
            "number_range": [0, 5],
            "numbers_include": [],
            "numbers_exclude": [],
            "num_numbers": 2,
            "operations": ['+']
        },
           "t5": {
            "preset": "t5",
            "description": "5 questions adding numbers 0 to 5",
            "note": "",
            "num_problems": 5,
            "number_range": [0, 5],
            "numbers_include": [],
            "numbers_exclude": [],
            "num_numbers": 2,
            "operations": ['+']
        },
        "a9": {
            "preset": "a9",
            "description": "20 questions adding numbers 0 to 9",
            "note": "",
            "num_problems": 20,
            "number_range": [0, 9],
            "numbers_include": [],
            "numbers_exclude": [],
            "num_numbers": 2,
            "operations": ['+']
        }
        // Add more presets here as needed
    };
}

function checkForGeneratedProblemList() {
    try {
        const stored = localStorage.getItem('generatedProblemList');
        const metadata = localStorage.getItem('generatedProblemListMetadata');
        
        if (stored && metadata) {
            const problemList = JSON.parse(stored);
            const meta = JSON.parse(metadata);
            
            if (problemList && Array.isArray(problemList) && problemList.length > 0) {
                // Auto-populate the problem list
                uploadedProblemList = problemList;
                uploadedProblemListMetadata = meta;
                settings.problem_list = problemList.map(p => ({ ...p }));
                settings.num_problems = problemList.length;
                
                // Clear stored data after using it
                localStorage.removeItem('generatedProblemList');
                localStorage.removeItem('generatedProblemListMetadata');
                
                console.log(`Loaded ${problemList.length} problems from fluency tracker`);
                return true;
            }
        }
    } catch (error) {
        console.error('Error checking for generated problem list:', error);
        // Clear potentially corrupted data
        localStorage.removeItem('generatedProblemList');
        localStorage.removeItem('generatedProblemListMetadata');
    }
    return false;
}

function getSettings() {
    const userInputs = document.getElementById('app-screens');
    const presets = getPresets();

    // Check for generated problem list from fluency tracker
    const generatedList = checkForGeneratedProblemList();
    
    userInputs.innerHTML = `
        <div class="main-text">
            <label>Select a preset or choose 'Custom': </label>
            <br>
            <select id="preset-select" class="input-select">
                <option value="">Custom</option>
                <option value="problem-list" ${generatedList ? 'selected' : ''}>Upload problem list (JSON/Markdown)</option>
                <option value="session-json">Upload past session JSON</option>
                ${Object.keys(presets).map(key => `<option value="${key}">${key}: ${presets[key].description}</option>`).join('')}
            </select>
        </div>
        <br>
        <button id="continue-button" class="btn btn-success">Continue</button>
    `;

    const presetSelect = document.getElementById('preset-select');
    const continueButton = document.getElementById('continue-button');
    
    // If generated list exists, auto-populate
    if (generatedList && presetSelect) {
        presetSelect.value = 'problem-list';
    }

    presetSelect.addEventListener('change', function() {
        if (this.value && this.value !== "problem-list" && this.value !== "session-json" && presets.hasOwnProperty(this.value)) {
            settings = Object.assign({}, presets[this.value]); // Create a copy
            settings.problem_list = [];
            delete settings.problem_list_metadata;
        }
    });

    continueButton.addEventListener('click', () => {
        const presetInput = presetSelect.value;
        // Only clear if not using a generated problem list
        const hasGeneratedList = uploadedProblemList && uploadedProblemList.length > 0 && 
                                 uploadedProblemListMetadata?.source === 'fluency-tracker';
        if (!hasGeneratedList) {
            uploadedProblemList = [];
            uploadedProblemListMetadata = null;
        }
        if (presetInput === "") {
            settings.problem_list = [];
            delete settings.problem_list_metadata;
            getCustomSettings();
        } else if (presetInput === "problem-list") {
            // Check if we already have a generated problem list
            if (uploadedProblemList && uploadedProblemList.length > 0) {
                settings = {
                    "preset": "problem_list",
                    "description": "Practice from fluency tracker generated list",
                    "note": uploadedProblemListMetadata?.note || "",
                    "num_problems": uploadedProblemList.length,
                    "number_range": [0, 0],
                    "numbers_include": [],
                    "numbers_exclude": [],
                    "num_numbers": 2,
                    "operations": ['+'],
                    "problem_list": uploadedProblemList.map(p => ({ ...p }))
                };
                settings.problem_list_metadata = uploadedProblemListMetadata;
                getNote();
            } else {
                settings = {
                    "preset": "problem_list",
                    "description": "Practice from uploaded problem list",
                    "note": "",
                    "num_problems": 0,
                    "number_range": [0, 0],
                    "numbers_include": [],
                    "numbers_exclude": [],
                    "num_numbers": 2,
                    "operations": ['+'],
                    "problem_list": []
                };
                getProblemListUpload('problem-list');
            }
        } else if (presetInput === "session-json") {
            settings = {
                "preset": "session_problem_list",
                "description": "Practice problems from uploaded session JSON",
                "note": "",
                "num_problems": 0,
                "number_range": [0, 0],
                "numbers_include": [],
                "numbers_exclude": [],
                "num_numbers": 2,
                "operations": ['+'],
                "problem_list": []
            };
            getProblemListUpload('session-json');
        } else if (presets.hasOwnProperty(presetInput)) {
            settings = Object.assign({}, presets[presetInput]); // Create a copy
            settings.problem_list = [];
            delete settings.problem_list_metadata;
            getNote();
        } else {
            appendMessage("Invalid preset. Please try again.");
        }
    });
}

function getCustomSettings() {
    const userInputs = document.getElementById('app-screens');
    userInputs.innerHTML = `
        <h2>Custom Quiz</h2>
        <label>Enter a note for this session (optional): </label>
        <input type="text" id="note-input" class="input-text"><br>
        <label>Enter the number of problems for this session: </label>
        <input type="number" id="num-problems-input" class="input-text" value="5"><br>
        <label>Enter the minimum number in the range: </label>
        <input type="number" id="min-range-input" class="input-text" value="0"><br>
        <label>Enter the maximum number in the range: </label>
        <input type="number" id="max-range-input" class="input-text" value="5"><br>
        <label>Enter numbers to include in one of the numbers (comma-separated): </label>
        <input type="text" id="numbers-include-input" class="input-text"><br>
        <label>Enter numbers to exclude from all numbers (comma-separated): </label>
        <input type="text" id="numbers-exclude-input" class="input-text"><br>
        <label>Enter number of numbers for each problem: </label>
        <input type="number" id="num-numbers-input" class="input-text" value="2"><br>
        <label>Enter operations to use separated by spaces (+ - * / ^): </label>
        <input type="text" id="operations-input" class="input-text" value="+"><br>
        <button id="submit-custom-settings" class="btn btn-submit">Submit</button>
    `;

    document.getElementById('submit-custom-settings').addEventListener('click', () => {
        settings = {
            "preset": "custom",
            "description": "",
            "note": document.getElementById('note-input').value || "",
            "num_problems": parseInt(document.getElementById('num-problems-input').value) || 5,
            "number_range": [
                parseInt(document.getElementById('min-range-input').value) || 0,
                parseInt(document.getElementById('max-range-input').value) || 5
            ],
            "numbers_include": parseNumberList(document.getElementById('numbers-include-input').value),
            "numbers_exclude": parseNumberList(document.getElementById('numbers-exclude-input').value),
            "num_numbers": parseInt(document.getElementById('num-numbers-input').value) || 2,
            "operations": parseOperations(document.getElementById('operations-input').value),
            "problem_list": []
        };
        delete settings.problem_list_metadata;
        getNote();
    });
}

function getProblemListUpload(mode = 'problem-list') {
    const userInputs = document.getElementById('app-screens');
    const isSessionMode = mode === 'session-json';
    uploadedProblemList = [];
    uploadedProblemListMetadata = null;

    const heading = isSessionMode ? 'Upload Session JSON' : 'Upload Problem List';
    const instructions = isSessionMode
        ? 'Upload a previous session JSON file exported by this app. The problems from that session will be replayed.'
        : 'Upload a Markdown (.md) or JSON (.json) file with the problems you want to practice. Example line: <code>3 + 4</code>';
    const acceptAttr = isSessionMode ? '.json' : '.json,.md,.markdown,.txt';

    userInputs.innerHTML = `
        <h2>${heading}</h2>
        <p>${instructions}</p>
        <input type="file" id="problem-list-file" accept="${acceptAttr}">
        <div id="problem-list-feedback" class="messages"></div>
        <button id="problem-list-continue" class="btn btn-submit" disabled>Continue</button>
        <button id="problem-list-back" class="btn btn-clear">Back</button>
    `;

    const fileInput = document.getElementById('problem-list-file');
    const feedback = document.getElementById('problem-list-feedback');
    const continueButton = document.getElementById('problem-list-continue');
    const backButton = document.getElementById('problem-list-back');

    fileInput.addEventListener('change', (event) => handleProblemListFile(event, feedback, continueButton, mode));
    backButton.addEventListener('click', () => {
        uploadedProblemList = [];
        uploadedProblemListMetadata = null;
        settings.problem_list = [];
        delete settings.problem_list_metadata;
        getSettings();
    });
    continueButton.addEventListener('click', () => {
        if (uploadedProblemList.length === 0) {
            feedback.innerHTML = '<span style="color: #f44336;">Please upload a file that contains problems.</span>';
            return;
        }
        settings.problem_list = uploadedProblemList.map(problem => ({ ...problem }));
        settings.num_problems = uploadedProblemList.length;
        const file = fileInput.files && fileInput.files[0] ? fileInput.files[0] : null;
        const metadata = { ...(uploadedProblemListMetadata || {}) };
        metadata.mode = metadata.mode || mode;
        if (file && !metadata.source) {
            metadata.source = file.name;
        }
        metadata.loaded_at = getCurrentDatetimeFileFriendly();
        metadata.count = settings.problem_list.length;
        settings.problem_list_metadata = metadata;
        getNote();
    });
}

function handleProblemListFile(event, feedbackElement, continueButton, mode = 'problem-list') {
    const file = event.target.files && event.target.files[0] ? event.target.files[0] : null;
    if (!file) {
        uploadedProblemList = [];
        uploadedProblemListMetadata = null;
        continueButton.disabled = true;
        feedbackElement.innerHTML = '';
        return;
    }

    const reader = new FileReader();
    reader.onload = function(loadEvent) {
        try {
            if (mode === 'session-json') {
                const result = parseSessionProblemListContent(loadEvent.target.result, file.name);
                uploadedProblemList = result.problems;
                uploadedProblemListMetadata = {
                    ...result.metadata,
                    source: file.name,
                    mode: mode
                };
                if (uploadedProblemList.length === 0) {
                    throw new Error('The selected session file does not contain any usable problems.');
                }
                continueButton.disabled = false;
                const sessionLabel = result.metadata && result.metadata.sessionId ? ` (Session ID: ${result.metadata.sessionId})` : '';
                feedbackElement.innerHTML = `<span style="color: #4CAF50;">Loaded ${uploadedProblemList.length} problem${uploadedProblemList.length === 1 ? '' : 's'} from ${file.name}${sessionLabel}.</span>`;
            } else {
                const problems = parseProblemListContent(loadEvent.target.result, file.name);
                uploadedProblemList = problems;
                uploadedProblemListMetadata = {
                    sourceType: 'problem-list',
                    source: file.name,
                    mode: mode
                };
                continueButton.disabled = false;
                feedbackElement.innerHTML = `<span style="color: #4CAF50;">Loaded ${problems.length} problem${problems.length === 1 ? '' : 's'} from ${file.name}.</span>`;
            }
        } catch (error) {
            uploadedProblemList = [];
            uploadedProblemListMetadata = null;
            continueButton.disabled = true;
            feedbackElement.innerHTML = `<span style="color: #f44336;">${error.message}</span>`;
        }
    };
    reader.onerror = function() {
        uploadedProblemList = [];
        uploadedProblemListMetadata = null;
        continueButton.disabled = true;
        feedbackElement.innerHTML = '<span style="color: #f44336;">Unable to read the selected file.</span>';
    };
    reader.readAsText(file);
}

function parseProblemListContent(fileContent, fileName) {
    let rawEntries = [];
    const lowerName = (fileName || '').toLowerCase();

    const extractExpression = (entry) => {
        if (typeof entry === 'string') {
            return entry.trim();
        }
        if (entry && typeof entry === 'object') {
            return (entry.problem || entry.expression || entry.text || '').trim();
        }
        return '';
    };

    if (lowerName.endsWith('.json')) {
        let parsed;
        try {
            parsed = JSON.parse(fileContent);
        } catch (error) {
            throw new Error('Invalid JSON file. Please check the file format.');
        }

        if (Array.isArray(parsed)) {
            rawEntries = parsed.map(extractExpression);
        } else if (parsed && Array.isArray(parsed.problems)) {
            rawEntries = parsed.problems.map(extractExpression);
        } else {
            throw new Error('JSON must be an array or contain a "problems" array.');
        }
    } else {
        const lines = fileContent.split(/\r?\n/);
        const bulletRegex = /^\s*(?:[-*+]\s+|\d+\.\s+)(.+)$/;
        rawEntries = lines.reduce((acc, line) => {
            const trimmed = line.trim();
            if (!trimmed) {
                return acc;
            }
            const bulletMatch = trimmed.match(bulletRegex);
            if (bulletMatch) {
                acc.push(bulletMatch[1].trim());
            }
            return acc;
        }, []);

        if (rawEntries.length === 0) {
            rawEntries = lines.map(line => line.trim()).filter(Boolean);
        }
    }

    const problems = rawEntries
        .map(entry => entry.trim())
        .filter(entry => entry.length > 0)
        .map(buildProblemFromExpression);

    if (problems.length === 0) {
        throw new Error('No valid problems found in the selected file.');
    }

    return problems;
}

function parseSessionProblemListContent(fileContent, fileName) {
    let parsed;
    try {
        parsed = JSON.parse(fileContent);
    } catch (error) {
        throw new Error('Invalid session JSON file.');
    }

    let sessionNode = parsed.session || null;
    if (!sessionNode && Array.isArray(parsed.sessions) && parsed.sessions.length > 0) {
        sessionNode = parsed.sessions[0];
    }
    if (!sessionNode) {
        throw new Error('Session JSON must include a "session" object.');
    }

    const problemsArray = Array.isArray(sessionNode.problems) ? sessionNode.problems : [];
    if (problemsArray.length === 0) {
        throw new Error('The session JSON does not contain any problems.');
    }

    const problems = problemsArray
        .map((entry, index) => buildProblemFromSessionEntry(entry, index))
        .filter(Boolean);

    if (problems.length === 0) {
        throw new Error('No valid problems could be extracted from the session file.');
    }

    const metadata = {
        sourceType: 'session-json',
        sessionId: sessionNode.id || null,
        sessionStart: sessionNode.start_time || null,
        sessionEnd: sessionNode.end_time || null,
        userName: (parsed.user && parsed.user.name) || (sessionNode.user && sessionNode.user.name) || null,
        note: sessionNode.settings && sessionNode.settings.note ? sessionNode.settings.note : undefined
    };

    return { problems, metadata };
}

function buildProblemFromExpression(expression) {
    if (typeof expression !== 'string') {
        throw new Error('Problem entries must be text.');
    }

    const original = expression.trim();
    if (!original) {
        throw new Error('Encountered an empty problem in the file.');
    }

    const normalized = original
        .replace(/×/g, '*')
        .replace(/÷/g, '/')
        .replace(/[xX]/g, '*')
        .replace(/–/g, '-')
        .replace(/=/g, '')
        .replace(/\s+/g, ' ')
        .trim();

    const match = normalized.match(/^(-?\d+(?:\.\d+)?)\s*([\+\-\*\/\^])\s*(-?\d+(?:\.\d+)?)/);
    if (!match) {
        throw new Error(`Could not parse problem "${original}". Use format like "3 + 4".`);
    }

    const firstNumber = parseFloat(match[1]);
    const operation = match[2];
    const secondNumber = parseFloat(match[3]);

    let correctAnswer;
    switch (operation) {
        case '+':
            correctAnswer = firstNumber + secondNumber;
            break;
        case '-':
            correctAnswer = firstNumber - secondNumber;
            break;
        case '*':
            correctAnswer = firstNumber * secondNumber;
            break;
        case '/':
            correctAnswer = secondNumber !== 0 ? firstNumber / secondNumber : (firstNumber === 0 ? NaN : Infinity);
            break;
        case '^':
            correctAnswer = Math.pow(firstNumber, secondNumber);
            break;
        default:
            throw new Error(`Unsupported operation "${operation}".`);
    }

    const baseProblem = `${firstNumber} ${operation} ${secondNumber}`;
    const displayProblem = baseProblem
        .replace(/\*/g, '&times;')
        .replace(/\//g, '&divide;');
    const speakableProblem = baseProblem
        .replace(/\*/g, 'times')
        .replace(/\//g, 'divided by')
        .replace(/\^/g, 'to the power of');

    return {
        rawExpression: original,
        normalizedExpression: baseProblem,
        displayProblem,
        speakableProblem,
        correctAnswer,
        problemId: assignProblemId(baseProblem)
    };
}

function buildProblemFromSessionEntry(entry, index = 0) {
    if (!entry) {
        console.warn('Skipping empty problem entry from session file at index', index);
        return null;
    }

    const coerceSessionNumber = (value) => {
        if (typeof value === 'number') {
            return value;
        }
        if (typeof value === 'string') {
            const trimmed = value.trim();
            if (!trimmed) {
                return NaN;
            }
            if (/^inf(inity)?$/i.test(trimmed)) {
                return Infinity;
            }
            if (/^-inf(inity)?$/i.test(trimmed)) {
                return -Infinity;
            }
            const parsed = Number(trimmed);
            return parsed;
        }
        return NaN;
    };

    const originalText =
        (typeof entry.problem_text === 'string' && entry.problem_text.trim()) ||
        (typeof entry.problem === 'string' && entry.problem.trim()) ||
        (typeof entry.expression === 'string' && entry.expression.trim()) ||
        (typeof entry.text === 'string' && entry.text.trim()) ||
        '';

    if (!originalText) {
        console.warn('Skipping session problem with no text at index', index);
        return null;
    }

    const sanitized = originalText
        .replace(/&times;/g, '*')
        .replace(/×/g, '*')
        .replace(/&divide;/g, '/')
        .replace(/÷/g, '/')
        .replace(/=/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();

    let problem;
    try {
        problem = buildProblemFromExpression(sanitized);
    } catch (error) {
        console.warn(`Skipping session problem that could not be parsed: "${originalText}"`, error);
        return null;
    }

    problem.rawExpression = originalText;
    if (typeof entry.correct_answer !== 'undefined') {
        const coercedAnswer = coerceSessionNumber(entry.correct_answer);
        if (Number.isFinite(coercedAnswer)) {
            problem.correctAnswer = coercedAnswer;
        } else if (coercedAnswer === Infinity || coercedAnswer === -Infinity) {
            problem.correctAnswer = coercedAnswer;
        } // otherwise retain expression-derived answer (handles null/NaN)
    }
    if (entry.user_answer !== undefined) {
        const coercedUserAnswer = coerceSessionNumber(entry.user_answer);
        problem.userAnswerFromSession = Number.isNaN(coercedUserAnswer) ? entry.user_answer : coercedUserAnswer;
    }
    problem.problemId = entry.id || problem.problemId || assignProblemId(sanitized);
    return problem;
}

function getNote() {
    const userInputs = document.getElementById('app-screens');
    userInputs.innerHTML = `
        <div class="main-text">
            <label>Enter a note for this session (optional): </label>
            <input type="text" id="note-input" class="input-text" value="${escapeHtml(settings.note || '')}">
        </div>
        <div id="audio-toggle" class="toggle-section">
            <label for="audio-enabled">Read Problems Aloud:</label>
            <input type="checkbox" id="audio-enabled">
        </div>
        <div id="speech-detection-toggle" class="toggle-section">
            <label for="speech-detection-enabled">Enable Automatic Speech Recognition (may be buggy):</label>
            <input type="checkbox" id="speech-detection-enabled">
        </div>
        <div id="auto-submit-toggle" class="toggle-section">
            <label for="auto-submit-enabled">Auto-submit When Answer Length Matches:</label>
            <input type="checkbox" id="auto-submit-enabled" checked>
        </div>
        <br>
        <button id="start-assessment" class="btn btn-submit">Start Assessment</button>
    `;
    document.getElementById('start-assessment').addEventListener('click', () => {
        settings.note = document.getElementById('note-input').value || settings.note;
        settings.audioEnabled = document.getElementById('audio-enabled').checked;
        settings.speechDetectionEnabled = document.getElementById('speech-detection-enabled').checked;
        settings.autoSubmitOnLength = document.getElementById('auto-submit-enabled').checked;
        runAssessment();
    });
}

function parseNumberList(input) {
    return input.split(',').map(num => parseInt(num.trim())).filter(num => !isNaN(num));
}

function parseOperations(input) {
    const validOps = ['+', '-', '*', '/', '^'];
    const ops = input.split(' ').filter(op => validOps.includes(op));
    return ops.length > 0 ? ops : ['+'];
}

// Quiz functions
function generateProblem() {
    let availableNumbers = [];
    for (let i = settings.number_range[0]; i <= settings.number_range[1]; i++) {
        if (!settings.numbers_exclude.includes(i)) {
            availableNumbers.push(i);
        }
    }

    // numbers_include contributes at most one number, so the available pool
    // must be non-empty whenever more than one number is needed
    if (availableNumbers.length === 0 && (settings.numbers_include.length === 0 || settings.num_numbers > 1)) {
        throw new Error("No available numbers to generate a problem. Adjust the number range or exclusions.");
    }

    let numbers = [];

    // Ensure one number is from numbers_include if provided
    if (settings.numbers_include.length > 0) {
        numbers.push(randomChoice(settings.numbers_include));
    }

    // Fill the rest of the numbers from available_numbers
    while (numbers.length < settings.num_numbers) {
        numbers.push(randomChoice(availableNumbers));
    }

    // Shuffle the numbers
    shuffleArray(numbers);

    const operation = randomChoice(settings.operations);
    let problemString = `${numbers[0]} ${operation} ${numbers[1]}`;

    // Create a speakable version of the problem
    let speakableProblem = problemString
        .replace("**", "to the power of")
        .replace("*", "times")
        .replace("/", "divided by");

    // Replace operation symbols for display
    let displayProblem = problemString
        .replace("**", "^")
        .replace("*", "&times;")
        .replace("/", "&divide;");

    // Calculate correct answer
    let correctAnswer;
    switch (operation) {
        case '+':
            correctAnswer = numbers[0] + numbers[1];
            break;
        case '-':
            correctAnswer = numbers[0] - numbers[1];
            break;
        case '*':
            correctAnswer = numbers[0] * numbers[1];
            break;
        case '/':
            correctAnswer = numbers[1] !== 0 ? numbers[0] / numbers[1] : (numbers[0] === 0 ? NaN : Infinity);
            break;
        case '^':
            correctAnswer = Math.pow(numbers[0], numbers[1]);
            break;
        default:
            throw new Error(`Unsupported operation: ${operation}`);
    }

    // problemText keeps canonical symbols (* /) for records; displayProblem is presentation-only
    return { problemText: problemString, displayProblem, speakableProblem, correctAnswer };
}

function assignProblemId(problemText) {
    // Generate an MD5 hash of the problem text; fall back to a simple string
    // hash when the md5 CDN script is unavailable (offline/local use). IDs are
    // only used for in-session dedupe and per-session DB rows, so the two
    // schemes never need to match each other.
    if (typeof md5 === 'undefined') {
        let hash = 5381;
        for (let i = 0; i < problemText.length; i++) {
            hash = ((hash << 5) + hash + problemText.charCodeAt(i)) >>> 0;
        }
        return `h${hash.toString(16)}`;
    }
    return md5(problemText).substring(0, 16);
}

function renderFlagDropdown() {
    const optionsHtml = FLAG_OPTIONS.map(option => `<option value="${option.value}">${option.label}</option>`).join('');
    return `
        <select id="flag-select" class="flag-dropdown" aria-label="Flag this problem">${optionsHtml}</select>
        <input type="text" id="flag-comment" class="flag-comment" placeholder="Add comment (optional)" style="display: none;">
    `;
}

function handleEnterKey(e) {
    if (e.key === 'Enter') {
        e.preventDefault(); // Prevent form submission
        submitAnswer();
    }
}

function nextProblem() {
    console.log(`Starting problem ${problemIndex + 1} of ${settings.num_problems}`);
    // Ensure messages are cleared
    document.getElementById('messages').innerHTML = '';

    clearFeedback(); // Clear any existing feedback

    const isProblemListMode = Array.isArray(settings.problem_list) && settings.problem_list.length > 0;

    if (problemIndex >= (isProblemListMode ? settings.problem_list.length : settings.num_problems)) {
        console.log("All problems completed, calling endAssessment");
        endAssessment();
        return;
    }

    if (isProblemListMode) {
        const listProblem = settings.problem_list[problemIndex];
        if (!listProblem) {
            appendMessage("Unable to load the next problem from the uploaded list.");
            console.error('Problem list entry missing at index', problemIndex);
            return;
        }
        problemData = {
            problemId: listProblem.problemId || assignProblemId(listProblem.normalizedExpression || listProblem.rawExpression || `list-problem-${problemIndex}`),
            problemText: listProblem.normalizedExpression || normalizeOperationSymbols(listProblem.rawExpression || listProblem.displayProblem || ''),
            displayProblem: listProblem.displayProblem || listProblem.rawExpression,
            speakableProblem: listProblem.speakableProblem || listProblem.rawExpression,
            correctAnswer: listProblem.correctAnswer
        };
    } else {
        // Generate a unique problem
        let maxAttempts = 100;
        problemData = null; // Reset problemData at the start

        try {
            for (let attempt = 0; attempt < maxAttempts; attempt++) {
                let { problemText, displayProblem, speakableProblem, correctAnswer } = generateProblem();
                let problemId = assignProblemId(problemText);

                if (!usedProblems.has(problemId)) {
                    usedProblems.add(problemId);
                    problemData = { problemId, problemText, displayProblem, speakableProblem, correctAnswer };
                    break;
                }
            }

            // If no unique problem found after maxAttempts, all unique problems are exhausted
            // Reset usedProblems to allow repeats, then generate a new problem
            if (!problemData) {
                usedProblems.clear(); // Reset to allow all problems again
                // Now generate a new problem (it will be unique since we just cleared usedProblems)
                let { problemText, displayProblem, speakableProblem, correctAnswer } = generateProblem();
                let problemId = assignProblemId(problemText);
                usedProblems.add(problemId);
                problemData = { problemId, problemText, displayProblem, speakableProblem, correctAnswer };
            }
        } catch (error) {
            console.error('Problem generation failed:', error);
            appendMessage(error.message);
            return;
        }
    }

    // Display the problem
    document.getElementById('problem').innerHTML = `
        <p class="problem-count">Problem ${problemIndex + 1} of ${isProblemListMode ? settings.problem_list.length : settings.num_problems}</p>
        <div class="problem-container">
            <div class="flag-control">
                ${renderFlagDropdown()}
            </div>
            <div class="problem-display">
                <span id="problem-text">${problemData.displayProblem.replace(/[×*]/g, '&times;')} =</span>
                <input type="text" id="answer-input" class="input-answer" placeholder="">
            </div>
        </div>
        <button id="dont-know-btn" class="btn btn-dont-know">I don't know</button>
        ${settings.speechDetectionEnabled ? `
            <div class="listening-buttons">
                <button id="start-listening" class="btn btn-listen">Start Listening</button>
                <button id="stop-listening" class="btn btn-stop-listen" style="display: none;">Stop Listening</button>
            </div>
        ` : ''}
    `;
    const answerInput = document.getElementById('answer-input');
    answerInput.value = '';
    answerInput.disabled = false;
    answerInput.focus();
    answerSubmitted = false; // New problem is on screen; accept one submission
    
    // Set up flag dropdown change handler to show/hide comment field
    const flagSelect = document.getElementById('flag-select');
    const flagComment = document.getElementById('flag-comment');
    if (flagSelect && flagComment) {
        flagSelect.addEventListener('change', function() {
            if (this.value && this.value !== '') {
                flagComment.style.display = 'block';
            } else {
                flagComment.style.display = 'none';
                flagComment.value = '';
            }
        });
        
        // Prevent Enter key in comment field from submitting answer
        flagComment.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                e.stopPropagation();
                submitAnswer();  // Submit immediately when Enter is pressed
            }
        });
    }
    
    // Replace the simple keypress handler with this new input handler
    if (settings.autoSubmitOnLength) {
        answerInput.addEventListener('input', handleAnswerInput);
    }
    answerInput.addEventListener('keypress', handleEnterKey);
    
    // Add event listener for "I don't know" button
    const dontKnowBtn = document.getElementById('dont-know-btn');
    if (dontKnowBtn) {
        dontKnowBtn.addEventListener('click', handleDontKnow);
    }
    
    startTime = new Date();

    // Add debugging code to check font sizes
    setTimeout(() => {
        const problemElement = document.querySelector('.problem');
        const problemText = document.getElementById('problem-text');
        const answerInput = document.getElementById('answer-input');

        console.log('Problem container font size:', window.getComputedStyle(problemElement).fontSize);
        console.log('Problem text font size:', window.getComputedStyle(problemText).fontSize);
        console.log('Answer input font size:', window.getComputedStyle(answerInput).fontSize);
    }, 0);

    // Speak the problem and then start listening if enabled
    speakText(problemData.speakableProblem + ' equals', () => {
        if (settings.speechDetectionEnabled) {
            startListening();
        }
    });

    // Set up event listeners for speech recognition buttons
    if (settings.speechDetectionEnabled) {
        document.getElementById('start-listening').addEventListener('click', startListening);
        document.getElementById('stop-listening').addEventListener('click', stopListening);
    }
}

function handleDontKnow() {
    // Store the "dontknow" flag marker so submitAnswer can use it
    window._dontKnowFlag = true;
    // Leave answer input empty and submit
    submitAnswer();
}

function handleEndQuizEarly() {
    if (confirm("Are you sure you want to end the quiz? Your progress will be saved.")) {
        // Stop any ongoing speech recognition
        if (isListening) {
            stopListening();
        }
        // Clear any pending timeouts for next problem
        if (window.nextProblemTimeout) {
            clearTimeout(window.nextProblemTimeout);
        }
        endAssessment();
    }
}

function submitAnswer() {
    if (answerSubmitted) {
        console.log('Ignoring duplicate answer submission');
        return;
    }
    const answerInput = document.getElementById('answer-input');
    if (!answerInput) {
        console.warn('submitAnswer called with no active problem; ignoring');
        return;
    }
    answerSubmitted = true;
    if (isListening) {
        stopListening();
    }
    console.log('Submitting answer...');
    answerInput.removeEventListener('keypress', handleEnterKey); // Remove the event listener
    answerInput.disabled = true; // Disable the input
    const flagSelect = document.getElementById('flag-select');
    const userAnswerString = answerInput.value.trim().toLowerCase();
    console.log('User answer:', userAnswerString);
    endTime = new Date();
    let responseTimeMs = endTime - startTime;

    let isCorrect = false;
    let userAnswerNumeric = null;

    // Handle special cases for division
    if (['infinity', 'inf'].includes(userAnswerString)) {
        isCorrect = problemData.correctAnswer === Infinity;
    } else if (['undefined', 'und'].includes(userAnswerString)) {
        isCorrect = isNaN(problemData.correctAnswer);
    } else {
        userAnswerNumeric = parseFloat(userAnswerString);
        
        if (!isNaN(userAnswerNumeric)) {
            if (isFinite(problemData.correctAnswer)) {
                // Round both answers to 3 decimal places
                const roundedCorrect = Math.round(problemData.correctAnswer * 1000) / 1000;
                const roundedUser = Math.round(userAnswerNumeric * 1000) / 1000;
                
                // Check if the first two decimal places match
                isCorrect = Math.abs(roundedCorrect - roundedUser) < 0.01;
            } else {
                isCorrect = false; // User entered a number for an infinite or undefined result
            }
        }
    }

    let feedbackMessage = '';
    if (isCorrect) {
        feedbackMessage = "Correct!";
        playCorrectSound();
        triggerConfetti();
    } else {
        let correctAnswerDisplay = isFinite(problemData.correctAnswer) 
            ? formatNumber(problemData.correctAnswer)
            : (isNaN(problemData.correctAnswer) ? 'Undefined' : 'Infinity');
        feedbackMessage = `Incorrect. The correct answer is ${correctAnswerDisplay}.`;
        playIncorrectSound();
    }

    // Display feedback
    displayFeedback(feedbackMessage, isCorrect);

    // Record problem data
    const problemRecord = {
        id: problemData.problemId,
        problem_text: problemData.problemText || normalizeOperationSymbols(problemData.displayProblem),
        correct_answer: problemData.correctAnswer,
        user_answer_string: userAnswerString,
        user_answer: userAnswerNumeric,
        is_correct: isCorrect,
        response_time_ms: responseTimeMs,
        flags: []
    };

    // Get flag elements
    const flagComment = document.getElementById('flag-comment');
    
    // Check if "I don't know" button was pressed
    if (window._dontKnowFlag) {
        const flagData = {
            reason: 'dontknow',
            label: FLAG_LABELS.dontknow || "I Don't Know",
            timestamp: new Date().toISOString(),
            notes: ''
        };
        problemRecord.flags.push(flagData);
        window._dontKnowFlag = false; // Reset the flag
    } else {
        // Handle regular flag dropdown
        const flagReason = flagSelect ? flagSelect.value : '';
        if (flagReason) {
            const flagCommentText = flagComment ? flagComment.value.trim() : '';
            const flagData = {
                reason: flagReason,
                label: FLAG_LABELS[flagReason] || flagReason,
                timestamp: new Date().toISOString(),
                notes: flagCommentText
            };
            problemRecord.flags.push(flagData);
        }
    }
    if (flagSelect) {
        flagSelect.disabled = true;
    }
    if (flagComment) {
        flagComment.disabled = true;
    }
    problemsAttempted.push(problemRecord);

    problemIndex++;
    if (isCorrect) {
        setTimeout(nextProblem, 1000);
    } else {
        // For incorrect answers, automatically move to the next problem after 5 seconds
        window.nextProblemTimeout = setTimeout(nextProblem, 5000);
    }
}

function displayFeedback(message, isCorrect) {
    console.log("Feedback message:", message);

    const feedbackContainer = document.getElementById('feedback-container');
    if (feedbackContainer) {
        feedbackContainer.innerHTML = `
            <div class="feedback-message ${isCorrect ? 'correct' : 'incorrect'}">
                ${message}
            </div>
            ${!isCorrect ? '<button id="override-button" class="btn btn-primary btn-override">Override (Mark as Correct)</button>' : ''}
        `;
        feedbackContainer.style.display = 'block';

        const overrideButton = document.getElementById('override-button');
        if (overrideButton) {
            overrideButton.addEventListener('click', overrideAnswer);
        }

        console.log("Feedback container updated");
    } else {
        console.error("Feedback container not found");
    }
}

function overrideAnswer() {
    console.log('Overriding answer...');
    // Get the last problem attempted
    const lastProblem = problemsAttempted[problemsAttempted.length - 1];
    
    // Mark it as correct and update the user answer
    lastProblem.is_correct = true;
    lastProblem.user_answer = lastProblem.correct_answer;
    lastProblem.user_answer_string = lastProblem.correct_answer.toString();

    // Display override feedback
    displayFeedback("Override applied successfully. Marked as correct!", true);

    playCorrectSound();
    triggerConfetti();

    // Clear any existing timeout for nextProblem
    clearTimeout(window.nextProblemTimeout);

    // Move to next problem after a short delay
    setTimeout(nextProblem, 1000);
}

function triggerConfetti() {
    if (typeof confetti === 'undefined') {
        console.log('Confetti library not available; skipping celebration.');
        return;
    }
    confetti({
        particleCount: 100,
        spread: 70,
        origin: { y: 0.6 }
    });
}

function clearFeedback() {
    console.log("Clearing feedback"); // Log clearing action
    const feedbackContainer = document.getElementById('feedback-container');
    if (feedbackContainer) {
        feedbackContainer.innerHTML = '';
        feedbackContainer.style.display = 'none';
        console.log("Feedback cleared"); // Log successful clearing
    } else {
        console.error("Feedback container not found when clearing"); // Log error if container is missing
    }
}

function endAssessment() {
    console.log("Entering endAssessment function");
    document.getElementById('quiz-section').classList.add('hidden');
    
    // Remove the end quiz button
    const endQuizBtn = document.getElementById('end-quiz-btn');
    if (endQuizBtn) {
        endQuizBtn.remove();
    }
    const totalProblems = problemsAttempted.length;
    const correctAnswers = problemsAttempted.filter(p => p.is_correct).length;
    const averageResponseTimeMs = problemsAttempted.reduce((sum, p) => sum + p.response_time_ms, 0) / totalProblems || 0;
    const incorrectProblems = problemsAttempted.filter(p => !p.is_correct);

    const totalTestTime = calculateTotalTestTime(sessionData.session.start_time, getCurrentDatetimeFileFriendly());

    const sessionSummary = {
        total_problems: totalProblems,
        correct_answers: correctAnswers,
        average_response_time_ms: Math.round(averageResponseTimeMs),
        total_test_time: totalTestTime
    };

    sessionData.session.end_time = getCurrentDatetimeFileFriendly();
    sessionData.session.summary = sessionSummary;
    sessionData.session.problems = problemsAttempted;

    console.log("Calling displaySummary");
    displaySummary(sessionSummary, incorrectProblems);
}

function displaySummary(sessionSummary, incorrectProblems) {
    console.log("Entering displaySummary function");
    const summaryDiv = document.getElementById('summary');
    summaryDiv.classList.remove('hidden');
    summaryDiv.innerHTML = `
        <h2>Session Summary:</h2>
        <p>Total problems attempted: ${sessionSummary.total_problems}</p>
        <p>Number of correct answers: ${sessionSummary.correct_answers}</p>
        <p>Average response time (ms): ${sessionSummary.average_response_time_ms}</p>
        <p>Total test time: ${sessionSummary.total_test_time}</p>
    `;

    if (incorrectProblems.length > 0) {
        summaryDiv.innerHTML += `<h3>Incorrectly answered problems:</h3>`;
        incorrectProblems.forEach(p => {
            summaryDiv.innerHTML += `
                <p>${formatProblemTextForDisplay(p.problem_text)} (Your answer: ${p.user_answer}, Correct answer: ${p.correct_answer})</p>
            `;
        });
    } else {
        summaryDiv.innerHTML += `<p>All answers were correct!</p>`;
    }

    console.log("Calling getAdditionalNote");
    getAdditionalNote();
}

function getAdditionalNote() {
    console.log("Entering getAdditionalNote function");
    const additionalNoteSection = document.getElementById('additional-note-section');
    additionalNoteSection.classList.remove('hidden');

    document.getElementById('submit-additional-note').addEventListener('click', () => {
        const additionalNote = document.getElementById('additional-note-input').value;
        if (additionalNote) {
            if (settings.note) {
                settings.note += `, POST QUIZ: ${additionalNote}`;
            } else {
                settings.note = `POST QUIZ: ${additionalNote}`;
            }
        }
        sessionData.session.settings.note = settings.note;
        promptDownload();
    });
}

function promptDownload() {
    console.log("Entering promptDownload function");
    document.getElementById('additional-note-section').classList.add('hidden');
    document.getElementById('download-section').classList.remove('hidden');
    
    // Automatically save the JSON data
    saveSessionData();
    
    // No need to remove 'hidden' class as it's already visible in HTML
    // document.getElementById('do-analysis-final').classList.remove('hidden');
    
    document.getElementById('download-json').onclick = () => {
        downloadSessionData();
    };
    
    document.getElementById('download-all-json-final').onclick = () => {
        downloadAllSessionsData();
    };
    
    document.getElementById('clear-all-sessions-final').onclick = () => {
        clearAllSessions();
    };
    
    document.getElementById('start-another-quiz').onclick = () => {
        location.reload();
    };
    
    document.getElementById('do-analysis-final').onclick = () => {
        navigateToAnalysis();
    };
    
    console.log('All buttons set up in promptDownload');
}

function saveSessionData() {
    const folderPath = 'math-quiz_data';
    const filename = `math_session_${sessionData.user.name}_${sessionData.session.start_time}.json`;
    const sessionDataString = JSON.stringify(sessionData, null, 2);

    // Save to localStorage
    try {
        localStorage.setItem(filename, sessionDataString);
        console.log(`Session data saved to ${folderPath}/${filename}`);
    } catch (error) {
        console.error('Could not save session to browser storage:', error);
        alert('Warning: this session could not be saved to browser storage (it may be full). Use "Download This Session Data" to keep a copy, then consider Clear All Sessions.');
    }
    listCurrentJsonFiles();
}

// Add this function to list saved JSON files
function listCurrentJsonFiles() {
    const curJsonFiles = [];
    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key.startsWith('math_session_') && key.endsWith('.json')) {
            curJsonFiles.push(key);
        }
    }

    console.log('Current JSON files in browser local storage:');
    curJsonFiles.forEach(file => console.log(file));
}

function downloadSessionData() {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(sessionData, null, 2));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    const filename = `math_session_${sessionData.user.name}_${sessionData.session.start_time}.json`;
    downloadAnchorNode.setAttribute("download", filename);
    document.body.appendChild(downloadAnchorNode); // Required for Firefox
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
}

// Modify the downloadAllSessionsData function
async function downloadAllSessionsData() {
    // Check if there are any JSON files to download
    const jsonFiles = Object.keys(localStorage).filter(key => key.startsWith('math_session_') && key.endsWith('.json'));

    if (jsonFiles.length === 0) {
        // No JSON files found, show an error message
        alert("No JSON files found. There is nothing to download.");
        return;
    }

    // Load the JSZip library dynamically
    if (typeof JSZip === 'undefined') {
        await loadJSZip();
    }

    const zip = new JSZip();
    const folder = zip.folder("math-quiz_data");

    for (const key of jsonFiles) {
        const data = localStorage.getItem(key);
        folder.file(key, data);
    }

    zip.generateAsync({type:"blob"})
    .then(function(content) {
        const downloadAnchorNode = document.createElement('a');
        downloadAnchorNode.setAttribute("href", URL.createObjectURL(content));
        downloadAnchorNode.setAttribute("download", "all_math_sessions.zip");
        document.body.appendChild(downloadAnchorNode); // Required for Firefox
        downloadAnchorNode.click();
        downloadAnchorNode.remove();
    });
}

// Add this function to load the JSZip library
function loadJSZip() {
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/jszip/3.7.1/jszip.min.js';
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

// Helper functions
function randomChoice(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
}

function shuffleArray(array) {
    array.sort(() => Math.random() - 0.5);
}

function generateUUID() {
    // Generate a simple UUID
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        let r = Math.random() * 16 | 0,
            v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

function getCurrentDatetimeFileFriendly() {
    const now = new Date();
    const pad = (n) => n.toString().padStart(2, '0');
    return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
}

function calculateTotalTestTime(startTimeStr, endTimeStr) {
    const parseTime = (str) => {
        const [datePart, timePart] = str.split('_');
        const [year, month, day] = datePart.split('-').map(Number);
        const hours = Number(timePart.substring(0, 2));
        const minutes = Number(timePart.substring(2, 4));
        const seconds = Number(timePart.substring(4, 6));
        return new Date(year, month - 1, day, hours, minutes, seconds);
    };

    const startTime = parseTime(startTimeStr);
    const endTime = parseTime(endTimeStr);
    let totalSeconds = (endTime - startTime) / 1000;
    const totalMinutes = Math.floor(totalSeconds / 60);
    const remainingSeconds = Math.round(totalSeconds % 60);
    return `${totalMinutes}:${remainingSeconds.toString().padStart(2, '0')}`;
}

// Add this function to load the confetti library
function loadConfettiLibrary() {
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/canvas-confetti@1.5.1/dist/confetti.browser.min.js';
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

// Add this function near the top of your file
function speakText(text, callback) {
    if (settings.audioEnabled && 'speechSynthesis' in window) {
        // Replace operation symbols with spoken words
        const speakableText = text
            .replace(/(\d+)\s*\+\s*(\d+)/g, '$1 plus $2')
            .replace(/(\d+)\s*\-\s*(\d+)/g, '$1 minus $2')
            .replace(/(\d+)\s*[×*]\s*(\d+)/g, '$1 times $2')
            .replace(/(\d+)\s*[÷/]\s*(\d+)/g, '$1 divided by $2')
            .replace(/(\d+)\s*\^\s*(\d+)/g, '$1 to the power of $2')
            .replace(/=/g, 'equals');

        const utterance = new SpeechSynthesisUtterance(speakableText);
        utterance.rate = 1.2; // Slightly faster than normal speech
        utterance.pitch = 1;
        utterance.onend = callback; // Call the callback when speech is finished
        speechSynthesis.speak(utterance);
    } else if (callback) {
        callback(); // If audio is disabled or speech synthesis is not available, call the callback immediately
    }
}

// Replace the playCorrectSound and playIncorrectSound functions
function playCorrectSound() {
    const audio = document.getElementById('correct-sound');
    if (audio) {
        audio.play().catch(error => {
            console.log("Sound files not available. Proceeding without sound effects.");
        });
    } else {
        console.log("Correct sound element not found. Proceeding without sound effects.");
    }
}

function playIncorrectSound() {
    const audio = document.getElementById('incorrect-sound');
    if (audio) {
        audio.play().catch(error => {
            console.log("Sound files not available. Proceeding without sound effects.");
        });
    } else {
        console.log("Incorrect sound element not found. Proceeding without sound effects.");
    }
}

// Add these functions to handle speech recognition
function startListening() {
    if (recognition && !isListening) {
        recognition.start();
        isListening = true;
        document.getElementById('start-listening').style.display = 'none';
        document.getElementById('stop-listening').style.display = 'inline-block';
        console.log('Speech recognition started');

        // Set a timeout to stop listening after 20 seconds
        setTimeout(() => {
            if (isListening) {
                stopListening();
            }
        }, 20000); // 20 seconds
    }
}

function stopListening() {
    if (recognition && isListening) {
        recognition.stop();
        isListening = false;
        document.getElementById('start-listening').style.display = 'inline-block';
        document.getElementById('stop-listening').style.display = 'none';
        console.log('Speech recognition stopped');
    }
}

// Modify the handleUserAnswer function to convert spelled-out numbers to numerals
function handleUserAnswer(transcript) {
    const userAnswerString = transcript.trim().toLowerCase();
    console.log('Handling user answer:', userAnswerString);
    const answerInput = document.getElementById('answer-input');
    if (answerSubmitted || !answerInput) {
        console.log('Ignoring speech result; problem already submitted');
        return;
    }
    const numericAnswer = convertSpelledOutNumberToNumeral(userAnswerString);
    console.log('Converted answer:', numericAnswer);
    answerInput.value = numericAnswer;
    submitAnswer();
}

// Add this new function to convert spelled-out numbers to numerals
function convertSpelledOutNumberToNumeral(spelledOutNumber) {
    const numberWords = {
        'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
        'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20,
        'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90
    };

    const words = spelledOutNumber.split(' ');
    let result = 0;
    let currentNumber = 0;

    for (let word of words) {
        if (numberWords.hasOwnProperty(word)) {
            currentNumber += numberWords[word];
        } else if (word === 'hundred') {
            currentNumber *= 100;
        } else if (word === 'thousand') {
            result += currentNumber * 1000;
            currentNumber = 0;
        } else if (word === 'million') {
            result += currentNumber * 1000000;
            currentNumber = 0;
        } else if (word === 'billion') {
            result += currentNumber * 1000000000;
            currentNumber = 0;
        } else if (word === 'and') {
            // Skip 'and'
        } else {
            // If it's already a number, parse it
            const parsedNumber = parseFloat(word);
            if (!isNaN(parsedNumber)) {
                return parsedNumber.toString();
            }
        }
    }

    result += currentNumber;
    return result.toString();
}

function clearAllSessions() {
    if (confirm("Are you sure? This will erase all the previous session data.")) {
        const keysToRemove = [];
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key.startsWith('math_session_') && key.endsWith('.json')) {
                keysToRemove.push(key);
            }
        }
        
        keysToRemove.forEach(key => localStorage.removeItem(key));
        
        console.log("All session data has been cleared.");
    }
}

// Add this new helper function to format numbers
function formatNumber(num) {
    // Convert the number to a string with a fixed number of decimal places
    let str = num.toFixed(3);
    // Remove trailing zeros after the decimal point
    str = str.replace(/\.?0+$/, "");
    // If it's just a whole number, remove the decimal point too
    return str.replace(/\.$/, "");
}

function logCSSFileInfo() {
    const rootStyles = getComputedStyle(document.documentElement);
    const fileInfo = rootStyles.getPropertyValue('--file-info').trim();
    if (fileInfo) {
      console.log('CSS file loaded. File info:', fileInfo);
    } else {
      console.log('File info not found in CSS.');
    }
  }
  
  // Call this function after the DOM is fully loaded
  document.addEventListener('DOMContentLoaded', logCSSFileInfo);
  

function maybeInitQuiz() {
    const appScreens = document.getElementById('app-screens');
    if (!appScreens) {
        console.log('Skipping quiz initialization because #app-screens is not present.');
        return;
    }
    initQuiz();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', maybeInitQuiz);
} else {
    maybeInitQuiz();
}

// Add this new function
function handleAnswerInput(e) {
    const answerInput = e.target;
    const userAnswer = answerInput.value.trim();
    
    // Skip if empty
    if (!userAnswer) return;
    
    // Get the number of digits in the correct answer
    const correctAnswerDigits = Math.abs(Math.round(problemData.correctAnswer))
        .toString()
        .length;
    
    // Get the number of digits in the user's answer
    const userAnswerDigits = userAnswer.replace(/[^0-9]/g, '').length;
    
    // Auto-submit if the lengths match
    if (userAnswerDigits === correctAnswerDigits) {
        submitAnswer();
    }
}

// Log viewport, DPI and font size info
document.addEventListener('DOMContentLoaded', function() {
    // Log viewport info
    console.log('Viewport width:', window.innerWidth);
    console.log('Device pixel ratio:', window.devicePixelRatio);
    
    // Log font size
    const root = document.documentElement;
    const computedStyle = getComputedStyle(root);
    console.log('Main font size:', computedStyle.getPropertyValue('--main-font-size'));
    
    // Log DPI info
    const isHighDPI = window.devicePixelRatio >= 2;
    console.log('Is High DPI display:', isHighDPI);
});

// ===== END OF FILE math_quiz.js =====
