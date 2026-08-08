# START OF FILE core/transcribe.py
# Library of functions and execution code to transcribe audio files

import os
import sys
import re
import threading
import httpx
from deepgram import DeepgramClient, PrerecordedOptions, FileSource
from datetime import datetime, timedelta
from requests import post
import requests
import yt_dlp as youtube_dl
from num2words import num2words
import json
import math
import mutagen  # Import mutagen to handle audio metadata
from wordfreq import top_n_list
import warnings  # Set the warnings to use a custom format
import cv2  # pip install opencv-python
import pytesseract
from PIL import Image
import numpy as np
import glob
import csv
import shutil
import time
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import pickle

from core.fileops import *
import core.fileops  # moving to namespace imports


# ---API KEYS AND SECRETS---
from dotenv import load_dotenv
load_dotenv(override=True)  # Load environment variables from .env file
DEEPGRAM_API_KEY = os.environ["DEEPGRAM_API_KEY"]
YOUTUBE_API_KEY = os.environ["YOUTUBE_API_KEY"]
# INSERT in chalice/config.json "DEEPGRAM_API_KEY": "DEEPGRAM_API_KEY"


# ---START OF SYNCED CODE--- only code below will be synchronized with chalicelib.

warnings.formatwarning = custom_formatwarning
# USAGE: warnings.warn(f"Insert warning message here")

# Get the directory name of the current file (transcribe.py) and the parent directory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir) # Add the parent directory to sys.path

# Get the top 3000 English words
common_english_vocab = set(top_n_list('en', 3000))

### YOUTUBE
def get_authenticated_service():
    """
    Creates an authenticated YouTube service with OAuth2.
    Handles token creation and refresh.
    """
    creds = None
    # Token file stores the user's access and refresh tokens
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            
    # If no valid credentials, let user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_secret_path = os.path.join(
                os.path.expanduser('~/.config/credentials-gdrive'),
                'client_secret_119941763167-c0oqkp63cv6elses4828p7fvthdqredv.apps.googleusercontent.com.json',
            )
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secret_path,
                [
                    'https://www.googleapis.com/auth/youtube.force-ssl',
                    'https://www.googleapis.com/auth/youtube.readonly',
                    'https://www.googleapis.com/auth/youtubepartner'
                ]
            )
            creds = flow.run_local_server(port=0)
        
        # Save credentials for future use
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('youtube', 'v3', credentials=creds)
def download_mp3_from_youtube(url, output_title='audio_download', output_dir='data/audio_inbox', skip_download=False, max_retries=10):
    """
    Downloads a YouTube video as MP3 audio file.

    :param url: string of the YouTube URL to download from.
    :param output_title: string of the title to save the audio file as (must not contain path separators).
    :param output_dir: string path to directory where audio will be saved. Default 'data/audio_inbox'.
    :param skip_download: boolean to skip download if file exists. If False, will delete existing file and start download.
    :param max_retries: int number of times to retry download on failure.
    :return: string of the path to the saved MP3 file.
    :raises ValueError: if output_title contains path separators.
    """
    # Validate output_title has no path separators
    if '/' in output_title or '\\' in output_title:
        raise ValueError(f"output_title must not contain path separators. Use output_dir parameter to specify path. Got: {output_title}")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_file_path = os.path.join(output_dir, output_title + '.mp3')
    if os.path.exists(output_file_path):
        if skip_download:
            print(f"Audio file exists at {output_file_path}. Using existing file (skip_download=True).")
            return output_file_path
        print(f"Audio file exists at {output_file_path}. Will delete existing file and start download.")
        os.remove(output_file_path)

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(output_dir, output_title),
    }

    for attempt in range(max_retries):
        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            break
        except Exception as e:
            if attempt < max_retries - 1:
                sleep_time = min(2 ** attempt, 60)
                print(f"\nDownload attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                print(f"Waiting {sleep_time} seconds before retrying...")
                time.sleep(sleep_time)
            else:
                print(f"\nAll {max_retries} download attempts failed. Last error: {str(e)}")
                raise

    return output_file_path
def get_youtube_title_length(url):
    """ 
    Retrieves the title and duration of a youtube video in a formatted timestamp.

    :param url: string of the youtube url to retrieve information from.
    :return: tuple containing the video title and its duration as a string in a formatted timestamp.
    """
    from core.fileops import tune_timestamp
    
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError(f"Could not extract video ID from URL: {url}")

    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        response = youtube.videos().list(
            part='snippet,contentDetails',
            id=video_id
        ).execute()

        if not response['items']:
            raise ValueError(f"No video found for ID: {video_id}")

        video_data = response['items'][0]
        video_title = video_data['snippet']['title']
        duration = parse_duration(video_data['contentDetails']['duration'])
        video_length = tune_timestamp(duration)
        
        return video_title, video_length
    
    except HttpError as e:
        raise ValueError(f"YouTube API error: {e}")
    finally:
        if 'youtube' in locals():
            youtube.close()
def download_link_list_to_mp3s(links, output_dir="data/audio_inbox", skip_download=False):  # NO CALLERS (3-3 RT)
    """
    Downloads a list of youtube links as mp3 files to a specified directory and stores the link-title pairs. Uses yt_dlp package.
    Calls download_mp3_from_youtube

    :param links: list of youtube links to be downloaded.
    :param output_dir: string of the directory path where the audio files will be saved.
    :return: dictionary mapping each youtube link to its corresponding title.
    """
    link_title_pairs = {}
    for link in links:
        title, length = get_youtube_title_length(link)  # Get title and length
        title = title.rsplit('.', 1)[0]  # Remove file extension from title
        link_title_pairs[link] = title  # Store link-title pair
        download_mp3_from_youtube(link, title, output_dir, skip_download)  # Download as MP3
    return link_title_pairs
def download_youtube_subtitles_url(subtitle_url): # DS, cat 1, omit unittests since called by next function
    """
    Downloads and extracts subtitle text from a given YouTube subtitle URL.
    Helper function to that is called from get_youtube_subtitles
    
    :param subtitle_url: string of the url from which subtitles are to be downloaded.
    :return: string of the extracted subtitle text, spaces between segments and stripped of new lines.
    """
    response = requests.get(subtitle_url)
    response.raise_for_status()  # This will raise an exception for HTTP errors
    subtitle_data = response.json()  # Parse JSON data

    # Extract transcript text from the subtitle data
    subtitle_text = ""
    for event in subtitle_data['events']:
        if 'segs' in event:
            for seg in event['segs']:
                if 'utf8' in seg:
                    subtitle_text += seg['utf8'] + " "

    return subtitle_text.replace('\n', ' ').strip()
def get_youtube_subtitles(url):  # 1-18 no longer working - uses yt-dlp
    """
    Retrieves English subtitles for a given YouTube video URL if available. Uses yt_dlp package.
    
    :param url: string of the youtube video url.
    :return: subtitles as a string if found, otherwise None.
    """
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en']  # Specify the language of subtitles you want to download
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        
        # Attempt to get the transcript (subtitles)
        subtitles = info_dict.get('subtitles', {})
        auto_captions = info_dict.get('automatic_captions', {})
        
        # Choose subtitles or automatic captions to return
        transcript_info = subtitles if subtitles else auto_captions
        
        # If there are subtitles or auto captions, download them
        if transcript_info.get('en'):
            subtitles_url = transcript_info['en'][0]['url']  # Get the URL for the first English subtitle track
            return download_youtube_subtitles_url(subtitles_url)
        else:
            print("No English subtitles found.")
def get_youtube_subtitles_oauth(url):  # added 1-18 but does not work
    """
    Retrieves English subtitles or closed captions for a YouTube video.
    Tries manual subtitles first, falls back to auto-generated captions if needed.
    
    :param url: string of the youtube video url.
    :return: tuple of (subtitle text as string, source type as string) or (None, None) if not found.
    """
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError(f"Could not extract video ID from URL: {url}")

    try:
        youtube = get_authenticated_service()
        
        # Get list of available captions
        captions_response = youtube.captions().list(
            part='snippet',
            videoId=video_id
        ).execute()

        caption_id = None
        is_auto_caption = True

        # First try to find manual subtitles
        for caption in captions_response.get('items', []):
            if caption['snippet']['language'] == 'en':
                if caption['snippet'].get('trackKind') != 'ASR':  # Not auto-generated
                    caption_id = caption['id']
                    is_auto_caption = False
                    break
        
        # If no manual subtitles, try auto-captions
        if not caption_id:
            for caption in captions_response.get('items', []):
                if caption['snippet']['language'] == 'en' and caption['snippet'].get('trackKind') == 'ASR':
                    caption_id = caption['id']
                    break

        if not caption_id:
            print("No English subtitles or captions found.")
            return None, None

        # Download the actual caption track
        subtitle_response = youtube.captions().download(
            id=caption_id,
            tfmt='srt'  # Request subtitles in SRT format
        ).execute()

        if not subtitle_response:
            print("Failed to download captions.")
            return None, None

        # Convert from bytes to string and clean up the text
        subtitle_text = subtitle_response.decode('utf-8')
        # Remove timecodes and subtitle numbers
        cleaned_text = ' '.join(
            line.strip() 
            for line in subtitle_text.split('\n') 
            if line.strip() and not line.strip().isdigit() and '-->' not in line
        )

        source_type = 'auto-captions' if is_auto_caption else 'subtitles'
        return cleaned_text, source_type

    except HttpError as e:
        print(f"YouTube API error: {e}")
        return None, None
    finally:
        if 'youtube' in locals():
            youtube.close()
def parse_duration(duration_str):
    """
    Parse ISO 8601 duration format to timedelta.
    Example: 'PT1H2M10S' -> 1 hour, 2 minutes, 10 seconds

    :param duration_str: string of ISO 8601 duration format.
    :return: string of formatted duration.
    """
    import re
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration_str)
    if not match:
        return "0:00:00"
    
    hours, minutes, seconds = match.groups()
    hours = int(hours) if hours else 0
    minutes = int(minutes) if minutes else 0
    seconds = int(seconds) if seconds else 0
    
    return str(timedelta(hours=hours, minutes=minutes, seconds=seconds))
def extract_video_id(url):
    """
    Extracts the video ID from a YouTube URL.
    Only accepts exact matches of standard YouTube URL formats.

    :param url: string of the youtube url.
    :return: string of the video ID or None if not found.
    """
    import re
    patterns = [
        r'^(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([0-9A-Za-z_-]{11})$',
        r'^(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([0-9A-Za-z_-]{11})$'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None
def get_youtube_all(url):
    """
    Retrieves all available information from a YouTube video URL using YouTube Data API v3.
    
    :param url: string of the youtube video url.
    :return: dictionary with video details or None if the URL is invalid.
    """
    # Extract video ID from URL
    video_id = extract_video_id(url)
    if not video_id:
        print(f"Could not extract video ID from URL: {url}")
        return None

    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

        # Get video details
        video_response = youtube.videos().list(
            part='snippet,contentDetails,status',
            id=video_id
        ).execute()

        if not video_response['items']:
            print(f"No video found for ID: {video_id}")
            return None

        video_data = video_response['items'][0]
        snippet = video_data['snippet']
        
        # Parse duration from ISO 8601 format
        duration = parse_duration(video_data['contentDetails']['duration'])
        video_length = str(duration)

        # Get captions if available
        captions_response = youtube.captions().list(
            part='snippet',
            videoId=video_id
        ).execute()

        transcript_source = None
        transcript_text = None
        if captions_response.get('items'):
            for caption in captions_response['items']:
                if caption['snippet']['language'] == 'en':
                    transcript_source = 'subtitles' if not caption['snippet'].get('trackKind') == 'ASR' else 'auto-captions'
                    break

        # Format the upload date
        upload_date = snippet['publishedAt'][:10].replace('-', '')

        extracted_features = []
        if snippet.get('description'):
            extracted_features.append('description')
        if transcript_source:
            extracted_features.append(f'transcript from {transcript_source}')

        print(f"For YouTube video title: {snippet['title']}")
        print(f"  extracted the following features: {', '.join(extracted_features)}")

        return {
            'title': snippet['title'],
            'channel': snippet['channelTitle'],
            'date': upload_date,
            'length': video_length,
            'chapters': '',  # Note: Chapters aren't available through the API
            'description': snippet['description'],
            'transcript': transcript_text or "No transcript found",
            'transcript source': transcript_source
        }
    
    except HttpError as e:
        print(f"An HTTP error occurred: {e}")
        return None
    finally:
        if 'youtube' in locals():
            youtube.close()
def is_valid_youtube_url(url):
    """ 
    Determine if a string of url is a valid YouTube URL by checking video ID format
    and making an API call to verify the video exists.

    :param url: string of url to be validated.
    :return: boolean where true if the url is valid, false otherwise.
    """
    # First check if we can extract a valid video ID
    video_id = extract_video_id(url)
    if not video_id:
        print(f"Invalid YouTube URL format: {url}")
        return False
        
    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        request = youtube.videos().list(
            part="id",
            id=video_id
        )
        response = request.execute()
        return bool(response.get('items'))  # Returns True only if video exists
        
    except Exception as e:
        print(f"Invalid YouTube URL: {url}")
        return False
    finally:
        if 'youtube' in locals():
            youtube.close()
def create_youtube_md(url, title_or_path=None):  # unittests 3 APICALL + 1 APIMOCK
    """
    Generates a markdown file containing metadata, chapters, description, and transcript from a YouTube video.

    :param url: string of the url to be processed.
    :param title_or_path: string of the title or path for the markdown file, defaults to None.
    :return: string of the path to the created markdown file.
    """
    if title_or_path is None:
        title_or_path, _ = get_youtube_title_length(url)
    
    default_folder = "data/audio_inbox"
    suffix_ext = "_yt.md"
    yt_md_file_path = core.fileops.create_full_path(title_or_path, suffix_ext, default_folder)

    yt_info_dict = get_youtube_all(url)
    yt_content = "## content\n\n"
    if yt_info_dict['chapters']:
        yt_content += "### chapters (youtube)\n\n" + '\n'.join([f"{chap['start_time']} - {chap['title']}" for chap in yt_info_dict['chapters']])
        yt_content += "\n\n"
    yt_content += "### description (youtube)\n\n" + yt_info_dict['description'] + "\n\n"
    yt_content += "### transcript (youtube)\n\n" + yt_info_dict['transcript']

    yt_metadata = "## metadata\n"  # below fields are inserted above
    date_today = datetime.now().strftime("%m-%d-%Y")  # Assign today's date in format MM-DD-YYYY
    yt_metadata = core.fileops.set_metadata_field(yt_metadata, 'last updated', date_today + ' Created')  # Updates last updated
    yt_metadata = core.fileops.set_metadata_field(yt_metadata, 'link', url)
    yt_metadata = core.fileops.set_metadata_field(yt_metadata, 'youtube title', yt_info_dict['title'])
    yt_metadata = core.fileops.set_metadata_field(yt_metadata, 'youtube transcript source', yt_info_dict['transcript source'])
    yt_metadata = core.fileops.set_metadata_field(yt_metadata, 'length', yt_info_dict['length'])
    
    core.fileops.write_metadata_and_content(yt_md_file_path, yt_metadata, yt_content, overwrite='yes')
    core.fileops.add_timestamp_links(yt_md_file_path)
    return yt_md_file_path
def create_youtube_md_from_file_link(md_file_path):
    """
    Creates a YouTube markdown file from a given file path by extracting the YouTube link from the file's metadata.
    
    :param md_file_path: string of the path to the markdown file containing the YouTube link in its metadata.
    :return: string of the path to the created YouTube markdown file.
    """
    from core.fileops import sub_suffix_in_str, read_metadata_and_content, read_metadata_field_from_file
    suffix_new = '_yt'

    metadata, _ = read_metadata_and_content(md_file_path)
    if metadata is None:
        raise ValueError("VALUE ERROR - metadata is None")

    metadata_result = read_metadata_field_from_file(md_file_path, "link")  # returns a tuple (line num, field val)
    if metadata_result is None or metadata_result[1] is None:
        raise ValueError(f"VALUE ERROR - 'link' metadata field is missing or None in the file: {md_file_path}")
    _, link = metadata_result
    yt_file_path = sub_suffix_in_str(md_file_path, suffix_sub=suffix_new)
    #print(f"DEBUG: before create call {yt_file_path}")
    yt_file_path = create_youtube_md(link, yt_file_path)  # creates and returns the same file_path so the assignment is not needed but do it in case there is a bug and a different file_path is returned
    #print(f"DEBUG: after create call {yt_file_path}")
    return yt_file_path
def extract_feature_from_youtube_md(yt_md_file_path, feature):  # updated 1-28-25 RT to use get_heading
    """
    Extracts a specified feature from a YouTube markdown file and returns it as a string.

    :param yt_md_file_path: string of the path to the markdown file from which the feature is to be extracted.
    :param feature: string of the feature to be extracted (e.g., 'chapters', 'description', 'transcript').
    :return: string of the extracted text under the specified feature
    """
    try:
        # Try both heading formats
        heading1 = f"### youtube {feature}"
        heading2 = f"### {feature} (youtube)"
        
        text = get_heading(yt_md_file_path, heading1, strip_heading_line=True)
        if text is None:
            text = get_heading(yt_md_file_path, heading2, strip_heading_line=True)

        # Special handling for chapters if not found
        if feature == 'chapters' and text is None:
            # Try both description heading formats
            desc_text = get_heading(yt_md_file_path, "### youtube description", strip_heading_line=True)
            if desc_text is None:
                desc_text = get_heading(yt_md_file_path, "### description (youtube)", strip_heading_line=True)
            
            if desc_text:
                timestamp_block = []
                in_timestamp_block = False
                
                for line in desc_text.splitlines():
                    if re.search(r'\[\d{1,2}:\d{2}(?::\d{2})?\]', line):
                        if not in_timestamp_block:
                            in_timestamp_block = True
                        timestamp_block.append(line.strip())
                    elif in_timestamp_block:
                        break
                
                if timestamp_block:
                    print("No chapters section found. Extracted chapter timestamp links from description field.")
                    return '\n'.join(timestamp_block) + '\n\n'

        if text is None:
            warnings.warn(f"Feature '{feature}' not found in YouTube markdown file.")
            return None
            
        return text.strip() + '\n\n'
        
    except Exception as e:
        raise ValueError(f"Error extracting {feature} from {yt_md_file_path}: {e}")

### JSON AND TRANSCRIPT SUPPORT
def get_media_length(file_path_or_url):
    """
    Retrieves the length (duration) of a media file or a YouTube video.
    For a local file, it returns the duration in seconds.
    For a YouTube video, it returns the duration in our tuned timestamp format.

    :param file_path_or_url: Path to a local media file or a URL to a YouTube video.
    :return: length (duration) of the media in seconds (for local files) or in our tuned timestamp format (for YouTube videos).
    """
    #from core.fileops import tune_timestamp

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with open(os.devnull, 'w') as fnull:
            sys.stderr = fnull
            try:
                if is_valid_youtube_url(file_path_or_url):
                    _, video_length = get_youtube_title_length(file_path_or_url)
                    return core.fileops.tune_timestamp(video_length)
                elif os.path.isfile(file_path_or_url):
                    # Use mutagen to get the length of the audio file
                    audio = mutagen.File(file_path_or_url)
                    if audio is not None and hasattr(audio.info, 'length'):
                        return core.fileops.tune_timestamp(str(timedelta(seconds=int(audio.info.length))))
                    else:
                        raise ValueError("Could not determine the length of the audio file.")
                else:
                    raise ValueError("Invalid YouTube URL or file path.")
            except Exception as e:
                raise ValueError(f"An error occurred while retrieving media length: {e}")
            finally:
                sys.stderr = sys.__stderr__
def add_link_to_json_metadata(json_file_path, link):
    """ 
    Add a hyperlink to the JSON file under the 'metadata' section.

    :param json_file_path: string, the path to the JSON file to be modified.
    :param link: string, the hyperlink to be added to the JSON file.
    :return: tuple, the path to the modified JSON file and None if successful, or None and an exception if an error occurs.
    """
    try:
        with open(json_file_path, 'r') as file:
            data = json.load(file)

        # Check if 'metadata' exists in the JSON
        if 'metadata' in data:
            # Add the 'link' field at the top of the 'metadata'
            data['metadata'] = {'link': link, **data['metadata']}
        else:
            # If 'metadata' does not exist, create it
            data['metadata'] = {'link': link}

        with open(json_file_path, 'w') as file:
            json.dump(data, file, indent=4)

        return json_file_path, None
    except Exception as e:
        print(f"Error processing file {json_file_path}: {e}")
        return None, e
def get_link_from_json_metadata(json_file_path):
    """ 
    Retrieve the hyperlink from the 'metadata' section of a JSON file.

    :param json_file_path: string, the path to the JSON file from which the hyperlink is to be retrieved.
    :return: string or None, the hyperlink if found in the JSON file's 'metadata' section, otherwise None.
    """
    try:
        with open(json_file_path, 'r') as file:
            data = json.load(file)
        link = data.get('metadata', {}).get('link', None)
    except Exception as e:
        print(f"Error extracting link from {json_file_path}: {e}")
        link = None
    return link
def get_summary_start_seconds(data, index):
    """ 
    Retrieves the start time in seconds of a word from the transcription data at the given index.

    :param data: dictionary of the transcription data.
    :param index: integer of the index of the word to find the start time for.
    :return: integer of the start time in seconds of the specified word, rounded down to the nearest whole number.
    """
    words_list = data.get('results', {}).get('channels', [])[0].get('alternatives', [])[0].get('words', [])
    if index < len(words_list):
        return math.floor(words_list[index].get('start', 0))
    return 0
def format_feature_segment(feature, segment, data):
    """
    Formats a segment of a feature with a timestamp and additional info.

    :param feature: string, the feature being extracted.
    :param segment: dict, the segment of the feature to be formatted.
    :param data: dict, the JSON data from the Deepgram file.
    :return: string, the formatted segment.
    """
    from core.fileops import convert_seconds_to_timestamp

    singular_feature_json = feature[:-1]  # Remove the last character to make it singular as found in the JSON
    singular_feature_print = singular_feature_json.capitalize()  # Capitalize the singular form for printing
    segment_text = segment.get('text', '')
    segment_start_index = int(segment.get('start_word', 0))
    segment_start_secs = get_summary_start_seconds(data, segment_start_index)
    segment_timestamp = convert_seconds_to_timestamp(segment_start_secs)
    segment_midline = ""

    if feature.lower() == "summaries":
        singular_feature_json = 'summary'
        singular_feature_print = singular_feature_json.capitalize()
        segment_text = segment.get(singular_feature_json, '')
    elif feature.lower() == "sentiments":
        sentiment = segment.get('sentiment')
        sentiment_score = segment.get('sentiment_score')
        segment_midline = f"{sentiment} - sentiment_score = {sentiment_score:.2f}"
    elif feature.lower() == "topics":
        # Assuming there's only one topic per segment, hence index [0]
        topic_info = segment.get('topics', [{}])[0]
        topic_name = topic_info.get('topic')
        confidence_score = topic_info.get('confidence_score')
        segment_midline = f"{topic_name} - confidence_score = {confidence_score:.2f}"
    elif feature.lower() == "intents":
        # Assuming there's only one intent per segment, hence index [0]
        intent_info = segment.get('intents', [{}])[0]
        intent_name = intent_info.get('intent')
        confidence_score = intent_info.get('confidence_score')
        segment_midline = f"{intent_name} - confidence_score = {confidence_score:.2f}"

    formatted_segment = f"{singular_feature_print}  {segment_timestamp}\n"
    if segment_midline:
        formatted_segment += f"{segment_midline}\n"
    formatted_segment += f"{segment_text}\n\n"

    return formatted_segment
def extract_feature_from_deepgram_json(json_file_path, feature):
    """
    Extract a specific feature section from a Deepgram JSON file and return it as a string.

    :param json_file_path: string of the path to the JSON file from which the feature is to be extracted.
    :param feature: string of the feature of the section to be extracted.
    :return: string of the extracted text under the specified feature, preceded by the feature itself (no pound signs) and a blank line.
    """
    try:
        with open(json_file_path, 'r') as file:
            data = json.load(file)

        extracted_text = ''
        if feature == "summaries":
            summaries = data.get('results', {}).get('channels', [])[0].get('alternatives', [])[0].get(feature, [])
            #print(f"DEBUG summaries {summaries}")
            for summary in summaries:
                extracted_text += format_feature_segment(feature, summary, data)
        elif feature in ["sentiments", "topics", "intents"]:
            segments = data.get('results', {}).get(feature, {}).get('segments', [])
            #print(f"DEBUG {feature} {segments}")
            for segment in segments:
                extracted_text += format_feature_segment(feature, segment, data)
        else:
            warnings.warn(f"in extract_feature_from_deepgram_json - Feature '{feature}' not found in Deepgram JSON")
            return None

        if extracted_text:
            return f"{extracted_text.strip()}\n\n"
        else:
            warnings.warn(f"in extract_feature_from_deepgram_json - Feature '{feature}' was found in Deepgram JSON but extracted text is None or empty string (should not get this warning!)")
            return None
    except Exception as e:
        raise ValueError(f"Error extracting {feature} from {json_file_path}: {e}")
def validate_transcript_json(json_file_path):
    """
    Validates the structure of a JSON file to ensure it contains specific keys and types.

    :param json_file_path: string of the path to the JSON file to be validated.
    :return: boolean, True if the JSON structure is as expected, False otherwise.
    """
    if not os.path.exists(json_file_path):
        raise ValueError(f"The file path does not exist for {json_file_path}.")
    
    try:
        with open(json_file_path, "r") as file:
            data = json.load(file)

        # Access the nested structure with checks for KeyError and TypeError
        results = data.get("results")
        if results is None:
            raise KeyError("results key not found")

        channels = results.get("channels")
        if not isinstance(channels, list) or not channels:
            raise TypeError("channels is not a non-empty list")

        alternatives = channels[0].get("alternatives")
        if not isinstance(alternatives, list) or not alternatives:
            raise TypeError("alternatives is not a non-empty list")

        words_data = alternatives[0].get("words")
        if not isinstance(words_data, list) or len(words_data) <= 1:
            raise ValueError("The list of words is empty or has only one word.")

        paragraphs_data = alternatives[0].get("paragraphs")
        if paragraphs_data is None:
            raise KeyError("paragraphs key not found")

        transcript = paragraphs_data.get("transcript", "").strip()
        if not transcript:
            raise ValueError("The transcript in paragraphs is empty.")

        paragraphs_list = paragraphs_data.get("paragraphs")
        if not isinstance(paragraphs_list, list) or not paragraphs_list:
            raise ValueError("There are no paragraphs in paragraphs.")

    except (KeyError, TypeError, ValueError) as e:
        print(f"Error occurred with file {json_file_path}: {str(e)}")
        return False

    return True
def set_various_transcript_headings(file_path, feature, source):
    """
    Sets the transcript heading in a file based on the extracted feature from a specified source.

    :param file_path: string of the path to the file where the heading is to be set.
    :param feature: string of the feature to extract and use as the heading.
    :param source: string of the source from which to extract the feature ('deepgram' or 'youtube').
    :return: None.
    """
    from core.fileops import set_heading, add_suffix_in_str, remove_all_suffixes_in_str, find_file_in_folders  # seems to be needed for unittest, see Claude thread

    folder_paths = ["data/f_c9_done_json_yt_host"]     
    if source == "deepgram":
        dg_json_file_path = file_path.replace('.md', '.json')
        if not os.path.isfile(dg_json_file_path):
            dg_json_file_path = find_file_in_folders(dg_json_file_path, folder_paths)
            if dg_json_file_path is None:
                raise ValueError(f"No companion deepgram json file found for {file_path}")
        extracted_feature_text = extract_feature_from_deepgram_json(dg_json_file_path, feature)
    elif source == "youtube":
        yt_md_file_path = add_suffix_in_str(remove_all_suffixes_in_str(file_path), "_yt")
        if not os.path.isfile(yt_md_file_path):
            yt_md_file_path = find_file_in_folders(yt_md_file_path, folder_paths)
            if yt_md_file_path is None:
                raise ValueError(f"No companion youtube md file found for {file_path}")
        extracted_feature_text = extract_feature_from_youtube_md(yt_md_file_path, feature)
    else:
        raise ValueError("source invalid")
    if extracted_feature_text is None:
        return

    set_heading(file_path, extracted_feature_text, "### " + feature)
def get_transcript_speaker_lines(transcript_text):
    """
    Extracts speaker lines with timestamps from transcript text.

    :param transcript_text: string, the full transcript text to process.
    :return result: list of tuples, each containing (line_number, speaker_line_text).
    """
    from core.fileops import get_timestamp

    speaker_lines = []
    lines = transcript_text.split('\n')
    
    for i, line in enumerate(lines):
        timestamp, index = get_timestamp(line)
        if index is not None:
            speaker_lines.append((i, line.strip()))
    
    return speaker_lines
def apply_youtube_chapters_as_section_titles(transcript_file_path):
    """
    Applies the YouTube chapters timestamps and titles as section headings in the transcript file.

    :param transcript_file_path: string, path to the transcript markdown file
    :return: None
    """
    # Get paths and content
    yt_file_path = sub_suffix_in_str(transcript_file_path, '_yt')
    chapters = extract_feature_from_youtube_md(yt_file_path, 'chapters').rstrip()
    if not chapters:
        print(f"Aborting apply_youtube_chapters_as_section_titles - No chapters found in YouTube file: {yt_file_path}")
        return
    chapters_lines = chapters.split('\n')
    print(f"Extracted {len(chapters_lines)} chapters from YouTube file: {yt_file_path}")
    
    transcript_text = get_heading(transcript_file_path, '### transcript')
    if not transcript_text:
        print(f"Aborting apply_youtube_chapters_as_section_titles - No transcript found in transcript file: {transcript_file_path}")
        return

    # Get all speaker lines with their line numbers
    speaker_lines = get_transcript_speaker_lines(transcript_text)
    
    # Convert speaker lines timestamps to seconds for comparison
    speaker_times = []
    for line_num, speaker_line in speaker_lines:
        timestamp_match = re.search(r'\[(\d+:\d+(?::\d+)?)\]', speaker_line)
        if timestamp_match:
            timestamp = timestamp_match.group(1)
            seconds = sum(int(x) * 60**i for i, x in enumerate(reversed(timestamp.split(':'))))
            speaker_times.append((seconds, line_num, speaker_line))
    
    # Build list of section titles and their positions
    section_titles = []
    section_num = 1
    
    # Process each chapter line
    for chapter_line in chapters.split('\n'):
        # Skip empty lines
        if not chapter_line.strip():
            continue
            
        # Extract timestamp and title from chapter line
        timestamp_match = re.match(r'\[(\d+:\d+(?::\d+)?)\]', chapter_line)
        if not timestamp_match:
            continue
            
        timestamp = timestamp_match.group(1)
        title = chapter_line[chapter_line.find(')') + 1:].strip()
        if not title:
            continue
            
        # Convert chapter timestamp to seconds
        chapter_seconds = sum(int(x) * 60**i for i, x in enumerate(reversed(timestamp.split(':'))))
        
        # Find the first speaker line that occurs after this chapter timestamp
        for speaker_seconds, line_num, speaker_line in speaker_times:
            if speaker_seconds >= chapter_seconds:
                section_heading = f"#### {section_num}. {title}"
                section_titles.append((line_num, section_heading))
                section_num += 1
                break
    
    # Insert all section titles
    if section_titles:
        # Split transcript into lines for modification
        transcript_lines = transcript_text.split('\n')
        
        # Insert sections in reverse order to maintain line numbers
        for line_num, heading in sorted(section_titles, reverse=True):
            transcript_lines.insert(line_num, heading)
        
        # Join lines back together
        new_transcript = '\n'.join(transcript_lines)
        
        # Update the transcript section in the file
        set_heading(transcript_file_path, new_transcript, '### transcript')
        
        print(f"Added {len(section_titles)} section titles to transcript")

### DEEPGRAM ALTERNATIVES
def test_deepgram_client():  # omit unittests
    """
    Tests the Deepgram client initialization with the provided API key and prints a success or failure message.
    Raises ValueError if test fails.
    """
    try:
        test_deepgram_client = DeepgramClient(DEEPGRAM_API_KEY)
        if test_deepgram_client:
            print("Successfully created Deepgram Client and accessed the DeepGram API key.")
        else:
            print("Failed to create the Deepgram Client and/or access the DeepGram API key.")
    except Exception as e:
        raise ValueError(f"VALUE ERROR in test of Deepgram client: {e}")
MIMETYPES = ['mp3', 'mp4', 'mp2', 'aac', 'wav', 'flac', 'pcm', 'm4a', 'ogg', 'opus', 'webm']
DG_MODEL_SUFFIX_MAP = {
    'nova-2-general': "_nova2gen",
    'nova-2-meeting': "_nova2meet",
    'enhanced-meeting': "_enhmeet",
    'whisper-medium': "_dgwhspm",
    'whisper-large': "_dgwhspl"
}
def transcribe_deepgram_sync(audio_file_path, model):
    """ 
    Calls the Deepgram API to transcribe the given audio file using the specified Deepgram model.

    :param audio_file_path: path to the audio file to be transcribed.
    :param model: the Deepgram model to use for transcription, accpets deepgram api call model or our suffix version (see below).
    :return: a dictionary containing the transcription results.
    """
    from core.fileops import get_current_datetime_humanfriendly, convert_to_epoch_seconds, get_elapsed_seconds, convert_seconds_to_timestamp, convert_timestamp_to_seconds
    
    deepgram = DeepgramClient(DEEPGRAM_API_KEY)

    if not any(audio_file_path.endswith(ext) for ext in MIMETYPES):
        raise ValueError(f"File {audio_file_path} does not have a supported MIME type.")

    if model not in DG_MODEL_SUFFIX_MAP:
        raise ValueError("Invalid or absent DeepGram model.")

    suffix = DG_MODEL_SUFFIX_MAP[model]
    json_file_path = None

    try:
        print(f"Deepgram transcribing model: {model}  file : {audio_file_path}")
        
        with open(audio_file_path, "rb") as file:
            buffer_data = file.read()

        # Extract the file extension and prepare the correct MIME type
        file_extension = audio_file_path.rsplit('.', 1)[1]
        mimetype = f'audio/{file_extension}'

        payload: FileSource = {
            "buffer": buffer_data,
            "mimetype": mimetype,
        }

        # STEP 2: Configure Deepgram options for audio analysis
        # diarize_model="latest" replaces the deprecated diarize=true (routes to the v2 batch diarizer); do not set both.
        options = {
            "punctuate": True, "diarize_model": "latest", "model": model, "measurements": True, "smart_format": True,
            # "summarize": True, "intents": True, "sentiment": True, "topics": True
        }

        audio_length = get_media_length(audio_file_path)
        start_time = get_current_datetime_humanfriendly()
        print(f"Start Non-SDK Synchronous Deepgram Transcription at {start_time} for audio length of {audio_length}")
        # STEP 3: Call the transcribe_file method with the text payload and options
        # Use a timeout to prevent the write operation from timing out
        try:
            # Use the Deepgram client to transcribe the audio file
            response = deepgram.listen.prerecorded.v("1").transcribe_file(payload, options, timeout=30*60)
            print("Response received successfully.")
            print('\n'.join(str(response).splitlines()[:5]))  # Print only the first five lines of the response JSON
        except Exception as e:
            print(f"An error occurred: {e}")
        
        elapsed_time = get_elapsed_seconds(convert_to_epoch_seconds(start_time))
        transcribe_time_ratio = int(round(elapsed_time / convert_timestamp_to_seconds(audio_length)*100))
        print(f"Elapsed time is {convert_seconds_to_timestamp(elapsed_time)} which is {transcribe_time_ratio}% of the audio length")
        
        # STEP 4: Save the response as a JSON file
        response_json = response.to_json(indent=4)
        json_file_path = audio_file_path.rsplit('.', 1)[0] + suffix + '.json'
        with open(json_file_path, "w") as json_file:
            json_file.write(response_json)
        print(f"Transcription saved to {json_file_path}")
        #audio_duration = get_youtube_title_length(url)
        # TODO fill in code to print elapsed
    except Exception as e:
        print(f"Error during transcription: {e}")
    return json_file_path
def transcribe_deepgram_sync_sdk_prerecorded(audio_file_path, model):
    """
    Calls the Deepgram API to transcribe the given audio file using the specified Deepgram model, utilizing the SDK.

    :param audio_file_path: path to the audio file to be transcribed.
    :param model: the Deepgram model to use for transcription.
    :return: path to the JSON file containing the transcription results.
    """
    from core.fileops import get_current_datetime_humanfriendly, convert_to_epoch_seconds, get_elapsed_seconds, convert_seconds_to_timestamp, convert_timestamp_to_seconds

    deepgram = DeepgramClient(DEEPGRAM_API_KEY)

    if not any(audio_file_path.endswith(ext) for ext in MIMETYPES):
        raise ValueError(f"File {audio_file_path} does not have a supported MIME type.")

    if model not in DG_MODEL_SUFFIX_MAP:
        raise ValueError("Invalid or absent DeepGram model.")

    suffix = DG_MODEL_SUFFIX_MAP[model]
    json_file_path = None

    try:
        print(f"Deepgram transcribing model: {model}  file : {audio_file_path}")

        # Read the audio file into a buffer
        with open(audio_file_path, "rb") as audio:
            buffer_data = audio.read()

        # Create the payload with the buffer data and mimetype
        payload: FileSource = {
            "buffer": buffer_data,
            "mimetype": f'audio/{audio_file_path.rsplit(".", 1)[1]}'
        }

        # Configure Deepgram options
        # Passed as a dict (not PrerecordedOptions) so we can send diarize_model, which the
        # installed SDK's typed options don't expose. diarize_model="latest" replaces the
        # deprecated diarize=true (v2 batch diarizer); do not set both.
        options = {
            "model": model,
            "smart_format": True,
            "punctuate": True,
            "measurements": True,
            "diarize_model": "latest",
        }

        audio_length = get_media_length(audio_file_path)
        start_time = get_current_datetime_humanfriendly()
        print(f"Start SDK Synchronous Deepgram Transcription at {start_time} for audio length of {audio_length}")

        # Call the transcribe method with an increased timeout
        response = deepgram.listen.rest.v("1").transcribe_file(
            payload, 
            options,
            timeout=httpx.Timeout(1800.0, connect=10.0)  # set timeout to be 30min
        )
        print("Response received successfully.")
        print('\n'.join(str(response).splitlines()[:5]))

        elapsed_time = get_elapsed_seconds(convert_to_epoch_seconds(start_time))
        transcribe_time_ratio = int(round(elapsed_time / convert_timestamp_to_seconds(audio_length)*100))
        print(f"Elapsed time is {convert_seconds_to_timestamp(elapsed_time)} which is {transcribe_time_ratio}% of the audio length")

        # Save the response to a JSON file
        json_file_path = audio_file_path.rsplit('.', 1)[0] + suffix + '.json'
        with open(json_file_path, "w") as json_file:
            json_file.write(response.to_json(indent=4))
        print(f"Transcription saved to {json_file_path}")

    except Exception as e:
        print(f"Error during transcription: {e}")

    return json_file_path
DG_CALLBACK_URL = 'https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/transcription'
MIMETYPES_MAP = {  # Supported MIME types mapping - USED IN transcribe_deepgram_callback
    'mp3': 'audio/mpeg',
    'mp4': 'audio/mp4',
    'mp2': 'audio/mpeg',
    'aac': 'audio/aac',
    'wav': 'audio/wav',
    'flac': 'audio/flac',
    'pcm': 'audio/l16',
    'm4a': 'audio/mp4',
    'ogg': 'audio/ogg',
    'opus': 'audio/opus',
    'webm': 'audio/webm',
}
def transcribe_deepgram_callback_lambda(audio_file_path, model, callback_url=DG_CALLBACK_URL):  # old version using deepfram-callback lambda function - deprecated for presigned s3
    """
    Transcribes the given audio file using the specified Deepgram model asynchronously with a callback URL.

    :param audio_file_path: path to the audio file to be transcribed.
    :param model: the Deepgram model to use for transcription.
    :param callback_url: URL to which Deepgram will send the transcription results.
    :return: Request ID from Deepgram indicating that the file has been accepted for processing.
    """
    from core.fileops import get_current_datetime_humanfriendly

    file_extension = audio_file_path.rsplit('.', 1)[1]
    if file_extension not in MIMETYPES_MAP:
        raise ValueError(f"File {audio_file_path} does not have a supported MIME type.")

    mimetype = MIMETYPES_MAP[file_extension]

    headers = {
        'Authorization': f'Token {DEEPGRAM_API_KEY}',
        'Content-Type': mimetype
    }

    # Set up the query parameters with the callback URL and callback headers
    params = {
        'callback': callback_url,
        'model': model,
        # diarize_model=latest replaces the deprecated diarize=true (v2 batch diarizer); do not set both.
        'diarize_model': 'latest', 'punctuate': 'true', 'measurements': 'true', 'smart_format': 'true',
        # 'keywords': 'Portola:5,Arastradero:5,Ladera:5,Rossotti:5,CERT:5'
    }

    with open(audio_file_path, 'rb') as file:
        audio_data = file.read()

    audio_length = get_media_length(audio_file_path)
    start_time = get_current_datetime_humanfriendly()
    print(f"Start Callback Deepgram Transcription at {start_time} for audio length of {audio_length}")
        
    response = post(
        url='https://api.deepgram.com/v1/listen',
        headers=headers,
        params=params,
        data=audio_data
    )

    # Adjusted to accept both 200 and 202 status codes as successful
    if response.status_code in (200, 202):        
        callback_response = response.json()
        request_id = callback_response.get('request_id', 'NO REQUEST_ID FIELD FOUND IN JSON')
        if request_id == 'NO REQUEST_ID FIELD FOUND IN JSON':
            print(f"Deepgram Callback FAIL - {request_id}")
        else:
            print(f"Deepgram Callback SUCCESS - request_id: {request_id}")
        base_audio_file_name = os.path.splitext(os.path.basename(audio_file_path))[0]
        return (request_id, base_audio_file_name)  # changed 11-1 to not return model

    else:
        raise Exception(f"Failed to submit audio: {response.text}, Status Code: {response.status_code}")

        # json_data = response.json()
        # with open('tests/test_data_files/transcribe/deepgram_response.json', 'r') as file:
        #     json_data = json.load(file)

        # request_id = json_data.get('request_id', 'NO REQUEST_ID FIELD FOUND IN JSON')
        # created_timestamp = json_data.get('created', 'NO CREATED FIELD FOUND IN JSON')

        # s3_bucket = 'fofpublic'
        # s3_path = 'deepgram-transcriptions'
        # cur_s3_object_name = f"{request_id}.json"
        # json_data = get_s3_json(s3_bucket, cur_s3_object_name, s3_path)
        # print(f"First characters of received JSON:\n\n{json.dumps(json_data)[:500]}")

        # created_timestamp = json_data.get('metadata', {}).get('created', 'NO CREATED FIELD FOUND IN JSON').replace(':', '').split('.')[0]
        
        # new_s3_object_name = f"{base_audio_file_name}_{created_timestamp}.json"
        # #rename_s3_object(s3_bucket, old_s3_object_name, new_s3_object_name, s3_path=s3_path)
        # return new_s3_object_name
def transcribe_deepgram_callback_lambda_sdk_prerecorded(audio_file_path, model, callback_url=DG_CALLBACK_URL):
    """
    Calls the Deepgram API to transcribe the given audio file using the specified Deepgram model,
    utilizing the SDK and callback functionality.

    :param audio_file_path: Path to the audio file to be transcribed.
    :param model: The Deepgram model to use for transcription.
    :param callback_url: The callback URL where Deepgram will send the transcription result.
    :return: Tuple containing the request_id, base_audio_file_name, and model.
    """
    from core.fileops import get_current_datetime_humanfriendly
    
    file_extension = audio_file_path.rsplit('.', 1)[-1]
    if file_extension not in MIMETYPES:
        raise ValueError(f"File {audio_file_path} does not have a supported MIME type.")

    mimetype = MIMETYPES[file_extension]
    deepgram = DeepgramClient()

    if model not in DG_MODEL_SUFFIX_MAP:
        raise ValueError("Invalid or absent Deepgram model.")

    try:
        print(f"Deepgram transcribing model: {model}  file: {audio_file_path}")

        # Read the audio file into a buffer

        with open(audio_file_path, 'rb') as audio:
            source = {'buffer': audio}

        # Configure Deepgram options
        # Passed as a dict (not PrerecordedOptions) so we can send diarize_model, which the
        # installed SDK's typed options don't expose. diarize_model="latest" replaces the
        # deprecated diarize=true (v2 batch diarizer); do not set both.
        options = {
            "model": model,
            "smart_format": True,
            "punctuate": True,
            "measurements": True,
            "diarize_model": "latest",
        }

        audio_length = get_media_length(audio_file_path)
        start_time = get_current_datetime_humanfriendly()
        print(f"Start SDK ThreadedDeepgram Transcription with Callback at {start_time} for audio length of {audio_length}")

        # Call the transcribe_url method with appropriate timeout
        url_response = deepgram.listen.rest.v("1").transcribe_url(
            callback_url, options
            #timeout=httpx.Timeout(30.0, connect=10.0)  # Short timeout since response is immediate with callback
        )

        # The response should include 'request_id'
        url_response_dict = url_response.to_dict()
        request_id = url_response_dict.get('request_id', 'NO REQUEST_ID FIELD FOUND IN RESPONSE')
        if request_id == 'NO REQUEST_ID FIELD FOUND IN RESPONSE':
            print(f"Deepgram Callback FAIL - {request_id}")
            raise Exception(f"Failed to get request_id from response: {url_response_dict}")
        else:
            print(f"Deepgram Callback SubmissionSUCCESS - request_id: {request_id}")
        base_audio_file_name = os.path.splitext(os.path.basename(audio_file_path))[0]
        return (request_id, base_audio_file_name, model)

    except httpx.TimeoutException as timeout_err:
        print(f"Timeout error: {timeout_err}")
        raise
    except httpx.HTTPError as http_err:
        print(f"HTTP error: {http_err}")
        raise
    except Exception as e:
        print(f"Error during transcription: {e}")
        raise

### NUMERAL CONVERT
def extract_context(line, match, context_radius):
    """ 
    Extracts a context window around a regex match within a string of text.

    :param line: string of text containing the match.
    :param match: regex match object containing the start and end positions of the match within the line.
    :param context_radius: integer specifying the number of words around the match to include in the context window.
    :return: string of text representing the context window around the match.
    """
 
    if match is None:
        raise ValueError("Match not found")

    # Define the number of words around the match to include in the context
    words = line.split()
    match_word_index = None

    # Find the index of the word that contains the match
    for index, word in enumerate(words):
        if match.start() >= line.find(word) and match.end() <= line.find(word) + len(word):
            match_word_index = index
            break

    if match_word_index is None:
        raise ValueError("Match not found within the words of the line")

    # Calculate the start and end indices for the context window
    context_start = max(match_word_index - context_radius, 0)
    context_end = min(match_word_index + context_radius + 1, len(words))

    # Extract the context window from the line
    context_window = ' '.join(words[context_start:context_end])
    return context_window
def print_num_exception(match_str, line_number, num_metadata_lines, printed_exceptions, exception_type, line):
    """ 
    Prints a message for numbers that are excluded from conversion and records the message.

    :param match_str: the string that matches the number to be excluded from conversion.
    :param line_number: the current line number in the file being processed.
    :param num_metadata_lines: the number of metadata lines in the file to adjust the actual line number.
    :param printed_exceptions: a list of exception messages that have already been printed.
    :param exception_type: the type of exception to be printed.
    :param line: the current line of text being processed.
    :return: None, but updates the printed_exceptions list with the new exception message if it hasn't been printed before.
    """
    match = re.search(re.escape(match_str), line)
    if match:
        exception_msg = f"Excluding conversion for {exception_type} at line {line_number+1+num_metadata_lines}: ...{extract_context(line, match, 5)}..."
        if exception_msg not in printed_exceptions:
            print(exception_msg)
            printed_exceptions.append(exception_msg)
    # DEBUG CODE to check if certain words are in english_vocab
    # debug_words = ["Like", "And", "Orca", "Shirley", "FTGSTKLOMNB"]
    # for word in debug_words:
    #     print(f"Is '{word}' in common_english_vocab? {'yes' if word.lower() in common_english_vocab else 'no'}")
def get_previous_word(substring, start_index):
    """ 
    Finds the word in a string that precedes the given start index.

    :param substring: the string from which to extract the previous word.
    :param start_index: the index in the string to start searching backward from.
    :return: the word found before the start index, or an empty string if no word is found.
    """
    # Find the last non-space character before the start_index
    word_end = start_index
    while word_end > 0 and substring[word_end-1].isspace():
        word_end -= 1
    # Find the start of the word
    word_start = word_end
    while word_start > 0 and not substring[word_start-1].isspace():
        word_start -= 1
    # Return the word found, if any
    return substring[word_start:word_end] if word_start != word_end else ""
def previous_word_exception(word, common_english_vocab, additional_exception_words):
    """ 
    Determines if a word is an exception based on its presence in additional exceptions or English vocabulary.

    :param word: the word to check for exception status.
    :param common_english_vocab: a set of common English words to compare against.
    :param additional_exception_words: a set of words that are always considered exceptions.
    :return: True if the word is an exception, False otherwise.
    """
    if word.lower() in additional_exception_words:
        #print(f"DEBUG: '{word}' before the number is in the additional exception list.")
        return True
    if word.istitle() and word.lower() not in common_english_vocab:
        #print(f"DEBUG: Capitalized '{word}' before the number is not in common English vocabulary.")
        return True
    return False
def convert_num_line_lowercase(line, num, num_str, line_number, num_metadata_lines, printed_exceptions, common_english_vocab):
    """ 
    Converts numbers in a line of text to their lowercase word equivalents, skipping exceptions.

    :param line: The line of text in which to convert numbers.
    :param num: The numerical value to convert to words.
    :param num_str: The string representation of the number to find in the line.
    :param line_number: The current line number in the text being processed.
    :param num_metadata_lines: The number of metadata lines in the text before the content.
    :param printed_exceptions: A set to record exceptions that have been printed.
    :param common_english_vocab: A set of common English vocabulary words.
    :return: A tuple containing the modified line and the total number of substitutions made.
    """
    num_subs_total = 0
    current_index = 0
    additional_exception_words = ["step"]
    while current_index < len(line):
        if line[current_index].isdigit():
            # Check if the digit is adjacent to any characters that are not digits or allowed punctuation
            if (current_index > 0 and not line[current_index-1] in '0123456789.,?! \n') or \
               (current_index < len(line) - 1 and not line[current_index+1] in '0123456789.,?! \n'):
                # Search forward until a space or a new line is found
                while current_index < len(line) and not line[current_index] in ' \n':
                    current_index += 1
                continue
            # Skip conversion if the digit is part of a decimal number (e.g., "1.0")
            if current_index < len(line) - 1 and not line[current_index+1].isdigit() and \
               current_index + 2 < len(line) and line[current_index+2].isdigit():
                current_index += 3  # Skip past the decimal point and the following digit(s)
                while current_index < len(line) and (line[current_index].isdigit() or line[current_index].isspace() or line[current_index] in '.,!?'):
                    current_index += 1
                continue
            # Check if the character directly before the number is a period, then skip conversion
            if current_index > 0 and line[current_index-1] == '.':
                    current_index += 2  # Skip past the period and the decimal point
                    while current_index < len(line) and line[current_index].isdigit():
                        current_index += 1
                    continue
            # Skip conversion if the number starts the line or is preceded only by whitespace and followed by a period and a space
            if (current_index == 0 or (current_index > 0 and line[:current_index].isspace())) and \
               (current_index + 1 < len(line) and line[current_index+1] == '.' and \
                (current_index + 2 < len(line) and line[current_index+2] == ' ')):
                current_index += 3  # Skip past the period and the space
                continue
            end_index = current_index + 1
            while end_index < len(line) and line[end_index].isdigit():
                end_index += 1
            number_str = line[current_index:end_index]
            if number_str == num_str:
                previous_word = get_previous_word(line, current_index)
                if not previous_word_exception(previous_word, common_english_vocab, additional_exception_words):
                    new_line, num_subs = re.subn(r'\b' + re.escape(num_str) + r'\b', num2words(num), line[current_index:], 1)
                    num_subs_total += num_subs
                    line = line[:current_index] + new_line
                    current_index = end_index
                else:
                    print_num_exception(line[current_index:end_index], line_number, num_metadata_lines, printed_exceptions, "proper name", line)
            current_index = end_index
        else:
            current_index += 1
    return line, num_subs_total
    # old comment - need to fix $3zero - found in FloodLAMP_Demo13_Plate_v1.md 'It cost about $30, but super helpful.'
def convert_num_line_capitalization(line, num, num_str):
    """ 
    Capitalize the numeral word at the beginning of a sentence or after punctuation.

    :param line: the line of text in which to perform capitalization.
    :param num: the numerical value to convert to words.
    :param num_str: the string representation of the number to find in the line.
    :return: a tuple containing the modified line and the total number of substitutions made.
    """
    num_subs_total = 0
    for punctuation in ['.', '?', '!']:
        # Include comma in the lookahead assertion
        pattern = r'(^|[' + re.escape(punctuation) + r']\s)' + re.escape(num_str) + r'(?=[\s,]|$)'
        new_line, num_subs = re.subn(pattern, lambda match: match.group(1) + num2words(num).capitalize(), line)
        num_subs_total += num_subs
        if num_subs > 0:
            line = new_line
    return line, num_subs_total
def skip_speaker_line_with_timestamp(line):
    """ 
    Determine if a line contains a single timestamp with max_words before the timestamp less that get_timestamp default val (8) and is therefore a speaker line to skip.

    :param line: The line of text to be checked for a timestamp.
    :return: boolean where True if a timestamp is found, otherwise False.
    """
    from core.fileops import get_timestamp
    timestamp_result = get_timestamp(line)
    return timestamp_result and any(value is not None for value in timestamp_result)
def convert_num_lines(lines, num, num_str, num_metadata_lines, verbose, printed_exceptions):
    """ 
    Converts numbers in lines of text to their word equivalents, handles capitalization, and skips lines with timestamps.
    Takes both num and num_str as separate parameters to provide flexibility in how the function is called.
    This design allows the caller to specify the string representation of the number 1 that should be searched for within the text lines,
    which may not always be a straightforward string conversion of num.
    For example, num could be an integer, but num_str could be a formatted string that represents the number
    in a specific way within the text (e.g., "001" instead of "1", or "1st" for the ordinal form).
    
    :param lines: list of text lines to process.
    :param num: the numerical value to convert to words.
    :param num_str: the string representation of the number to find in the lines.
    :param num_metadata_lines: the number of metadata lines in the document to adjust line numbering for output.
    :param verbose: boolean indicating whether to print the conversion output.
    :param printed_exceptions: list to record any exceptions encountered during processing.
    :return: tuple containing the list of processed lines and the total number of substitutions made.
    """
    num_subs_total = 0
    for i, line in enumerate(lines):
        if skip_speaker_line_with_timestamp(line):
            continue  # Skip lines with timestamps
        line, num_subs = convert_num_line_capitalization(line, num, num_str)
        num_subs_total += num_subs
        if num_subs > 0 and verbose:
            print(f"  convert in line {i+1+num_metadata_lines} the number: {num}")
        line, num_subs = convert_num_line_lowercase(line, num, num_str, i, num_metadata_lines, printed_exceptions, common_english_vocab)
        num_subs_total += num_subs
        lines[i] = line  # Update the line in lines
    return lines, num_subs_total
def convert_numbers_in_content(content, num_limit, additional_numbers, num_metadata_lines, print_output):
    """ 
    Converts numerical values in text content to their word equivalents, excluding lines with timestamps.

    :param content: string containing the text content to be processed.
    :param num_limit: integer representing the upper limit for numbers to convert.
    :param additional_numbers: list of additional numbers to be converted outside the standard range.
    :param num_metadata_lines: integer representing the number of metadata lines in the content.
    :param print_output: boolean indicating whether to print the conversion output.
    :return: tuple containing the converted content as a string and the total number of substitutions made.
    """
    lines = content.split('\n')  # Break the content into lines
    num_subs_total = 0  # Initialize counter for the number of conversions
    printed_exceptions = []  # Initialize a list to keep track of printed exceptions
    for num in list(range(num_limit)) + additional_numbers:  # Loop over all numbers from 0 to 9 and additional numbers
        num_str = str(num)  # Convert the number to a string
        lines, num_subs = convert_num_lines(lines, num, num_str, num_metadata_lines, print_output, printed_exceptions)
        num_subs_total += num_subs
        #print(f"Convert number {num} with conversions: {num_subs}")
    return '\n'.join(lines), num_subs_total
def convert_ordinals_in_content(content, punct_capitalization):
    """ 
    Converts ordinal numbers in a string of text to their word equivalents and capitalizes words following specified punctuation.

    :param content: string of text containing ordinal numbers and punctuation.
    :param punct_capitalization: list of punctuation characters after which the following word should be capitalized.
    :return: string of text with ordinal numbers converted and words capitalized as specified.
    """

    ordinal_map = {
        '1st': 'first', '2nd': 'second', '3rd': 'third', '4th': 'fourth',
        '5th': 'fifth', '6th': 'sixth', '7th': 'seventh', '8th': 'eighth',
        '9th': 'ninth'
    }
    converted_content = content
    for ordinal, word in ordinal_map.items():
        converted_content = re.sub(r'\b' + re.escape(ordinal) + r'\b', word, converted_content)
    # Capitalize where necessary
    for punctuation in punct_capitalization:
        pattern = r'(^|[' + re.escape(punctuation) + r']\s)(\w)'
        converted_content = re.sub(pattern, lambda match: match.group(1) + match.group(2).upper(), converted_content)
    return converted_content
    # DONE fill in code to change "1st" to "first", "2nd" to "second", etc. up to "9th"
    # DONE fill in code to capilatize when needed as is done in @convert_nums_to_words
def convert_nums_to_words(file_path, verbose=False):
    """
    Converts numerals in the content of a file to their corresponding words, appends a specified suffix to the filename, and creates a new file with the converted content.

    :param file_path: string of the path to the original file.
    :param verbose: boolean for printing verbose messages. Defaults to False.
    :return: string of the path to the newly created file with the converted content.
    """
    from core.fileops import read_file_flex, write_metadata_and_content, verbose_print

    num_limit = 10  # number up to which will be converted plus any additional numbers
    additional_numbers = [1000000, 1000000000, 1000000000000]
    metadata, content = read_file_flex(file_path)
    
    # Handle case where metadata is None (no metadata in file)
    num_metadata_lines = 0 if metadata is None else len(metadata.splitlines())
    
    content = convert_ordinals_in_content(content, ['.', '?', '!'])
    converted_content, num_subs_total = convert_numbers_in_content(content, num_limit, additional_numbers, num_metadata_lines, verbose)

    verbose_print(verbose, "Review and fix manually: addresses")
    verbose_print(verbose, f"END convert_nums_to_words - Conversion Count: {num_subs_total}\n")
    write_metadata_and_content(file_path, metadata, converted_content, overwrite='yes')
    return file_path  # Return the path of the modified file

### SPEAKER NAMES
def read_speaker_names_from_json(json_file_path):
    """ 
    Reads speaker names from a JSON file's metadata, which have been inserted by us and are not in the raw deepgram json files.

    :param json_file_path: string of the path to the JSON file.
    :return: list of speaker names if they exist, otherwise an empty list.
    """ 
    if not os.path.exists(json_file_path):
        raise ValueError(f"The file path does not exist for {json_file_path}.")
    with open(json_file_path, 'r') as file:
        data = json.load(file)

    # Return the speaker_names if they exist in the metadata
    return data.get('metadata', {}).get('speaker_names', [])
def write_speaker_names_to_json(json_file_path, speaker_names, verbose=False):
    """ 
    Writes speaker names to a JSON file's metadata. Overwrites file.

    :param json_file_path: string of the path to the JSON file.
    :param speaker_names: list of strings containing speaker names.
    :return: None.
    """ 
    from core.fileops import verbose_print

    if not os.path.exists(json_file_path):
        raise ValueError(f"The file path does not exist for {json_file_path}.")
    # Read the existing JSON file's content
    with open(json_file_path, 'r') as file:
        data = json.load(file)

    # Initialize a flag to check if speaker_names have been updated
    speaker_names_updated = False

    # Check if 'metadata' exists and if 'speaker_names' is present
    if 'metadata' in data and 'speaker_names' in data['metadata']:
        # If the new speaker_names are different from the existing ones, update them
        if data['metadata']['speaker_names'] != speaker_names:
            data['metadata']['speaker_names'] = speaker_names
            speaker_names_updated = True
    else:
        # If 'metadata' does not exist or 'speaker_names' is not present, create 'metadata' with speaker_names
        data.setdefault('metadata', {}).update({'speaker_names': speaker_names})
        speaker_names_updated = True

    # Write the modified data back to the JSON file
    with open(json_file_path, 'w') as file:
        json.dump(data, file, indent=4)

    # Print a statement to the console if the speaker_names have been updated
    if speaker_names_updated:
        verbose_print(verbose, f"Speaker names in the JSON have been updated.")
    else:
        verbose_print(verbose, f"Speaker names in the JSON are unchanged.")
def find_unassigned_speakers(md_file_path, verbose=False):
    """ 
    Identifies speakers in the markdown file who do not have assigned names.
    This is determined by if the line has a valid timestamp and then looking for 'Speaker X' before the timestamp.

    :param md_file_path: string of the path to the markdown file.
    :return: list of strings of unassigned speaker names, or None if all speakers are assigned.
    """
    from core.fileops import verbose_print, get_timestamp
    
    if not os.path.exists(md_file_path):
        raise ValueError(f"The file path does not exist for {md_file_path}.")

    unassigned_speaker_numbers = []
    with open(md_file_path, 'r') as md_file:
        for line in md_file:
            timestamp_index = get_timestamp(line)
            if timestamp_index:
                # Search for unnamed speaker pattern before the timestamp
                match = re.search(r"Speaker\s+(\d+)", line[:timestamp_index[1]])
                if match:
                    speaker_number = int(match.group(1))
                    if speaker_number not in unassigned_speaker_numbers:
                        unassigned_speaker_numbers.append(speaker_number)

    # Sort the list of unassigned speaker numbers
    unassigned_speaker_numbers.sort()

    # Convert the sorted list of numbers to the required string format
    unassigned_speakers = [f"Speaker {number}" for number in unassigned_speaker_numbers]

    num_unassigned = len(unassigned_speakers)
    if num_unassigned > 0:
        verbose_print(verbose, f"From find_unassigned_speakers - Number of speakers not assigned names: {num_unassigned}. Speaker names: {' '.join(unassigned_speakers)}")
        return unassigned_speakers
    else:
        verbose_print(verbose, f"From find_unassigned_speakers - All speakers have been assigned names.")
        return None
    # DONE fill in code to find all speakers without names assigned ('Speaker X') using code similar to @propagate_speaker_names_throughout_md
    # DONE fill in code to print the number of speakers not assigned followed by the specific speaker numbers, as a single print line
    # DONE return a list of the unassigned speaker numbers or NONE
# TODO think this is done but double check - change to propagate the speaker assignment backwards as well as forwards in the Markdown file.
def propagate_speaker_names_throughout_md(md_file_path, input_speaker_names=None):
    """
    Propagates speaker names throughout a markdown file based on provided input names or existing assignments.

    :param md_file_path: string of the path to the markdown file.
    :param input_speaker_names: list of tuples with speaker numbers and names, if available.
    :return: list of tuples with speaker numbers and names after propagation.
    """
    from core.fileops import get_timestamp

    # Initialize speaker names list based on input
    speaker_names = input_speaker_names.copy() if input_speaker_names else []

    # Read the content of the markdown file
    with open(md_file_path, 'r') as file:
        content = file.readlines()

    updated_content = []
    for i, line in enumerate(content):
        # Extract timestamp index from the line
        _, index = get_timestamp(line, max_words=10)
        if index is not None:
            # Search for speaker name assignment before the timestamp
            match = re.search(r"Speaker\s+(\d+)\s*=\s*(.+)", line[:index])
            if match:
                speaker_num, name = match.groups()
                speaker_num = int(speaker_num)  # Ensure speaker number is an integer
                name = name.strip()
                # Add new speaker name if not already in the list
                if (speaker_num, name) not in speaker_names:
                    speaker_names.append((speaker_num, name))
                # Update the line with the speaker name and timestamp
                line = f"{name}  {line[index:].lstrip()}"
            else:
                # Replace speaker placeholders with names throughout the document
                for spkr_num, spkr_name in speaker_names:
                    line = re.sub(rf"\bSpeaker {spkr_num}\b\s*", f"{spkr_name}  ", line)

        updated_content.append(line)

    # After the forward pass, perform a backward pass to propagate names to earlier mentions
    for i in range(len(updated_content) - 1, -1, -1):
        line = updated_content[i]
        _, index = get_timestamp(line, max_words=10)
        if index is not None:
            for spkr_num, spkr_name in speaker_names:
                line = re.sub(rf"\bSpeaker {spkr_num}\b\s*", f"{spkr_name}  ", line)
            updated_content[i] = line    

    # Write the updated content back to the markdown file
    with open(md_file_path, 'w') as file:
        file.writelines(updated_content)

    # Sort the speaker names by speaker number for consistency
    speaker_names.sort(key=lambda x: x[0])
    return speaker_names
def iterate_input_speaker_names(md_file_path, input_speaker_names=None):
    """
    Iterates over input speaker names and updates the markdown file until the user decides to exit.

    :param md_file_path: string of the path to the markdown file.
    :param input_speaker_names: list of tuples with speaker numbers and names, if available.
    :return: list of tuples with speaker numbers and names after all iterations.
    """
    if not os.path.exists(md_file_path):
        raise ValueError(f"The file path does not exist for {md_file_path}.")

    overall_speaker_names = input_speaker_names.copy() if input_speaker_names else []

    while True:
        current_speaker_names = propagate_speaker_names_throughout_md(md_file_path, overall_speaker_names)
        
        for speaker_name in current_speaker_names:
            if speaker_name not in overall_speaker_names:
                overall_speaker_names.append(speaker_name)
        
        overall_speaker_names.sort(key=lambda x: x[0])
        
        if not overall_speaker_names:
            print("No Speaker Names")
        else:
            print("Current speaker_names:")
            for num, name in overall_speaker_names:
                print(f"Speaker {num}: {name}")
        
        continue_prompt = input("\nASSIGN SPEAKER NAMES NOW - hit enter to continue or E/exit to exit: ").strip().lower()
        if continue_prompt == '':
            continue
        elif continue_prompt in ['e', 'exit']:
            unassigned_speakers = find_unassigned_speakers(md_file_path)
            if unassigned_speakers:
                print("Unassigned speakers:")
                for spkr in unassigned_speakers:
                    print(f"  {spkr}")
            else:
                print("All speakers have been assigned.")
            print("\nAssigned speaker names:")
            for num, name in overall_speaker_names:
                print(f"  Speaker {num}: {name}")
            return overall_speaker_names
        else:
            print("Invalid input. Please either hit enter to continue or type 'E'/'Exit' to exit.")
def assign_speaker_names(md_file_path):
    """
    Assigns speaker names to markdown file by reading from a corresponding JSON file, updating, and writing back to the json if changed.
    Prompts the user iteratively through assigning the names.
    
    :param md_file_path: string of the path to the markdown file.
    :return: None
    """
    json_file_path = md_file_path.replace('.md', '.json')
    try:
        with open(json_file_path, 'r') as file:
            # Check if there is a corresponding JSON file
            speaker_names = read_speaker_names_from_json(json_file_path)
    except FileNotFoundError:
        # If the JSON file does not exist, start with an empty list
        speaker_names = []

    # Iterate over speaker_names and update them
    updated_speaker_names = iterate_input_speaker_names(md_file_path, speaker_names)

    # Check if the updated speaker_names are different from the original ones
    if updated_speaker_names != speaker_names:
        # Write the updated speaker_names back to the JSON file
        write_speaker_names_to_json(json_file_path, updated_speaker_names)

### TRANSCRIBE WRAPPER
def create_transcript_md_from_json(json_file_path, combine_segs=True):
    """
    Creates a markdown transcript from a JSON file containing Deepgram transcription data.
    If combine_segs is True, combines consecutive segments from the same speaker.

    :param json_file_path: string of the path to the json file containing transcription data.
    :param combine_segs: boolean indicating whether to combine consecutive segments from the same speaker.
    :return: string of the path to the created markdown file or None if the json file is not valid.
    """
    from core.fileops import create_initial_metadata, convert_seconds_to_timestamp, set_metadata_field
    from core.fileops import write_metadata_and_content, add_timestamp_links
    
    md_file_path = json_file_path[:-5] + ".md"
    link = get_link_from_json_metadata(json_file_path)
    lines = []

    if not validate_transcript_json(json_file_path):
        return None

    with open(json_file_path, "r") as file:
        data = json.load(file)
        model_name = data["metadata"]["model_info"][list(data["metadata"]["model_info"].keys())[0]]["name"]
        paragraph_data = data["results"]["channels"][0]["alternatives"][0]["paragraphs"]["paragraphs"]

        # Initialize current paragraph information
        curr_speaker = None
        curr_timestamp = None
        curr_transcript = ""

        for para in paragraph_data:
            speaker_id = str(para['speaker'])  # Keep speaker_id as string
            speaker = f'Speaker {speaker_id}'

            start_timestamp = convert_seconds_to_timestamp(para['start'])

            # Extract sentences from paragraph and join them
            sentences = para.get('sentences', [])
            transcript = ' '.join(sentence.get('text', '') for sentence in sentences)

            if combine_segs and speaker == curr_speaker:
                # If combine_segs is True and the speaker is the same as the previous paragraph, continue accumulating the transcript
                curr_transcript += " " + transcript
            else:
                # If it's a new speaker, write the accumulated transcript to lines, then reset curr_speaker, curr_timestamp, and curr_transcript
                if curr_transcript:
                    # Add speaker, timestamp and transcript to lines
                    lines.extend([curr_speaker + '  ' + curr_timestamp, curr_transcript, ''])
                curr_speaker = speaker
                curr_timestamp = start_timestamp
                curr_transcript = transcript

        # Write the last paragraph to lines
        if curr_transcript:
            lines.extend([curr_speaker + '  ' + curr_timestamp, curr_transcript, ''])

    content = "## content\n\n### transcript\n\n" + "\n".join(lines)
    #print(f"DEBUG - content: {content}")
    metadata = create_initial_metadata()
    date_today = datetime.now().strftime("%m-%d-%Y") # Assign today's date in format MM-DD-YYY
    metadata = set_metadata_field(metadata, 'last updated', date_today + ' Created')  
    metadata = set_metadata_field(metadata, 'link', link)
    metadata = set_metadata_field(metadata, 'transcript source', 'deepgram '+model_name+'-dl')
    
    write_metadata_and_content(md_file_path, metadata, content, overwrite='yes')
    convert_nums_to_words(md_file_path)
    add_timestamp_links(md_file_path)
    return md_file_path
def process_deepgram_transcription_sync(title, link, model, output_dir="data/audio_inbox", skip_download=False):  # unittests 1 TEMP SKIPPED
    """
    Processes a Deepgram transcription from a YouTube video link by downloading the audio, transcribing it, and creating a markdown transcript.

    :param title: the title of the video used to name the downloaded audio file.
    :param link: the YouTube link to the video to be transcribed.
    :param model: the Deepgram model used for transcription.
    :param output_dir: the directory path where the audio file will be downloaded.
    :param skip_download: if True, will use existing audio file instead of redownloading.
    :return: the path to the created markdown file or None if transcription fails.
    """
    # Download the audio file
    audio_file_path = download_mp3_from_youtube(link, title, output_dir, skip_download)
    
    # Transcribe the downloaded audio file
    json_file_path = transcribe_deepgram_sync(audio_file_path, model)
    if json_file_path is None:
        print("transcription failed or the file type is incorrect.")
        return None
    print(json_file_path)

    # Add the YouTube link to the transcription JSON
    add_link_to_json_metadata(json_file_path, link)

    # Create a markdown transcript from the JSON file and process it
    md_file_path = create_transcript_md_from_json(json_file_path)
    
    # Assign speaker names to the markdown transcript
    assign_speaker_names(md_file_path)
    
    return md_file_path
def process_deepgram_transcription_sync_from_audio_file(audio_file_path, link, model):  # unittests 1 TEMP SKIPPED
    """ 
    Transcribes an audio file using the Deepgram service, adds the YouTube link to the transcription, creates a markdown transcript, and assigns speaker names.

    :param audio_file_path: string of the path to the audio file to be transcribed.
    :param link: string of the youtube link to be added to the transcription json.
    :param model: string of the deepgram model to be used for transcription.
    :return: string of the path to the markdown file with the completed transcription or None if transcription fails.
    """
    # Transcribe the downloaded audio file
    json_file_path = transcribe_deepgram_sync(audio_file_path, model)
    if json_file_path is None:
        raise ValueError("Transcription failed or the file type is incorrect.")
    # Add the YouTube link to the transcription JSON
    add_link_to_json_metadata(json_file_path, link)

    # Create a markdown transcript from the JSON file and process it
    md_file_path = create_transcript_md_from_json(json_file_path)

    # Assign speaker names to the markdown transcript
    assign_speaker_names(md_file_path)

    return md_file_path

def transcribe_deepgram_callback_presigneds3(audio_file_path, model):
    """
    Upload the local audio file to S3 (if not already there).
    Generate a GET presigned URL for Deepgram to read it,
    Generate a PUT presigned URL for Deepgram to write the transcript
    (with a name derived from the audio filename + model suffix),
    and kick off the asynchronous transcription with callback=PUT.

    :param audio_file_path: Local path to the audio file
    :param model: Deepgram model, e.g. 'nova', mapped by DG_MODEL_SUFFIX_MAP
    :return: (request_id, transcript_s3_key, base_audio_file_name, s3_bucket)
    """
    from core.aws import upload_file_to_s3, generate_presigned_s3_url
    
    # Pull your model suffix here
    suffix = DG_MODEL_SUFFIX_MAP[model]

    # 1) Define your bucket and object keys
    s3_bucket = '[S3-BUCKET]'
    base_audio_file_name = os.path.basename(audio_file_path)  # e.g. "my_audio.mp3"
    audio_s3_key = f"audio/{base_audio_file_name}"

    # 2) Upload to S3 (audio folder).
    upload_file_to_s3(
        file_path=audio_file_path,
        bucket=s3_bucket,
        object_name=base_audio_file_name,  # S3 uses the file's basename
        s3_path='audio'
    )

    # 3) Generate a GET presigned URL for Deepgram to access the audio
    presigned_get_url = generate_presigned_s3_url(
        bucket=s3_bucket,
        object_key=audio_s3_key,
        method='get',
        expire_seconds=1800  # 30 min, adjust as needed
    )

    # 4) Generate a descriptive S3 key for the final transcript in 'transcripts' folder
    #    Example: transcripts/<my_audio>_<suffix>_<uuid>.json
    file_root, _ext = os.path.splitext(base_audio_file_name)
    transcript_s3_key = f"transcripts/{file_root}{suffix}.json"

    # 5) Generate a PUT presigned URL for Deepgram to write the transcript
    presigned_put_url = generate_presigned_s3_url(
        bucket=s3_bucket,
        object_key=transcript_s3_key,
        method='put',
        content_type='application/json',
        expire_seconds=1800
    )

    # 6) Call Deepgram asynchronously
    headers = {
        'Authorization': f'Token {DEEPGRAM_API_KEY}'
    }
    params = {
        'model': model,
        'callback': presigned_put_url,
        'callback_method': 'put',
        'smart_format': 'true',
        # diarize_model=latest replaces the deprecated diarize=true (v2 batch diarizer); do not set both.
        'diarize_model': 'latest',
        'punctuate': 'true',
        'measurements': 'true'
    }
    source = {'url': presigned_get_url}

    start_time = get_current_datetime_humanfriendly()
    print(f"Start Callback Deepgram Transcription at {start_time} using presigned URLs.")

    try:
        response = requests.post('https://api.deepgram.com/v1/listen', headers=headers, params=params, json=source)
    except requests.exceptions.SSLError as ssl_err:
        print(f"SSL error: {ssl_err}")
        raise
    except requests.exceptions.RequestException as req_err:
        print(f"Request error: {req_err}")
        raise

    if response.status_code not in (200, 202):
        raise Exception(f"Failed to submit audio: {response.text}, Status Code: {response.status_code}")

    # 7) Extract the request_id from the Deepgram response
    callback_response = response.json()
    request_id = callback_response.get('request_id', 'NO_REQUEST_ID_FOUND')
    if request_id == 'NO_REQUEST_ID_FOUND':
        print("WARNING: Deepgram response did not return request_id.")

    print(f"Deepgram Callback SUCCESS - request_id: {request_id}")

    # Return everything the downstream code needs
    return (request_id, transcript_s3_key, base_audio_file_name, s3_bucket)
def process_deepgram_transcription_callback_presigneds3(title, link, model, output_dir="data/audio_inbox", audio_file_path=None):
    """
    Download or reuse local audio, then send it to Deepgram with presigned S3 callback.
    Write a "waiting file" with everything needed to later retrieve the final transcript from S3.

    :param title: The title (for naming local waiting file).
    :param link: The YouTube link (for metadata).
    :param model: The Deepgram model key (maps to suffix).
    :param output_dir: Where to store local audio + waiting file.
    :param audio_file_path: If provided, skip YouTube download and use this local file.
    :return: The path to the created waiting file.
    """
    print(f"\nStarting process_deepgram_transcription_callback_presigneds3 for title: {title}")
    
    waiting_prefix = "WAITING-CALLBACK_"
    suffix = DG_MODEL_SUFFIX_MAP[model]
    print(f"Using model: {model} with suffix: {suffix}")
    
    # 1) Possibly download from YouTube
    if audio_file_path is None:
        print("No audio file provided - downloading from YouTube...")
        audio_file_path = download_mp3_from_youtube(link, title, output_dir)
        downloaded_from_youtube = True
    else:
        print(f"Using provided audio file: {audio_file_path}")
        downloaded_from_youtube = False

    # 2) Transcribe with presigned S3 callback
    print("Starting Deepgram transcription with presigned S3 callback...")
    (callback_request_id, transcript_s3_key, base_audio_file_name, s3_bucket) = transcribe_deepgram_callback_presigneds3(
        audio_file_path,
        model
    )
    print(f"Transcription initiated - request ID: {callback_request_id}")

    # 3) Create a local "waiting" file with all info needed to retrieve final transcript
    waiting_file_name = f"{waiting_prefix}{title}{suffix}.txt"
    waiting_file_path = os.path.join(output_dir, waiting_file_name)
    print(f"Creating waiting file at: {waiting_file_path}")
    
    with open(waiting_file_path, 'w') as f:
        f.write(f"request_id: {callback_request_id}\n")
        f.write(f"bucket: {s3_bucket}\n")
        f.write(f"object_key: {transcript_s3_key}\n")
        f.write(f"link: {link}\n")
        f.write(f"model: {model}\n")
    
    print(f"Created waiting file at: {waiting_file_path}")
    with open(waiting_file_path, 'r') as f:
        print(f"File contents:\n{f.read()}\n")

    # 4) If we downloaded the audio from YouTube, remove it locally
    if downloaded_from_youtube and os.path.exists(audio_file_path):
        print(f"Cleaning up - removing downloaded audio file: {audio_file_path}")
        os.remove(audio_file_path)
        print(f"Removed downloaded audio file: {audio_file_path}")
    
    print(f"Process completed successfully. Waiting file created at: {waiting_file_path}")
    return waiting_file_path
def download_deepgram_callback_waiting(local_folder="data/audio_inbox", prefix="WAITING-CALLBACK_"):
    from core.aws import download_file_from_s3
    import os

    waiting_files = [
        os.path.join(local_folder, f)
        for f in os.listdir(local_folder)
        if f.startswith(prefix)
    ]

    for waiting_file in waiting_files:
        with open(waiting_file, 'r') as f:
            content = f.read()
            lines = content.split('\n')
            
            request_id = None
            bucket = None
            object_key = None
            link = None
            model = None

            for line in lines:
                if line.startswith('request_id:'):
                    request_id = line.split('request_id:')[1].strip()
                elif line.startswith('bucket:'):
                    bucket = line.split('bucket:')[1].strip()
                elif line.startswith('object_key:'):
                    object_key = line.split('object_key:')[1].strip()
                elif line.startswith('link:'):
                    link = line.split('link:')[1].strip()
                elif line.startswith('model:'):
                    model = line.split('model:')[1].strip()

            if not object_key or not bucket:
                print(f"Warning: No object_key or bucket found in {waiting_file}. Skipping.")
                continue

            # Download that object_key from S3
            # e.g. 'transcripts/MyAudio_nova_1234.json' from bucket '[S3-BUCKET]'
            local_json_path = download_file_from_s3(
                bucket=bucket,
                key=os.path.basename(object_key),     # e.g. 'MyAudio_nova_1234.json'
                s3_path=os.path.dirname(object_key),  # e.g. 'transcripts'
                local_folder=local_folder
            )
            print(f"DEBUG - object_key => {object_key}, local_json_path => {local_json_path}")

            if local_json_path:
                # Construct a final local name if desired
                waiting_base = os.path.basename(waiting_file)[len(prefix):-4]  # remove prefix & ".txt"
                new_json_path = os.path.join(local_folder, f"{waiting_base}.json")
                
                os.rename(local_json_path, new_json_path)
                os.remove(waiting_file)
                
                # Insert link into the JSON, or do additional processing
                add_link_to_json_metadata(new_json_path, link)
                md_file_path = create_transcript_md_from_json(new_json_path)
                
                print(f"Processed WAITING file => created MD file: {md_file_path}")

def process_multiple_videos(videos_to_process, model='both', bool_callback=True, bool_youtube=True):  # unittests 1 MOCK
    """
    Processes multiple videos by transcribing them and creating YouTube markdown files if bool_youtube is True.

    :param videos_to_process: list of tuples containing the title and link of each video to be processed.
    :param model: string of the deepgram model to be used for transcription. 'both' will run both whisper-medium and nova-2-general models.
    :param bool_callback: boolean indicating whether to use callback transcription. Defaults to True.
    :param bool_youtube: boolean indicating whether to create YouTube markdown files. Defaults to True.
    :return: None
    """
    local_folder = "data/audio_inbox"
    prefix = "WAITING-CALLBACK_"
    
    for title, link in videos_to_process:
        try:
            if model == 'both':
                # Run both Whisper Medium and Nova 2 models
                model1 = 'whisper-medium'
                model2 = 'nova-2-general'
                if bool_callback:
                    process_deepgram_transcription_callback_presigneds3(title, link, model1)
                    process_deepgram_transcription_callback_presigneds3(title, link, model2)
                else:
                    process_deepgram_transcription_sync(title, link, model1)
                    process_deepgram_transcription_sync(title, link, model2)
            else:
                # Run single specified model
                if bool_callback:
                    process_deepgram_transcription_callback_presigneds3(title, link, model)
                else:
                    process_deepgram_transcription_sync(title, link, model)
                    
            if bool_youtube:
                create_youtube_md(link, title)
        except ValueError as e:
            print(f"Error processing video {title}: {e}")
        # schedule_recurring_task(
        #     interval_minutes=5,
        #     check_function=lambda: check_for_waiting_files(local_folder, prefix),
        #     work_function=lambda: download_deepgram_callback_waiting(local_folder, prefix),
        #     max_runs=5
        # )
# TODO: Fix these
def check_for_waiting_files(local_folder="data/audio_inbox", prefix="WAITING-CALLBACK_"):
    """
    Checks if there are any waiting files in the specified folder with the given prefix.
    
    :param local_folder: string of the path to check for waiting files. Defaults to "data/audio_inbox"
    :param prefix: string prefix of waiting files to look for. Defaults to "WAITING-CALLBACK_"
    :return: boolean indicating whether any waiting files were found
    """
    waiting_files = [f for f in os.listdir(local_folder) if f.startswith(prefix)]
    num_waiting = len(waiting_files)
    print(f"CHECK_FOR_WAITING_FILES - Found {num_waiting} waiting files")
    return num_waiting > 0
def schedule_recurring_task(interval_minutes, check_function, work_function, max_runs=1, run_immediately=True):
    """
    Schedules a recurring task that runs work_function when check_function returns True.
    Can be configured to perform an immediate first check and terminate after a specific number of executions.

    :param interval_minutes: Number of minutes between checks
    :param check_function: Function that returns a boolean indicating whether work_function should run
    :param work_function: Function to execute when check_function returns True
    :param max_runs: Maximum number of times to run work_function before terminating. None for infinite runs
    :param run_immediately: Whether to perform an immediate check before starting the schedule. Defaults to True
    :return: None
    """
    import schedule
    import time
    from core.fileops import get_current_datetime_humanfriendly

    runs_completed = 0

    def job():
        nonlocal runs_completed
        print(f"\nRun #{runs_completed + 1} - Checking {check_function.__name__}...")
        if check_function():
            print(f"Check passed - Running {work_function.__name__}")
            work_function()
            runs_completed += 1
            if max_runs is not None and runs_completed >= max_runs:
                # Clear all scheduled jobs and return False to stop the scheduler
                schedule.clear()
                return schedule.CancelJob
        else:
            print(f"Check not passed - Not running {work_function.__name__}")

    # Perform immediate first check if requested
    if run_immediately:
        job()
    
    # If we haven't hit max_runs, schedule recurring checks
    if runs_completed < (max_runs or float('inf')):
        # Schedule the job to run every interval_minutes
        schedule.every(interval_minutes).minutes.do(job)

        # Keep running until all jobs are cleared (when max_runs is reached)
        while len(schedule.get_jobs()) > 0:
            schedule.run_pending()
            now = get_current_datetime_humanfriendly()
            print(f"\nWaiting {interval_minutes} minutes from {now} until next check...")
            time.sleep(1)



# END OF FILE transcribe.py
