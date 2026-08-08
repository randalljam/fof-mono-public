import os
import json
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import hashlib
import hmac
import pytz
from datetime import datetime, timedelta
import jwt


# ---API KEYS AND SECRETS---
# USERS_HMAC_SECRET_KEY = os.environ["USERS_HMAC_SECRET_KEY"]  # Not in chalice/config.json

# ---START OF SYNCED CODE--- only code below will be synchronized with chalicelib.

### HMAC HASH
def generate_hmac_hash(input_text, secret_key):
    """
    Generate a HMAC hash for the given input text using the provided secret key.

    :param input_text: The text to be hashed
    :param secret_key: The secret key used for hashing
    :return: The HMAC hash as a hexadecimal string of 64 characters
    """
    # Encode the input text to bytes
    input_bytes = input_text.encode('utf-8')
    
    # Create a new HMAC object with the secret key
    hmac_obj = hmac.new(secret_key.encode('utf-8'), input_bytes, hashlib.sha256)
    
    # Return the HMAC hash as a hexadecimal string
    return hmac_obj.hexdigest()
def mtest_generate_hmac_hash():
    pass
#if __name__ == "__main__":
    # Test the generate_hmac_hash function with randy@floodlamp.bio
    email = "[REDACTED-EMAIL]"
    hashed_email = generate_hmac_hash(email, USERS_HMAC_SECRET_KEY)
    print(f"HMAC hash for {email}: {hashed_email}")

    # Verify the hash by generating it again
    verification_hash = generate_hmac_hash(email, USERS_HMAC_SECRET_KEY)
    print(f"Verification hash: {verification_hash}")

    # Check if the hashes match
    if hashed_email == verification_hash:
        print("Hash verification successful!")
    else:
        print("Hash verification failed.")

### AWS S3
def upload_file_to_s3(file_path, bucket='fofpublic', object_name=None, s3_path=None, prompt_overwrite=False):
    """
    Upload a file to an S3 bucket

    :param file_path: File to upload
    :param bucket: Name of the S3 bucket, default is 'fofpublic', others: '[S3-BUCKET]', 'deutsch-audio'
    :param object_name: S3 object name. If not specified, the file name is used
    :param s3_path: S3 folder path where the file will be stored, e.g. 'podcasts/'
    :param prompt_overwrite: If True, prompts for confirmation before overwriting existing files
    :return: The object name of the file in S3, or None if upload was cancelled or failed
    """
    # Create an S3 client
    s3_client = boto3.client('s3')

    # Extract the file name from the file path if object_name is not provided
    if object_name is None:
        object_name = os.path.basename(file_path)

    # Prepend the s3_path if provided
    if s3_path:
        object_name = os.path.join(s3_path, object_name)

    try:
        # Check if file exists
        if prompt_overwrite:
            try:
                s3_client.head_object(Bucket=bucket, Key=object_name)
                # File exists, prompt for confirmation
                response = input(f"\n⚠️ Warning: {object_name} already exists in {bucket}. Overwrite? (y/n): ")
                if response.lower() != 'y':
                    print("Upload cancelled")
                    return None
            except ClientError as e:
                # File doesn't exist, continue with upload
                if e.response['Error']['Code'] != '404':
                    # Some other error occurred
                    raise

        # Upload the file
        s3_client.upload_file(file_path, bucket, object_name)
        print(f"Uploaded to S3 bucket: {bucket}  object: {object_name}")
        return object_name

    except FileNotFoundError:
        print(f"Local file not found: {file_path}")
        return None
    except NoCredentialsError:
        print("Credentials not available")
        return None
    except ClientError as e:
        print(f"Error uploading to S3: {str(e)}")
        return None

def rename_s3_object(bucket, old_key, new_key, s3_path=None):
    """
    Rename an object in an S3 bucket by copying it to a new key and deleting the old key.

    :param bucket: Name of the S3 bucket
    :param old_key: The current key (path) of the object in the S3 bucket
    :param new_key: The new key (path) for the object in the S3 bucket
    :param s3_path: Optional S3 folder path to prepend to the keys
    :return: None
    """
    s3 = boto3.client('s3', region_name='us-west-2')

    # Adjust keys if s3_path is provided
    if s3_path:
        old_key = f"{s3_path}/{old_key}"
        new_key = f"{s3_path}/{new_key}"
        
    # Copy the old object to the new key
    copy_source = f"{bucket}/{old_key}"
    print(f"Function rename_s3_object is attempting to copy from {copy_source} to {new_key} in bucket {bucket}")
    s3.copy_object(Bucket=bucket, CopySource=copy_source, Key=new_key)
    
    # Delete the old object
    s3.delete_object(Bucket=bucket, Key=old_key)
    print(f"Renamed {old_key} to {new_key} in bucket {bucket}")
    return

def get_s3_object(bucket, key, s3_path=None, parse_json=True, verbose=False):
    """
    Retrieve an object from an S3 bucket.

    :param bucket: Name of the S3 bucket
    :param key: The key (path) of the object in the S3 bucket
    :param s3_path: Optional S3 folder path to prepend to the key
    :param parse_json: Whether to parse the object content as JSON (default: True)
    :param verbose: Whether to print verbose output (default: False)
    :return: The object content (parsed as JSON if parse_json is True) if found, otherwise None
    """
    s3 = boto3.client('s3', region_name='us-west-2')

    # Adjust key if s3_path is provided
    if s3_path:
        # Remove trailing slash from s3_path and leading slash from key
        full_key = f"{s3_path.rstrip('/')}/{key.lstrip('/')}"
    else:
        full_key = key

    verbose_print(verbose, f"Function get_s3_object is attempting to access key: {full_key} in bucket: {bucket}")

    try:
        response = s3.get_object(Bucket=bucket, Key=full_key)
        content = response['Body'].read().decode('utf-8')
        if parse_json:
            return json.loads(content)
        return content
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchKey':
            print(f"Error: No such key: {full_key} in bucket: {bucket}")
        elif error_code == 'NoSuchBucket':
            print(f"Error: No such bucket: {bucket}")
        else:
            print(f"Error: {e}")
        return None
    except Exception as e:
        print(f"Error: Failed to retrieve {full_key} from {bucket}: {str(e)}")
        return None
def mtest_get_s3_object():
    pass
#if __name__ == "__main__":
    # Test the get_s3_object function
    bucket = "[S3-BUCKET]"
    key = "qrag-exch_2024-10-06_140708.json"
    s3_path = "s3-qrag-deutsch-v3"
    
    # Retrieve the object
    result = get_s3_object(bucket, key, s3_path=s3_path)
    
    # Print the result
    if result is not None:
        print(f"Retrieved object for key '{key}' from bucket '{bucket}' in path '{s3_path}':")
        print(json.dumps(result, indent=2))
    else:
        print(f"Failed to retrieve object for key '{key}' from bucket '{bucket}' in path '{s3_path}'")

def list_s3_files(bucket, s3_path, file_extension='.json'):
    """
    List all files with a specific extension in the specified S3 bucket and path.

    :param bucket: Name of the S3 bucket.
    :param s3_path: The folder path (path) in the S3 bucket.
    :param file_extension: The file extension to filter by (default: '.json').
    :return: List of file names (without path) with the specified extension, sorted lexicographically.
    """
    s3_client = boto3.client('s3')
    matching_files = []
    paginator = s3_client.get_paginator('list_objects_v2')
    try:
        for page in paginator.paginate(Bucket=bucket, Prefix=s3_path):
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    if key.endswith(file_extension):
                        # Extract only the file name without the path
                        file_name = os.path.basename(key)
                        matching_files.append(file_name)
        print(f"Found {len(matching_files)} {file_extension} files in bucket '{bucket}' with path '{s3_path}'.")
        
        # Sort the list of matching files lexicographically
        matching_files.sort()
        
        return matching_files
    except ClientError as e:
        print(f"Error listing S3objects in bucket '{bucket}' with path '{s3_path}': {e}")
        return []
def mtest_list_s3_files():
    pass
#if __name__ == "__main__":
    bucket = '[S3-BUCKET]'
    s3_path = 's3-qrag-deutsch/'
    file_extension = '.json'  # Specify the file extension
    files = list_s3_files(bucket, s3_path, file_extension)
    num_files = len(files)
    print(f"Number of exchange files: {num_files}")
    if num_files > 0:
        print(f"First item: {files[0]}")
        print(f"Last item:  {files[-1]}")
    else:
        print("No files found in S3 bucket and folder.")

def remove_from_file_list(folder_path, base_file_list):
    """
    Removes files found in the specified folder (including subfolders) from the given base file list.

    :param folder_path: String path to the folder to search for files.
    :param base_file_list: List of base file names (without paths) to filter.
    :return: A new list with matching files removed.
    """
    # Get all JSON files in the folder and subfolders
    full_file_paths = get_files_in_folder(folder_path, include_subfolders=True, suffixpat_include='.json')
    
    # Extract base file names from the full paths
    folder_base_files = [os.path.basename(file_path) for file_path in full_file_paths]
    
    # Remove matching files from the base_file_list
    filtered_list = [file for file in base_file_list if file not in folder_base_files]
    
    # Print the number of files removed
    num_removed = len(base_file_list) - len(filtered_list)
    print(f"Number of files removed from the base file list: {num_removed}")
    
    return filtered_list
def mtest_remove_from_file_list():
    folder_path = 'exchanges/deutsch_qrag'  # Use this as the folder path
    base_file_list = mtest_list_s3_files()
    
    # Call the function to remove files found in the folder from the base file list
    filtered_list = remove_from_file_list(folder_path, base_file_list)
    
    # Print the filtered list
    print(f"Filtered list has {len(filtered_list)} items.")

def download_s3_files_new(bucket, s3_path, local_folder):
    """
    Download new files from S3 to a local folder.

    :param bucket: Name of the S3 bucket.
    :param s3_path: S3 path to the files.
    :param local_folder: Local folder where both files to exclude and files to download will be saved.
    :return: None
    """
    s3_client = boto3.client('s3')
    s3_files = list_s3_files(bucket, s3_path, file_extension='.json')

    files_to_download = remove_from_file_list(local_folder, s3_files)

    # Create a 'new' subfolder if it doesn't exist
    new_folder = os.path.join(local_folder, 'new')
    os.makedirs(new_folder, exist_ok=True)

    # Download the remaining files to the 'new' subfolder
    downloaded_count = 0
    for file_name in files_to_download:
        s3_key = os.path.join(s3_path, file_name)
        local_file_path = os.path.join(new_folder, file_name)
        try:
            s3_client.download_file(bucket, s3_key, local_file_path)
            downloaded_count += 1
        except ClientError as e:
            print(f"Error downloading '{s3_key}': {e}")
    
    print(f"Downloaded {downloaded_count} files from S3 to '{new_folder}'.")
def mtest_download_s3_files_new():
    bucket = '[S3-BUCKET]'
    s3_path = 's3-qrag-deutsch-v3'
    local_folder = 'exchanges/deutsch_qrag'
    download_s3_files_new(bucket, s3_path, local_folder)

def download_s3_files_date_range(bucket, s3_path, local_folder, start_date, end_date, timezone='America/Los_Angeles'):
    """
    Download files from S3 to a local folder that were last modified within a specified date range.

    :param bucket: string, name of the S3 bucket.
    :param s3_path: string, S3 path to the files.
    :param local_folder: string, local folder where files will be downloaded.
    :param start_date: string, start date in format 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'.
    :param end_date: string, end date in format 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'.
    :param timezone: string, timezone for date comparison. Defaults to 'America/Los_Angeles'.
    :return: None
    """
    s3_client = boto3.client('s3')
    s3_files = list_s3_files(bucket, s3_path, file_extension='.json')
    
    # Convert start and end dates to timezone-aware datetime objects
    tz = pytz.timezone(timezone)
    
    # Handle both date-only and date-time formats
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        start_dt = start_dt.replace(hour=0, minute=0, second=0)
    
    try:
        end_dt = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        end_dt = end_dt.replace(hour=23, minute=59, second=59)
    
    # Localize the datetime objects
    start_dt = tz.localize(start_dt)
    end_dt = tz.localize(end_dt)

    # Create local folder if it doesn't exist
    os.makedirs(local_folder, exist_ok=True)

    downloaded_count = 0
    for file_name in s3_files:
        s3_key = os.path.join(s3_path, file_name)
        try:
            response = s3_client.head_object(Bucket=bucket, Key=s3_key)
            last_modified = response['LastModified']
            last_modified_tz = last_modified.astimezone(tz)
            
            if start_dt <= last_modified_tz <= end_dt:
                local_file_path = os.path.join(local_folder, file_name)
                s3_client.download_file(bucket, s3_key, local_file_path)
                downloaded_count += 1
                
        except ClientError as e:
            print(f"Error accessing '{s3_key}': {e}")
    
    print(f"Downloaded {downloaded_count} files from S3 to '{local_folder}' (files modified between {start_date} and {end_date} {timezone}).")
def mtest_download_s3_files_new():
    pass
#if __name__ == "__main__":
    bucket = 'fofpublic'
    s3_path = 'deepgram-transcriptions'
    local_folder = 'data/audio_inbox'
    download_s3_files_date_range(bucket, s3_path, local_folder, start_date="2024-11-04", end_date="2024-11-05")

def download_file_from_s3(bucket, key, s3_path, local_folder, overwrite=True):
    """
    Download a single file from S3 to a local folder.

    :param bucket: Name of the S3 bucket
    :param key: The key (filename) of the object in the S3 bucket
    :param s3_path: S3 folder path where the file is stored
    :param local_folder: Local folder where the file will be downloaded
    :param overwrite: If False, skip download if file already exists (default: False)
    :return: Path to the downloaded file if successful, None otherwise
    """
    s3_client = boto3.client('s3')

    # Adjust key if s3_path is provided
    if s3_path:
        s3_key = f"{s3_path}/{key}"
    else:
        s3_key = key

    # Create local folder if it doesn't exist
    os.makedirs(local_folder, exist_ok=True)

    # Set the local file path
    local_file_path = os.path.join(local_folder, os.path.basename(key))

    # Check if file exists and handle based on overwrite setting
    if os.path.exists(local_file_path):
        if not overwrite:
            print(f"File already exists at '{local_file_path}' and overwrite=False, skipping download")
            return local_file_path
        else:
            print(f"File already exists at '{local_file_path}' and overwrite=True, overriding existing file")

    try:
        s3_client.download_file(bucket, s3_key, local_file_path)
        print(f"Downloaded '{s3_key}' from bucket '{bucket}' to '{local_file_path}'")
        return local_file_path
    except ClientError as e:
        print(f"Error downloading '{s3_key}' from bucket '{bucket}': {e}")
        return None
def mtest_download_file_from_s3():
    pass
#if __name__ == "__main__":
    bucket = 'fofpublic'
    key = '5f3deb13-b6ec-4656-b31b-bc1f82255733.json'
    s3_path = 'deepgram-transcriptions'
    local_folder = 'data/audio_inbox'
    download_file_path = download_file_from_s3(bucket, key, s3_path, local_folder)

def mrun_S3_mtests():
    pass
#if __name__ == "__main__":
    mtest_get_s3_object()
    mtest_list_s3_files()
    mtest_remove_from_file_list()
    mtest_download_new_s3_files()

def generate_presigned_s3_url(bucket, object_key, method='get', content_type=None, expire_seconds=1800):
    """
    Generate a presigned URL for 'get' or 'put' to allow temporary access to S3 objects.

    :param bucket: S3 bucket name
    :param object_key: Full S3 key, e.g. "audio/filename.mp3"
    :param method: 'get' or 'put'
    :param content_type: Set this if you're generating a PUT URL for JSON or other media
    :param expire_seconds: How many seconds this URL remains valid (default 30 min)
    :return: The presigned URL string
    """
    from botocore.client import Config

    s3_client = boto3.client('s3', config=Config(signature_version='s3v4'))

    if method.lower() == 'put':
        # For PUT, specify the ContentType so S3 stores the object type correctly.
        return s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket,
                'Key': object_key,
                'ContentType': content_type or 'application/json',
            },
            ExpiresIn=expire_seconds
        )
    else:
        # Default is GET
        return s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': object_key},
            ExpiresIn=expire_seconds
        )

def get_large_context_from_s3(filename):
    """
    Fetch large context file from S3.

    :param filename: str, name of the file to fetch from large-context-files folder
    :return: str, content of the file
    :raises: ClientError with specific error details
    """
    s3 = boto3.client('s3')
    bucket = '[S3-BUCKET]'
    key = f'large-context-files/{filename}'
    
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        return response['Body'].read().decode('utf-8')
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchKey':
            print(f"File not found: {filename}")
            return None
        elif error_code == 'AccessDenied':
            print(f"Access denied to s3://{bucket}/{key}. Check IAM permissions.")
            return None
        else:
            print(f"AWS Error: {str(e)}")
            return None
def mtest_get_large_context_from_s3():
    pass
#if __name__ == "__main__":
    # Test valid file
    try:
        filename = 'deutsch_large_context_v1.md'
        print(f"\nTesting get_large_context_from_s3 with file:{filename}")
        content = get_large_context_from_s3(filename)
        if content:
            print(f"Successfully retrieved file. First 100 chars: {content[:100]}")
        else:
            print("Error: No content returned")
    except ClientError as e:
        print(f"AWS Error: {str(e)}")
        print(f"Error Code: {e.response['Error']['Code']}")
        print(f"Error Message: {e.response['Error']['Message']}")

    # Test non-existent file
    try:
        filename = 'nonexistent_file.txt'
        print(f"\nTesting with non-existent file: {filename}")
        content = get_large_context_from_s3(filename)
    except ClientError as e:
        print(f"Expected error for non-existent file: {str(e)}")

def upload_large_context_files_to_s3(folder_path='data/large_context_files'):  # not tested
    s3 = boto3.client('s3')
    s3_folder = 'large-context-files'
    uploaded_count = 0
    try:
        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)
            if os.path.isfile(file_path):
                s3.upload_file(
                    Bucket='[S3-BUCKET]',
                    Key=f'{s3_folder}/{file_name}',
                    Filename=file_path
                )
                uploaded_count += 1
        print(f"Successfully uploaded {uploaded_count} files to S3")
    except Exception as e:
        print(f"Error uploading to S3: {str(e)}")
def mrun_upload_large_context_files_to_s3():
    pass
#if __name__ == "__main__":
    upload_large_context_files_to_s3()


# ===== API GATEWAY SECTION OF FILE primary/aws.py =====

### AWS API KEYS
def create_api_key(key_name, description="API key for Lambda function"):
    """
    Create an API key in API Gateway.
    
    :param key_name: Name of the API key
    :param description: Description of the API key
    :return: API key ID and value
    """
    api_client = boto3.client('apigateway')
    
    try:
        response = api_client.create_api_key(
            name=key_name,
            description=description,
            enabled=True
        )
        print(f"Created API key - name: {key_name}  id: {response['id']}, value: {response['value']}")
        return {
            'id': response['id'],
            'value': response['value']
        }
    except ClientError as e:
        print(f"Error creating API key: {e}")
        return None

def create_usage_plan(plan_name, rate_limit=10, burst_limit=20, quota_limit=1000, quota_period='DAY'):
    """
    Create a usage plan in API Gateway.
    
    :param plan_name: Name of the usage plan
    :param rate_limit: Requests per second
    :param burst_limit: Maximum concurrent requests
    :param quota_limit: Number of requests per period
    :param quota_period: Period for quota (DAY, WEEK, or MONTH)
    :return: Usage plan ID
    """
    api_client = boto3.client('apigateway')
    
    try:
        response = api_client.create_usage_plan(
            name=plan_name,
            description=f"Usage plan for {plan_name}",
            throttle={
                'rateLimit': rate_limit,
                'burstLimit': burst_limit
            },
            quota={
                'limit': quota_limit,
                'period': quota_period
            }
        )
        print(f"Created usage plan: {plan_name}")
        return response['id']
    except ClientError as e:
        print(f"Error creating usage plan: {e}")
        return None
USAGE_PLAN_NAME_DEMO = "usage-plan-demo"
API_KEY_NAME_DEMO = "api-key-demo"
API_KEY_ID_DEMO = "hpn6ghxmk8"
def mrun_create_usage_plan():
    pass
#if __name__ == "__main__":
    create_usage_plan(USAGE_PLAN_NAME_DEMO, rate_limit=10, burst_limit=20, quota_limit=1000, quota_period='DAY')

def get_usage_plan_id_by_name(plan_name):
    """
    Get a usage plan ID by its name.
    
    :param plan_name: Name of the usage plan
    :return: Usage plan ID if found, None otherwise
    """
    api_client = boto3.client('apigateway')
    
    try:
        # Get all usage plans
        response = api_client.get_usage_plans()
        
        # Find the plan with matching name
        for plan in response.get('items', []):
            if plan['name'] == plan_name:
                return plan['id']
        
        print(f"No usage plan found with name: {plan_name}")
        return None
        
    except ClientError as e:
        print(f"Error getting usage plan: {e}")
        return None

def associate_api_key_with_usage_plan(usage_plan_id, api_key_id):
    """
    Associate an API key with a usage plan.
    
    :param usage_plan_id: ID of the usage plan
    :param api_key_id: ID of the API key
    :return: True if successful, False otherwise
    """
    api_client = boto3.client('apigateway')
    
    try:
        api_client.create_usage_plan_key(
            usagePlanId=usage_plan_id,
            keyId=api_key_id,
            keyType='API_KEY'
        )
        print(f"Associated API key ID: {api_key_id} with usage plan ID: {usage_plan_id}")
        return True
    except ClientError as e:
        print(f"Error associating API key with usage plan: {e}")
        return False
def mrun_create_api_key_and_associate_with_usage_plan():
    pass
#if __name__ == "__main__":
    # Create new API key
    new_api_key = create_api_key(
        API_KEY_NAME_DEMO, 
        f"API key for demo phase that will be exposed in client-side javascript"
    )
    
    if new_api_key:
        # Get usage plan ID
        usage_plan_id = get_usage_plan_id_by_name(USAGE_PLAN_NAME_DEMO)
        if usage_plan_id:
            # Associate API key with usage plan
            associate_api_key_with_usage_plan(usage_plan_id, new_api_key['id'])
        else:
            print("Failed to get usage plan ID")
    else:
        print("Failed to create API key")

# NOTE: changed 3-26 for 'dev' stage instead of old 'api' stage
def associate_usage_plan_with_api_gateway(usage_plan_id, rest_api_id, stage):
    """
    Associate a usage plan with an API Gateway stage.
    
    :param usage_plan_id: ID of the usage plan
    :param rest_api_id: ID of the REST API Gateway
    :param stage: API stage name (dev or prod)
    :return: True if successful, False otherwise
    """
    api_client = boto3.client('apigateway')
    
    try:
        api_client.update_usage_plan(
            usagePlanId=usage_plan_id,
            patchOperations=[
                {
                    'op': 'add',
                    'path': '/apiStages',
                    'value': f'{rest_api_id}:{stage}'
                }
            ]
        )
        print(f"Associated usage plan {usage_plan_id} with API Gateway {rest_api_id} stage {stage}")
        return True
    except ClientError as e:
        print(f"Error associating usage plan with API Gateway: {e}")
        return False

def enable_api_key_requirement(rest_api_id, resource_id, http_method):
    """
    Enable API key requirement for a specific API method.
    
    :param rest_api_id: ID of the REST API
    :param resource_id: ID of the API resource
    :param http_method: HTTP method (GET, POST, etc.)
    :return: True if successful, False otherwise
    """
    api_client = boto3.client('apigateway')
    
    try:
        api_client.update_method(
            restApiId=rest_api_id,
            resourceId=resource_id,
            httpMethod=http_method,
            patchOperations=[
                {
                    'op': 'replace',
                    'path': '/apiKeyRequired',
                    'value': 'true'
                }
            ]
        )
        print(f"Enabled API key requirement for {http_method} method")
        return True
    except ClientError as e:
        print(f"Error enabling API key requirement: {e}")
        return False
def mrun_enable_api_key_requirement():
    pass
#if __name__ == "__main__":
    rest_api_id = "[API-GATEWAY-ID]"
    resource_id = "gawjouz445"
    http_method = "GET"
    enable_api_key_requirement(rest_api_id, resource_id, http_method)

def get_api_gateway_and_resource_ids(api_gateway_name, http_method='POST', verbose=False):
    """
    Get API Gateway ID and resource ID.
    Finds the API Gateway by name, not by hardcoded ID.
    
    :param api_gateway_name: str, name of the API Gateway
    :param http_method: str, HTTP method to check
    :param verbose: bool, if True prints diagnostic information
    :return tuple: (rest_api_id, resource_id)
    """
    api_client = boto3.client('apigateway')
    
    # Get all APIs
    apis = api_client.get_rest_apis()
    if verbose:
        print(f"Found {len(apis['items'])} API Gateways")
    
    # Find the API by name
    matching_apis = [api for api in apis['items'] if api['name'] == api_gateway_name]
    
    if not matching_apis:
        print(f"No API Gateway found with name: {api_gateway_name}")
        return None, None
    
    if len(matching_apis) > 1:
        print(f"Multiple API Gateways found with name '{api_gateway_name}':")
        for api in matching_apis:
            print(f"  ID: {api['id']}, Created: {api.get('createdDate', 'unknown')}")
        raise ValueError(f"Multiple API Gateways found with name '{api_gateway_name}'. Please ensure unique names.")
    
    rest_api_id = matching_apis[0]['id']
    
    if verbose:
        print(f"Using API Gateway '{api_gateway_name}' with ID: {rest_api_id}")
    
    # Get resources
    resources = api_client.get_resources(restApiId=rest_api_id)
    
    # Find the resource for the root path (typically /api/{lambda-name})
    resource_id = None
    for resource in resources['items']:
        # Look for /api/{lambda-name} or just /
        path = resource.get('path', '')
        if path == f"/api/{api_gateway_name}" or path.endswith(f"/{api_gateway_name}"):
            resource_id = resource['id']
            break
    
    if not resource_id:
        # If no specific resource was found, try to find the root resource 
        # that has a POST method
        for resource in resources['items']:
            try:
                api_client.get_method(
                    restApiId=rest_api_id,
                    resourceId=resource['id'],
                    httpMethod=http_method
                )
                resource_id = resource['id']
                break
            except:
                continue
    
    if not resource_id:
        print(f"No resource found with {http_method} method for API: {api_gateway_name}")
        return rest_api_id, None
    
    return rest_api_id, resource_id
def mrun_get_api_gateway_and_resource_ids():
    pass
#if __name__ == "__main__":
    api_gateway_name = "hmac-hash"
    print(get_api_gateway_and_resource_ids(api_gateway_name))

def rename_api_gateway(rest_api_id, new_name):
    """
    Rename an API Gateway.
    
    :param rest_api_id: str, ID of the REST API
    :param new_name: str, New name for the API Gateway
    """
    api_client = boto3.client('apigateway')
    api_client.update_rest_api(
        restApiId=rest_api_id,
        patchOperations=[
            {
                'op': 'replace',
                'path': '/name',
                'value': new_name
            }
        ]
    )
    
    # Lookup the name after rename to confirm the change
    response = api_client.get_rest_api(restApiId=rest_api_id)
    current_name = response.get('name', 'unknown')
    print(f"API Gateway renamed: ID {rest_api_id} is now named '{current_name}'")
def mrun_rename_api_gateway():
    pass
#if __name__ == "__main__":
    rename_api_gateway("[API-GATEWAY-ID]", "hmac-hash-prod")
def rename_api_gateway_stage(rest_api_id, old_stage_name, new_stage_name):
    """
    Rename a stage of an API Gateway.
    
    :param rest_api_id: str, ID of the REST API
    :param old_stage_name: str, Current name of the stage
    :param new_stage_name: str, New name for the stage
    :return: bool, True if successful, False otherwise
    """
    api_client = boto3.client('apigateway')
    
    try:
        # Get the current stage to copy its configuration
        response = api_client.get_stage(
            restApiId=rest_api_id,
            stageName=old_stage_name
        )
        
        # Extract the current deployment ID and other settings
        deployment_id = response.get('deploymentId')
        
        # Build parameters for create_stage
        params = {
            'restApiId': rest_api_id,
            'stageName': new_stage_name,
            'deploymentId': deployment_id,
            'description': response.get('description', f'Renamed from {old_stage_name}'),
            'variables': response.get('variables', {})
        }
        
        # Only include cache parameters if caching is enabled
        if response.get('cacheClusterEnabled', False):
            params['cacheClusterEnabled'] = True
            params['cacheClusterSize'] = response.get('cacheClusterSize', '0.5')
        else:
            params['cacheClusterEnabled'] = False
        
        # Create a new stage with the same deployment ID and settings
        api_client.create_stage(**params)
        
        # Delete the old stage
        api_client.delete_stage(
            restApiId=rest_api_id,
            stageName=old_stage_name
        )
        
        print(f"API Gateway stage renamed: '{old_stage_name}' to '{new_stage_name}' for API {rest_api_id}")
        return True
        
    except Exception as e:
        print(f"Error renaming API Gateway stage: {e}")
        return False
def mrun_rename_api_gateway_stage():
    pass
#if __name__ == "__main__":
    rename_api_gateway_stage("[API-GATEWAY-ID]", "api", "prod")

### DEPRECATED OLD LOGGING FUNCTIONS 4-6-25
def generate_deployment_log(api_gateway_name, stage, deployment_type, validation_logger=None):
    """
    Generate a comprehensive deployment log that includes validation results and API state.
    
    :param api_gateway_name: str, name of the API Gateway
    :param stage: str, deployment stage ('dev' or 'prod')
    :param validation_logger: ValidationLogger object or None
    :param deployment_type: str, type of deployment
    :return: str, path to the generated log file
    """
    # Create directory structure
    base_log_dir = "logs/aws_deployments"
    stage_log_dir = f"{base_log_dir}/{stage}"
    os.makedirs(stage_log_dir, exist_ok=True)
    
    # Create timestamp
    timestamp = get_current_datetime_filefriendly()
    log_file = f"{stage_log_dir}/{api_gateway_name}_{timestamp}.md"
    
    with open(log_file, 'w', encoding='utf-8') as f:
        # Write header
        f.write(f"# Deployment: {api_gateway_name} - {stage}\n")
        f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Type: {deployment_type}\n\n")
        
        # Add validation results if available
        if validation_logger:
            f.write("## Validation Changes\n")
            f.write("```\n")
            f.write(validation_logger.get_summary())
            f.write("\n```\n\n")
        
        # Generate API state report
        f.write("## API State After Deployment\n\n")
        
        # Get REST API ID
        api_client = boto3.client('apigateway')
        rest_api_id = None
        try:
            apis = api_client.get_rest_apis()
            api_matches = [api for api in apis['items'] if api['name'] == api_gateway_name]
            if api_matches:
                rest_api_id = api_matches[0]['id']
        except Exception as e:
            f.write(f"Error getting API ID: {str(e)}\n\n")
        
        if rest_api_id:
            # Get deployment info
            deployment_info = get_api_stage_current_config(rest_api_id, stage)
            
            # Write deployment info
            f.write(f"### Active Deployment\n")
            deployment = deployment_info['deployment']
            f.write(f"ID: {deployment.get('id', 'None')}\n")
            f.write(f"Date: {deployment.get('date', 'Unknown')}\n")
            f.write(f"Description: {deployment.get('description', 'None')}\n\n")
            
            # Write Lambda info
            lambda_info = deployment_info['lambda']
            f.write(f"### Lambda Function\n")
            if lambda_info.get('name'):
                f.write(f"Name: {lambda_info.get('name')}\n")
                f.write(f"Runtime: {lambda_info.get('runtime', 'Unknown')}\n")
                f.write(f"Memory: {lambda_info.get('memory', 'Unknown')} MB\n")
                f.write(f"Timeout: {lambda_info.get('timeout', 'Unknown')}s\n")
                if 'last_updated' in lambda_info:
                    f.write(f"Last Updated: {lambda_info['last_updated']}\n")
            else:
                f.write("No Lambda function found\n")
            f.write("\n")
            
            # Add validation models
            validation_models = get_api_validation_models(rest_api_id)
            f.write(f"### Request Validation Models: {len(validation_models)}\n")
            if not validation_models:
                f.write("No models configured\n\n")
            else:
                for model_name, schema, content_type, used_by in validation_models:
                    f.write(f"#### Model: {model_name}\n")
                    if used_by:
                        f.write(f"Used by: {', '.join(used_by)}\n")
                    f.write(f"Content Type: {content_type}\n")
                    f.write("```json\n")
                    try:
                        formatted_schema = json.dumps(schema, indent=2)
                        f.write(formatted_schema)
                    except (TypeError, ValueError):
                        if isinstance(schema, str):
                            f.write(schema)
                    f.write("\n```\n\n")
        else:
            f.write("API Gateway not found or could not retrieve state information.\n\n")
    
    print(f"Comprehensive deployment log written to: {log_file}")
    return log_file
def log_deployment_to_history(api_gateway_name, stage, deployment_type="API Gateway deployment", detailed_log_path=None):
    """
    Log a deployment to the deployment history file with a link to the detailed log.
    
    :param api_gateway_name: str, name of the API Gateway
    :param stage: str, deployment stage ('dev' or 'prod')
    :param deployment_type: str, type of deployment (for documentation)
    :param detailed_log_path: str, path to the detailed log file (optional)
    :return: bool, True if successful, False otherwise
    """
    try:
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_file = os.path.join(log_dir, "web/aws_chalice/chalicelib_mirror_deploy_log.md")
        
        # Ensure the log file exists with proper headings
        if not os.path.exists(log_file):
            with open(log_file, 'w') as f:
                f.write("# prod\n\n# dev\n\n")
        
        # Format timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Read existing content
        with open(log_file, 'r') as f:
            content = f.read()
        
        # Prepare the log entry
        log_entry = f"{timestamp}  {api_gateway_name}  ({deployment_type})"
        
        # Add link to detailed log if provided
        if detailed_log_path:
            # Create a relative path from the log file to the detailed log
            rel_path = os.path.relpath(detailed_log_path, os.path.dirname(log_file))
            log_entry += f" [Details]({rel_path})"
        
        # Insert new entry after the appropriate heading
        if stage.lower() == 'prod':
            marker = "# prod"
        else:
            marker = "# dev"
            
        # Find the marker position and insert after it
        marker_pos = content.find(marker)
        if marker_pos >= 0:
            insert_pos = marker_pos + len(marker) + 1  # +1 for newline
            new_content = content[:insert_pos] + f"{log_entry}\n" + content[insert_pos:]
            
            # Write updated content
            with open(log_file, 'w') as f:
                f.write(new_content)
                
            print(f"Deployment logged to history: {log_file}")
            return True
        else:
            print(f"⚠️ Warning: Could not find section marker '{marker}' in log file")
            return False
            
    except Exception as e:
        print(f"Warning: Could not log deployment to history: {e}")
        return False
def mtest_log_deployment_to_history():
    pass
#if __name__ == "__main__":
    log_deployment_to_history("fake-out", "dev", "API deployment test") 


def create_api_gateway_deployment(rest_api_id, stage, description=""):  # updated 3-29 for dev/prod
    """
    Create a deployment for the API Gateway to apply changes.
    
    :param rest_api_id: ID of the REST API
    :param stage: Name of the stage to deploy to, i.e. 'dev' or 'prod'
    :return: True if successful, False otherwise
    """
    api_client = boto3.client('apigateway')
    
    try:
        api_client.create_deployment(
            restApiId=rest_api_id,
            stageName=stage
        )
        print(f"Created new deployment for stage: {stage}")

        return True
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_msg = e.response["Error"]["Message"]
        
        if error_code == "BadRequestException":
            print(f"Invalid request parameters: {error_code} - {error_msg}")
        elif error_code == "UnauthorizedException":
            print(f"Not authorized to create deployment: {error_code} - {error_msg}")
        elif error_code == "NotFoundException":
            print(f"API Gateway or stage not found: {error_code} - {error_msg}")
        elif error_code == "TooManyRequestsException":
            print(f"API request throttled (try again later): {error_code} - {error_msg}")
        elif error_code == "ConflictException":
            print(f"Deployment conflict: {error_code} - {error_msg}")
        else:
            print(f"Error creating deployment: {error_code} - {error_msg}")
        return False
def mrun_create_api_gateway_deployment():  # NEED TO TRY updated 3-16 for dev/prod
    pass
#if __name__ == "__main__":
    rest_api_id, _ = get_api_gateway_and_resource_ids("hmac-hash")
    stage = "dev"
    create_api_gateway_deployment(rest_api_id, stage)

# NOTE: changed 3-16 for 'dev' stage instead of old 'api' stage
def setup_api_security(api_gateway_name, api_key_id=None, usage_plan_name=USAGE_PLAN_NAME_DEMO, stage='dev', http_method='POST'):  # NEED TO TEST updated 3-16 for dev/prod
    """
    Set up API security for a Lambda function. Assumes the stage is 'dev'.
    
    Assumes:
    - API Gateway name matches the lambda_function_base_name
    - Full Lambda function name is {lambda_function_base_name}-{stage}
    - Example: api_gateway_name='testapp', stage='dev' → Lambda name='testapp-dev'
    
    :param api_gateway_name: Base name of the Lambda function (e.g., 'testapp')
    :param usage_plan_name: Name of the usage plan to associate with the API key (default: USAGE_PLAN_NAME_DEMO)
    :param stage: Stage suffix for Lambda function name (default: 'dev')
    :param http_method: HTTP method to secure (default: 'POST')
    :param api_key_id: Optional existing API key ID to use
    :return: Dictionary containing API key and usage plan details
    """
    # Get REST API ID and resource ID programmatically
    rest_api_id, resource_id = get_api_gateway_and_resource_ids(api_gateway_name, http_method)
    
    if not rest_api_id or not resource_id:
        print(f"Failed to get API Gateway IDs for {api_gateway_name}")
        return None
        
    print(f"Found API Gateway IDs for {api_gateway_name}:")
    print(f"REST API ID: {rest_api_id}")
    print(f"Resource ID: {resource_id}")
    
    # Use existing API key if provided, otherwise create a new one
    if api_key_id:
        print(f"Using existing API key ID: {api_key_id}")
        api_key = {'id': api_key_id}
    else:
        # Full Lambda function name
        lambda_function_name = api_gateway_name + '-' + stage
        
        # Create API key
        api_key_name = f"{lambda_function_name}_key_{get_current_datetime_filefriendly()}"
        api_key = create_api_key(
            api_key_name,
            f"API key for {lambda_function_name}"
        )
        if not api_key:
            print("Failed to create API key")
            return None
    
    # Get usage plan ID from name
    usage_plan_id = get_usage_plan_id_by_name(usage_plan_name)
    if not usage_plan_id:
        print(f"Failed to find usage plan with name: {usage_plan_name}")
        return None
    print(f"Using Usage Plan Name: {usage_plan_name} with Usage PlanID: {usage_plan_id}")

    # Associate API key with usage plan
    if not associate_api_key_with_usage_plan(usage_plan_id, api_key['id']):
        print("Failed to associate API key with usage plan")
        return None
    
    # Associate usage plan with API Gateway stage
    if not associate_usage_plan_with_api_gateway(usage_plan_id, rest_api_id, stage):
        print("Failed to associate usage plan with API Gateway stage")
        return None
   
    # Enable API key requirement for the specified method
    if not enable_api_key_requirement(rest_api_id, resource_id, http_method):
        print("Error: Failed to enable API key requirement")
        return None
    
    # Create a new deployment to apply changes
    if not create_api_gateway_deployment(rest_api_id):
        print("Error: Failed to deploy API changes")
        return None
    
    return {
        'api_key': api_key,
        'usage_plan_id': usage_plan_id
    }
# NOTE: changed 3-16 for 'dev' stage instead of old 'api' stage
def mrun_setup_api_security():
    pass
#if __name__ == "__main__":
    api_gateway_name = "hash-store"
    result = setup_api_security(api_gateway_name)
    
    if result:
        print("API security setup successful!")
        print(f"API Key: {result['api_key']['value']}")
        print(f"API Key ID: {result['api_key']['id']}")
        print(f"Usage Plan ID: {result['usage_plan_id']}")
    else:
        print("API security setup failed!")

def list_api_keys(name_prefix=None, show_api_key=False):
    """
    List all API keys with their associated usage plans and APIs.
    
    :param name_prefix: Optional prefix to filter API keys by name
    :param show_api_key: If True, show full API key value. If False, show only first 5 chars
    :return: List of API key details
    """
    api_client = boto3.client('apigateway')
    now_datetime = get_current_datetime_filefriendly()
    
    # Get all REST APIs
    apis = api_client.get_rest_apis()['items']
    print(f"Found {len(apis)} API Gateways")

    try:
        # Get API keys
        if name_prefix:
            print(f"\nListing API keys with prefix: {name_prefix}")
            response = api_client.get_api_keys(
                nameQuery=name_prefix,
                includeValues=True
            )
        else:
            print("\nListing all API keys:")
            response = api_client.get_api_keys(includeValues=True)
        
        keys = response['items']
        print(f"\n## {now_datetime}  Found {len(keys)} API keys:")
        
        # Dictionary to store usage plans and their associated APIs
        usage_plans_info = {}

        # For each API key, get its usage plans and directly associated APIs
        for key in keys:
            print("\n----------------------------------------")
            print(f"### API Key Name: {key['name']}")
            print(f"API Key ID: {key['id']}")
            api_key_value = key.get('value', 'N/A')
            if not show_api_key and api_key_value != 'N/A':
                api_key_value = f"{api_key_value[:5]}..."
            print(f"API Key Value: {api_key_value}")
            print(f"Enabled: {key.get('enabled', False)}")
            print(f"Created Date:      {key.get('createdDate', 'N/A')}")
            print(f"Last Updated Date: {key.get('lastUpdatedDate', 'N/A')}")
            
            # Get directly associated APIs
            try:
                api_stages_response = api_client.get_api_key(apiKey=key['id'], includeValue=False)
                api_stages = api_stages_response.get('stageKeys', [])
                
                if api_stages:
                    print("Directly Associated APIs:")
                    for stage in api_stages:
                        rest_api_id, stage_name = stage.split(':')
                        api_details = api_client.get_rest_api(restApiId=rest_api_id)
                        print(f"  - API Gateway Name: {api_details['name']}")
                        print(f"  - API Gateway ID: {rest_api_id}")
                        print(f"    Stage: {stage_name}")
                else:
                    print("No APIs directly associated with this API key.")
                    
            except ClientError as e:
                print(f"Error getting directly associated APIs for key {key['id']}: {e}")
            
            # Get usage plans for this API key
            try:
                usage_plans_response = api_client.get_usage_plans(keyId=key['id'])
                usage_plans = usage_plans_response.get('items', [])
                
                if usage_plans:
                    print("Associated Usage Plans:")
                    for plan in usage_plans:
                        print(f"  Usage Plan: {plan['name']}")
                        print(f"  Usage Plan ID: {plan['id']}")
                        
                        # Store usage plan info for later
                        if plan['id'] not in usage_plans_info:
                            usage_plans_info[plan['id']] = {
                                'name': plan['name'],
                                'apiStages': plan.get('apiStages', [])
                            }
                else:
                    print("\nNo usage plans associated with this API key!")
                    
            except ClientError as e:
                print(f"\nError getting usage plans for key {key['id']}: {e}")
        
        # Print all usage plans and their associated APIs
        print("\n----------------------------------------")
        print("Usage Plans and Associated APIs:")
        for plan_id, plan_info in usage_plans_info.items():
            print(f"\nUsage Plan: {plan_info['name']}")
            print(f"Usage Plan ID: {plan_id}")
            
            # Get detailed usage plan info
            try:
                plan_details = api_client.get_usage_plan(usagePlanId=plan_id)
                
                # Print throttle settings
                throttle = plan_details.get('throttle', {})
                if throttle:
                    print("Throttling:")
                    print(f"  Rate Limit: {throttle.get('rateLimit', 'Not set')} requests per second")
                    print(f"  Burst Limit: {throttle.get('burstLimit', 'Not set')} requests")
                
                # Print quota settings  
                quota = plan_details.get('quota', {})
                if quota:
                    print("Quota:")
                    print(f"  Limit: {quota.get('limit', 'Not set')} requests")
                    print(f"  Period: {quota.get('period', 'Not set')}")
                    print(f"  Offset: {quota.get('offset', 'Not set')}")
                
                # Print associated APIs
                if plan_info['apiStages']:
                    print(f"\nAssociated API Gateways:")
                    for api_stage in plan_info['apiStages']:
                        try:
                            api_details = api_client.get_rest_api(restApiId=api_stage['apiId'])
                            # Get resources and methods for this API
                            resources = api_client.get_resources(restApiId=api_stage['apiId'])
                            print(f"\n  {api_details['name']:<20} ID: {api_stage['apiId']}  Stage: {api_stage['stage']}")
                            
                            for resource in resources['items']:
                                if 'resourceMethods' in resource:
                                    for method, method_info in resource['resourceMethods'].items():
                                        # Get method details to check if API key is required
                                        method_details = api_client.get_method(
                                            restApiId=api_stage['apiId'],
                                            resourceId=resource['id'],
                                            httpMethod=method
                                        )
                                        api_key_required = method_details.get('apiKeyRequired', False)
                                        key_requirement = "API key required" if api_key_required else "None"
                                        print(f"      {method:<10}: {key_requirement}")
                        except ClientError as e:
                            print(f"Error getting API details for {api_stage['apiId']}: {e}")
                else:
                    print("No APIs associated with this usage plan.")
                    
            except ClientError as e:
                print(f"Error getting usage plan details for {plan_id}: {e}")

        # Get all associated API IDs from usage plans
        associated_api_ids = set()
        for plan_info in usage_plans_info.values():
            for api_stage in plan_info.get('apiStages', []):
                associated_api_ids.add(api_stage['apiId'])

        # Print unassociated APIs
        print("\n----------------------------------------")
        print("Unassociated API Gateways (not in any usage plan):")
        unassociated_count = 0
        for api in apis:
            if api['id'] not in associated_api_ids:
                unassociated_count += 1
                print(f"\n  {api['name']:<20} ID: {api['id']}")
                try:
                    # Get resources and methods for this API
                    resources = api_client.get_resources(restApiId=api['id'])
                    for resource in resources['items']:
                        if 'resourceMethods' in resource:
                            for method in resource['resourceMethods']:
                                # Get method details to check if API key is required
                                method_details = api_client.get_method(
                                    restApiId=api['id'],
                                    resourceId=resource['id'],
                                    httpMethod=method
                                )
                                api_key_required = method_details.get('apiKeyRequired', False)
                                key_requirement = "API key required" if api_key_required else "None"
                                print(f"      {method:<10}: {key_requirement}")
                except ClientError as e:
                    print(f"    Error getting API details: {e}")

        if unassociated_count == 0:
            print("  None found - all API Gateways are associated with usage plans")
        
        return keys
    
    except ClientError as e:
        print(f"\nError listing API keys:")
        print(f"Error code: {e.response['Error']['Code']}")
        print(f"Error message: {e.response['Error']['Message']}")
        return None
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        return None
def mtest_list_api_keys():
    pass
#if __name__ == "__main__":
    list_api_keys()

def delete_api_key(key_id=None):
    """
    Delete an API key by its ID. If no key_id provided, prompts user for input.
    
    :param key_id: ID of the API key to delete (optional)
    :return: True if successful, False otherwise
    """
    api_client = boto3.client('apigateway')
    
    if not key_id:
        key_id = input("Enter the ID of the API key to delete (or press Enter to skip): ")
        if not key_id:
            return False
            
    try:
        api_client.delete_api_key(apiKey=key_id)
        print(f"Deleted API key: {key_id}")
        return True
    except ClientError as e:
        print(f"Error deleting API key: {e}")
        return False
def mrun_delete_api_key():
    pass
#if __name__ == "__main__":
    delete_api_key(key_id='hpn6ghxmk8')  # get from list_api_keys()
    list_api_keys()

def test_api_key(api_key, input_text="test@example.com", show_command=False, verbose=False):
    """
    Test an API key by making a curl request to the HMAC hash endpoint.
    """    
    curl_command = [
        'curl',
        '-s',  # Silent mode
    ]
    
    if verbose:
        curl_command.append('-v')  # Add verbose flag, but NOT -i
        
    curl_command.extend([
        '-X', 'POST',
        'https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/generate-hash',
        '-H', 'Content-Type: application/json',
        '-H', f'x-api-key: {api_key}',
        '-d', json.dumps({"input_text": input_text})
    ])
    
    try:
        result = subprocess.run(curl_command, capture_output=True, text=True)
        
        if show_command:
            safe_command = ' '.join(curl_command).replace(api_key, f"{api_key[:5]}...")
            print(f"Executed command: {safe_command}")
        
        # Only print debug info if verbose
        if verbose and result.stderr:
            print(f"STDERR: {result.stderr}")
            
        try:
            response_json = json.loads(result.stdout)
            if "message" in response_json and "forbidden" in response_json["message"].lower():
                return {"error": "403 Forbidden"}
            return response_json
        except json.JSONDecodeError:
            if "403" in result.stderr or "forbidden" in result.stderr.lower():
                return {"error": "403 Forbidden"}
            if verbose:
                print(f"Raw response: {result.stdout}")
            return {"error": "Failed to parse response"}
            
    except subprocess.SubprocessError as e:
        return {"error": f"Failed to execute curl command: {str(e)}"}
def mtest_test_api_key():
    pass
#if __name__ == "__main__":
    result = test_api_key(API_KEY_ID_DEMO)
    print("\nAPI Test Result:")
    print(json.dumps(result, indent=2))

# NOTE: changed 3-26 for 'dev' stage instead of old 'api' stage
def detach_usage_plan_from_api(usage_plan_id, api_id, stage):
    """
    Remove an API stage from a usage plan.
    
    :param usage_plan_id: ID of the usage plan
    :param api_id: ID of the API to detach
    :param stage: API stage name (default: 'api')
    :return: True if successful, False otherwise
    """
    api_client = boto3.client('apigateway')
    
    try:
        # Remove the API stage from the usage plan
        api_client.update_usage_plan(
            usagePlanId=usage_plan_id,
            patchOperations=[
                {
                    'op': 'remove',
                    'path': f'/apiStages',
                    'value': f'{api_id}:{stage}'
                }
            ]
        )
        print(f"Detached API {api_id} from usage plan {usage_plan_id}")
        return True
    except ClientError as e:
        print(f"Error detaching API from usage plan: {e}")
        return False
def mrun_detach_usage_plan_from_api():
    pass
#if __name__ == "__main__":
    """Didn't actually run this 12-20 RT"""
    usage_plan_id = 'djv4a9'  # from demo usage plan, can get from list_api_keys()
    apis_to_detach = [
        '[API-GATEWAY-ID]',  # send-email
        '[API-GATEWAY-ID]',  # vrag-llm
        '[API-GATEWAY-ID]',  # qrag-llm
        '[API-GATEWAY-ID]',  # qrag-routing
        '[API-GATEWAY-ID]',  # hash-store
    ]
    for api_id in apis_to_detach:
        detach_usage_plan_from_api(usage_plan_id, api_id, stage='dev')
    list_api_keys()

### AWS WAF
def quick_waf_test():
    """Quick test to verify WAF is connected"""
    api_key = AWS_API_KEY_DEMO
    
    print("\nSending 5 test requests...")
    for i in range(5):
        result = test_api_key(api_key, f"test{i}@example.com")
        print(f"Request {i+1}: {'OK' if 'hash' in result else 'Failed - ' + str(result.get('error', 'Unknown error'))}")
        sleep(1)  # 1 second delay between requests
def mrun_quick_waf_test():
    pass
#if __name__ == "__main__":
    quick_waf_test()    

def test_rate_limits():
    """
    Quick test of WAF and API Gateway rate limits using the HMAC hash endpoint
    """
    api_key = AWS_API_KEY_DEMO
    
    print("\nTesting API Gateway throttling (10 req/sec)...")
    throttle_count = 0
    waf_block_count = 0
    
    # Test 1: API Gateway Throttling
    print("Sending 30 requests rapidly (expect throttling after ~10)...")
    for i in range(30):
        result = test_api_key(api_key, f"test{i}@example.com", print_command=(i==0))
        
        # Check for specific error messages
        error = str(result.get('error', ''))
        if 'throttling' in error.lower() or 'throttle' in error.lower():
            status = 'THROTTLED'
            throttle_count += 1
        elif '403' in error:
            status = 'WAF BLOCKED'
            waf_block_count += 1
        elif 'hash' in result:
            status = 'OK'
        else:
            status = f"OTHER ERROR: {error}"
            
        print(f"Request {i+1:3d}: {status}")
        sleep(0.01)
    
    print(f"\nThrottle Summary:")
    print(f"Successful requests: {30 - throttle_count - waf_block_count}")
    print(f"Throttled requests: {throttle_count}")
    print(f"WAF blocked requests: {waf_block_count}")
    
    print("\nWaiting 10 seconds to let limits reset...")
    sleep(10)
    
    # Test 2: WAF Rate Limit
    print("\nTesting WAF rate limit (100 req/5 min)...")
    throttle_count = 0
    waf_block_count = 0
    
    print("Sending 120 requests rapidly (expect WAF blocks after ~100)...")
    for i in range(120):
        result = test_api_key(api_key, f"test{i}@example.com", print_command=(i==0))
        
        error = str(result.get('error', ''))
        if 'throttling' in error.lower() or 'throttle' in error.lower():
            status = 'THROTTLED'
            throttle_count += 1
        elif '403' in error:
            status = 'WAF BLOCKED'
            waf_block_count += 1
        elif 'hash' in result:
            status = 'OK'
        else:
            status = f"OTHER ERROR: {error}"
            
        print(f"Request {i+1:3d}: {status}")
        sleep(0.05)  # Slightly longer delay to ensure WAF counting
    
    print(f"\nWAF Test Summary:")
    print(f"Successful requests: {120 - throttle_count - waf_block_count}")
    print(f"Throttled requests: {throttle_count}")
    print(f"WAF blocked requests: {waf_block_count}")
def mrun_test_rate_limits():
    pass
#if __name__ == "__main__":
    test_rate_limits()
def test_waf_limit_old():
    """
    Aggressive test focusing only on WAF rate limit with detailed diagnostics
    """
    api_key = AWS_API_KEY_DEMO
    success_count = 0
    block_count = 0
    other_errors = 0
    
    print("\nTesting WAF rate limit (10 req/5 min)...")
    print("Sending 20 requests rapidly...")
    
    # Send initial burst to exceed rate limit
    for i in range(20):
        result = test_api_key(api_key, f"test{i}@example.com", show_command=(i==0))
        
        error = str(result.get('error', ''))
        if '403' in error or 'Forbidden' in error:
            status = 'WAF BLOCKED'
            block_count += 1
        elif 'hash' in result:
            status = 'OK'
            success_count += 1
        else:
            status = f"ERROR: {error}"
            other_errors += 1
                
        print(f"Request {i+1:3d}: {status}")
        # No sleep to send requests rapidly

    # Wait for WAF to start enforcing the block
    print("\nWaiting 2 minutes for WAF to enforce rate limit...")
    time.sleep(120)  # Wait 2 minutes

    print("\nSending 5 more requests to test if WAF is blocking...")
    for i in range(5):
        result = test_api_key(api_key, f"test_extra{i}@example.com")
        
        error = str(result.get('error', ''))
        if '403' in error or 'Forbidden' in error:
            status = 'WAF BLOCKED'
            block_count += 1
        elif 'hash' in result:
            status = 'OK'
            success_count += 1
        else:
            status = f"ERROR: {error}"
            other_errors += 1
                
        print(f"Extra Request {i+1}: {status}")

    print(f"\nWAF Test Summary:")
    print(f"Successful requests: {success_count}")
    print(f"Blocked requests: {block_count}")
    if other_errors > 0:
        print(f"Other errors: {other_errors}")

def test_waf_limit(initial_rapid_requests=20, wait_minutes=2, post_wait_requests=5, verbose=False):
    """
    Aggressive test focusing only on WAF rate limit with detailed diagnostics
    
    :param verbose: If True, prints detailed debugging info including full responses
    :param initial_rapid_requests: Number of initial rapid requests to send
    :param wait_minutes: Minutes to wait after initial requests (0 to skip wait and post-wait requests)
    :param post_wait_requests: Number of requests to send after waiting
    """
    api_key = AWS_API_KEY_DEMO
    success_count = 0
    block_count = 0
    other_errors = 0
    
    if verbose:
        print("\nTesting WAF rate limit...")
        print(f"Sending {initial_rapid_requests} requests rapidly...")
    
    start_time = time.time()
    for i in range(initial_rapid_requests):
        result = test_api_key(api_key, f"test{i}@example.com", 
                            show_command=(i==0 and verbose),
                            verbose=verbose)
        
        error = str(result.get('error', ''))
        if '403' in error or 'forbidden' in error.lower():
            status = 'WAF BLOCKED'
            block_count += 1
        elif 'hash' in result:
            status = 'OK'
            success_count += 1
        else:
            status = error if verbose else 'ERROR'
            other_errors += 1
                
        print(f"Request {i+1:3d}: {status}")

    elapsed_time = time.time() - start_time
    if wait_minutes > 0:
        if verbose:
            print(f"\nSent {initial_rapid_requests} requests in {elapsed_time:.2f} seconds")
            print(f"Results: {success_count} successful, {block_count} blocked, {other_errors} errors")
            print(f"\nWaiting {wait_minutes} minutes for WAF to enforce rate limit...")
        time.sleep(wait_minutes * 60)

        if verbose:
            print(f"\nSending {post_wait_requests} more requests to test if WAF is blocking...")
        for i in range(post_wait_requests):
            result = test_api_key(api_key, f"test_extra{i}@example.com", show_command=False)
            
            error = str(result.get('error', ''))
            if '403' in error or 'forbidden' in error.lower():
                status = 'WAF BLOCKED'
                block_count += 1
            elif 'hash' in result:
                status = 'OK'
                success_count += 1
            else:
                status = f"ERROR: {error[:100]}..."
                other_errors += 1
            
            if verbose:
                print(f"\nFull response for request {i+1}:")
                print(json.dumps(result, indent=2))
                    
            print(f"Extra Request {i+1}: {status}")

    if verbose:
        print(f"\nWAF Test Summary:")
        print(f"Successful requests: {success_count}")
        print(f"Blocked requests: {block_count}")
        if other_errors > 0:
            print(f"Other errors: {other_errors}")
        print(f"Finished test_waf_limit() at {get_current_datetime_filefriendly(include_utc=True)}")
def mrun_test_waf_limit():
    pass
#if __name__ == "__main__":
    #test_waf_limit()
    test_waf_limit(initial_rapid_requests=20, wait_minutes=2, post_wait_requests=5, verbose=False)
    # (see 12-4 cursor chat)

### AWS JWT
def get_jwt_signing_key():
    """
    Retrieve JWT signing key from AWS Secrets Manager.

    :return str: The JWT signing key
    """
    secret_name = "jwt-secret-demo"
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager'
    )
    
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        secret = json.loads(get_secret_value_response['SecretString'])
        return secret['JWT_SIGNING_KEY_DEMO']
    except Exception as e:
        print(f"Error retrieving secret: {e}")
        raise
def generate_jwt(subject_claim, expiry_days):
    """
    Generate a JWT token with specified subject claim and expiry.

    :param subject_claim: str, value for the 'sub' claim in JWT
    :param expiry_days: int, number of days until token expires
    :return str: JWT token
    """
    secret_key = get_jwt_signing_key()
    expiry = datetime.utcnow() + timedelta(days=expiry_days)
    
    payload = {
        'sub': subject_claim,
        'iat': datetime.utcnow(),
        'exp': expiry
    }
    
    return jwt.encode(payload, secret_key, algorithm='HS256')
def verify_jwt(token):
    """
    Verify a JWT token.

    :param token: str, the JWT token to verify
    :return: dict with decoded claims if valid, None if invalid
    """
    try:
        secret_key = get_jwt_signing_key()
        return jwt.decode(token, secret_key, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        print("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        print(f"Invalid token: {e}")
        return None
def mrun_verify_jwt():
    pass
#if __name__ == "__main__":
    #token = os.environ["JWT_01-22"]
    token = "[REMOVED-JWT]"
    result = verify_jwt(token)
    print(f"Verification result: {result}")
def mrun_generate_and_verifyjwt():
    pass
#if __name__ == "__main__":
    # Generate a JWT token
    token = generate_jwt("api-gateway-test", 90)
    print(f"Generated JWT: {token}")

    # Verify the JWT token
    result = verify_jwt(token)
    print(f"Verification result: {result}")


# ===== END OF FILE primary/aws.py =====
