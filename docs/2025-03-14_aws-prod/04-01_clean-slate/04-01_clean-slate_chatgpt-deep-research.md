# ChatGPT Deep Research - Preamble
Great, thank you for the clarification! I’ll put together a recommended AWS architecture and deployment strategy using Chalice for managing separate dev and production environments within the same AWS account.

I'll include:
- Best practices for using separate Lambda functions, API Gateway stages or gateways, and IAM roles
- A simplified Chalice config pattern with stage-specific settings
- A recommended workflow to promote code from dev to prod (using both Chalice CLI and a boto3 script option)
- Tips on handling API Gateway schema validation per stage
- Specific pitfalls to watch out for

I'll get back to you shortly with a full breakdown and example configurations.

# # ChatGPT Deep Research - Response: Managing Dev and Prod Environments with AWS Chalice

When deploying AWS Chalice applications, you can cleanly separate **development (dev)** and **production (prod)** environments for safety and clarity. This guide explains a recommended architecture and best practices for AWS Chalice (v1.31.2) projects, including how to configure Chalice stages, IAM roles, API Gateway setups, deployment workflows, and common pitfalls to avoid.

## Architecture for Isolated Environments

**Goal:** Ensure your dev deployments never affect production. Given that cost is not a major concern, we recommend **duplicating resources for dev and prod** rather than trying to share them. This yields a simple mental model for junior developers.

- **Separate API Gateways per Stage:** By default, Chalice stages create completely separate AWS resources for each environment ([Upgrade Notes — AWS Chalice](https://aws.github.io/chalice/upgrading.html#:~:text=two%20separate%20sets%20of%20AWS,resources%2C%20one%20set%20per%20stage)). For example, deploying a Chalice app to a new stage (e.g. `prod`) will provision a new API Gateway REST API, a new Lambda function, and a new IAM role (unless configured otherwise) ([Chalice Stages — AWS Chalice](https://aws.github.io/chalice/topics/stages.html#:~:text=By%20creating%20a%20new%20chalice,will%20be%20created%20for%20you)). This means your dev and prod APIs have distinct endpoints (URLs) and backing Lambda functions. Dev changes won’t automatically appear in prod, providing strong isolation.

- **Alternative (Not Recommended Here):** API Gateway *does* support multiple stages on a single API (e.g. a single API Gateway with a “dev” and “prod” stage path) ([amazon web services - What is the recommended way to separate environments within AWS API Gateway? - Stack Overflow](https://stackoverflow.com/questions/62271556/what-is-the-recommended-way-to-separate-environments-within-aws-api-gateway#:~:text=0)). In such a design, you could deploy different versions of your API under one gateway. However, **Chalice’s native behavior is to use separate APIs per stage**, and adopting the single API/multiple stage model with Chalice would require custom adjustments (like using Lambda aliases and stage variables). This adds complexity and risk. For clarity and low friction, we suggest sticking with Chalice’s stage mechanism (separate APIs).

**Benefits of Separate APIs per Stage:**

- **True Isolation:** Each stage has its own API endpoint, Lambda, logs, and configuration. You can test new features in dev without any chance of breaking prod traffic ([Chalice Stages — AWS Chalice](https://aws.github.io/chalice/topics/stages.html#:~:text=We%20now%20have%20two%20completely,separate%20rest%20APIs)) ([Chalice Stages — AWS Chalice](https://aws.github.io/chalice/topics/stages.html#:~:text=%24%20chalice%20url%20,2.amazonaws.com%2Fapi)). For example, after deploying both stages, `chalice url --stage dev` might return `https://abc123.execute-api.us-west-2.amazonaws.com/api/` and `chalice url --stage prod` a different URL like `https://xyz789.execute-api.us-west-2.amazonaws.com/api/` – they are independent APIs.

- **Independent Configuration:** You can attach different AWS WAF web ACLs, usage plans, or domain names to each API. For instance, you might use a less restrictive WAF for dev (or none at all) and a stricter WAF for prod. Since 2018, API Gateway allows direct WAF integration per API stage ([Amazon API Gateway adds support for AWS WAF | AWS Compute Blog](https://aws.amazon.com/blogs/compute/amazon-api-gateway-adds-support-for-aws-waf/#:~:text=Today%2C%20I%E2%80%99m%20excited%20to%20tell,distribution%20to%20add%20that%20capability)), so you can protect each environment’s endpoint separately.

- **Separate IAM and Resources:** Because each Lambda and API are distinct, you can assign different IAM roles, environment variables, and resource access per environment (e.g., dev Lambda can write to a *dev* S3 bucket, while prod Lambda writes to a *prod* bucket).

**Drawback:** The only downside is slight resource duplication (two APIs, two Lambdas, etc.), but given cost is not a concern, this trade-off is acceptable for simplicity and safety.

## Chalice Stages and Configuration

AWS Chalice has first-class support for multiple stages (like “dev” and “prod”). When you create a new stage with Chalice, it sets up a separate stack of resources automatically ([Chalice Stages — AWS Chalice](https://aws.github.io/chalice/topics/stages.html#:~:text=By%20creating%20a%20new%20chalice,will%20be%20created%20for%20you)). 

**Creating and Using Stages:**

- By default, Chalice uses a stage named `"dev"` if you don’t specify any stage. 
- To deploy a new stage, use the `--stage` flag in the Chalice CLI. For example: 

```bash
# Deploy to the dev stage (default if --stage omitted)
chalice deploy --stage dev

# Deploy to the prod stage
chalice deploy --stage prod
```

The first time you deploy to a new stage, Chalice will create the necessary resources for that stage ([Chalice Stages — AWS Chalice](https://aws.github.io/chalice/topics/stages.html#:~:text=To%20create%20a%20new%20chalice,will%20be%20created%20for%20you)). Subsequent deployments will update the existing stage’s resources.

Chalice commands that accept the `--stage` parameter include `deploy`, `invoke`, `url`, `logs`, `package`, etc. ([Upgrade Notes — AWS Chalice](https://aws.github.io/chalice/upgrading.html#:~:text=%2A%20A%20new%20%60,will%20be%20created%20for%20you)). Always specify `--stage` when working with multiple environments to avoid confusion. For example, use `chalice logs --stage dev` to view CloudWatch logs for the dev Lambda.

**Chalice Config for Multiple Stages:**

Chalice uses a `.chalice/config.json` file to define your app’s configuration. You can provide **stage-specific settings** under the `"stages"` key, as well as global defaults. Below is an example `config.json` illustrating a dev/prod setup:

```json
{
  "version": "2.0",
  "app_name": "myapp",
  "api_gateway_stage": "api",            // default API Gateway URL path prefix
  "stages": {
    "dev": {
      "api_gateway_stage": "api",        // Use "api" as the URL base path (defaults to this)
      "autogen_policy": true,           // Let Chalice autogenerate IAM policy for dev
      "environment_variables": {
        "MODEL_ENDPOINT": "https://api-dev.example.com/ai", 
        "S3_BUCKET": "myapp-dev-bucket"
      }
    },
    "prod": {
      "api_gateway_stage": "prod",       // Use "prod" as the URL base path for clarity
      "manage_iam_role": false,         // We will manually manage the IAM role for prod
      "iam_role_arn": "arn:aws:iam::123456789012:role/myapp-prod-role",
      "environment_variables": {
        "MODEL_ENDPOINT": "https://api.example.com/ai",
        "S3_BUCKET": "myapp-prod-bucket"
      }
    }
  }
}
```

Key points in this configuration:

- **Different IAM Roles:** In this example, the prod stage is configured to use an existing IAM role (`myapp-prod-role`) that you’ve created with stricter policies. We set `"manage_iam_role": false` for prod and supply the ARN via `"iam_role_arn"`. This tells Chalice **not** to create or alter the role in prod, but to simply attach the Lambda to the given role ([Configuration File — AWS Chalice](https://aws.github.io/chalice/topics/configfile.html#:~:text=%7D%2C%20,role%22)). For the dev stage, we allow Chalice to autogenerate an IAM policy (`"autogen_policy": true`), which means Chalice will create a role (named after your app and stage, e.g. `myapp-dev`) and infer permissions from your code. This way, devs can move quickly without writing IAM policies by hand, while prod uses a tightly controlled role.

- **Stage-specific API Gateway Stage Name:** We set `"api_gateway_stage"` differently. By default, Chalice uses `"api"` as the stage name in the URL path for all stages (or whatever you put as top-level `"api_gateway_stage"`). In the config above, dev inherits the top-level `"api_gateway_stage": "api"`, so dev endpoints will look like `.../api/...`. For prod, we override it to `"prod"`, so the prod endpoint URL will contain `/prod/` as the path prefix. This is optional – it mainly affects the URL structure. Some teams use the same base path for all stages, others include the stage name in the URL for clarity ([Configuration File — AWS Chalice](https://aws.github.io/chalice/topics/configfile.html#:~:text=In%20this%20config%20file%2C%20both,...%7D%7D%60%20mapping)). Choose what makes sense (if you use custom domains, you might not need a stage prefix at all).

- **Environment Variables per Stage:** We include an `"environment_variables"` section for each stage to point to the appropriate resources (e.g., a dev vs prod model endpoint URL, dev vs prod S3 bucket). Chalice will inject these into the Lambda’s environment. In our example, `app.py` can read `os.environ['MODEL_ENDPOINT']` to know which external AI service URL to call. Using stage-specific env vars ensures your code talks to the correct backend in each environment.

- **Other Configurations:** You can also override memory, timeout, or VPC settings per stage or per function. For example, if prod needs more memory, you could set `"lambda_memory_size": 1024` under the prod stage. Chalice’s config supports nested `"lambda_functions"` config if you have multiple Lambdas in one app (for non-API functions) ([Configuration File — AWS Chalice](https://aws.github.io/chalice/topics/configfile.html#:~:text=,policy.json)). In our single-endpoint scenario, you might not need that.

## Deploying to Dev and Prod

With the config in place, deploying is straightforward. Developers can deploy to the **dev environment** for testing, and once tested, deploy the same code to **prod**:

- **Deploy to Dev:** Run `chalice deploy --stage dev`. Chalice will package your app, create/update the dev Lambda, dev API Gateway, and assign the dev IAM role. It will output the API endpoint URL (and you can also retrieve it with `chalice url --stage dev`). After deployment, test your API (e.g., using curl or Postman) to ensure it works as expected.

- **Deploy to Prod:** When ready to go live, run `chalice deploy --stage prod`. Chalice will package the app (using the same application code, but now applying any prod-specific config like environment variables and role) and update the prod Lambda and API Gateway. The prod API gets its own URL. Make sure to note the prod URL or set up a custom domain if needed (Chalice can manage custom domain mappings via config as well).

Chalice keeps track of deployed resources in `.chalice/deployed/<stage>.json`. These files contain the resource IDs (like the Lambda ARN and API Gateway ID) for each stage. For example, `.chalice/deployed/dev.json` and `.chalice/deployed/prod.json` will list the function names (e.g., `myapp-dev` vs `myapp-prod`) and API Gateway IDs for each environment ([Chalice Stages — AWS Chalice](https://aws.github.io/chalice/topics/stages.html#:~:text=%24%20chalice%20url%20,2.amazonaws.com%2Fapi)). This helps Chalice know what to update on subsequent deploys.

**Tip:** It’s a good practice to test your prod deployment in a staging phase before exposing it to real users. For example, you might deploy to prod but only internal users hit it initially, or use API Gateway’s [Canary deployments](https://docs.aws.amazon.com/apigateway/latest/developerguide/canary-release.html) to route a small percentage of traffic to the new version. Chalice doesn’t directly manage canaries, but API Gateway console or CloudFormation can.

## Promotion Workflow: From Dev to Prod

In many workflows, you deploy to dev, test, then “promote” the exact same artifact to prod. With Chalice, the simplest promotion is just redeploying the code to prod via the CLI. However, you can also automate promotion using AWS tools (boto3 or AWS CLI) to reduce manual steps and ensure consistency.

One approach to promotion is to reuse the deployment package from dev for prod. Here’s a **bash script** example using AWS CLI and `boto3` logic to copy the Lambda code from a dev deployment to prod:

```bash
#!/bin/bash
set -e

# Names of the Lambda functions for each stage (from Chalice deployed JSON or naming convention)
DEV_FUNCTION_NAME="myapp-dev"
PROD_FUNCTION_NAME="myapp-prod"
REGION="us-west-2"  # adjust region as needed

echo "Fetching deployment package of $DEV_FUNCTION_NAME..."
# Get a presigned URL for the code of the dev Lambda
DEV_CODE_URL=$(aws lambda get-function \
    --function-name "$DEV_FUNCTION_NAME" \
    --region $REGION \
    --query 'Code.Location' --output text)

# Download the deployment package zip
curl -s "$DEV_CODE_URL" -o /tmp/dev_package.zip
echo "Downloaded dev package to /tmp/dev_package.zip (size: $(du -h /tmp/dev_package.zip | cut -f1))"

# Update the prod Lambda code with this package
echo "Updating $PROD_FUNCTION_NAME code to match dev..."
aws lambda update-function-code \
    --function-name "$PROD_FUNCTION_NAME" \
    --region $REGION \
    --zip-file fileb:///tmp/dev_package.zip

echo "Deployment package promoted from dev to prod successfully."
```

What this script does:

1. Uses `aws lambda get-function` to retrieve a temporary URL to the *dev* Lambda’s code package (AWS provides a presigned URL to the `.zip` file).  
2. Downloads that package locally (you could also stream it and pipe to the next command).  
3. Calls `aws lambda update-function-code` to update the *prod* Lambda with the exact same code zip. 

After running this, the prod Lambda’s code is identical to dev’s code (assuming dev was the tested good version). The API Gateway prod stage will now start invoking the updated prod Lambda code. Since we didn’t run `chalice deploy` for prod in this scenario, **Chalice’s internal tracking won’t know about this update**. It’s a direct AWS-level promotion. This is fine as long as you’re careful; you might later do a `chalice deploy --stage prod` to sync any infrastructure changes. Alternatively, you could integrate promotion in a CI/CD pipeline:

- Package the Chalice app (e.g., `chalice package --stage dev`) to generate a CloudFormation template and Lambda zip.
- Deploy the dev stack, test it.
- Use the same template/zip (with perhaps minor adjustments like different stack name or parameter for role) to deploy to prod, ensuring the code is identical.

For most straightforward cases, running `chalice deploy` separately for each stage is acceptable. But the above script demonstrates how to promote code without rebuilding or risking drift. If you use this method, remember that any configuration differences (environment variables, etc.) are already set on the prod Lambda from earlier; you are only updating the code. **Never promote dev code to prod if it depends on dev-only resources** (e.g., make sure your code reads the correct `S3_BUCKET` environment variable so it writes to the prod bucket when running in prod).

## API Gateway Validation Models per Environment

For robust APIs, you might use **request/response validation** in API Gateway. This means defining JSON Schema models and enabling request validation so that API Gateway rejects bad inputs (or ensures your Lambda’s outputs conform to a model). Managing these in a Chalice multi-stage setup requires some extra steps, as Chalice does not natively define API Gateway models or request validators out-of-the-box ([APIGateway configuration · Issue #564 · aws/chalice · GitHub](https://github.com/aws/chalice/issues/564#:~:text=kyleknap%20%20%20commented%20,67)) ([APIGateway configuration · Issue #564 · aws/chalice · GitHub](https://github.com/aws/chalice/issues/564#:~:text=Add%20schema%20validation%20to%20chalice,core%20concepts)).

**Key points:**

- **Chalice and Swagger/OpenAPI:** Chalice can generate an OpenAPI/Swagger definition for your API when you run `chalice package`. However, by default it won’t include model schemas or validators. You can manually edit the CloudFormation template or the Swagger definitions to add models. Each stage’s API (being separate) would need its own models defined.

- **Stage-Specific Models:** Because dev and prod are separate API Gateways, you can have different models or validation rules if desired. For example, in dev you might relax certain validations to allow experimentation, while prod has stricter schema requirements. In practice, though, you’ll likely want the same models in both (to ensure you’re testing the same expectations in dev).

- **How to Set Up Validation:** One approach is to use AWS CLI or boto3 after Chalice deploys your API:
  1. Define your JSON Schema for the request/response in a file (or in code).
  2. Use `aws apigateway create-model` (for REST APIs) to create a Model in the API Gateway (you'll need the API ID which you can get from `.chalice/deployed/stage.json` or `chalice describe` if available).
  3. Use `aws apigateway update-method` to attach a `RequestValidator` and specify the model for the method’s request body (and similarly `update-integration-response` for response models if needed). This can be done for each resource/method. You might also create a `RequestValidator` via `create-request-validator` (e.g., one that validates body only or params as well).

- **Automation:** This process is a bit involved to do manually for every deploy. You can write a script in Python (boto3’s API Gateway client) to loop through your API’s resources and set up the models/validators. Alternatively, maintain an OpenAPI spec and apply it after deployment. As of now, Chalice doesn’t have a built-in decorator or config for request schemas (there is a feature request open for this ([APIGateway configuration · Issue #564 · aws/chalice · GitHub](https://github.com/aws/chalice/issues/564#:~:text=kyleknap%20%20%20commented%20,67)) ([APIGateway configuration · Issue #564 · aws/chalice · GitHub](https://github.com/aws/chalice/issues/564#:~:text=Add%20schema%20validation%20to%20chalice,core%20concepts))).

- **Keep Models in Sync:** A common pitfall is forgetting to update your API Gateway models when your API changes. If you add a new endpoint or change input format, update the JSON Schema accordingly and reapply it to dev and prod. You might integrate this in your deployment pipeline so that it’s not overlooked.

**Stage-specific differences:** If you truly need different schemas in dev vs prod, you can manage two sets of models (perhaps with different names or versions). But strive to keep them consistent unless there’s a compelling reason—ideally, dev is a mirror of prod for testing, not a divergent API.

## IAM Roles and Policies Best Practices

Using **separate IAM roles** for dev and prod Lambdas is highly recommended. This limits the blast radius if dev credentials are compromised or if a dev function misbehaves.

- **Least Privilege:** For production, craft a minimal IAM policy. If your Chalice app only needs to call a specific AWS AI service and access one S3 bucket, the prod role’s policy should allow exactly those actions (and CloudWatch logging). In dev, you might allow a broader range or point to dev resources. Chalice’s policy generation can help by analyzing your code for AWS SDK calls. You can let Chalice create an initial policy for dev, then use it as a starting point for a stricter prod policy.

- **Chalice Config for IAM:** As shown earlier, you can supply an `iam_policy_file` per stage or an `iam_role_arn` ([Configuration File — AWS Chalice](https://aws.github.io/chalice/topics/configfile.html#:~:text=,policy.json)) ([Configuration File — AWS Chalice](https://aws.github.io/chalice/topics/configfile.html#:~:text=%7D%2C%20,role%22)). For example, you might have `.chalice/policy-dev.json` and `.chalice/policy-prod.json` files with tailored policies. In `config.json`:
  ```json
  "stages": {
    "dev": { "iam_policy_file": "policy-dev.json" },
    "prod": { "iam_policy_file": "policy-prod.json", "manage_iam_role": true }
  }
  ```
  If `manage_iam_role` is true (the default), Chalice will create a new role for that stage if one doesn’t exist and attach the policy. You could also use `iam_role_arn` (with `manage_iam_role: false`) to attach to a preexisting role you created via AWS console/IaC.

- **Separate vs Shared Roles:** Do **not** reuse the same IAM role for both dev and prod Lambdas. That would violate isolation (dev could get permissions meant for prod). Chalice by default names roles with the app and stage (e.g., `myapp-dev-role` and `myapp-prod-role`), so conflicts are unlikely unless you explicitly override to the same ARN.

- **Rotation and Auditing:** Since these are in the same AWS account, ensure that CloudTrail is logging actions in both environments and that you monitor the usage of roles. This is more of a security best practice but worth noting.

## API Gateway Configuration Best Practices

- **Deployment Stages vs Chalice Stages:** Be aware of terminology. Chalice *stage* = completely separate API. API Gateway *stage* = a deployment snapshot of a single API. In our recommended setup, each Chalice stage uses a single API Gateway stage (often named "api" or "prod" as set in config). This is straightforward. If you do use additional API Gateway stages on the same API (not covered in depth here), ensure you understand how to deploy new stages via Chalice’s `--api-gateway-stage` option ([Upgrade Notes — AWS Chalice](https://aws.github.io/chalice/upgrading.html#:~:text=The%20optional%20deprecated%20positional%20parameter,command)), which is rarely needed in the separate-resources model.

- **Custom Domains:** If you use custom domain names, you can set up one domain with multiple base path mappings (e.g., `api.example.com/dev` and `api.example.com/prod` mapping to your two API Gateways). Alternatively, use separate subdomains (e.g., `dev-api.example.com` vs `api.example.com`). Chalice config supports custom domains per stage as well ([Configuration File — AWS Chalice](https://aws.github.io/chalice/topics/configfile.html#:~:text=Here%E2%80%99s%20an%20example%20for%20configuring,dev%20stage%20for%20REST%20API)) ([Configuration File — AWS Chalice](https://aws.github.io/chalice/topics/configfile.html#:~:text=,bar)). This can simplify client access (developers hitting dev vs users hitting prod).

- **Monitoring:** CloudWatch Logs and metrics for each Lambda will be separate (by function name). Set up CloudWatch Alarms for prod specifically (e.g., on errors or latency). For dev, you might choose lower thresholds or none. Also, consider X-Ray tracing (`"xray": true` in Chalice config) if you need deeper debugging; it can be enabled per stage if needed.

- **WAF and Security:** Attach AWS WAF to your API Gateway stages to protect against common web exploits. You can have one WebACL for prod (stricter rules) and another for dev (perhaps allowing testers from your IP, etc.). Since the APIs are separate, they can have different WAF associations. Also, ensure that if your APIs are public, you’re using authentication/authorization (Chalice supports API Gateway authorizers, Cognito, etc., which you can configure in your app code). For internal dev environments, you might restrict access by IP or AWS credentials.

## Common Pitfalls and How to Avoid Them

Finally, here are some common mistakes when managing Chalice deployments and how to avoid them:

- **Forgetting the `--stage` Flag:** It’s easy to run `chalice deploy` and assume you updated prod, when in fact you updated dev (or vice versa). Always double-check the stage or make it explicit by always using `--stage`. Similarly, use stage flags for `chalice logs` to avoid looking at the wrong logs.

- **Mixing Up Configurations:** If you hard-code resource names or URLs in your code, you might accidentally point prod code at dev resources. Always utilize stage-specific config for things like S3 bucket names, ARNs, or endpoint URLs. This way, your code can remain identical between stages, and only config changes. For example, using `app.current_request.context['stage']` (if needed) or environment variables as shown earlier can help your function know its environment.

- **Not Updating Both Environments:** After adding a new API route or functionality, you deploy to dev and test, but then forget to deploy to prod, resulting in prod missing that feature. Make it a practice to deploy to prod (or at least a staging environment) as part of your release process. If you are using CI/CD, have separate jobs or pipelines for dev and prod triggered appropriately.

- **IAM Over-Permissions:** While convenience in dev is nice (e.g., wildcard `*` permissions), ensure prod’s IAM role is not overly broad. A mistake here could mean an exploited prod function can access more than it should. Test your IAM policies by reviewing CloudTrail or attempting least-privilege simulations. Chalice’s autogen policy is helpful, but always review the generated policy (`.chalice/policy-dev.json`) to understand what it grants.

- **Chalice Policy Autogen Gaps:** Chalice infers needed AWS permissions by static analysis of your code. Sometimes it might miss dynamically constructed resource access. For example, if your code uses `boto3.client('s3')` and accesses a bucket whose name is computed at runtime, Chalice might not catch that. In such cases, your function could fail in prod due to lack of permission. **Pitfall solution:** Provide an explicit `iam_policy_file` with the needed actions or manually attach the permission after deployment. Always test your Lambda’s functionality in each stage (monitor for AccessDenied errors in CloudWatch Logs).

- **Using Same Names**: If you manually create resources (like DynamoDB tables, S3 buckets) for dev and prod, naming them too similarly can cause confusion or even code mistakes (e.g., writing to the wrong table). A convention is to suffix or prefix resource names with the stage (as we did with `myapp-dev-bucket`). This visual cue helps prevent cross-contamination.

- **Manual Tweaks in Console:** Avoid making manual changes to the API Gateway or Lambda in one stage but not applying them in your IaC/Chalice config. For example, if you enable request validation in prod via the console but don’t automate it, a future `chalice deploy` might overwrite or you might forget to do it for dev. Aim to script or config **everything** (in Chalice or supplementary scripts), so dev and prod can be recreated from source control.

- **Not Cleaning Up:** Over time, you might accumulate old dev deployments or stages. Chalice lets you remove a stage’s resources with `chalice delete --stage dev` if they are no longer needed. Keeping only active environments avoids confusion. **Warning:** Be careful with `chalice delete` in prod – it will delete the live resources! Use it only when you intend to tear down that environment entirely.

By adhering to these practices – **clear separation of resources, careful configuration management, and automation of repetitive tasks** – even junior developers can confidently deploy and manage web apps using AWS Chalice in a multi-environment setup. The result will be a robust dev/prod workflow where development iterations remain isolated from production stability, until you choose to promote them.

## References

- AWS Chalice Documentation – *Chalice Stages and Configuration*: Chalice creates separate resources per stage (dev, prod) ([Upgrade Notes — AWS Chalice](https://aws.github.io/chalice/upgrading.html#:~:text=two%20separate%20sets%20of%20AWS,resources%2C%20one%20set%20per%20stage)) ([Chalice Stages — AWS Chalice](https://aws.github.io/chalice/topics/stages.html#:~:text=By%20creating%20a%20new%20chalice,will%20be%20created%20for%20you)) and provides a config system for stage-specific settings ([Configuration File — AWS Chalice](https://aws.github.io/chalice/topics/configfile.html#:~:text=,policy.json)) ([Configuration File — AWS Chalice](https://aws.github.io/chalice/topics/configfile.html#:~:text=%7D%2C%20,role%22)).  
- AWS Chalice CLI Reference: Use `chalice deploy --stage <name>` to deploy to different stages ([Chalice Stages — AWS Chalice](https://aws.github.io/chalice/topics/stages.html#:~:text=To%20create%20a%20new%20chalice,will%20be%20created%20for%20you)) and other commands with `--stage` flag ([Upgrade Notes — AWS Chalice](https://aws.github.io/chalice/upgrading.html#:~:text=%2A%20A%20new%20%60,will%20be%20created%20for%20you)).  
- AWS Chalice Example Configurations: Illustrations of multi-stage `.chalice/config.json` usage for IAM roles and custom domains ([Configuration File — AWS Chalice](https://aws.github.io/chalice/topics/configfile.html#:~:text=,policy.json)) ([Configuration File — AWS Chalice](https://aws.github.io/chalice/topics/configfile.html#:~:text=%7D%2C%20,role%22)).  
- AWS API Gateway & WAF: API Gateway supports attaching WAF directly to protect APIs (no CloudFront needed) ([Amazon API Gateway adds support for AWS WAF | AWS Compute Blog](https://aws.amazon.com/blogs/compute/amazon-api-gateway-adds-support-for-aws-waf/#:~:text=Today%2C%20I%E2%80%99m%20excited%20to%20tell,distribution%20to%20add%20that%20capability)).  
- AWS Forums/Blogs: Best practices on separating dev/prod environments within one AWS account often favor isolated resources or even separate AWS accounts for strong separation ([Upgrade Notes — AWS Chalice](https://aws.github.io/chalice/upgrading.html#:~:text=Note%2C%20the%20AWS%20resource%20names,prod)) ([amazon web services - What is the recommended way to separate environments within AWS API Gateway? - Stack Overflow](https://stackoverflow.com/questions/62271556/what-is-the-recommended-way-to-separate-environments-within-aws-api-gateway#:~:text=0)).


# Sources 12
Citations
aws.github.io
Upgrade Notes — AWS Chalice
two separate sets of AWS resources, one set per stage:
aws.github.io
Chalice Stages — AWS Chalice
By creating a new chalice stage, a new API Gateway rest API, Lambda function, and potentially (depending on config settings) a new IAM role will be created for you.
Faviconstackoverflow.com
amazon web services - What is the recommended way to separate environments within AWS API Gateway? - Stack Overflow
0
aws.github.io
Chalice Stages — AWS Chalice
We now have two completely separate rest APIs:
aws.github.io
Chalice Stages — AWS Chalice
$ chalice url --stage dev https://mmnkdi.execute-api.us-west-2.amazonaws.com/api/
Faviconaws.amazon.com
Amazon API Gateway adds support for AWS WAF | AWS Compute Blog
Today, I’m excited to tell you about the Amazon API Gateway native integration with AWS WAF. Previously, if you wanted to secure your API in Amazon API Gateway with 125, you had to deploy a Regional API endpoint and use your own Amazon CloudFront distribution. This new feature now enables you to provision any­­ API Gateway endpoint and secure it with AWS WAF without having to configure your own CloudFront distribution to add that capability.
aws.github.io
Chalice Stages — AWS Chalice
To create a new chalice stage, specify the `--stage` argument. If the stage does not exist yet, it will be created for you:
aws.github.io
Upgrade Notes — AWS Chalice
* A new `--stage` argument was added to the `deploy`, `logs`, `url`, `generate-sdk`, and `package` commands. If this value is specified and the stage does not exist, a new chalice stage with that name will be created for you.
aws.github.io
Configuration File — AWS Chalice
}, "prod": { "manage_iam_role": false, "iam_role_arn": "arn:aws:iam::...:role/prod-role" }
aws.github.io
Configuration File — AWS Chalice
In this config file, both the `dev` and `beta` stage will have an API gateway stage name of `api` because they will default to the top level `api_gateway_stage` key. However, the `prod` stage will have an API gateway stage name of `prod` because the `api_gateway_stage` is specified in `{"stages": {"prod": ...}}` mapping.
aws.github.io
Configuration File — AWS Chalice
"app_name": "app", "stages": { "dev": { "autogen_policy": true, "api_gateway_stage": "dev" }, "beta": { "autogen_policy": false, "iam_policy_file": "beta-app-policy.json"
Favicongithub.com
APIGateway configuration · Issue #564 · aws/chalice · GitHub
kyleknap commented 67
Favicongithub.com
APIGateway configuration · Issue #564 · aws/chalice · GitHub
Add schema validation to chalice core concepts
aws.github.io
Upgrade Notes — AWS Chalice
The optional deprecated positional parameter in the `chalice deploy` command for specifying the API Gateway stage has been removed. If you want to specify the API Gateway stage, you can use the `--api-gateway-stage` option in the `chalice deploy` command:
aws.github.io
Configuration File — AWS Chalice
Here’s an example for configuring Custom domain name for dev stage for REST API:
aws.github.io
Configuration File — AWS Chalice
"domain_name": "api.example.com", "security_policy": "TLS 1.2|TLS 1.0", "certificate_arn": "arn:aws:acm:example.com", "url_prefixes": ["foo", "bar"],
aws.github.io
Upgrade Notes — AWS Chalice
Note, the AWS resource names it creates now have the form ``<app-name>-<stage- name>``, e.g. ``myapp-dev``, ``m