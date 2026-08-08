# Focus on Foundations Site Specification

## Purpose
Focus on Foundations is a deployed Astro static site for source-backed AI Q&A demos and transcript browsing. It replaced the prior Webflow embed stack while keeping the existing AWS API Gateway/Lambda QRAG backends, corpus data, and public domains.

This single `app` capability is the S2-deployed baseline for the whole application: public site shell, QRAG demo UI, transcript corpus pages, legacy redirects, legal pages, and AWS static-hosting/deploy mechanics. Split it into narrower capabilities later only when the file becomes too large or different behavior areas need independent change control.

## Workflows
### Workflow: Explore Public Site
Open home page -> navigate demos, transcripts, terms, and privacy -> land on shared static pages or the not-found page when a route is missing.
Exercises requirements: Public Site Shell, Demo Catalog, Legal Pages

### Workflow: Ask A QRAG Question
Open a demo -> accept privacy consent -> submit a name -> choose chunk count and date range -> ask a validated question -> see routed excerpts and final AI answer in the result accordion.
Exercises requirements: Demo Catalog, Privacy Consent And User Identity, QRAG Query Configuration, Input Validation, QRAG Request Flow, QRAG Result Presentation

### Workflow: Save Or Share QRAG Results
Receive a QRAG result -> download accumulated markdown or reveal the email form -> validate the email -> send the rendered result content and record the action.
Exercises requirements: Result Download And Email Sharing, Input Validation

### Workflow: Browse Source Transcripts
Open transcript hub -> choose a corpus -> open a transcript item -> fetch or render the transcript/Q&A viewer -> toggle transcript versus Q&A and fold detail levels.
Exercises requirements: Transcript Corpus Indexes, Transcript Item Viewers, Transcript Folding Controls

### Workflow: Preserve Routes And Deploy Content
Open a legacy Webflow-era URL -> redirect to the current Astro route -> build static content -> sync to S3 with cache headers -> invalidate CloudFront for staging or production.
Exercises requirements: Legacy Redirects, Static Hosting And Deployment, Public Site Shell

## Requirements
### Requirement: Public Site Shell
The system SHALL serve a static Focus on Foundations public site with shared layout, navigation, home page, demo hub, transcript hub, legal links, and a not-found page.

#### Scenario: Visitor opens the home page
- **WHEN** a visitor opens `/`
- **THEN** the system displays the Focus on Foundations landing page with the "Deep Optimism" tagline, links to the demos, and context areas for education, public safety, government and policy, pandemic response, and serious-use AI tools.

#### Scenario: Visitor uses the main navigation
- **WHEN** a visitor views a page with the shared header
- **THEN** the system provides navigation links to Home, Demos, Transcripts, Terms, and Privacy, with the active section marked for the current path.

#### Scenario: Visitor requests an unknown page
- **WHEN** a visitor opens a path that does not map to a generated Astro route
- **THEN** the system serves a static not-found page with links back to the home page and demos.

### Requirement: Demo Catalog
The system SHALL publish a demo hub and four QRAG demo pages configured from the app's demo registry.

#### Scenario: Visitor opens the demo hub
- **WHEN** a visitor opens `/demos/`
- **THEN** the system lists the Deutsch Interviews, FDA COVID-19 Town Halls, PV School Evacuation, and The Sovereign Child demos.

#### Scenario: Visitor opens a demo page
- **WHEN** a visitor opens one of the four `/demos/<slug>/` routes
- **THEN** the system displays that demo's title, description, source-transcript link, privacy consent box, name input, chunk-count selector, date range controls, question input, submit button, and results area.

### Requirement: Privacy Consent And User Identity
The system SHALL require current privacy consent and a submitted user name before accepting a QRAG question.

#### Scenario: Consent has not been accepted
- **WHEN** a visitor tries to submit a name or question without the current privacy consent version in session storage
- **THEN** the system shows a consent error and does not proceed with the submission.

#### Scenario: User accepts consent
- **WHEN** a visitor checks the privacy consent box
- **THEN** the system records consent version `2024-12-17` in session storage and hides the consent box.

#### Scenario: User submits a valid name
- **WHEN** a visitor enters a valid name and submits it by Enter or blur after consent
- **THEN** the system stores the name in session storage, posts the name context to the hash-store endpoint, stores returned JWT and hashed context values when present, blurs the name field, and briefly shows "Name saved".

### Requirement: QRAG Query Configuration
The system SHALL configure QRAG requests according to the selected demo, selected chunk count, current date range, and stored user context.

#### Scenario: Demo initializes
- **WHEN** a QRAG demo page loads
- **THEN** the system initializes that demo's vector index, route dictionary, optional large-context filename, date range bounds, submit button id, and display type from the demo registry.

#### Scenario: Visitor selects chunk count
- **WHEN** a visitor chooses 5, 10, 20, or 50 quoted selections
- **THEN** the system marks the selected option and stores the selected chunk count in session storage, defaulting to 10 when no value is stored.

#### Scenario: Visitor changes date range
- **WHEN** a visitor changes the start or end date
- **THEN** the system stores both dates in session storage and adjusts the opposing control so the start date cannot be after the end date.

### Requirement: Input Validation
The system SHALL validate and sanitize names, questions, and email addresses before sending them to backend APIs.

#### Scenario: Input is empty
- **WHEN** a visitor submits an empty name, question, or email field
- **THEN** the system rejects the value and shows a field-specific validation message.

#### Scenario: Input includes suspicious content
- **WHEN** a visitor submits content containing patterns such as script tags, `javascript:`, inline event handlers, or `eval(`
- **THEN** the system rejects the value, identifies it as suspicious, and sends a security notification attempt.

#### Scenario: Input is too long or contains disallowed characters
- **WHEN** a visitor submits otherwise acceptable input that exceeds length limits or contains disallowed characters
- **THEN** the system truncates or removes invalid characters, returns the sanitized value, and reports the modification when applicable.

### Requirement: QRAG Request Flow
The system SHALL submit each accepted question through the configured QRAG routing endpoint and then the QRAG LLM endpoint when the demo uses both functions.

#### Scenario: Question is accepted
- **WHEN** a visitor with consent and a stored name submits a valid question
- **THEN** the system sends the question, vector index, route dictionary, chunk count, user id, hashed user context, and stored date range to the QRAG routing endpoint.

#### Scenario: Routing response arrives
- **WHEN** the QRAG routing endpoint returns a response for a quoted-QA demo
- **THEN** the system creates a visible accordion result item before waiting for the final AI answer.

#### Scenario: LLM response requests retry
- **WHEN** the QRAG LLM endpoint returns a retry response
- **THEN** the system replaces the current accordion content with the retry response and retries the LLM call until the retry limit is exceeded or a final response arrives.

### Requirement: QRAG Result Presentation
The system SHALL render QRAG results as newest-first accordion items with the AI answer or waiting placeholder above extracted source quotes.

#### Scenario: Initial or final result is rendered
- **WHEN** the system creates or replaces a QRAG result item
- **THEN** it displays the user question as the accordion title and renders the AI answer or waiting text before the route preamble and extracted quotes.

#### Scenario: Extracted quotes are available
- **WHEN** a result includes quoted source Q&A
- **THEN** the system renders those quotes inside an open foldable "EXTRACTED QUOTES" details section.

#### Scenario: Submission finishes
- **WHEN** the question flow finishes successfully
- **THEN** the system resets the submit button, clears the question field, and preserves the rendered result in the results area.

### Requirement: Result Download And Email Sharing
The system SHALL allow users to download and email accumulated QRAG result markdown after the first result creates the sharing controls.

#### Scenario: User downloads results
- **WHEN** a visitor clicks the download action
- **THEN** the system downloads the hidden markdown transcript using a filename with the Pacific-time timestamp and demo-specific QRAG label.

#### Scenario: User sends results by email
- **WHEN** a visitor enters a valid email address and clicks send
- **THEN** the system posts the email context to hash-store, sends the rendered result content through the send-email endpoint, shows sending and success or failure status, and attempts to notify the site owner of the action.

#### Scenario: User expands email input
- **WHEN** a visitor clicks the email action
- **THEN** the system reveals the email input, restores a stored email when present, and shows the email-list checkbox only when no email is already stored.

### Requirement: Transcript Corpus Indexes
The system SHALL publish static transcript corpus indexes from committed corpus manifests.

#### Scenario: Visitor opens the transcript hub
- **WHEN** a visitor opens `/transcripts/`
- **THEN** the system lists each configured corpus with links to its source index and QRAG demo.

#### Scenario: Visitor opens a corpus index
- **WHEN** a visitor opens `/transcripts/deutsch/`, `/transcripts/fda-town-halls/`, `/transcripts/sovereign-child/`, or `/transcripts/pv-evacuation/`
- **THEN** the system lists the manifest items for that corpus and provides each item's transcript-and-Q&A link plus available external source links.

#### Scenario: Manifest counts are loaded
- **WHEN** the app loads the committed corpus manifests
- **THEN** the manifest set contains 95 Deutsch items, 100 FDA town hall items, 8 Sovereign Child items, and 3 PV evacuation items.

### Requirement: Transcript Item Viewers
The system SHALL generate per-document transcript routes that render the current viewer variant for each manifest item.

#### Scenario: Generic or FDA transcript opens
- **WHEN** a visitor opens a non-PV transcript item route
- **THEN** the system client-fetches the transcript HTML and Q&A HTML from the item's configured S3 URLs, renders both containers, and initially shows the transcript container.

#### Scenario: Transcript and Q&A are toggled
- **WHEN** a visitor clicks the loaded viewer's document toggle button
- **THEN** the system switches between transcript and Q&A containers while keeping the other container hidden.

#### Scenario: PV evacuation transcript opens
- **WHEN** a visitor opens a PV evacuation transcript item route
- **THEN** the system reads the committed markdown file at build time and initializes the Van11y accordion rendering for that markdown.

### Requirement: Transcript Folding Controls
The system SHALL provide transcript folding controls that match the current viewer variant.

#### Scenario: Generic flat document controls are used
- **WHEN** a visitor applies the generic collapse or all control on a flat transcript/Q&A document
- **THEN** the system closes or opens all `details` elements in the visible container.

#### Scenario: FDA-style nested controls are used
- **WHEN** a visitor applies FDA-style sections, questions, answers, all, or collapse controls
- **THEN** the system opens or closes nested `details` elements according to the selected depth.

### Requirement: Legacy Redirects
The system SHALL preserve legacy Webflow-era paths by redirecting them to the current Astro routes.

#### Scenario: Legacy FDA demo path opens
- **WHEN** a visitor opens `/fda-town-halls-qrag-demo/`
- **THEN** the system redirects permanently to `/demos/fda-town-halls/`.

#### Scenario: Legacy transcript index path opens
- **WHEN** a visitor opens `/deutsch-interviews-index`, `/fl-fda-vth-index`, or `/sov-child-transcripts-index`
- **THEN** the system redirects permanently to the corresponding `/transcripts/<corpus>/` index.

#### Scenario: Legacy transcript item path opens
- **WHEN** a visitor opens a generated legacy item route under deutsch, FDA town halls, sovereign child, sovereign child index, or PV evac prefixes
- **THEN** the system redirects permanently to the corresponding `/transcripts/<corpus>/<slug>/` route.

### Requirement: Legal Pages
The system SHALL render the current privacy policy and terms of service from shared Markdown source files.

#### Scenario: Visitor opens the privacy page
- **WHEN** a visitor opens `/privacy/`
- **THEN** the system displays the Privacy Policy page with last-updated date `2024-12-17` and rendered Markdown content from the shared privacy policy file.

#### Scenario: Visitor opens the terms page
- **WHEN** a visitor opens `/terms/`
- **THEN** the system displays the Terms of Service page with last-updated date `2024-12-17` and rendered Markdown content from the shared terms file.

#### Scenario: Visitor opens a legacy legal alias
- **WHEN** a visitor opens `/privacy-policy/` or `/terms-of-service/`
- **THEN** the system redirects permanently to `/privacy/` or `/terms/` respectively.

### Requirement: Static Hosting And Deployment
The system SHALL define and deploy the Astro static site through the app's AWS CDK infrastructure and content deployment scripts.

#### Scenario: CDK stack is synthesized
- **WHEN** the staging or production static-site stack is synthesized
- **THEN** the system defines a private versioned S3 bucket, CloudFront distribution, S3 origin access control, HTTPS redirect, URL rewrite function for extensionless routes, static 404 error responses, and long-lived cache policies for `_astro/*` and `assets/*`.

#### Scenario: External certificate mode is used
- **WHEN** a certificate ARN is supplied for staging or production
- **THEN** the system attaches the configured custom domain aliases and ACM certificate to CloudFront without creating Route 53 records.

#### Scenario: Content deploy runs
- **WHEN** `web/scripts/deploy.js` runs for staging or production
- **THEN** the system builds the Astro site, syncs HTML files with no-cache headers, syncs non-HTML assets with immutable cache headers, and creates a CloudFront invalidation for `/*`.
