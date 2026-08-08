// ===== START OF FILE web/aws_chalice/chalice_new_lambda_checklist.md =====

## Update - delete lambda resource-based policy ApiGatewayInvoke

Resource-based policies on Lambda functions authorize other services (like API Gateway) to invoke your Lambda. Here's how they work:

1. **Resource-based policies vs. IAM role policies**:
   - **Resource-based policies**: Control who can access your Lambda function
   - **IAM role policies**: Control what AWS resources your Lambda function can access

2. **Your two statements**:
   - The first one (with ID 64444ff9...) is likely automatically created when API Gateway is set up, with a specific ARN condition limiting which API Gateway can invoke it
   - The second one (ApiGatewayInvoke) is the manual one added in step 8 of your checklist and gives broader permission to API Gateway generally

3. **Do you need both?** No, they're redundant. The first one is actually more secure because it restricts invocation to a specific API Gateway ARN. The second one (manual "ApiGatewayInvoke") is broader and allows any API Gateway to invoke your function.

4. **API Gateway permissions**: API Gateway doesn't need its own resource policy since it's the one doing the invoking. The permissions flow is:
   - Client → API Gateway → Lambda

You can safely delete the second broader policy (ApiGatewayInvoke) since the first one already provides the necessary permission with better security through the ArnLike condition.


##  Process Checklist - New AWS Lambda Function

### Purpose
Create a new AWS Lambda function using Chalice and according to our conventions and standards, including security, monitoring, and logging.

### Deliverables
- A new Chalice-based Lambda function deployed to AWS.
- Updated `config.json` to include environment variables, API key requirements, and IAM role configuration.
- IAM policies attached to the Lambda’s execution role and resource-based policies added for API Gateway invocation.
- AWS API Gateway usage plan and API key association.
- AWS WAF Web ACL linked to API Gateway for rate-based rules.
- CloudWatch alarms and AWS Budget alerts verified.
- Logging of user input (hashed) and IP addresses in S3 for compliance.

### Background
- Using Chalice for quick creation and deployment of Lambda functions.
- The existing environment includes previously deployed functions and WAF configuration.
- Enhanced security steps (API keys, WAF) and logging (CloudWatch, S3) have been incrementally added to other functions, serving as references.

### Relevant Files and Folders
- `web/aws_chalice`: corpus-tools repo root folder for all AWS lambda functions
- `web/aws_chalice/<my_new_func>`: new lambda function folder
  - `app.py`: The main Chalice application code.  
  - `chalicelib/*.py`: Python modules containing logic reused across Chalice functions.
  - `.chalice/config.json`: Chalice configuration file for environment variables, IAM roles, and deployment settings.
  - `requirements.txt`: List of dependencies for the new function.
- `web/aws_chalice/chalicelib_mirror_deploy.sh`: Script to deploy and sync `chalicelib` modules and inject environment variables.
- `.env`: File containing secrets and environment variables.

### Undecided
- What IAM policies and roles will be managed via the AWS Console vs set in aws.py code vs in config.json?


## Task Punch List

1. [x] Decide on new lambda function name, then run the following terminal commands:
  - `cd web/aws_chalice`
  - `chalice new-project <my_new_func>`
  - `cd <my_new_func>`
2. [x] Copy key files from the most similar existing lambda function.
  - [x] delete the existing `app.py`, `config.json`, and `requirements.txt`
  - [x] copy over `app.py`
  - [x] copy over the entire `chalicelib` folder
  - [x] copy over `.chalice/config.json` and replace function name
  - [x] copy over `requirements.txt`
3. [x] Setup the new `app.py` file:
  - [x] find and replace existing function name with new function name
  - [x] change app route if needed
  - WAIT to edit the code and the bottom section with the API url and tests
4. [NONE] Update `requirements.txt` with any new dependencies.
5. [NONE] Update `config.json` with any changes to environment variables, `api_key_required` routes, and IAM role ARN.
6. [x] Do quick code edit on the app.py file
7. [x] Deploy the new function with the mirror script
  - [x] copy the API url and arn to the bottom section of app.py
8. [x] Add resource-based policy to allow API Gateway invocation by running at terminal
  - make sure to replace <my_new_func-dev> with the actual function name including the -dev suffix
aws lambda add-permission \
    --function-name <my_new_func-dev> \
    --statement-id ApiGatewayInvoke \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com
9. [x] Update IAM role policies- open by going to Lambda > Functions > <my_new_func> > Configuration > Execution role
  - [x] Add AWSLambdaBasicExecutionRole
        - go to Add permissions > Attach policies > start typing in Search box" AWSL...e > check the box > Add permissions
  - [x] Add S3LambdaReadWriteAccess-[S3-BUCKET]
        - go to Add permissions > Attach policies > Filter by type - select Customer managed policies ...
10. [x] Test with portal API gateway
        - if error, check for any packages that are not installed in requirements.txt
11. [x] Configure API Gateway to associate usage plan and API key
        - run aws.py setup_api_security("my_new_func") - leave API_key_id blank (NONE) to use the demo key
        - run list_api_keys() to confirm the API Gateway is associated with the usage plan and API key
12. [x] Test with curl with API key
13. [x] Integrate AWS WAF with the API Gateway stage for rate-based IP limiting.
        - go to AWS WAF > Web ACLs > <my_new_func-dev> > Associated AWS resources > Add AWS resources
14. [x] Verify CloudWatch alarms, AWS Budget alerts, and logging for the new function.
       - see below, use name API-<my-new-func>-5XXError-Alarm
15. [x] Test with curl with API key

## Implementation Details

### 8. IAM role policies
Customer managed policy:
S3LambdaReadWriteAccess-[S3-BUCKET]
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3ReadWriteAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectAcl",
        "s3:PutObject",
        "s3:PutObjectAcl"
      ],
      "Resource": "arn:aws:s3:::[S3-BUCKET]/*"
    }
  ]
}
```
---

### 14. Cloudwatch Logs
Based on your previous setup, here's how to add CloudWatch monitoring to your new API Gateway:

1. Configure API Gateway Settings for CloudWatch
- Go to API Gateway console
- Select your new API (hash-store)
- Click "Settings" in the left navigation
- Under "CloudWatch log role ARN", paste your existing role ARN:
  APIGatewayCloudWatchLogsRole
- Click "Save"

2. Enable CloudWatch Logging for API Stage
- Still in API Gateway console
- Select "Stages" in the left navigation
- Select your API stage (likely "api")
- Go to "Logs/Tracing" tab
- Click "Edit"
- Enable these settings:
  - [x] CloudWatch logs: Errors and info logs
  - [x] Data tracing
  - [x] Detailed Metrics
  - [ ] Leave Custom access logging unchecked
  - [ ] Leave X-Ray tracing unchecked
- Click "Save"

3. Create CloudWatch Alarm for 5XXError
- Go to CloudWatch console
- Click "Alarms" in left navigation
- Click "Create alarm"
- Click "Select metric"
- Navigate to:
  - API Gateway
  - API Metrics
  - Find your API (hash-store)
  - Select "5XXError"
- Configure settings:
  - Threshold: Greater than or equal to 1
  - Period: 5 minutes
- Configure actions:
  - Use your existing SNS topic "security-alarms"
- Name the alarm: "hash-store-5XXError-Alarm"
- Click "Create alarm"

4. Verify Setup
- Go to Lambda console
- Select your hash-store function
- Go to "Monitor" tab
- Check "CloudWatch Logs" section
- Verify you see log entries (might need to make a test request first)


## EARLY TRY DON'T USE THIS - JUST KEEPING FOR REFERENCE - Task Detailed Steps

### 1. [ ] Set up and customize Chalice project structure
#### Task Requirements
- Initialize a new Chalice project.
- Replace `app.py` and `chalicelib` contents with templates from a similar secured Lambda function.
- Ensure the `requirements.txt` is updated and ready.

#### Task Changes
File Change: `.chalice/config.json`  
File Change: `app.py`  
File Change: `chalicelib/*.py`

#### Task Steps
[ ] Step 1: Create a new Chalice project directory and run `chalice new-project <function_name>`  
   - Current behavior: No project directory.  
   - After change: A new Chalice project folder with basic scaffold.

[ ] Step 2: Copy the contents from an existing similar function’s `app.py` and `chalicelib` into the new project.  
   - Current behavior: Minimal stub `app.py` from Chalice.  
   - After change: `app.py` and `chalicelib` reflect updated security, API key requirements, etc.

[ ] Step 3: Adjust `requirements.txt` for needed dependencies (if any).

#### Implementation
{Add notes, code references, or testing instructions here once done.}

---

### 2. [ ] Configure `config.json`
#### Task Requirements
- Update `.chalice/config.json` with `environment_variables` from `.env`.
- Set `manage_iam_role` to `false` and add `iam_role_arn`.
- Enable `api_gateway_stage` and confirm `autogen_policy` is false.

#### Task Changes
File Change: `.chalice/config.json`

#### Task Steps
[ ] Step 1: Open `.chalice/config.json` and specify the IAM role ARN of the Lambda’s execution role.  
[ ] Step 2: Set `api_key_required` on the routes in `app.py` and confirm `autogen_policy: false`.  
[ ] Step 3: Ensure environment variables (like `USERS_HMAC_SECRET_KEY`, `API_KEY_1`) are defined in `config.json` and replaced by `chalicelib_mirror_deploy.sh` from `.env`.

#### Implementation
Example snippet for `config.json`:
```json
{
  "version": "2.0",
  "app_name": "new-lambda",
  "stages": {
    "dev": {
      "api_gateway_stage": "api",
      "autogen_policy": false,
      "manage_iam_role": false,
      "iam_role_arn": "arn:aws:iam::123456789012:role/YourLambdaExecutionRole",
      "environment_variables": {
        "USERS_HMAC_SECRET_KEY": "REPLACE_WITH_ENV",
        "API_KEY_1": "REPLACE_WITH_ENV",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```
### 3. [ ] Update IAM Roles and Policies
#### Task Requirements
- Attach `AWSLambdaBasicExecutionRole` and any S3 or other resource access policies to the Lambda’s execution role.
- Create inline policies if needed.

#### Task Changes
No file changes locally, all done in AWS Console IAM.

#### Task Steps
[ ] Step 1: In IAM Console, go to the role assigned to this Lambda and click "Add Permissions" → "Attach policies", add `AWSLambdaBasicExecutionRole`.  
[ ] Step 2: For additional resources (e.g., S3 write), create inline policies by clicking "Add permissions" → "Create inline policy" and pasting JSON from known working policies.

#### Implementation
Use an inline policy like the following by clicking "Create inline policy" in the IAM Console:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3WriteAccess",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::your-bucket-name/*"
    }
  ]
}
```

---

### 4. [ ] Add Resource-Based Policy to Lambda for API Gateway
#### Task Requirements
- Allow `apigateway.amazonaws.com` to invoke the Lambda function.

#### Task Steps
[ ] Step 1: In the Lambda Console, go to Configuration → Permissions → "Add permissions" → Add a resource-based policy statement:
```json
{
  "Sid": "ApiGatewayInvoke",
  "Effect": "Allow",
  "Principal": {
    "Service": "apigateway.amazonaws.com"
  },
  "Action": "lambda:InvokeFunction",
  "Resource": "arn:aws:lambda:REGION:ACCOUNT_ID:function:YOUR_FUNCTION_NAME"
}
```

#### Implementation
Check that the function’s Permissions tab now shows the new resource-based policy.

---

### 5. [ ] Configure API Gateway for API Keys
#### Task Requirements
- Enable "API Key Required" for the relevant routes in API Gateway.
- Associate the function with a usage plan and create an API key.

#### Task Steps
[ ] Step 1: In API Gateway Console, select the API, go to the method settings, and enable "API Key Required".  
[ ] Step 2: Create or select a usage plan and associate the API stages.  
[ ] Step 3: Create a new API key and associate it with the usage plan.  
[ ] Step 4: Update frontend or clients to include `x-api-key` header.

#### Implementation
Test with a curl command:
```bash
curl -X POST https://<api_id>.execute-api.<region>.amazonaws.com/api/endpoint \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{"input_text": "test@example.com"}'
```

---

### 6. [ ] Integrate AWS WAF
#### Task Requirements
- Link WAF Web ACL to the API Gateway stage.
- Set a rate-based rule for IP throttling.

#### Task Steps
[ ] Step 1: In AWS WAF Console, create or edit a Web ACL and add a rate-based rule (e.g., block after 50 requests per 5 minutes per IP).  
[ ] Step 2: Associate the Web ACL with the API Gateway stage hosting the new function.

#### Implementation
Test by sending multiple rapid requests and checking if WAF blocks them. Verify CloudWatch metrics for WAF.

---

### 7. [ ] Verify CloudWatch Alarms and AWS Budget Alerts
#### Task Requirements
- Ensure CloudWatch alarms (5XX errors, latency) are in place.
- Confirm AWS Budget alerts are configured.

#### Task Steps
[ ] Step 1: In CloudWatch, ensure alarms on `5XXError` metrics for the API Gateway are set up.  
[ ] Step 2: Check AWS Budgets in the Billing Console to confirm existing alerts.  
[ ] Step 3: Trigger a test error and confirm that alarms and notifications are received.

#### Implementation
No code changes needed. Just verification steps.

---

### 8. [ ] Implement HMAC Hashing of PII
#### Task Requirements
- Use `generate_hmac_hash` to hash user name/IP before storing to S3.
- Ensure `.env` and `config.json` handle `USERS_HMAC_SECRET_KEY`.

#### Task Steps
[ ] Step 1: In `app.py` or `chalicelib`, call `generate_hmac_hash` before saving user data.  
[ ] Step 2: Verify `.gitignore` excludes PII files.  
[ ] Step 3: Test with sample PII input to ensure hashed data is stored.

#### Implementation
Example snippet:
```python
hashed_ip = generate_hmac_hash(user_ip, os.environ["USERS_HMAC_SECRET_KEY"])
# Store hashed_ip in S3
```

---

### 9. [ ] Test End-to-End Deployment
#### Task Requirements
- Deploy with `chalice deploy`.
- Test the endpoint with correct API key.
- Validate WAF blocks, CloudWatch logs, and alarm triggers.

#### Task Steps
[ ] Step 1: Run `chalice deploy` to push changes.  
[ ] Step 2: Test endpoint with `curl` or Postman.  
[ ] Step 3: Check CloudWatch Logs, WAF metrics, and alarms for expected behavior.

#### Implementation
Deploy:
```bash
chalice deploy
```
Then test and review logs.


// ===== END OF FILE web/aws_chalice/chalice_new_lambda_checklist.md =====


