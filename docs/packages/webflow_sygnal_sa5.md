# sa5 overview
https://attr.sygnal.com/

Sygnal Attributes v5
Webflow Tools that Make Your Site Better
SA5 is the lastest version of Sygnal's Webflow Utilities Library.
The tools here are 100% free, 100% open-source, and 100% designed for Webflow.  
Libraries
SA5 is divided into a series of individual libraries. 
Our Most Popular Libs
Library	Purpose	Features
SA5 HTML
A huge range of page-modification capabilities
Dynamic attributes
Truncate text w/ ellipses
Advanced sorting
Advanced filtering
Encoded Emails
Hide Sections w/ Empty Collection Lists
and much more...
SA5 User Accounts
Get logged in user info to personalize your site and improve user experience.
Custom-route on login. 
User name
Email
Custom fields
Access groups
SA5 Rich Text
Add capabilities to Webflow's Rich Text Block
Responsive inline images
SA5 Layout
Advanced, dynamic layouts for your Webflow pages
Restructure your collection lists entirely into groups
Create dynamic tabs from the CMS
Overcome Webflow's 5-nested-item limit 
SA5 Forms
Easily replace Webflow's native form handler with your choice of 3rd party handlers like Basin, Zapier, Make, and n8n. 
Eliminate SPAM
Trigger automations  
SA5 Modals
Create powerful, consistent modals with full design control and zero interactions
SA5 Hotkeys
Define custom hotkeys to trigger your scripts, page actions and navigation
SA5 URL
Special URL enhancement tools
Pass-through your query params from one page to another for referer tracking
Target all external links to a new tab
SA5 Video
Add capabilities to your video elements 
Youtube Hide related videos
Background Video poster image
Video player
SA5 Elements
Control Webflow's elements with code, and receive events when they change
Tabs
Sliders
Buttons
Dropdown menus
Lightboxes
Radio buttons
Accordions
Lotties
Locale Switcher
SA5 Format
Format numbers and currencies & dates specially
Locale-specific formatting
SA5 Track
Special tracking using cookies and webStorage
SA5 Select Custom
Custom Select element based on Finsweet's attribute of the same name.  Adds some dynamic update capabilities
Specialized Use / Advanced Libs;
Library	Purpose	Features
SA5 Core
Central to SA5, but has a few tricks up its sleeve
Hide objects in the designer and make them visible in the published site
SA5 Cache
Handle high-latency tasks such as content-fetching with a built-in caching layer.
Allows complex calculations and slow data retrievals to easily cache.
Code your update directly to the cache layer and it will "lazy load" the content when needed.
SA5 Embeds 
Embed external content into your blog posts and pages.
Tables from Google Docs
SA5 Social Share
Adds Email as a social share option.  Designed to work in conjunction with Finsweet's Social Share component.
Adds share-to-email
SA5 Analytics
Adds some analytics capabilities to your site using attributes. 
GTM dataLayer events
UTM Tracking
Rel Attributes
A/B testing
SA5 Data
Extract CMS data into JS objects from your collection lists, to power your custom code and calculations. 
Extract data from collection lists into datasources
Extract querystring data, and URL data
Cookies and webStorage
Data-bind these pieces of information to text elements and form inputs
SA5 404
Improve your 404 pages 
Smart search trigger Webflow site search based on the Path the user was looking for 
SA5 Countup
Animated count up to a set value. Triggers on scroll-into-view 
SA5 UI
Special UI components 
5-star ratings component ( display only ) 
SA5 Demo
Add special capabilities to your Webflow demo sites, such as links to the correct readonly link page. 
SA5 Commerce
Simple commerce solutions for one-off purchases. 
Paypal
Windcave
SA5 Trigger
Custom trigger items and interactions from text links and buttons. 
Trigger interactions, such as pop-ups and modals from a link
Support CMS-driven scenarios 
Experimental Libraries & Features 🧪
These are libraries we're experimenting with. 
Now you can sponsor the development of those features, and they will be added to the library for everyone to use. 
Library	Purpose	Features
SA5 Calc 🧪
Calculate & sum items
SA5 SEO 🧪
Some SEO tools
Noindex
Nofollow
JSON-LD 
SA5 Fixup 🧪
Fix a few things in Webflow editor and published sites.
SA5 Logic 🧪
Add logic capabilities using attributes, for conditional visibility and page structuring
If
Switch
SA5 Effects 🧪
Experimental effects
Depthmap ( fake 3d ) 
SA5 State 🧪
State management 
SA5 Booking 🧪
Tag trigger elements easily to invoke 3rd party booking systems with the correct service, location, category, and staff member. 
GetTimely
SimplyBook
SA5 Localization 🧪
Various localization features
SA5 Detect 🧪
Detect and manipulate your page depending on how 
SA5 Table
Add HTML tables
We've also begun including our dev team and roadmap notes in these docs so that they are available for community comment and discussion. You can expand most features for a Future notes document. 
Feature Requests
Share your ideas in SA5's forum. 
If you'd like a specific feature built that you already see on our design board here, you can sponsor a feature.  Features marked with 
2023 Review of SA5's Capabilities

Navigating the Docs
Documentation is organized by library 
At the top of most libraries, you'll two important pages-
🔍 About this Library, which gives you an overview of the capabilities
🚀 Quick Start, which gives you the library code you need 
Within each library the features are grouped separately
A lot of features have subpages- make sure to click the > to expand those sections

🧪 indicates EXPERIMENTAL items, which are not yet available 
📝 indicates NOTES, which are primarily for the dev team 
▶️ indicates VIDEO TUTORIALS, which we're just beginning to add
What’s new in v5?
The tech changes we've made in v5 open the doors to a lot of new capabilities.
If you are using v4, none of these changes will affect your current websites. 
Since all of our CDN URLs are version-locked, you’ll continue to use the same libraries you are using now until you upgrade to the newer versions, someday, if you want to.
The v5 Tech Stack
We’ve changing from a JavaScript ES6 codebase to TypeScript
We’ve changed fully from CSS to SASS.
We’ve eliminating all use of jQuery in the libraries.
We’ve separated classes through the library into discrete source files
We’ve bundled the distributed files differently for even greater efficiency
We've integrated debugging features 
We’re excited about the tremendous capabilities the new stack gives us.
Switching to v5
If you choose to switch to the upgraded v5 libraries at some point, you’ll see a few minor integration changes;
Javascript <script> elements;
Will be moved from the before-/body section to the before-/head section of your pages and site-wide code settings.
The library URLs will change to point at the /dist/ path, rather than the /src/ path.
You'll also notice that the type=module is dropped
CSS <link> elements will essentially remain unchanged, and will continue to point to /dist/css/
All of this is covered in the docs for each feature, and we’ll update the docs as each library is migrated, so that you can upgrade them if you choose to.
What about attribute or code changes?
You can simply reference the new libraries with no changes to your custom attributes or existing features- and you’ll still get the enhanced features and performance benefits.
Will I need to upgrade to v5 eventually?
Nope! If you’re happy with things as they are and don’t need any of the new features, you don’t need to change a thing. v4 will continue to run indefinitely. 
Last updated 1 month ago

# sa5 user accounts
## quick start SA5 user accounts
https://attr.sygnal.com/sa5-user-accounts/quick-start
Quick Start | SA5 User Accounts
How to Easily Add SA5's User Info & Advanced Routing Enhancements to Your Webflow Memberships Site
All of SA5's Membership features are now consolidated into a single library, so you only need one library include. 
How to Add the Library
Add this script to the site wide custom code HEAD area of your site. 
Copy
<!-- Sygnal Attributes 5 | User Accounts --> 
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/sygnaltech/webflow-util@5.4.6/dist/css/webflow-membership.css"> 
<script defer src="https://cdn.jsdelivr.net/gh/sygnaltech/webflow-util@5.4.6/dist/nocode/webflow-membership.js"></script>
<script>
window.sa5 = window.sa5 || [];
window.sa5.push(['getMembershipConfig', 
  (config) => {
    // Apply any configuration settings here
    // such as access groups 
    return config;
  }]);
</script>
Once you've added the library, both the User Info and the Advanced Log-In & Sign-Up Flow features are available to use.
Current User Info Quick Start
The User Info library can be considered as 3 feature sets. 
Basic user info like name, email, and opt-in is automatically accessible once the library is installed. 
Custom user fields requires special setup on your /access-group page. Make sure to read that section if you want to access that data.
Access groups also requires a special setup. Make sure to read those pages if you want access to your access group data. 
User info works automatically behind the scenes, and gathers data when a User first logs in. 
To access User Info, you can use the data-binding feature on an element, such as a form field. Add a custom attribute of wfu-bind with the DSD you want to the element you want data-bound. 
For example, this custom attribute setting on an INPUT element will data-bind the user's email;
wfu-bind = $user.email
See SA5's full list of data source descriptors for User Info here. 
If you want to use the user's info in custom code, use the callback option, and you get the full user object.
Users who are already logged in will need to log out, and log in again in order for the library to refresh their data. 
Log-In & Sign-Up Flow Quick Start
We use the same library above for this module.
However it requires configuration which is done through a configuration callback.
See here for the code to configure log-in & sign-up flow. 
Add the custom attributes for the features you need, described in each feature separately.  

## callback option - Logged-In User Info
Logged-In User Info ❺
In Webflow Memberships, get details of the currently logged-in user, anywhere in your site.
Questions? Comments? Suggestions? Join the Sygnal Attributes forum on discourse.
NOTE: because User Info is a complex module in Sygnal Attributes, documentation is split in to several pages. Make sure to find and expand this item in the left-side nav, and explore the sub-pages below this one, they contain important configuration information. 
One of the most sought-after capabilities in Webflow User Accounts is the ability to access information about the currently logged in user, anywhere in your site.
Use cases include;
Personalize your site by displaying the user's name in the top navigation of all pages
Auto-fill the logged-in user's email in a form email field, so they don't have to type it every time.
Have a unique identifier for the user, for integrating into external systems via logic, script, or automation.
Use custom user field data anywhere in your site to personalize their experience... favorite color, darkmode, calculations based on their age, or gender... whatever you like. 
Customize any page of your site to specific access groups, so that certain elements only appear to those who should see them. 
Features;
Get the current user's email, name, and marketing opt-in status 
Get a unique, User-specific alternate ID which can be used for system integrations 
Get custom user fields 
Get access groups 
Heavily optimized, with a multi-layered, asynchronous load approach to assembling the user data.  
Limitations; 
For custom user fields, the File field type is unsupported for now 
Currently the Webflow UserID is not easily available. See here for solutions, if you need it for external system integrations with Webflow's API. 
Currently this library depends on the User Account screen in order to access user data and compose the user object. You can do what you want with your User Account page however those user fields must exist in the page ( even hidden ) in order for this library to work.   
Read-only. The library is designed to read user data, but not to update it. 
Demonstration
Here's a new cloneable, specific for SA5-
Logo
Get the Current User's Info in Memberships - Webflow
Get the Current User's Info in Memberships
Accessing User Information
When a user is logged in, the User Info is constructed and the object contains this information;
name - The user's name, as they've specified in account info
email - The user's email address
name_short - A pseudonym, composed from the email's name@ portion
name_short_clean - The name_short pseudonym, without the @
name_short_tcase - The name_short_clean pseudonym, title cased
user_id_alt - A unique ID for the User. This is not the Webflow Membership's ID, and cannot be used with Webflow's API - but is equally usable for 3rd party system integration and tracking.
data - A map of the user's custom fields. These are named using Webflow's internal data field names, which is based on your individual user field slugs.
Any of these can be accessed directly from the User object, which is provided in the callback function as soon as it is available.
Data Binding
You can automatically data-bind user information to any element you like, using custom attributes. 
Simply use the wfu-bind custom attribute, with $user. and the value you want.
For example;
To data-bind the User's email address to an input field, add the custom attribute;
wfu-bind = $user.email
To data-bind the User's name to a text field, add the custom attribute;
wfu-bind = $user.name
To data-bind a custom user field, named City ( slug city ), add the custom attribute;
wfu-bind = $user.data.city
The $user convention is used only in the wfu-bind custom attribute. If you want to access the user object in JavaScript, see the next section. 
Accessing the User object in JavaScript
If you want to access the user object in code, you can do this most easily in the callback function, where the user object is already passed. Here you know the user object has been initialized and contains data, so it's the best place to access it.
Copy
<script>
window.sa5 = window.sa5 || [];
window.sa5.push(['userInfoChanged', 
  (user) => {
    console.log("USER INFO CHANGED", user); 
  }]); 
</script> 
Usage Notes
Drop in the script below. User information loads automatically, and asynchronously.
If a user is logged in, any data-bound fields will be populated automatically. Your callback JS function will be also called, and you can do what you want with the user's available info in script. 
IMPORTANT: This library depends on Webflow's User Account  page ( at/user-account ) as the mechanism to access and load User data. 
All basic user info fields MUST exist, including Name, Email, and the Opt-in checkbox. These fields may be hidden, but they MUST exist in the page. Custom User Data fields must also exist if you want them, see Custom User Fields for details. 
If you have removed any fields or need to add custom fields, you can add these in using the right side designer menu when the form is selected on the User Account page. 
Data Security
We protect user data.
We consider all user data to be sensitive and it's important to treat it carefully. 
Even basic contact information should never be kept in the browser cache longer than necessary. To maximize security, we build the user information object on first request, and then dispose of it as soon as the browser tab is closed. 
In our testing, this gives the best user data security, while maximizing your site's performance- both of which are primary concerns for us and our clients. 
Questions? Let us know - attr@sygnal.com. 
Personally Identifiable Information ( PII )
In Webflow Memberships, the only unique, persistent identifier we have access to client-side is the user's email address, which can not be changed. 
However as this absolutely qualifies as PII, we do not want to use this as an identifier for integrating with other external systems. 
To provide for this, we manufacture an Alt User ID as a one-way hash of the user's email. Use this when you need to "attach" data in an external system. 
Future
Callback on login
Login on external system, retrieve data
Callback on first login
Setup account on external system
Inactivity logout timer settings 
Login activity logging 
Getting Started ( NOCODE )
IMPORTANT: If you are upgrading from SA4, it's important to note that the code is now completely different and much simpler. 
It's now in the site-wide before HEAD rather than the before BODY code area
You no longer include the data-binding library
You do not need to initialize the data-binding library
The script is no longer type=module, and it needs defer 
Don't blindly copy and paste URLs, you're much better to copy the code block here, and replace the old one directly. If you are using the custom callback feature, it is redesign as well, see STEP 3 for that new code. 
STEP 1 - Add the Library
First, add the library as detailed in Quick Start.
STEP 2 - Use the wfu-bind attribute to automatically load data into DOM elements 
SA5's Data-Binding feature can access logged-in user info as well, and you can easily data-bind it to text elements, titles, spans, form INPUT elements, and more. You can use this to, for example, automatically populate a form field with the logged-in User's email address.
See above for details. 
STEP 3 - ( OPTIONAL ) Add custom code to use User Info specially
Place this also in the before HEAD of your site, just after the library code above. If it's page-specific, you can instead place it on the before HEAD of specific pages if you like. 
Copy
<!-- Sygnal Attributes 5 | Memberships | User Info Changed Event -->
<script>
window.sa5 = window.sa5 || [];
window.sa5.push(['userInfoChanged', 
  (user) => {
    console.log("USER INFO CHANGED", user); 
  }]); 
</script> 
You should be able to have multiple instances of this code block, for example site-wide, and page specific, at the same time - however this has not been production tested. Test it carefully if you want to experiment with this approach. 
Last updated 3 months ago