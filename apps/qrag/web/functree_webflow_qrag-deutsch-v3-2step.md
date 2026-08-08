
## document.addEventListener("DOMContentLoaded", function())
├── getElementById('submitButtonQragDemo')
├── getElementById('userInputQragDemo')
├── userInputElementQragDemo.addEventListener('keydown', function(event))
│   └── event.preventDefault()
│   └── __submitButtonElementQragDemo.click()__
└── submitButtonElementQragDemo.addEventListener('click', submitInputQragDemo)

## submitInputQragDemo(event)
├── event.preventDefault()
├── getElementById('userInputQragDemo')
├── getElementById('submitButtonQragDemo')
├── __fetch('https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/qrag-routing'__, {...})
│   └── response.json()
│       └── __fetch('https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/qrag-llm'__, {...})
│           └── response.json()
│               └── __createAccordionSection(finalData.response)__
│                   ├── __ensureHiddenDivAndButtons()__
│                   |   ├── __downloadMarkdown()__
│                   |   └── __sendEmail(event)__
│                   └── __processJsonToMarkdown(response)__ > to write in Hidden Div
├── getElementById('userInputQragDemo')
└── Reset Button and Icon

## createAccordionSection(response)
├── __ensureHiddenDivAndButtons()__
├── processes json response to create new accordion elements
├── __processJsonToMarkdown(response)__
├── getElementById('hiddenMarkdownContent')
├── __addEventListener('click', function() {...})__
├── querySelectorAll('.accordion-dropdown-list')
├── appendChild()
└── insertBefore()

## ensureHiddenDivAndButtons()
├── getElementById('hiddenMarkdownContent')
├── createElement - downloadButton.addEventListener('click', downloadMarkdown)
├── createElement - emailButton.addEventListener('click', function() {...})
├── createElement - emailInput.addEventListener('keypress', function(event))
│   └── __sendEmail(event)__
├── createElement - emailCheckbox
├── createElement - emailCheckboxLabel
└── appendChild()

## sendEmail(event)
├── event.preventDefault()
├── getElementById('emailInputQragDemo')
├── getElementById('hiddenMarkdownContent')
├── __processMarkdownToTextAndHtml(markdownContent)__
├── __fetch('https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/send-email'__, {...})
│   └── response.json()
└── __displayMessage__

// only called by sendEmail - may be able to delete or reuse in other functions
## displayMessage(message, type)
├── createElement('div')
└── appendChild()

## processJsonToMarkdown(jsonData)
└── Process and format JSON to Markdown

## downloadMarkdown()
├── getElementById('hiddenMarkdownContent')
├── createElement('a')
└── link.click()

## simpleMarkdownToHtml(markdownString)
└── Convert Markdown to HTML
