# Webflow - User pages overview

Source: [Webflow Help Center - User pages overview](https://help.webflow.com/hc/en-us/articles/33961392822803-User-pages-overview#how-to-access-user-pages)
Last updated: 2 months ago

Access User pages to edit and style the pages that users will see.
When you click the Pages icon in the Webflow Designer, you'll see 5 types of pages:

- Static pages
- Utility pages (404, Password page, etc.)
- CMS Collection pages  
- Ecommerce pages
- User pages (appears after enabling User Accounts)

## Accessing User Pages

To access User pages, first ensure that you have User Accounts enabled on your site. Then:

1. Click the Pages icon to open the Pages panel 
2. User pages will show up under the User pages section

## Page Types

### Log in Page 

The Log in page is a form that allows users to log into their existing account or sign up for a new account if they don't already have one.

The Log in form contains:
- Heading
- Email field
- Password field  
- "Log in" button
- "Don't have an account?" span
- Sign up link

You can edit the text or styling for any of the elements in the Log in form.

**Note:** You can't remove the user email field, user password field, or the "Log in" button from the Log in form.

#### Form States and Configuration

The Log in form block has 2 states:

**Normal State:**
- Default state shown initially
- After successful submission, user is taken to redirect fallback page
- If accessing restricted content while logged out, successful login redirects to that content

To modify redirect after login:
1. Select the Log in form block
2. Go to Element settings > Log in form block settings
3. Choose page from redirect fallback dropdown

**Error State:**
- Shows when submission fails
- Error div block appears below form
- Can customize styling and error messages

Error message types:
- General error: "We're having trouble logging you in. Please try again, or contact us if you continue to have problems."
- Wrong credentials: "Invalid email or password. Please try again."

To edit error messages:
1. Select Log in form block
2. Go to Element settings > Log in form block settings
3. Choose error state
4. Select Error message text block
5. Go to Element settings > Error message settings
6. Click pencil icon and edit message

### Sign up Page

The Sign up page allows users to create a new account or log in to an existing one. 

The Sign up form contains:
- Heading
- Email field
- Name field
- Password field
- Privacy policy/terms checkbox
- Communications consent checkbox  
- Sign up button
- "Already have an account?" link
- Log in link

**Note:** Email field, password field and sign up button cannot be removed. Other fields can be removed via Element settings:

1. Select Sign up form on canvas
2. Go to Element settings > Sign up form settings
3. Click trash icon next to field to remove
4. To restore: Click plus icon next to Common fields and select from dropdown

#### Custom Fields

You can add custom fields to collect additional information:

1. Select Sign up form
2. Go to Element settings > Sign up form settings
3. Click plus icon next to Custom fields
4. Select field from Add input dropdown

**Important:** If a custom field is marked as required in User account settings, it must be added to the Sign up form to prevent submission errors.

#### Form Statuses

The sign up form has two main statuses:

**Default Status:**
- Normal state: Empty form for new signups
- Success state: Shows after email verification with:
  - Account activated heading
  - Success message
  - Call-to-action button to login page
- Error state: Shows validation errors

Error message types:
- General error: "There was an error signing you up..."
- Email not allowed: "You're not allowed to access this site..."
- Invalid email: "Make sure your email exists and is properly formatted..."
- Email already exists: "An account with this email address already exists..."
- Must use invite email: "Use the same email address your invitation was sent to..."
- Invalid password: "Your password must be at least 8 characters..."

**Verification Status:**
- Normal state: Shows email verification instructions
- Error state: Shows verification failed/expired messages

Verification error types:
- Verification failed: "We couldn't verify your account..."
- Verification expired: "This verification link has expired..." (valid for 24 hours)

### Reset Password Page

The Reset password page allows users to reset forgotten passwords.

Contains:
- Heading
- User email field
- Reset password button

**Note:** Email field and reset button cannot be removed.

#### Form States

Has three states:

**Normal State:**
- Initial form for email submission

**Success State:**
- Shows after valid email submitted
- Contains:
  - Image
  - Heading
  - Confirmation message about email sent
  - All elements can be styled

**Error State:**
- Shows for invalid email
- Displays error message below form
- Can customize message:
  1. Select Reset password form
  2. Go to Element settings > Reset password form block settings
  3. Select error state
  4. Edit message in settings

### Update Password Page

Accessed via reset password email link. 

Contains:
- Heading
- Explanation paragraph
- New password field
- Update button

**Note:** Password field and update button cannot be removed.

#### Form States

**Normal State:**
- Password entry form
- Requires minimum 8 characters

**Success State:**
- Shows after valid password update
- Contains:
  - Image
  - "Password updated" heading
  - Success message
  - Homepage button (auto-logs in user)

**Error State:**
- Shows for invalid password/general errors
- Error messages:
  - General error: "There was an error updating your password..."
  - Weak password: "Your password must be at least 8 characters..."

### Access Denied Page

The Access denied page appears when users attempt to access restricted content. Users can only access the requested page if:
- They are logged in 
- They are part of the access group that allows them to access that particular restricted content 

Contains:
- Lock icon
- "Access denied" heading
- Explanation paragraph about site membership requirement
- Sign up and Log in page links

All elements on the access denied page can be styled.

### User Account Page

The User account page allows users (verified or unverified) to manage their account information. The page shows pre-filled data from sign up and contains:

**Basic Elements:**
- "My Account" heading
- User account form with:
  - Email field (cannot be removed)
  - Name text field
  - "Password settings" heading
  - Reset password link
  - Marketing emails consent checkbox
  - Save changes button
  - Cancel button
- Custom fields (optional)
- Subscriptions management (if Ecommerce enabled)

#### Adding/Removing Fields

**To add a common field:**
1. Select User account form
2. Go to Element settings > User account form settings
3. Click plus icon next to Common fields

**To add a custom field:**
1. Select User account form
2. Go to Element settings > User account form settings
3. Click plus icon next to Custom fields 
4. Select field from Add input dropdown

**To remove a field:**
1. Select User account form
2. Go to Element settings > User account form settings
3. Click trash icon next to field in Common fields or Custom fields

**Note:** The "accept privacy policy and terms of service" checkbox cannot appear on the User account page to prevent users from un-accepting these terms.

#### Form States

The User account form has three states:

**Normal State:**
- Shows personal information
- Allows checking/unchecking marketing consent
- Enables saving changes

**Success State:**
- Shows after successful update
- Displays message: "Your account was updated successfully"
- Message can be edited/styled

**Error State:**
- Shows when form submission fails
- Displays error message: "There was an error updating your account. Please try again, or contact us if you continue to have problems"
- Message can be customized

#### Subscriptions Element

A prebuilt Subscriptions element can be added to manage site subscriptions:

**Requirements:**
- Both User Accounts and Ecommerce must be enabled
- Users must verify their account before purchasing memberships

**To add Subscriptions:**
1. Navigate to User account page
2. Go to Add panel > Elements > Ecommerce
3. Drag Subscriptions element onto canvas

Contains:
- Placeholder images
- Subscription details (name, price, dates)
- Cancel button
- Purchase/billing information

**Important:** Strong Card Authentication (SCA) purchases are currently not supported.

## Customization Options

### Forms

**Re-adding Forms:**
- Forms can be removed/re-added from Add panel
- Available for: Login, Sign up, Reset password, Update password, and User account pages
- Not available for Access denied page
- Useful for resetting to original styling

### Form Elements

#### Checkboxes

Default checkboxes:
- Sign up page: Privacy policy and communications consent
- User account page: Marketing emails consent

Customization options:
- Change checkbox name
- Switch between default/custom style
- Set as required/optional
- Set default checked state

To make required:
1. Select Checkbox
2. Go to Element settings > Checkbox settings
3. Check "Required" checkbox

To set default state:
1. Select Checkbox
2. Go to Element settings > Checkbox settings
3. Check/uncheck "Start checked" checkbox

#### Text Fields

Available on all pages except Access denied page.

**Placeholder Text:**
- Can be added to any field type
- Shows as light text in field
- Disappears on typing
- Not recommended for crucial information
- May not work with translation tools/screen readers

To add placeholder:
1. Select Text field
2. Go to Element settings > Text field settings
3. Add text to placeholder field

**Autofocus:**
- Available for non-password fields
- Places cursor in field on page load
- Best practice: Use on first field only
- Avoid on hidden fields

To add autofocus:
1. Select Text field
2. Go to Element settings > Text field settings
3. Check autofocus checkbox

#### Buttons

**Submit Button Customization:**
- Can edit default text (shown on load)
- Can edit waiting text (shown during submission)

To edit default text:
1. Select Submit button
2. Go to Element settings > Submit button settings
3. Edit text in Text field

To edit waiting text:
1. Select Submit button
2. Go to Element settings > Submit button settings
3. Edit text in Waiting text field

**Cancel Button:**
- Available on User account page
- Can customize default text
- To edit: Select button > Element settings > Cancel button settings

#### Links
- Available on all pages except Reset/Update password pages
- Can modify destination and settings
- To configure: Select Link > Element settings > Link settings

### User Account Settings

The User account settings provide control over user data fields and form layouts:

**Access Settings:**
1. Open Users panel
2. Hover over User accounts tab
3. Click settings cog on right side

#### Custom Fields

Two types of input fields:
- Common fields (email, name, password)
- Custom fields (up to 20 per site)

**Adding Custom Fields:**
1. Open Users panel
2. Click settings cog in User accounts section
3. Click Add field in Custom fields section
4. Select Field type
5. Input field name and slug
6. Configure additional settings

**Important Notes:**
- Custom fields must be manually added to forms
- Can set character count limits
- Required fields must be added to Sign up form
- Required status can only be changed in User account settings

**Updating Custom Fields:**
1. Open Users panel
2. Access Custom fields section
3. Click settings cog next to field
4. Make updates

**Removing Custom Fields:**
1. Open Users panel
2. Access Custom fields section
3. Click settings cog next to field
4. Click trash icon

### URL Structure

Reserved URLs (cannot be modified):
- /log-in
- /sign-up  
- /reset-password
- /update-password
- /access-denied
- /user-account

**Note:** These slugs remain reserved even after removing User Accounts.

### Additional Settings

#### Disabling User Systems

While User Accounts cannot be fully removed, you can:
- Disable user systems temporarily
- Unpublish user pages
- Retain user data for future reactivation

To disable:
1. Open Users panel
2. Click settings cog in User accounts
3. Toggle off "Enable publishing of user systems & pages"
4. Click Disable User systems
5. Publish site

#### Search Settings

**Excluding from Site Search:**
1. Open Pages panel
2. Click settings cog next to page
3. Go to Site search settings
4. Check "Exclude this page from site search results"

**Excluding from Search Engines:**
- Can disable indexing for user pages
- Prevents pages appearing in search results
- Configure through search engine indexing settings

**Important:** Disabling user systems will:
- Deactivate pending invites
- Stop new user imports
- Unpublish existing user pages
- Preserve existing user details and access groups

For more detailed information about specific features:
- [Learn more about excluding static pages](link)
- [Learn more about disabling indexing of site pages](link)
