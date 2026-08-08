import boto3
import os
import json
from botocore.exceptions import ClientError, NoCredentialsError

# s3 paths are like folders, pass something like 'podcasts/' to put the object in an s3 folder
def upload_file_to_s3(file_path, bucket='fofpublic', object_name=None, s3_path=''):
    """
    Upload a file to an S3 bucket

    :param file_path: File to upload
    :param bucket: Name of the S3 bucket, default is 'fofpublic', others: '[S3-BUCKET]', 'deutsch-audio'
    :param object_name: S3 object name. If not specified, the file name is used
    :param s3_path: S3 folder path where the file will be stored
    :return: The object name of the file in S3
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
        # Upload the file
        s3_client.upload_file(file_path, bucket, object_name)
        print(f"uploaded {object_name} to {bucket}")
        return object_name

    except FileNotFoundError:
        return None
    except NoCredentialsError:
        print("Credentials not available")

def rename_s3_object(bucket, old_key, new_key, s3_path=None):
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

def get_s3_json(bucket, key, s3_path=None):
    s3 = boto3.client('s3', region_name='us-west-2')

    # Adjust key if s3_path is provided
    if s3_path:
        key = f"{s3_path}/{key}"

    print(f"Function get_s3_json is attempting to access key: {key} in bucket: {bucket}")

    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        json_data = json.loads(response['Body'].read().decode('utf-8'))
        return json_data
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchKey':
            print(f"No such key: {key} in bucket: {bucket}")
        else:
            print(f"Client error: {e}")
        return None
    except Exception as e:
        print(f"Failed to retrieve {key} from {bucket}: {str(e)}")
        return None



# aws s3api head-object --bucket fofpublic --key deepgram-transcriptions/b4ea528e-4fc8-468a-8320-d5e7f34566b2.json

# old_key = "705a4ad4-b195-4a03-8077-cc7d3881eb1a.json"
# cur_s3_path = 'deepgram-transcriptions'
# json_data = get_s3_json('fofpublic', old_key, cur_s3_path)
# print(f"First characters of received JSON:\n\n{json.dumps(json_data)[:500]}")

# new_key = "fun1.json"
# rename_s3_object('fofpublic', old_key, new_key, s3_path=cur_s3_path)

# cur_file_path='data/pv/meetings_epc/f0_agendas_for_upcoming/2024-05-02_PV-EPC_packet.pdf'
# print(upload_file_to_s3(cur_file_path))
