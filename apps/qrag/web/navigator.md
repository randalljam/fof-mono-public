rag-devpage
NAVIGATOR VIEW
Body
├── Bot Page (class)
│   ├── Nav bar (component)
│   ├── Page Title Section (class)
│   │   └── Page Title Container (class)
│   │       └── Page Title Wrapper (class)
│   │           ├── Page Title Heading (class)
│   │           └── Page Title Paragraph (class)
│   ├── Bot Section (class)
│   │   └── Bot Container (class="w-layout-blockcontainer bot-container w-container") *id="container_rag-devpage_qrag"*
│   │       ├── Bot Title Text (class)
│   │       ├── container (class='text-submission-container')
│   │       |   |   __Text Submission Component (component)  DYNAMIC ASSIGN IDs for all 3__
│   │       |   └── div (class='html-embed w-embed')
│   │       |        ├──p (class='botsubmit-error') *id="submitError_rag-devpage_qrag"*
│   │       |        ├──textarea (class='botsubmit-textarea') *id="inputText_rag-devpage_qrag"*
│   │       |         └──button (class="primary-button w-button") *id="submitButton_rag-devpage_qrag"*
│   |       |           └──span >arrow_upward< (class="material-symbols-rounded") *id="submitIcon_rag-devpage_qrag"*
│   │       └── __Accordion Container (class="accordion-container") NO ID - ACCESS BY SUBMIT BUTTON REF__
│   |             └── __Accordion Card (class="accordion-card")  NO ID - ACCESS BY SUBMIT BUTTON REF__
│   └── Bot Section (class)
│       └── Bot Container (class="w-layout-blockcontainer bot-container w-container") *id="container_rag-devpage_vrag"*
│           ├── Bot Title Text (class)
│           |   |   __Text Submission Component (component)  DYNAMIC ASSIGN IDs for all 3__
│           |   └── div (class='html-embed w-embed')
│           |     ├──textarea (no class) *id="inputText_rag-devpage_vrag"*
│           |     └──button (class="primary-button w-button") *id="submitButton_rag-devpage_vrag"*
│           |        └──span >arrow_upward< (class="material-symbols-rounded") *id="submitIcon_rag-devpage_vrag"*
│           ├── __div 'hiddenDiv' (class='hidden-div')  DYNAMIC CREATE but no IDs needed__
│           ├── __div 'shareDiv' (class='share-div')  DYNAMIC CREATE INCLUDING ALL CHILDREN but no IDs needed__
│           │     ├── button 'downloadButton' (class="primary-button w-button") 
│           |     |   └──span >download< (class="material-symbols-rounded")
│           │     ├── button 'emailButton' (class="primary-button w-button")
│           |     |   └──span >mail< (class="material-symbols-rounded")
│           │     ├── input (class="email-input-address") (type="email")
│           |     └── container (class="email-checkbox-container")
│           │         ├── input (class="email-checkbox") (type="checkbox")
│           │         └── label (class="email-checkbox-label")
│           └── __Accordion Container (class="accordion-container") NO ID - ACCESS BY SUBMIT BUTTON REF__
│                 └── __Accordion Card (class="accordion-card")  NO ID - ACCESS BY SUBMIT BUTTON REF__
│                       └── Accordion Item (class="accordion-item w-dropdown")  CREATED BY JS
│                           ├── Accordion Toggle (class="accordion-toggle w-dropdown-toggle")
│                           │   ├── Accordion Icon (class="accordion-icon w-icon-dropdown-toggle")
│                           │   └── Accordion Title Text (class)
│                           └── Accordion Dropdown List (class="accordion-dropdown-list w-dropdown-list")
│                               ├── Accordion Dropdown Text (class)
│                               ├── Accordion Dropdown Text (class)
│                               └── Accordion Dropdown Text (class)
└── Footer (component)

# Prompts and Example
## Prompt to update based on function
Consider the following included function, INSERT FUNCTION NAME.
This function may create new elements or update attributes (class and ID) of existing elements.
Also included is the current Navigator View which is the hierarchical tree structure of a web page with specific formatting and information.
The task I would like you to append those elements to the current Navigator View of my page. Appended elements should be in the same format and include the appropriate information as those in the current Navigator View.
In your response only include the updated section, underneath an existing line for reference.

## Prompt to create from scratch
Please provide a hierarchical tree diagram using Markdown format with the following specifications:

Use '├──' to indicate branches.
Use '│' for continuing branches.
Use '└──' for the last child item in a group.
Ensure the vertical pipes ('│') connect lines at the same level but do not continue downward after the last item at that hierarchy level.
For any container or section that is the last child, use the '└──' symbol to properly terminate the hierarchy lines, ensuring there are no vertical pipes continuing after them.
For any elements that are components and are preceded by a small cube icon in the image, have them start with an asterisk.

Here's an example for clarity below. Do not include these instructions or the example in your response. Do include the page title line ('rag-test-deutsch-view' in the example) and the 'NAVIGATOR VIEW' line. Make your response only the hierarchical tree diagram in a css block, with no text before or after it.


rag-test-deutsch-both
NAVIGATOR VIEW
Body
├── Bot Page
│   ├── * Nav bar
│   ├── Page Title Section
│   │   └── Page Title Container
│   │       └── Page Title Wrapper
│   │           ├── Page Title Heading
│   │           └── Page Title Paragraph
│   ├── Bot Section
│   │   └── Bot Container
│   │       ├── Bot Title Text
│   │       ├── * Text Submission Component
│   │       └── Accordion Container
│   └── Bot Section
│       └── Bot Container
│           ├── Bot Title Text
│           ├── * Text Submission Component
│           └── Accordion Container
│               └── Accordion Card
└── * Footer


Body
├── qrag demo page
│   ├── Nav bar
│   ├── Hero Without Image 4
│   │   └── Container 15
│   │       └── Hero Wrapper Two 3
│   │           ├── Heading 7
│   │           └── Paragraph
│   ├── Section
│   │   └── Container
│   │       ├── Text Block 2
│   │       ├── User Input Text
│   │       └── Container 15
│   │           └── Accordion Card
│   └── Section
│       └── Container
│           ├── Text Block 2
│           ├── User Input Text
│           └── Container 15
│               └── Accordion Card
└── Footer


