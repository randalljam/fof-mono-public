# AWS Architecture for Chalice Dev/Prod Environments

## Recommended Architecture

For your Chalice applications, use a single API Gateway with separate stages (dev/prod) - this is the simplest and most cost-effective approach that still provides proper separation.

```
App: hmac-hash
  └── API Gateway: hmac-hash
      ├── Stage: dev → Lambda: hmac-hash-dev
      └── Stage: prod → Lambda: hmac-hash-prod
```

## Implementation Steps

### 1. Configure Chalice for Multiple Stages

Create/update `.chalice/config.json`:

```json
{
  "version": "2.0",
  "app_name": "hmac-hash",
  "stages": {
    "dev": {
      "api_gateway_stage": "dev",
      "environment_variables": {
        "STAGE": "dev"
      }
    },
    "prod": {
      "api_gateway_stage": "prod",
      "environment_variables": {
        "STAGE": "prod"
      },
      "iam_role_arn": "arn:aws:iam::ACCOUNT_ID:role/hmac-hash-prod-role"
    }
  }
}
```

### 2. Separate IAM Roles (Recommended)

Create distinct IAM roles for dev and prod with appropriate permissions. For prod, reference the exact role ARN in your config.

### 3. Deployment Commands

Deploy to dev:
```
chalice deploy --stage dev
```

Deploy to prod:
```
chalice deploy --stage prod
```

### 4. Managing API Gateway Validation Models

Store validation schemas in a version-controlled directory:

```
hmac-hash/
├── .chalice/
├── app.py
└── schemas/
    ├── dev/
    │   └── request_schema.json
    └── prod/
    │   └── request_schema.json
```

In your app.py:

```python
import os
import json

stage = os.environ.get('STAGE', 'dev')
schema_path = f'schemas/{stage}/request_schema.json'

with open(schema_path) as f:
    request_schema = json.load(f)

@app.route('/endpoint', methods=['POST'])
def my_endpoint():
    # Your endpoint code
```

### 5. Automated Promotion from Dev to Prod

Create a Python script using boto3:

```python
import boto3
import json

def promote_dev_to_prod():
    """
    Promotes Lambda function from dev to prod.
    """
    lambda_client = boto3.client('lambda')
    
    # Get the dev function configuration
    dev_function = lambda_client.get_function(
        FunctionName='hmac-hash-dev'
    )
    
    # Update the prod function with dev code
    lambda_client.update_function_code(
        FunctionName='hmac-hash-prod',
        S3Bucket=dev_function['Code']['Location'].split('/')[-2],
        S3Key=dev_function['Code']['Location'].split('/')[-1]
    )
    
    print("Successfully promoted dev to prod")

if __name__ == "__main__":
    promote_dev_to_prod()
```

## Common Pitfalls to Avoid

1. **Environment Variables**: Don't hardcode environment-specific values
2. **IAM Permissions**: Ensure prod has stricter permissions than dev
3. **Shared Resources**: Watch for resources that might be affected by both environments
4. **Testing**: Always validate the API in dev before promoting to prod
5. **Rollback Plan**: Have a strategy to quickly revert prod changes if needed

This architecture balances simplicity with proper separation of concerns, making it suitable for your team of junior developers while minimizing production risks.
