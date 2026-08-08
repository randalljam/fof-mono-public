# pip install --upgrade google-api-python-client google-auth google-auth-httplib2 google-auth-oauthlib
'''ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.
corpus-tools 1.0 requires openai==1.13.3, but you have openai 1.16.2 which is incompatible.
corpus-tools 1.0 requires tqdm==4.65.0, but you have tqdm 4.66.2 which is incompatible.'''

import os
import json
import csv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload  # Add MediaFileUpload import
import google.auth
from google.auth import impersonated_credentials
from google.oauth2.service_account import Credentials

# Define suffix extension options as a list
suffix_extension_options_list = [
    ".mp3",
    "_whspraw.txt",
    "_spfix.txt",
    "_whspjspl.txt",
    "_whspcorlog.txt",
    "_whspcor.txt",
    "_whspmerge.txt",
    "_reffile.txt",
    "_logfile.txt",
    "_testfile.txt",
    "_titles.txt",
    "_dgwhspm.json",
    "Custom"
]
suffix_extension_list = suffix_extension_options_list[:-1] # make a list of the possible suffix and extensions, to use with get_titles_from_local function
suffix_extension_options_dict = {opt: opt for opt in suffix_extension_options_list} # Construct suffix_extension_options_dict from suffix_extension_options
suffix_extension_options_str = ', '.join(f'"{option}"' for option in suffix_extension_options_list)

# Define folder_id_options
FOLDER_ID_OPTIONS_DICT = {
    "0) Helper Files": "1JHwbiFeuTBjqTrPoLM6vKHh5FDBH5K-7",
    "1) .mp3 Audio Files": "1Ic_w3kuSbdIqRUM25ZXX_SSHSlLWuwdK",
    "2) _spfix.txt Speaker Fix Transcript": "1a5emP6hTJGcDhTPl4YHYh7yT9ji-bWmD",
    "3) _whspraw.txt Whisper Raw Transcript": "1KELSOTHo8WGvrYuNK3v9LH7LOeAWdRSy",
    "4) _whspjspl.txt Whisper Junction Spliced": "1B6zQnu1qP81F3wQtfdNl3w8Brw8f59Lf",
    "5) _whspcorlog.txt Whisper Correction Log": "141IiLgbn1pvKaWVuTbPQGdj5YAjnXhHU",
    "6) _whspcor.txt Whisper Corrected Transcript": "1rFQnYF3cefaBcM2sHhmZhkOGX3rp7Hcw",
    "7) _whspmerge.txt Whisper Merged Transcript": "1OY1YpYlP-TKX4Vw7tOiqv3-ZF_8hyuti",
    "8) _whspmerge.md Whisper Merged Markdown Files": "1p-GNC22jy80pxwXTqreUuXtd-yzOaDrX",
    "9) _dgwhspm Deepgram Transcripts": "1gsk3Md44TpyRwb12N6G6GPgrZFBlPDfY",
    "TEST": "1n7U1cgoB4-7968ldakgNb7cVP0EV99G0",
    "PV EPC - Emergency Preparedness Committee PUBLIC GDRIVE FOLDER": "1ZrfdaL1LIY99s_ON7r5ITGI0RljBJ7rE"
}

folder_id_options_list = list(FOLDER_ID_OPTIONS_DICT.keys()) # Construct folder_id_options_list from folder_id_options
# folder_id_options_str = ', '.join(f'"{option}"' for option in folder_id_options_list) # Construct a string representation of the options

# google user to share folders with fofgeneral-service-account@fofgeneral-gdrive.iam.gserviceaccount.com

# GDRIVE_KEY_PATH_FOFGENERAL20 = 'gdrive_service_account_fofgeneral20_personal.json'
# def load_gdrive_creds_OLD(gdrive_key_path=GDRIVE_KEY_PATH_FOFGENERAL20, verbose=False):
#     """
#     Loads Google Drive service account credentials from a specified JSON key file and initializes the Google Drive service.

#     :param gdrive_key_path: string of the path to the service account JSON key file.
#     :return: the initialized Google Drive service object if successful, None otherwise.

#     :category: 1
#     :heading: 
#     :usage: gdrive_service = load_gdrive_creds('path/to/service_account.json')
#     """
#     from general.fileops import verbose_print
#     # Load the service account credentials USED WITH FOFGENERAL20 SERVICE ACCOUNT pre 6-1
#     if os.path.isfile(gdrive_key_path):
#         try:
#             # note scopes is hardcoded but was previousl a global variable in colab code
#             creds = service_account.Credentials.from_service_account_file(gdrive_key_path, scopes=['https://www.googleapis.com/auth/drive'])
#             if creds:
#                 print("Success: The service account JSON key file is valid and the credentials were loaded.")
#                 # Build the GDrive service
#                 gdrive_service = build('drive', 'v3', credentials=creds)
#             else:
#                 print("Error: Unable to load credentials from service account JSON key file.")
#         except Exception as e:
#             print(f"Error while loading credentials from service account JSON key file: {str(e)}")
#     else:
#         print("Warning: The service account JSON key file does not exist. Skipping GDrive service initialization.")

#     # Test the Google Drive API
#     try:
#         # Confirm the file path.
#         if not os.path.isfile(gdrive_key_path):
#             print(f"Error: File {gdrive_key_path} does not exist.")
#         else:
#             verbose_print(verbose, f"Success: File {gdrive_key_path} exists.")

#             # Validate JSON key.
#             try:
#                 with open(gdrive_key_path, 'r') as key_file:
#                     key_content = json.load(key_file)
#                 # Check for necessary fields in the JSON file
#                 necessary_fields = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id"]
#                 for field in necessary_fields:
#                     if field not in key_content:
#                         print(f"Error: '{field}' is missing in JSON key.")
#                 verbose_print(verbose, f"Success: All necessary fields exist in JSON key.")
#             except Exception as e:
#                 verbose_print(verbose, f"Error while validating JSON key: {str(e)}")

#             # File permissions.
#             try:
#                 with open(gdrive_key_path, 'r') as key_file:
#                     verbose_print(verbose, "Success: Read permissions for the JSON key file are correct.")
#             except Exception as e:
#                 print(f"Error: Could not read the JSON key file. {str(e)}")
#     except HttpError as err:
#         # The HttpError exception is raised if the request to the discovery service fails.
#         print(f"Error while building Google Drive service: {err}")
#     except Exception as e:
#         # Catch any other exceptions
#         print(f"Error while building Google Drive service: {str(e)}")
#     return gdrive_service
# GDRIVE_SERVICE_FOFGENERAL20 = load_gdrive_creds_OLD()

GDRIVE_CREDENTIALS_DIR = os.path.expanduser('~/.config/credentials-gdrive')
GDRIVE_KEY_PATH_FLWORKSPACE = os.path.join(GDRIVE_CREDENTIALS_DIR, 'floodlamp-gdrive-jackie-cce56b4f953f.json')
IMPERSONATED_USER_EMAIL = 'randy@floodlamp.bio'
def load_gdrive_creds(gdrive_key_path=GDRIVE_KEY_PATH_FLWORKSPACE, impersonated_user=IMPERSONATED_USER_EMAIL, verbose=False):
    from core.fileops import verbose_print
    creds = None

    if os.path.isfile(gdrive_key_path):
        try:
            creds = service_account.Credentials.from_service_account_file(
                gdrive_key_path,
                scopes=['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive.metadata.readonly'],
                subject=impersonated_user
            )
            if creds:
                print("Success: The service account JSON key file is valid and the credentials were loaded.")
                gdrive_service = build('drive', 'v3', credentials=creds)
            else:
                print("Error: Unable to load credentials from service account JSON key file.")
        except Exception as e:
            print(f"Error while loading credentials from service account JSON key file: {str(e)}")
    else:
        print("Warning: The service account JSON key file does not exist. Skipping GDrive service initialization.")

    try:
        if not os.path.isfile(gdrive_key_path):
            print(f"Error: File {gdrive_key_path} does not exist.")
        else:
            verbose_print(verbose, f"Success: File {gdrive_key_path} exists.")
            try:
                with open(gdrive_key_path, 'r') as key_file:
                    key_content = json.load(key_file)
                necessary_fields = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id"]
                for field in necessary_fields:
                    if field not in key_content:
                        print(f"Error: '{field}' is missing in JSON key.")
                verbose_print(verbose, f"Success: All necessary fields exist in JSON key.")
            except Exception as e:
                verbose_print(verbose, f"Error while validating JSON key: {str(e)}")

            try:
                with open(gdrive_key_path, 'r') as key_file:
                    verbose_print(verbose, "Success: Read permissions for the JSON key file are correct.")
            except Exception as e:
                print(f"Error: Could not read the JSON key file. {str(e)}")
    except HttpError as err:
        print(f"Error while building Google Drive service: {err}")
    except Exception as e:
        print(f"Error while building Google Drive service: {str(e)}")
    return gdrive_service
GDRIVE_SERVICE_FLWORKSPACE = load_gdrive_creds()

def list_files_in_shared_drive(shared_drive_id, folder_id, service=GDRIVE_SERVICE_FLWORKSPACE):
    try:
        results = service.files().list(
            corpora="drive",
            driveId=shared_drive_id,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
            q=f"'{folder_id}' in parents",
            pageSize=10,
            fields="nextPageToken, files(id, name)"
        ).execute()
        items = results.get('files', [])
        if not items:
            print('No files found.')
        else:
            print('Files:')
            for item in items:
                print(u'{0} ({1})'.format(item['name'], item['id']))
    except Exception as e:
        print(f"Error listing files: {str(e)}")
    # OAuth 2.0 Playground URI that worked:
    # https://www.googleapis.com/drive/v3/files?corpora=drive&driveId=0AEvH3N5wS0EVUk9PVA&includeItemsFromAllDrives=true&supportsAllDrives=true&q='1D1YcJd_rYAj2aIye0twemh76qRm8PY4D'+in+parents&fields=files(id,name)       

def get_full_folder_path(folder_id, service=GDRIVE_SERVICE_FLWORKSPACE):
    """
    Returns the full path of a folder from the root of the shared drive given its folder ID.

    :param folder_id: Google Drive folder ID to get the path for.
    :param service: Authenticated Google Drive service object.
    :return: String representing the full path of the folder.
    """
    path = []

    def build_path(current_id):
        # Get the folder metadata
        try:
            print(f"Retrieving metadata for folder ID: {current_id}")
            folder = service.files().get(fileId=current_id, fields='name, parents').execute()
            print(f"Folder metadata: {folder}")
        except Exception as e:
            print(f"Error retrieving folder metadata: {str(e)}")
            return

        # Prepend the folder name to the path
        path.insert(0, folder['name'])

        # Check if the folder has a parent
        if 'parents' in folder:
            # Recursively build the path from the parent folder
            build_path(folder['parents'][0])

    # Start building the path from the given folder ID
    build_path(folder_id)

    # Join the path elements with '/'
    return '/' + '/'.join(path)

def get_full_folder_path_OLD(folder_id, service=GDRIVE_SERVICE_FLWORKSPACE):
    """
    Returns the full path of a folder from the root of the shared drive given its folder ID.

    :param folder_id: Google Drive folder ID to get the path for.
    :param service: Authenticated Google Drive service object.
    :return: String representing the full path of the folder.
    """
    path = []

    def build_path(current_id):
        # Get the folder metadata
        try:
            folder = service.files().get(fileId=current_id, fields='name, parents').execute()
        except Exception as e:
            print(f"Error retrieving folder metadata: {str(e)}")
            return

        # Prepend the folder name to the path
        path.insert(0, folder['name'])

        # Check if the folder has a parent
        if 'parents' in folder:
            # Recursively build the path from the parent folder
            build_path(folder['parents'][0])

    # Start building the path from the given folder ID
    build_path(folder_id)

    # Join the path elements with '/'
    return '/' + '/'.join(path)

def list_gdrive_files(folder_id, service=GDRIVE_SERVICE_FLWORKSPACE):
    """ 
    Retrieves all files in a specified Google Drive folder and includes their MIME type.

    :param service: the Google Drive service instance used to access files.
    :param folder_id: string of the folder id to list files from.
    :return: list of dictionaries containing file id, name, and MIME type.

    :usage: files = list_gdrive_files('folder_id_string')
    """
    results = service.files().list(
        pageSize=100,
        fields="nextPageToken, files(id, name, mimeType)",
        q=f"'{folder_id}' in parents"
    ).execute()

    files = results.get('files', [])
    files = sorted(files, key=lambda k: k['name'], reverse=True)
    return files

def list_gdrive_files_iteratively(folder_id, output_file_path_prefix='', service=GDRIVE_SERVICE_FLWORKSPACE):
    """
    Iteratively lists files in a Google Drive folder and returns the result of an iterative query of files.
    Note: Check that 'folder_id' is an appropiate object before calling this function. Make checks for 'service' too 

    :param service: Authenticated Google Drive service object.
    :param folder_id: Google Drive folder ID to list contents of.
    :param output_file_path_prefix: Path of the parent folder for iteration.
    :return: list of dictionaries containing file id, name, and MIME type.

    :usage: print(list_files_iterative(folder_id))
    """
    from queue import Queue

    def get_sorted_files_with_query(query, fields='files(id, name, mimeType, parents)'):
        # Helper function, make a query and specifying fields to be returned
        results = service.files().list(q=query, fields=fields).execute()
        files = results.get('files', [])
        files = sorted(files, key=lambda k: k['name'], reverse=True)
        return files

    # Prepare to make queries with different ids
    make_query_id_in_parents = lambda id: f"'{id}' in parents"

    # Files will be queued for processing
    queue = Queue()
    for file in get_sorted_files_with_query(make_query_id_in_parents(folder_id)):
        queue.put(file)
    results = []
    while not queue.empty():
        # Pop item
        item = queue.get()
        # Usually you want output_file_path_prefix to be ''
        if not item.get('filePath', ''):
            item['filePath'] = f"{output_file_path_prefix}/"
        if item['mimeType'] == 'application/vnd.google-apps.folder':
            # New query
            for file in get_sorted_files_with_query(make_query_id_in_parents(item.get('id'))):
                # Files are children of our current item, so inherit file_path
                file['filePath'] = item['filePath'] + item.get('name', '') + '/'
                queue.put(file)
        else:
            results.append(item)
    return results

def create_gdrive_folder_csv(folder_id, csv_path, service=GDRIVE_SERVICE_FLWORKSPACE):
    """
    Creates a CSV file with folder_id, file_id, file_path, file_name and file_type of all files in a Google Drive folder.

    :param service: the Google Drive service instance used to access files.
    :param folder_id: string of the folder ID to list files from.
    :param csv_path: string of the path to save the CSV file.
    :return csv_path: string of the path to CSV file.

    :usage: create_gdrive_folder_csv('folder_id_string', 'path_to_save_file.csv')
    """
    # Query files
    files = list_gdrive_files_iteratively(folder_id)

    # Write data to CSV
    with open(csv_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        # Header
        writer.writerow(['folder_id', 'file_id', 'file_path', 'file_name', 'file_type'])
        # Write to CSV
        for file in files:
            print("Writing to CSV:", file['parents'][0], file['id'], file['filePath'], file['name'], file['mimeType'])
            writer.writerow([file['parents'][0], file['id'], file['filePath'], file['name'], file['mimeType']])

        print(f"CSV file with {len(files)} rows created at {csv_path}")

    return csv_path

### OLD EXECUTION CODE
cur_gdrive_key_path = os.path.join(GDRIVE_CREDENTIALS_DIR, 'gdrive_service_account_fofgeneral20_personal.json')
gdrive_service = load_gdrive_creds(cur_gdrive_key_path)
# print(list_gdrive_files(gdrive_service, 'XXXOOXXX'))  # TODO should give an error for invalid gdrive folder id 
# print(list_gdrive_files(gdrive_service, '1n7U1cgoB4-7968ldakgNb7cVP0EV99G0'))  # for DD corpus Test folder
# print(list_gdrive_files(gdrive_service, '1n7U1cgoB4-7968ldakgNb7cVP0EV99G0'))  # for PV EPC - Emergency Preparedness Committee PUBLIC GDRIVE FOLDER

# print(list_gdrive_files(gdrive_service, '1Ic_w3kuSbdIqRUM25ZXX_SSHSlLWuwdK')) 

# Simple test (ok)
test_folder_id = '1tX2bGgZBraVnhnG9j00etIexAD_Nlxbp'

# Helper files (ok)
helper_files_folder_id = '1JHwbiFeuTBjqTrPoLM6vKHh5FDBH5K-7'

# mp3 Audio files (ok)
mp3_audio_files_folder_id = '1Ic_w3kuSbdIqRUM25ZXX_SSHSlLWuwdK'

# This is what we want to be listed (leaves an empty CSV file)
priority_folder_id = '1ZrfdaL1LIY99s_ON7r5ITGI0RljBJ7rE'


# create_gdrive_folder_csv(gdrive_service, test_folder_id,'gdrive_test.csv')

# create_gdrive_folder_csv(gdrive_service, helper_files_folder_id,'gdrive_helper_files.csv')

# create_gdrive_folder_csv(gdrive_service, mp3_audio_files_folder_id,'gdrive_mp3_audio_files.csv')

# create_gdrive_folder_csv(gdrive_service, priority_folder_id,'gdrive_priority.csv')


# orphaned scratch line (dangling indent, undefined `file`) — commented out so core.gdrive imports cleanly
#         print(f"File Name: {file.name} | File Size: {file.size} bytes | File Type: {file.content_type}")