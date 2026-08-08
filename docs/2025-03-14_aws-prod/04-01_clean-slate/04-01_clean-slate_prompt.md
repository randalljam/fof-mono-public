# PROMPT clean slate
NEED: Help with and recommended AWS architecture and setup for migration to separate dev and production environments for Chalice web apps.

I'm working with AWS Lambda and API Gateway using the Chalice framework (v1.31.2) and need to properly implement separate development and production environments.

My use case:
- I'm not a professional developer with limited experience in web infrastructure and AWS
- My applications primarily handle AI-related API calls to external services
- Each Lambda function typically has a single API route/endpoint
- I need a simplified dev/prod setup that other junior developers can easily understand and use
- I want to minimize production downtime risks while avoiding an overly complex architecture

My current setup for example app/function:
- App named 'hmac-hash'
- Initial Chalice deployment created:
  * Lambda function: hmac-hash-dev
  * API Gateway: 'hmac-hash' with single stage 'api'

My AWS services:
- Lambda functions with Python 3.11 runtime
- API Gateway with dev/prod stages
- CloudWatch for logs and metrics
- IAM roles for Lambda execution
- Web Application Firewall (WAF) with ACLs

I want to create a proper development/production setup where:
1. Deployments to dev don't affect production
2. Once my dev changes are thoroughly tested, I can 'push to production' either by:
  a. deploying from local code and configs (making sure no local changes since dev testing)
  b. or probably preferably 'promote dev to prod' by using boto3 python code (preferred) or bash script to obtain the appropriate AWS 'dev' resources and copy/push them to the corresponding 'prod' versions of those resources (some resources such as log groups or roles with different dev vs prod policies may not get updated)

My testing consists of:
1. Local python module function testing (both unittests and manual testing)
2. Automated API validation testing using a custom framework that:
   - Tests both direct Lambda invocation and API Gateway requests
   - Uses three categories of test requests:
     * Clean requests (should pass for both Lambda and API Gateway)
     * Schema invalid requests (should pass for Lambda but fail at API Gateway validation)
     * Function invalid requests (should fail for both Lambda and API Gateway)
   - Generates comprehensive test reports that verify proper integration
3. Front-end testing with the actual web interface using dev endpoints before promoting to production

Questions:
1. What is the standard AWS architectural pattern for separating dev/prod in API Gateway and Lambda for Chalice projects? Should I:
   - Create two separate API Gateways?
   - Use one API Gateway with two stages?
   - Use shared or separate IAM roles?
2. How does Chalice CLI natively support multiple stages (dev/prod)? What commands/config files are involved?
3. For API Gateway validation models (request validation schemas), what's the proper way to manage different schemas for dev vs prod?
4. What is the recommended AWS architecture and setup for my use case?
   - What's the proper deployment workflow from dev to prod? 
   - What specific steps should I follow to implement this properly with Chalice?
5. What common pitfalls should I avoid (especially regarding deployment errors or stage configuration)?

Please explain with specific terminal commands and config file examples where appropriate.