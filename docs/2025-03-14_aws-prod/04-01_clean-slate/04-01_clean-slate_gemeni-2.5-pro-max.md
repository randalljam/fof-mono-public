Okay, I understand you're looking for guidance on setting up separate development (`dev`) and production (`prod`) environments for your AWS Chalice applications, based on the detailed requirements and questions outlined in your `04-01_clean-slate_prompt.md` file.

Here's a breakdown addressing your questions, aiming for the simplified setup you prefer:

**1. Standard AWS Architectural Pattern (Chalice Dev/Prod)**

*   **API Gateway:** The standard and recommended approach is to use a **single API Gateway** for your application (e.g., `hmac-hash`) and utilize **API Gateway Stages** within it (e.g., `dev` and `prod`). Chalice is designed to work seamlessly with this pattern. Each stage can point to a different Lambda function deployment and have its own stage-specific configurations (like stage variables, logging levels). Creating separate API Gateways adds unnecessary complexity for your use case.
*   **Lambda Functions:** Chalice will automatically create and manage separate Lambda functions for each stage. When you deploy to the `dev` stage, it creates/updates a function like `hmac-hash-dev`. Deploying to `prod` creates/updates `hmac-hash-prod`. This ensures complete isolation at the compute layer.
*   **IAM Roles:** It is best practice to use **separate IAM roles** for `dev` and `prod` (e.g., `hmac-hash-dev-role`, `hmac-hash-prod-role`). This adheres to the principle of least privilege. Your `prod` environment might need different permissions (e.g., access to production databases or different external API keys) than `dev`. You can define these separate roles and their permissions within Chalice's configuration.

**2. Chalice CLI Support for Multiple Stages**

Chalice has excellent built-in support for stages:

*   **Configuration (`.chalice/config.json`):** This is the central file for managing stage-specific settings. You can define configurations that apply only to `dev` or `prod`.

    ```json
    // .chalice/config.json Example Structure
    {
      "version": "2.0",
      "app_name": "hmac-hash",
      "stages": {
        "dev": {
          "lambda_memory_size": 128,
          "environment_variables": {
            "API_ENDPOINT": "https://api.dev.example.com",
            "LOG_LEVEL": "DEBUG"
          },
          "iam_role_arn": "arn:aws:iam::123456789012:role/hmac-hash-dev-role"
          // other dev-specific settings...
        },
        "prod": {
          "lambda_memory_size": 256,
          "environment_variables": {
            "API_ENDPOINT": "https://api.prod.example.com",
            "LOG_LEVEL": "INFO"
          },
          "iam_role_arn": "arn:aws:iam::123456789012:role/hmac-hash-prod-role",
          "api_gateway_stage": "api" // Optional: customize prod stage name if needed, defaults to stage name ('prod')
          // other prod-specific settings...
        }
      }
      // Default settings applied if not overridden by a stage
      // "manage_iam_role": false // Set to false if providing your own role ARNs
    }
    ```
    *Note:* If you want Chalice to manage IAM roles automatically but with different policies per stage, you can define `iam_policy_file` within each stage block pointing to different policy JSON files (`"iam_policy_file": "policy-dev.json"`). If you specify `iam_role_arn`, set `manage_iam_role` to `false` at the top level or ensure it's omitted (default is `true`).

*   **Commands:**
    *   `chalice deploy --stage dev`: Deploys the current code and configuration to the `dev` stage. Creates `hmac-hash-dev` Lambda, the `dev` stage in API Gateway, and associated resources if they don't exist.
    *   `chalice deploy --stage prod`: Deploys the current code and configuration to the `prod` stage. Creates `hmac-hash-prod` Lambda, the `prod` stage in API Gateway.
    *   `chalice url --stage dev`: Retrieves the invocation URL for the `dev` stage.
    *   `chalice url --stage prod`: Retrieves the invocation URL for the `prod` stage.
    *   `chalice delete --stage dev`: Deletes the AWS resources associated with the `dev` stage.
    *   If you omit `--stage`, Chalice defaults to `dev`.

**3. Managing API Gateway Validation Models (Dev vs. Prod)**

API Gateway Request Validation Models are defined at the API Gateway level, not typically within Chalice's stage configuration directly.

*   **Consistency is Key:** For simplicity, the recommended approach is to keep the validation schemas **identical** across `dev` and `prod`. Differences here can lead to subtle bugs. Your testing process should ensure the code handles requests according to *the* defined schema.
*   **Manual/IaC Management:** If you *absolutely* need different schemas (which should be rare), you would typically manage these API Gateway Model resources outside the direct `chalice deploy` flow. This could be done via:
    *   AWS Console (manual, prone to drift)
    *   AWS CLI/SDK scripts
    *   Infrastructure as Code tools (CloudFormation, Terraform, CDK) alongside your Chalice deployments.
*   **Recommendation:** Strive to use the same schema for both stages. Validate thoroughly in `dev` before deploying the *same* code (which implicitly uses that schema) to `prod`.

**4. Recommended Architecture and Deployment Workflow**

*   **Architecture Summary:**
    *   1 Application Name (`hmac-hash`)
    *   1 API Gateway (`hmac-hash`)
    *   2 API Gateway Stages (`dev`, `prod`)
    *   2 Lambda Functions (`hmac-hash-dev`, `hmac-hash-prod`)
    *   2 IAM Roles (`hmac-hash-dev-role`, `hmac-hash-prod-role`)
    *   Stage-specific configuration managed in `.chalice/config.json`.

*   **Recommended Deployment Workflow (Your Option 'a' adapted):**
    1.  **Develop:** Make code changes on a feature branch (e.g., `feature/new-logic`).
    2.  **Local Test:** Run unit tests locally.
    3.  **Merge to Dev Branch:** Merge the feature branch into a `develop` branch (optional, but good practice).
    4.  **Deploy to Dev:** Check out the `develop` branch. Ensure your workspace is clean. Run:
        ```bash
        chalice deploy --stage dev
        ```
    5.  **Test Dev:** Use the URL from `chalice url --stage dev` to run your automated API validation tests and front-end tests. Thoroughly verify functionality and integration.
    6.  **Prepare for Production:**
        *   Merge the tested `develop` branch into your main branch (e.g., `main` or `master`).
        *   **Crucially:** Create a Git tag for the release (e.g., `git tag v1.1.0`, `git push origin v1.1.0`). This marks the exact code version deployed.
    7.  **Deploy to Prod:** Check out the tag or the main branch at the tagged commit. Ensure your workspace reflects *exactly* the code tested in dev. Run:
        ```bash
        chalice deploy --stage prod
        ```
    8.  **Test Prod:** Run essential smoke tests against the `prod` URL (`chalice url --stage prod`). Monitor CloudWatch logs and metrics closely after deployment.

*   **Why Not Option 'b' (Promote Dev to Prod via AWS Tools):** While technically possible (e.g., using `boto3` to update the `prod` stage's Lambda function pointer), this approach bypasses Chalice's deployment logic. It becomes much harder to ensure that stage-specific configurations (environment variables, Lambda settings defined in `config.json`) are correctly applied during promotion. It adds significant complexity and risk, especially for a team aiming for simplicity. Sticking to `chalice deploy --stage prod` with version-controlled code is far more robust and manageable.

**5. Common Pitfalls to Avoid**

*   **Deploying Wrong Code:** Accidentally running `chalice deploy --stage prod` with local, untested changes or from the wrong Git branch.
    *   *Mitigation:* Strict adherence to the workflow (test `dev` first), use Git tags/branches, double-check `git status` before deploying to `prod`.
*   **Configuration Drift:** Making manual changes to resources (Lambda settings, API Gateway stage settings) in the AWS Console for one stage and forgetting to update `.chalice/config.json` or the other stage.
    *   *Mitigation:* Treat `.chalice/config.json` as the source of truth. Avoid manual console changes for settings managed by Chalice.
*   **IAM Permissions Errors:** The `prod` IAM role lacking permissions that were implicitly available or explicitly set for the `dev` role.
    *   *Mitigation:* Define separate, explicit IAM roles (`iam_role_arn` in `config.json`) or policies (`iam_policy_file`) per stage. Test permissions thoroughly in `dev`.
*   **Secrets Management:** Hardcoding sensitive information (API keys, etc.) in code or `config.json`.
    *   *Mitigation:* Use environment variables defined in `config.json` stages. For highly sensitive data, fetch from AWS Secrets Manager or Parameter Store using the Lambda execution role's permissions.
*   **Forgetting Stage Variables:** Relying on an environment variable set in `dev` but forgetting to define it for the `prod` stage in `config.json`.
    *   *Mitigation:* Carefully review the `stages` section in `config.json` before `prod` deployment.

By following the single API Gateway/multiple stage pattern, leveraging Chalice's stage management features, and adopting a disciplined Git and deployment workflow, you can achieve a robust and relatively simple dev/prod setup.
