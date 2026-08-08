# Webflow - User pages overview CONDENSED

Source: [Webflow Help Center - User pages overview](https://help.webflow.com/hc/en-us/articles/33961392822803-User-pages-overview#how-to-access-user-pages)
Last updated: 2 months ago

User pages allow you to edit and style the pages that site visitors will see when interacting with user account functionality. The Pages panel in the Webflow Designer shows 5 page types:

- Static pages
- Utility pages (404, Password page, etc.)
- CMS Collection pages  
- Ecommerce pages
- User pages (appears after enabling User Accounts)

## Accessing User Pages

1. Enable User Accounts for your site
2. Click the Pages icon to open the Pages panel
3. Find User pages section

## Page Types

### Log in Page

The Log in page contains a form for existing users to log in or new users to sign up. Key elements include:

- Heading
- Email field
- Password field  
- "Log in" button
- "Don't have an account?" text
- Sign up link

**Note:** The email field, password field, and login button cannot be removed.

The form has two states:

- Normal - Default state shown initially
- Error - Shown when submission fails

To modify the redirect after successful login:

1. Select the Log in form
2. Go to Element settings > Log in form block settings
3. Choose page from redirect fallback dropdown

Error messages that can appear:

- General error: "We're having trouble logging you in..."
- Wrong credentials: "Invalid email or password..."

### Sign up Page

The Sign up page allows new users to create an account. Form elements include:

- Heading
- Email field
- Name field
- Password field
- Privacy policy/terms checkbox
- Communications consent checkbox  
- Sign up button
- "Already have an account?" link
- Log in link

**Note:** Email field, password field and sign up button cannot be removed. Other fields can be removed via Element settings.

The form has two statuses:

**Default Status**
- Normal state - Empty form
- Success state - Shows after email verification
- Error state - Various validation errors

**Verification Status** 
- Normal state - Email verification instructions
- Error state - Verification failed/expired

### Reset Password Page

Allows users to reset forgotten passwords. Contains:

- Heading
- Email field
- Reset password button

States:
- Normal - Initial form
- Success - Email sent confirmation
- Error - Invalid email/general error

### Update Password Page

Accessed via reset password email link. Contains:

- Heading
- Instructions
- New password field
- Update button

States:
- Normal - Password entry form
- Success - Password updated confirmation
- Error - Invalid password/general error

### Access Denied Page

Shown when users attempt to access restricted content. Contains:

- Lock icon
- "Access denied" heading
- Explanation text
- Sign up/Login links

### User Account Page

Displays account information for logged in users. Contains:

- Account heading
- Email field
- Name field
- Password reset section
- Marketing consent checkbox
- Save/Cancel buttons
- Optional custom fields
- Optional subscription management

States:
- Normal - Account form
- Success - Update confirmation
- Error - Update failed

## Customization Options

### Forms
- Can be removed and re-added from Add panel
- Default fields cannot be removed
- Custom fields can be added/removed

### Elements
- Text fields support placeholder text and autofocus
- Checkboxes can be required/optional
- Submit/cancel button text is customizable
- Links can be reconfigured

### User Account Settings
- Manage data fields
- Add up to 20 custom fields
- Preview form layouts

### URL Structure
Reserved URLs:
- /log-in
- /sign-up  
- /reset-password
- /update-password
- /access-denied
- /user-account

### Additional Settings
- Can disable user systems temporarily
- Pages can be excluded from site search
- Pages can be excluded from search indexing

