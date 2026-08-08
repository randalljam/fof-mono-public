# Spec Delta — Auth Accounts Init

## MODIFIED Requirements

### Requirement: Privacy Consent And User Identity
The system SHALL require current privacy consent before accepting a QRAG question, and SHALL NOT collect a user name; accepting consent starts a guest session (a logged consent event that issues the demo session token) transparently.

#### Scenario: Consent has not been accepted
- **WHEN** a visitor tries to submit a question without the current privacy consent version in session storage
- **THEN** the system shows a consent error and does not proceed.

#### Scenario: Visitor accepts consent
- **WHEN** a visitor checks the privacy consent box
- **THEN** the system records the consent version, hides the consent box, and obtains the demo session token in the background; the first question waits for the token instead of failing.

## ADDED Requirements

### Requirement: Terms Acceptance At Account Creation
The system SHALL require explicit acceptance of the Terms of Service and Privacy Policy (with links) to create an account, record the accepted version on the user's profile, and present Terms/Privacy links on the account and create-account pages rather than in the site header and footer.

#### Scenario: Creation without acceptance is refused
- **WHEN** the create-account form is submitted without the terms checkbox checked
- **THEN** the system shows an error and does not create the account.

### Requirement: Account Creation And Email Confirmation
The system SHALL let a visitor create an account with an email address and password, and SHALL require email confirmation before the account can sign in.

#### Scenario: Visitor creates an account
- **WHEN** a visitor submits the create-account form with a valid email and a password meeting the password policy
- **THEN** the system creates a Cognito user, sends a confirmation code to the email address, and shows the confirm-email step.

#### Scenario: Visitor confirms their email
- **WHEN** the visitor enters the emailed confirmation code
- **THEN** the system confirms the account and directs the user to sign in (or completes sign-in when auto-sign-in applies).

### Requirement: Password Sign-In
The system SHALL let a confirmed user sign in with email and password, maintain the session via Cognito-issued tokens with automatic refresh, and let the user sign out.

#### Scenario: User signs in with password
- **WHEN** a confirmed user submits a correct email and password
- **THEN** the system establishes a signed-in session and the header reflects the signed-in state.

#### Scenario: User signs out
- **WHEN** a signed-in user chooses sign out
- **THEN** the system clears local tokens and returns the header to the signed-out state.

### Requirement: Email Code Sign-In
The system SHALL offer passwordless sign-in where the user requests a code, receives it by email, and enters it to sign in.

#### Scenario: User signs in with an emailed code
- **WHEN** a user chooses "email me a code" and submits their address, then enters the code from the email
- **THEN** the system signs the user in without a password.

### Requirement: Password Reset
The system SHALL provide a forgot-password flow that emails a reset code and accepts a new password.

#### Scenario: User resets a forgotten password
- **WHEN** a user requests a password reset, enters the emailed code, and submits a new valid password
- **THEN** the system updates the password and the user can sign in with it.

### Requirement: Social Sign-In Readiness
The system SHALL support Google and Facebook sign-in through Cognito identity providers, with each provider active only when its OAuth credentials are configured, and SHALL hide social buttons for providers that are not active.

#### Scenario: Provider is not yet configured
- **WHEN** the account pages render while no social identity provider is enabled in configuration
- **THEN** the system shows only email-based sign-in options.

#### Scenario: Provider is configured
- **WHEN** Google or Facebook is enabled in configuration and a user chooses it
- **THEN** the system completes the OAuth redirect flow through the Cognito hosted domain and establishes a signed-in session.

### Requirement: Guest Mode
The system SHALL let visitors use site features without an account, store guest work in browser local storage under a dedicated namespace, and tell guests that creating an account will preserve their work.

#### Scenario: Guest sees the local-storage notice
- **WHEN** a visitor uses a feature that saves guest work while signed out
- **THEN** the system shows a notice that work is stored locally in this browser and will carry over if they create an account.

#### Scenario: Guest creates an account
- **WHEN** a guest with locally stored work creates an account and signs in
- **THEN** the system invokes the guest-migration hook so guest work is preserved for the account (server-side upload activates when the user-data API ships).

### Requirement: Family Accounts
The system SHALL let a signed-in adult create a family, invite co-guardians with single-use expiring codes, and create child accounts; guardians manage children's access settings and data, and children cannot manage entitlements, read other members' data, or delete their own accounts.

#### Scenario: Guardian creates a child account with recorded consent
- **WHEN** a guardian submits the add-child form with a display name, sign-in email, password, and the checked guardian-consent statement
- **THEN** the system creates the child's sign-in without any self-signup step, records the consent (guardian, version, timestamp) on the family membership and the child's profile, and applies child-default entitlements (no analysis access).

#### Scenario: Child account creation without consent is refused
- **WHEN** a child-account request arrives without the consent agreement
- **THEN** the system refuses with an error and creates nothing.

#### Scenario: Guardian reviews a child's data
- **WHEN** a guardian with family-scope analysis access requests a family member's data
- **THEN** the system verifies the guardian role and family membership server-side and returns the child's entries, profile, and consent record.

#### Scenario: Non-guardians cannot cross account boundaries
- **WHEN** a child or a non-family user requests another user's data, or a child attempts to change entitlements or delete their own account
- **THEN** the system refuses with a forbidden error; child deletion is available only to the family's guardians.

#### Scenario: Guardian invites a co-guardian by email
- **WHEN** a guardian submits an invitee email (optionally with a custom message and a send-me-a-copy option)
- **THEN** the system emails the invitee a link carrying a single-use, expiring invite; opening it and signing in (or creating an account) joins them to the family as a guardian without manually entering a code.

#### Scenario: Guardian deletes a child account (consent revocation)
- **WHEN** a guardian confirms child-account deletion
- **THEN** the system permanently removes the child's data partition, files, sign-in, and family membership.

### Requirement: Per-App Entitlements
The system SHALL resolve per-app access settings (analysis-tool access and own-versus-family scope) from an account's profile, defaulting guardians to family-scope analysis, children to none, and standalone adults to own-scope; guardians set children's entitlements, and family-scope data reads are enforced against the caller's entitlements server-side.

#### Scenario: Entitlement resolution order
- **WHEN** an app checks an account's entitlement
- **THEN** the app-specific setting wins over the account's default (`*`) setting, and absence of both denies analysis access.

### Requirement: Per-User Data Foundation
The system SHALL provision a per-environment DynamoDB user-data table keyed by Cognito user id, designed so that all of a user's data can be enumerated and deleted, with reserved key patterns for app data and future billing/credits/API-key records.

#### Scenario: Account data is deletable
- **WHEN** an account deletion is executed (operationally in phase 1; self-serve in a later phase)
- **THEN** all items under the user's partition key can be removed and the Cognito user deleted, leaving no server-side account data.
