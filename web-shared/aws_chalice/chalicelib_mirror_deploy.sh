# ===== START OF FILE chalicelib_mirror_deploy.sh =====
# file_path: web-shared/aws_chalice/chalicelib_mirror_deploy.sh
# contains: bash script to mirror code from core/ to chalicelib/
#          and replace environment variables in config.json with actual values from .env
#          and deploy the chalice application

#!/bin/bash

# Commands to run in terminal from the directory of the Chalice project, e.g., 'hmac-hash'
# FOR DEV DEPLOYMENT:
# ../chalicelib_mirror_deploy.sh

# FOR PROD INITIATION ONLY - NOT FOR SUBSEQUENT PROD DEPLOYMENTS:
# ../chalicelib_mirror_deploy.sh prod

# Enable debug mode (optional for troubleshooting)
#set -x

# Create a temporary file to capture ALL script output
SCRIPT_OUTPUT=$(mktemp)
# Capture all script output to both terminal and the temp file
exec > >(tee -a "$SCRIPT_OUTPUT") 2>&1

# Determine environment ('dev' or 'prod') from command line argument (default to "dev")
ENV=${1:-dev}

# Get the current folder name (Chalice project name)
CHALICE_FOLDER=$(basename "$PWD")

# Function to find the repository root. Defined early so the script does not
# depend on any specific Chalice app location relative to repo root. Chalice
# apps may live under web-shared/aws_chalice/<app>/, apps/<app>/, apps/<area>/api/<app>/,
# or any other depth. All cd-to-root and source-path lookups below use REPO_ROOT.
find_repo_root() {
    local current_dir="$PWD"
    while [[ "$current_dir" != "/" ]]; do
        if [[ -d "$current_dir/.git" ]]; then
            echo "$current_dir"
            return 0
        fi
        current_dir="$(dirname "$current_dir")"
    done
    echo "Repository root not found" >&2
    return 1
}

REPO_ROOT=$(find_repo_root)
if [[ $? -ne 0 || -z "$REPO_ROOT" ]]; then
    echo "Error: Unable to locate repository root"
    exit 1
fi

# Path of the Chalice app relative to repo root, e.g., "web-shared/aws_chalice/qrag-llm"
# or "apps/qrag/api/qrag-llm". Used for repo-root-anchored markdown links and
# log paths.
CHALICE_APP_REL="${PWD#${REPO_ROOT}/}"

echo "Running chalicelib_mirror_deploy.sh - LAST UPDATED: 5-29 refactor to use find_repo_root() and absolute paths; Chalice apps can now live at any depth"
# PREVIOUS LAST UPDATED: 4-13 0800 change composite logging to call add_line_to_top_of_file_but_below_header_lines
echo "Deploying to Chalice folder: $CHALICE_FOLDER (rel path: $CHALICE_APP_REL), environment: $ENV"

# ========================================================================================
echo "### === CHECK API GATEWAY STATUS ==="
app_name=$CHALICE_FOLDER
cd "$REPO_ROOT"
python3 -c "
import sys
try:
    from core.aws import get_api_gateway_and_resource_ids
    
    # For prod only: check if prod API Gateway already exists FIRST
    if '${ENV}' == 'prod':
        api_gateway_name_prod = '${app_name}-prod'
        print(f'Checking if prod API Gateway already exists: {api_gateway_name_prod}')
        
        try:
            rest_api_id_prod, _ = get_api_gateway_and_resource_ids(api_gateway_name_prod, http_method='POST', verbose=False)
            if rest_api_id_prod:
                print(f'❌ ERROR: Production API Gateway {api_gateway_name_prod} already exists with ID: {rest_api_id_prod}', file=sys.stderr)
                print('To avoid accidental overwrites, prod deployment is not allowed when the API Gateway already exists.', file=sys.stderr)
                print('This is a safety measure to prevent unintended changes to production.', file=sys.stderr)
                print('If you need to update an existing production API, please use a different process.', file=sys.stderr)
                sys.exit(2)
        except ValueError:
            # ValueError could mean no gateway or multiple gateways, but we only care if one exists
            pass
        
        print('✅ No existing production API Gateway found. Continuing with deployment.')
    
    # Then check the base API Gateway
    api_gateway_name = '${app_name}'
    print(f'Validating API Gateway: {api_gateway_name}')
    
    try:
        # This will raise ValueError if multiple gateways are found
        rest_api_id, resource_id = get_api_gateway_and_resource_ids(api_gateway_name, http_method='POST', verbose=True)
        if rest_api_id:
            print(f'✅ Confirmed API Gateway for {api_gateway_name} - rest_api_id: {rest_api_id}')
        else:
            print(f'❌ ERROR: No API Gateway found with name: {api_gateway_name}', file=sys.stderr)
            print('This script requires an existing API Gateway.', file=sys.stderr)
            print('Please create the API Gateway first using straight chalice deploy.', file=sys.stderr)
            sys.exit(1)
    except ValueError as e:
        print(f'❌ ERROR: {str(e)}', file=sys.stderr)
        print('You must resolve this issue before deploying.', file=sys.stderr)
        print('Consider deleting one of the duplicate API Gateways.', file=sys.stderr)
        sys.exit(1)
        
except Exception as e:
    print(f'⚠️ Warning: API Gateway check error: {str(e)}', file=sys.stderr)
    sys.exit(3)
"
# Capture the exit code from the Python script
API_CHECK_EXIT_CODE=$?
cd - > /dev/null

# If the API check failed, exit the script
if [ $API_CHECK_EXIT_CODE -ne 0 ]; then
    if [ $API_CHECK_EXIT_CODE -eq 2 ]; then
        echo "❌ Aborting production deployment: A production API Gateway already exists"
    else
        echo "❌ Aborting deployment due to API Gateway validation failure"
    fi
    exit 1
fi

# ========================================================================================
# Do replacement of environment variable in config.json first so that the used secrets can be updated in the .py module headers.
echo ""
echo "### === LOAD SECRET ENV VARIABLES FROM .ENV INTO CHALICE CONFIG.JSON ==="


# REPO_ROOT and find_repo_root are defined at the top of the script.

# Path to the .env file
ENV_FILE="$REPO_ROOT/.env"

# Path to the config.json file (relative to the current script location)
CONFIG_JSON=".chalice/config.json"

# Check if the config.json file exists
if [ ! -f "$CONFIG_JSON" ]; then
  echo "config.json file not found at $CONFIG_JSON"
  exit 1
fi

# Create a temporary copy of config.json
cp "$CONFIG_JSON" "${CONFIG_JSON}.temp"

# If deploying to prod, update app_name to use -prod suffix
if [ "$ENV" == "prod" ]; then
    # Create a temporary file
    CONFIG_TMP="${CONFIG_JSON}.tmp"
    # Update app_name to use -prod instead of -dev
    sed 's/"app_name": "\([^"]*\)-dev"/"app_name": "\1-prod"/' "${CONFIG_JSON}.temp" > "$CONFIG_TMP"
    mv "$CONFIG_TMP" "${CONFIG_JSON}.temp"
    echo "Updated app_name to use -prod suffix"
fi

# Function to replace secrets with actual values from .env and create a list of environment variable keys
replace_secrets() {
    local config_file="$1"
    local env_file="$2"
    local in_env_section=false
    local temp_file="${config_file}.tmp"
    local SKIP_ENV_VARS=("ALLOWED_ORIGIN")
    ENV_VAR_KEYS=()

    while IFS= read -r line; do
        if [[ $line == *"environment_variables"* ]]; then
            in_env_section=true
            echo "$line" >> "$temp_file"
        elif [[ $in_env_section == true && $line == *"}"* ]]; then
            in_env_section=false
            echo "$line" >> "$temp_file"
        elif [[ $in_env_section == true ]]; then
            key=$(echo "$line" | sed -E 's/.*"([^"]+)": *"([^"]+)".*/\1/')
            env_key=$(echo "$line" | sed -E 's/.*"([^"]+)": *"([^"]+)".*/\2/')
            
            # Check if this key should be skipped
            skip_var=false
            for skip_key in "${SKIP_ENV_VARS[@]}"; do
                if [[ "$key" == "$skip_key" ]]; then
                    skip_var=true
                    echo "Skipping replacement for $key" >&2
                    echo "$line" >> "$temp_file"
                    break
                fi
            done
            
            # If not skipped, proceed with replacement
            if [[ "$skip_var" == false ]]; then
                value=$(grep "^$env_key *=" "$env_file" | sed 's/^[^=]*= *//g' | sed 's/^"//; s/"$//; s/ *#.*$//' | tr -d '"')
                
                if [ -n "$value" ]; then
                    replaced_line=$(echo "$line" | sed -E "s/(\"$key\": *)\"[^\"]*\"/\1\"$value\"/")
                    echo "$replaced_line" >> "$temp_file"
                    value_preview="${value:0:12}..."
                    echo "Replaced with actual secret: $line -> first 12 chars: $value_preview" >&2
                    ENV_VAR_KEYS+=("$key")
                else
                    echo "Error: Value for $env_key not found in $env_file" >&2
                    rm "$temp_file"
                    exit 1
                fi
            fi
        else
            echo "$line" >> "$temp_file"
        fi
    done < "$config_file"

    mv "$temp_file" "$config_file"
}

# Replace secrets
if [ -f "$ENV_FILE" ]; then
    replace_secrets "$CONFIG_JSON" "$ENV_FILE"
else
    echo "Error: $ENV_FILE not found"
    exit 1
fi

# ========================================================================================
# Define the target Chalice lib folder within the current directory
echo ""
echo "### === SYNC CODE FILES TO CHALICE LIB ==="

TARGET_FOLDER="./chalicelib"

# Check if target folder exists - if not, skip module copying
if [ ! -d "$TARGET_FOLDER" ]; then
    echo "Warning: Chalice lib folder '$TARGET_FOLDER' does not exist. Skipping module copying."
else
    # List of paths to the files that have the code you want copied into the chalicelib files
    FILES_TO_COPY=(
        "${REPO_ROOT}/core/aws.py"
        "${REPO_ROOT}/core/fileops.py"
        "${REPO_ROOT}/core/llm.py"
        "${REPO_ROOT}/core/rag.py"
        "${REPO_ROOT}/core/vectordb.py"
        "${REPO_ROOT}/core/rag_prompts_routes.py"
        # Add more file paths as needed
    )

    # Delimiter to indicate where to start syncing code
    DELIMITER="# ---START OF SYNCED CODE---"

    # Iterate over the specified files
    for file in "${FILES_TO_COPY[@]}"; do
        # Get the base name of the file (without directory)
        base_name=$(basename "$file")

        # Find the corresponding file in the chalice lib folder
        target_file="$TARGET_FOLDER/$base_name"

        if [ -f "$target_file" ] && [ -f "$file" ]; then
            echo "Updating '$target_file' with code from '$file'"

            # Extract content from the target file above the delimiter
            awk -v delim="$DELIMITER" '
                $0 ~ delim {exit}
                {print}
            ' "$target_file" > temp_target_header.py

            # Extract content from the source file including and below the delimiter
            awk -v delim="$DELIMITER" '
                $0 ~ delim {p=1}
                p
            ' "$file" > temp_source_code.py

            # Combine the target header and source code
            cat temp_target_header.py temp_source_code.py > "$target_file"

            # Clean up temporary files
            rm temp_target_header.py temp_source_code.py
        else
            echo "Either source file '$file' or target file '$target_file' does not exist. Skipping."
        fi
    done

    # Function to process Python module headers
    process_module_header() {
        local file="$1"
        local temp_file="${file}.tmp"
        local in_secrets_section=false
        local in_synced_code=false

        while IFS= read -r line; do
            if [[ $line == *"# ---API KEYS AND SECRETS---"* ]]; then
                in_secrets_section=true
                echo "$line" >> "$temp_file"
            elif [[ $line == *"# ---START OF SYNCED CODE---"* ]]; then
                in_synced_code=true
                in_secrets_section=false
                echo "$line" >> "$temp_file"
            elif [[ $in_secrets_section == true ]]; then
                if [[ $line == *"from dotenv"* || $line == *"load_dotenv"* ]]; then
                    continue  # Skip these lines
                elif [[ $line == *"="* && ! $line == \#* ]]; then
                    var_name=$(echo "$line" | cut -d'=' -f1 | tr -d ' ')
                    if [[ " ${ENV_VAR_KEYS[@]} " =~ " ${var_name} " ]]; then
                        echo "$var_name = os.environ[\"$var_name\"]" >> "$temp_file"
                    else
                        echo "# $line  # Not in chalice/config.json" >> "$temp_file"
                    fi
                else
                    echo "$line" >> "$temp_file"
                fi
            else
                echo "$line" >> "$temp_file"
            fi
        done < "$file"

        mv "$temp_file" "$file"
    }

    # Process Python module headers
    for file in "${FILES_TO_COPY[@]}"; do
        target_file="$TARGET_FOLDER/$(basename "$file")"
        if [ -f "$target_file" ]; then
            echo "Processing header of $target_file"
            process_module_header "$target_file"
        else
            echo "Target file $target_file not found. Skipping header processing."
        fi
    done

    # Replace "from core." with "from chalicelib."
    echo "Replacing 'from core.' with 'from chalicelib.' in Python modules..."
    for py_file in "$TARGET_FOLDER"/*.py; do
        if [ -f "$py_file" ]; then
            echo "Processing $py_file"
            if [[ "$OSTYPE" == "darwin"* ]]; then
                # macOS (BSD) sed
                sed -i '' 's/from core\./from chalicelib./' "$py_file"
            else
                # GNU sed
                sed -i 's/from core\./from chalicelib./' "$py_file"
            fi
        fi
    done
fi

# ========================================================================================
echo ""
echo "### === EXECUTE CHALICE DEPLOYMENT ==="
echo "Deploying Chalice application with chalice deploy --stage $ENV"
echo "Following lines are the output of the chalice deploy command:"
echo ""

# Create a temporary file to capture deployment output
CHALICE_OUTPUT=$(mktemp)
chalice deploy --stage $ENV | tee "$CHALICE_OUTPUT"
echo ""
echo "Chalice deploy command completed."

# Capture the exit code
DEPLOY_EXIT_CODE=$?

# Check if deployment was successful
if [ $DEPLOY_EXIT_CODE -ne 0 ]; then
    echo "❌ Chalice deployment failed with exit code: $DEPLOY_EXIT_CODE"
    rm "$CHALICE_OUTPUT"
    exit $DEPLOY_EXIT_CODE
fi

# Restore the original config.json immediately after deployment
mv "${CONFIG_JSON}.temp" "$CONFIG_JSON"
echo "Restored original config.json"

# ========================================================================================
### SET UP API GATEWAY VALIDATION
# Ask user to confirm before proceeding
# read -p "Press Enter to continue with API Gateway validation setup, or Ctrl+C to abort: " user_input

# Add a small delay to ensure API Gateway changes are propagated
API_GATEWAY_WAIT_TIME=5
echo "Waiting before setting up API Gateway validation (${API_GATEWAY_WAIT_TIME} seconds)..."
sleep $API_GATEWAY_WAIT_TIME

# Create timestamp here to best match the AWS console history for 2nd API Gateway deployment
TIMESTAMP=$(date '+%Y-%m-%d_%H%M%S')

echo ""
echo "### === SET UP API GATEWAY VALIDATION ==="
cd "$REPO_ROOT"
python3 -c "
from core.aws_valid import set_request_validation, APIS_VALIDATION_ENABLED, UnifiedLogger, map_names_env_stages
import boto3
import time
import os

try:
    # Make sure the boto3 client is properly initialized
    boto3.client('apigateway')  # This ensures boto3 is loaded
    
    app_name = '${app_name}'
    env = '${ENV}'
    
    # Map app name and environment to correct API Gateway name and stage
    api_gateway_name, stage, _ = map_names_env_stages(app_name, env)
    
    print(f'Running request validation setup for {api_gateway_name} (stage: {stage})...')
    
    # Create a deployment log directory if needed
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # Create a logger to capture all output
    logger = UnifiedLogger()
    
    # Check if validation is enabled before setup
    validation_enabled = APIS_VALIDATION_ENABLED.get(api_gateway_name, False)
    
    # Run setup with the logger
    result = set_request_validation(api_gateway_name, stage, skip_deployment=False, logger=logger)
    
    if result:
        if not validation_enabled:
            print('ℹ️ Validation is disabled for this API by configuration')
        else:
            print('✅ Successfully set up and deployed request validation')
        
        # Look for the most recent log file
        try:
            validation_logs = [f for f in os.listdir(log_dir) if f.startswith(f'api_validation_{api_gateway_name}_{stage}')]
            if validation_logs:
                latest_log = max(validation_logs)
                print(f'📝 Detailed validation log available at: {os.path.join(log_dir, latest_log)}')
        except Exception as e:
            print(f'Note: Could not locate validation log file: {e}')
    else:
        print('❌ Validation setup failed - check logs for details')
        print('Summary of validation attempt:')
        print(logger.get_summary())
except Exception as e:
    print(f'Error setting up validation: {str(e)}')
"
cd - > /dev/null

# Add a small delay to ensure API Gateway changes are propagated
API_GATEWAY_WAIT_TIME=5
echo "Waiting for API Gateway changes to propagate for (${API_GATEWAY_WAIT_TIME} seconds)..."
sleep $API_GATEWAY_WAIT_TIME

# ========================================================================================
echo ""
echo "### === DEPLOYMENT LOGGING ==="

# Show deployment result
if grep -q "Resources deployed:" "$SCRIPT_OUTPUT"; then
    echo "✅ Function ${app_name}-${ENV} deployed successfully"
else
    echo "⚠️ Deployment completed with warnings - checking Lambda function status..."
    if aws lambda get-function --function-name ${app_name}-${ENV} >/dev/null 2>&1; then
        echo "✅ Function ${app_name}-${ENV} exists and appears to be working"
    else
        echo "❌ Function ${app_name}-${ENV} deployment failed"
    fi
fi

# Create individual deployment log file for dev deployments.
# Logs live under the gitignored root logs/ mount (local-only), not beside the Chalice app.
if [ "$ENV" == "dev" ]; then
    DEV_LOG_DIR="${REPO_ROOT}/logs/aws_chalice_deploys/${app_name}/deployed_dev_logs"
    mkdir -p "$DEV_LOG_DIR"

    # Use above timestamp for dev log filename
    DEV_LOG_FILE="$DEV_LOG_DIR/deployed_dev_log_$TIMESTAMP.md"

    # Write header to the log file
    echo "# Deployed Dev Log for $app_name $TIMESTAMP" > "$DEV_LOG_FILE"

    # Extract the "last updated" comment from app.py if it exists
    APP_PY="./app.py"
    LAST_UPDATED_COMMENT=""
    if [ -f "$APP_PY" ]; then
        # Use the Python function extract_last_updated_comment from aws_valid.py
        echo "Extracting last updated comment from $APP_PY (local)..."
        LAST_UPDATED_COMMENT=$(python3 -c "
from core.aws_valid import extract_last_updated_comment
import sys
import os

try:
    full_path = os.path.abspath('$APP_PY')
    print(f'Reading from {full_path}', file=sys.stderr)
    with open(full_path, 'r') as f:
        app_content = f.read()

    result = extract_last_updated_comment(app_content)
    print(result)
except Exception as e:
    print(f'Error: {str(e)}', file=sys.stderr)
    # Don't exit here, just continue with empty comment
" 2>/dev/null)

        if [ -n "$LAST_UPDATED_COMMENT" ]; then
            echo "app.py LAST UPDATED $LAST_UPDATED_COMMENT" >> "$DEV_LOG_FILE"
        fi
    fi
    echo "" >> "$DEV_LOG_FILE"

    # Generate API state report
    echo "## API State Report" >> "$DEV_LOG_FILE"
    API_STATE_REPORT_FOLDER="logs/aws_api_state_reports"

    # Create directories if they don't exist
    cd "$REPO_ROOT"
    mkdir -p "$API_STATE_REPORT_FOLDER"

    # Generate the API state report
    API_REPORT_OUTPUT=$(python3 -c "
from core.aws_valid import generate_api_state_report
import os

# Make sure the output folder exists
os.makedirs('$API_STATE_REPORT_FOLDER', exist_ok=True)

# Generate the API state report with correct parameters
report_path = generate_api_state_report(['$app_name', '$app_name-prod'], output_folder='$API_STATE_REPORT_FOLDER')
print(report_path)
")

    cd - > /dev/null

    # Extract just the filename from the report path
    REPORT_FILENAME=$(basename "$API_REPORT_OUTPUT")

    # Dev log is at logs/aws_chalice_deploys/<app>/deployed_dev_logs/; API reports
    # are at logs/aws_api_state_reports/ — fixed relative link between those trees.
    if [ -n "$API_REPORT_OUTPUT" ]; then
        echo "[$REPORT_FILENAME](../../aws_api_state_reports/$REPORT_FILENAME)" >> "$DEV_LOG_FILE"
    else
        echo "API state report not generated successfully" >> "$DEV_LOG_FILE"
    fi
    echo "" >> "$DEV_LOG_FILE"

    # Add chalice deployment output to the log file
    echo "## Chalice Deployment Output" >> "$DEV_LOG_FILE"
    cat "$SCRIPT_OUTPUT" >> "$DEV_LOG_FILE"
    echo "" >> "$DEV_LOG_FILE"

    # Add a log entry indicating the individual log file
    echo "Individual deployment log created at: $DEV_LOG_FILE"
fi

# Clean up temporary files
rm -f "$CHALICE_OUTPUT" "$SCRIPT_OUTPUT"

# Log the deployment to the composite deployment log file. The composite log
# stays at web-shared/aws_chalice/ even when individual Chalice apps live elsewhere
# (e.g., apps/qrag/api/). Anchor it to repo root.
COMPOSITE_LOG_FILE="${REPO_ROOT}/web-shared/aws_chalice/chalicelib_mirror_deploy_composite_log.md"
APP_PY="./app.py"

# Use the Python function extract_last_updated_comment from aws_valid.py
echo "Extracting last updated comment from $APP_PY..."
LAST_UPDATED_COMMENT=""
if [ -f "$APP_PY" ]; then
    LAST_UPDATED_COMMENT=$(python3 -c "
from core.aws_valid import extract_last_updated_comment
import sys
import os

try:
    full_path = os.path.abspath('$APP_PY')
    print(f'Reading from {full_path}', file=sys.stderr)
    with open(full_path, 'r') as f:
        app_content = f.read()
    
    result = extract_last_updated_comment(app_content)
    print(result)
except Exception as e:
    print(f'Error: {str(e)}', file=sys.stderr)
    # Don't exit, just continue with empty comment
" 2>/dev/null)
fi

echo "Last updated comment: '$LAST_UPDATED_COMMENT'"

# Ensure the log file exists with the start of file marker
if [ ! -f "$COMPOSITE_LOG_FILE" ]; then
    echo ""
    echo "⚠️ WARNING! ⚠️ ⚠️ WARNING! ⚠️ ⚠️ WARNING! ⚠️"
    echo "COMPOSITE LOG FILE NOT FOUND: $COMPOSITE_LOG_FILE"
    echo "This file should already exist. Creating a new one now. Please investigate why the original file is missing."
    echo "<START OF FILE web-shared/aws_chalice/chalicelib_mirror_deploy_composite_log.md>" > "$COMPOSITE_LOG_FILE"
    echo -e "\n\n" >> "$COMPOSITE_LOG_FILE" # Add two blank lines after header
    echo "Created new composite log file at: $COMPOSITE_LOG_FILE"
    echo ""
fi

# Create the new log entry
if [ "$ENV" == "prod" ]; then
    # For prod, placeholder for now
    NEW_ENTRY="$TIMESTAMP    ======prod-init======    ${app_name}"
else
    # For dev, create markdown link to the individual log file. DEV_LOG_PATH
    # is repo-root-relative under logs/aws_chalice_deploys/; the link
    # "../../$DEV_LOG_PATH" from the composite log (web-shared/aws_chalice/)
    # resolves correctly.
    DEV_LOG_FILENAME="deployed_dev_log_$TIMESTAMP.md"
    DEV_LOG_PATH="logs/aws_chalice_deploys/${app_name}/deployed_dev_logs/$DEV_LOG_FILENAME"
    # Make sure there are two spaces between app_name and LAST_UPDATED_COMMENT
    NEW_ENTRY="$TIMESTAMP    _dev_    ${app_name}  ${LAST_UPDATED_COMMENT} [log](../../$DEV_LOG_PATH)"
    echo "Created log entry: $NEW_ENTRY"
fi

# Use Python function to add the new entry below header lines
# This ensures entries appear under section headings (lines starting with #)
echo "Adding entry to composite log: '$NEW_ENTRY'"
python3 -c "
import sys
from core.aws_valid import add_line_to_top_of_file_but_below_header_lines

# Pass the new entry directly as a string literal
add_line_to_top_of_file_but_below_header_lines('$COMPOSITE_LOG_FILE', '''$NEW_ENTRY''')
"
echo "Deployment logged to $COMPOSITE_LOG_FILE"

# Find and display the most recent deployment package
echo ""
echo "### === DEPLOYMENT ZIP FILE ==="
DEPLOYMENT_DIR="./.chalice/deployments"
if [ -d "$DEPLOYMENT_DIR" ]; then
    LATEST_DEPLOYMENT=$(ls -t "$DEPLOYMENT_DIR" 2>/dev/null | head -1)
    if [ -n "$LATEST_DEPLOYMENT" ]; then
        # Get current directory name (app name)
        CURRENT_DIR=$(basename "$PWD")
        
        # Original deployment zip
        ORIGINAL_DEPLOYMENT_ZIP="$DEPLOYMENT_DIR/$LATEST_DEPLOYMENT"
        
        # Create new filename with timestamp prefix
        NEW_FILENAME="${TIMESTAMP}_${LATEST_DEPLOYMENT}"
        NEW_DEPLOYMENT_ZIP="$DEPLOYMENT_DIR/$NEW_FILENAME"
        ZIP_PREAMBLE="Lambda zip created by deployment: "
        
        # Rename the file
        mv "$ORIGINAL_DEPLOYMENT_ZIP" "$NEW_DEPLOYMENT_ZIP"
        
        # Construct full repo-root-relative path for display and logging.
        # Anchored at CHALICE_APP_REL so it works regardless of Chalice app location.
        FULL_RELATIVE_PATH="${CHALICE_APP_REL}/$DEPLOYMENT_DIR/$NEW_FILENAME"
        FULL_RELATIVE_PATH=${FULL_RELATIVE_PATH/.\//}
        
        echo "$ZIP_PREAMBLE $FULL_RELATIVE_PATH"
        
        # Add the deployment zip path to the most recent log entry - escaped for sed
        ESCAPED_ZIP=$(echo "$FULL_RELATIVE_PATH" | sed 's/[\/&]/\\&/g')
        
        # Also update the individual dev log file with the correct renamed zip file
        if [ "$ENV" == "dev" ] && [ -f "$DEV_LOG_FILE" ]; then
            echo "### DEPLOYMENT ZIP FILE" >> "$DEV_LOG_FILE"
            echo "$ZIP_PREAMBLE" >> "$DEV_LOG_FILE"
            echo "$FULL_RELATIVE_PATH" >> "$DEV_LOG_FILE"
            echo "" >> "$DEV_LOG_FILE"
        fi
        
        if [ "$ENV" == "prod" ]; then
            if [[ "$OSTYPE" == "darwin"* ]]; then
                # macOS (BSD) sed - find the first non-empty line after # prod and append to it
                sed -i '' "/^# prod/{n;s/$/\n  ${ZIP_PREAMBLE}${ESCAPED_ZIP}/;}" "$COMPOSITE_LOG_FILE"
            else
                # GNU sed
                sed -i "/^# prod/{n;s/$/\n  ${ZIP_PREAMBLE}${ESCAPED_ZIP}/;}" "$COMPOSITE_LOG_FILE"
            fi
        else
            if [[ "$OSTYPE" == "darwin"* ]]; then
                # macOS (BSD) sed - find the first non-empty line after # dev and append to it
                sed -i '' "/^# dev/{n;s/$/\n  ${ZIP_PREAMBLE}${ESCAPED_ZIP}/;}" "$COMPOSITE_LOG_FILE"
            else
                # GNU sed
                sed -i "/^# dev/{n;s/$/\n  ${ZIP_PREAMBLE}${ESCAPED_ZIP}/;}" "$COMPOSITE_LOG_FILE"
            fi
        fi
    else
        echo "No deployment packages found in $DEPLOYMENT_DIR"
    fi
else
    echo "Deployment directory not found: $DEPLOYMENT_DIR"
fi

echo "Script completed at $(date '+%Y-%m-%d %H:%M:%S')"

# ===== END OF FILE chalicelib_mirror_deploy.sh =====


