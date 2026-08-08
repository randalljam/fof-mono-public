# ===== START OF FILE core/video.py =====
# Library of functions and execution code to process video files

import os
import sys
import yt_dlp as youtube_dl
import cv2  # pip install opencv-python
import pytesseract
from PIL import Image
import numpy as np
import glob
import csv
import shutil
import time
import re
from difflib import SequenceMatcher
import scipy.stats


### YOUTUBE VIDEO
def download_video_from_youtube(url, output_title, output_dir='data/0_gitignore', skip_download=False, max_retries=10):  # change skip_download=True for testing
    """ 
    Downloads a video file from a YouTube URL and saves it as an mkv file. Uses yt_dlp package.

    :param url: string of the YouTube URL from which to download the video.
    :param output_title: string of the title to save the downloaded video file as (must not contain path separators).
    :param output_dir: string path to directory where video will be saved. Default 'data/0_gitignore'.
    :param skip_download: boolean to skip download if file exists. If False, will delete existing file then start download.
    :param max_retries: int number of times to retry download on failure.
    :return: string of the path to the saved video file.
    :raises ValueError: if output_title contains path separators.
    """
    # Validate output_title has no path separators
    if '/' in output_title or '\\' in output_title:
        raise ValueError(f"output_title must not contain path separators. Use output_dir parameter to specify path. Got: {output_title}")
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_file_path = os.path.join(output_dir, output_title + '.mkv')
    if os.path.exists(output_file_path):
        if skip_download:
            print(f"Video file exists at {output_file_path}. Using existing file (skip_download=True).")
            return output_file_path
        print(f"Video file exists at {output_file_path}. Will delete existing file and start download.")
        os.remove(output_file_path)

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': os.path.join(output_dir, output_title + '.%(ext)s'),
        'merge_output_format': 'mkv',  # Explicitly specify mkv as output format
    }

    for attempt in range(max_retries):
        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            # If download succeeds, break out of retry loop
            break
        except Exception as e:
            if attempt < max_retries - 1:  # Don't sleep on last attempt
                sleep_time = min(2 ** attempt, 60)  # Exponential backoff, max 60 seconds
                print(f"\nDownload attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                print(f"Waiting {sleep_time} seconds before retrying...")
                time.sleep(sleep_time)
            else:
                print(f"\nAll {max_retries} download attempts failed. Last error: {str(e)}")
                raise  # Re-raise the last exception if all retries failed

    return output_file_path

REGION_LL = (0, 0.97, 0.09, 1)
REGION_C = (0.2, 0.4, 0.8, 0.6)
REGION_UR = (0.833, 0.14, 0.93, 0.165)
TC_PER_REGION_PARAMS = {
    #'LL': {'mode': 'grayscale'},
    'LL': {'mode': 'binary', 'binary_threshold': 200},
    'C':  {'mode': 'binary', 'binary_threshold': 136, 'detection_threshold': 0.95},
    #'UR': {'mode': 'grayscale'}
    'UR': {'mode': 'binary', 'binary_threshold': 200}
}
### IMAGE PROCESSING OPTIMIZATION
def extract_frame_with_region(video_path, timestamp, region_coords):
    """
    Extracts a frame from a video at the specified timestamp and saves two images:
    1. Full frame with the region outlined in red
    2. Cropped region only
    
    :param video_path: string of the path to the video file
    :param timestamp_str: string in format "HH:MM:SS" or "HH:MM:SS.xxx"
    :param region_coords: tuple of (x_start_pct, y_start_pct, x_end_pct, y_end_pct) as percentages
    :return: tuple of paths to (full frame image, cropped region image)
    """
    from core.fileops import convert_timestamp_to_seconds
    
    # Convert timestamp string to seconds
    time_seconds = convert_timestamp_to_seconds(timestamp)
    
    # Use video's directory as output folder
    output_folder = os.path.dirname(video_path)
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        
    # Open video and seek to timestamp
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"Cannot open video file {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_number = int(time_seconds * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    
    # Read frame
    ret, frame = cap.read()
    if not ret:
        cap.release()
        raise ValueError(f"Could not read frame at time_seconds {time_seconds}s")
    
    # Get frame dimensions
    height, width = frame.shape[:2]
    
    # Calculate region coordinates
    x_start_pct, y_start_pct, x_end_pct, y_end_pct = region_coords
    x_start = int(x_start_pct * width)
    y_start = int(y_start_pct * height)
    x_end = int(x_end_pct * width)
    y_end = int(y_end_pct * height)
    
    # Create copy of frame with rectangle
    frame_with_region = frame.copy()
    cv2.rectangle(frame_with_region, (x_start, y_start), (x_end, y_end), (0, 0, 255), 2)
    
    # Crop region
    region_frame = frame[y_start:y_end, x_start:x_end]
    
    # Save images
    full_frame_path = os.path.join(output_folder, f"frame_full.png")
    region_frame_path = os.path.join(output_folder, f"frame_region.png")
    
    cv2.imwrite(full_frame_path, frame_with_region)
    cv2.imwrite(region_frame_path, region_frame)
    
    cap.release()
    
    print(f"Saved frame images:")
    print(f"Full frame with region: {full_frame_path}")
    print(f"Cropped region: {region_frame_path}")
    print(f"Frame dimensions: {width}x{height}")
    print(f"Region coordinates (pixels): ({x_start}, {y_start}) to ({x_end}, {y_end})")
    
    return full_frame_path, region_frame_path
def mrun_extract_frame_with_region():
    pass
#if __name__ == "__main__":
    video_path = "data/0_gitignore/video_extracted_profiles.mkv"
    # 0,0 is UL (x_start%, y_start%, x_end%, y_end%)
    # timestamp = "1:07:58"
    #region_coords = REGION_UR
    # timestamp = "1:57:14"
    #region_coords = REGION_LL
    timestamp = "1:08:23"  # "13:24" Town of Portola Valley, initial "36:01"
    region_coords = REGION_UR
    (full_frame_path, region_frame_path) = extract_frame_with_region(video_path, timestamp, region_coords)
    print(f"Full frame path: {full_frame_path}")  # data/0_gitignore/frame_full.png
    print(f"Region frame path: {region_frame_path}")  # data/0_gitignore/frame_region.png

def determine_optimal_thresholds(region_image):
    """
    Determines two optimal threshold values for a given region image.

    :param region_image: numpy array of the region image.
    :return: tuple (binary_threshold, detection_threshold)
    """
    # Convert to grayscale
    gray = cv2.cvtColor(region_image, cv2.COLOR_BGR2GRAY)

    # Flatten the image to 1D array
    pixels = gray.flatten()

    # Compute Otsu's threshold for binary thresholding
    binary_threshold, _ = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    # Compute skewness and kurtosis for bimodality coefficient
    skewness = scipy.stats.skew(pixels)
    kurtosis = scipy.stats.kurtosis(pixels, fisher=False)  # Pearson's kurtosis

    # Prevent division by zero in bimodality coefficient calculation
    if kurtosis == 0:
        bimodality_coefficient = 0
    else:
        bimodality_coefficient = (skewness ** 2 + 1) / kurtosis

    detection_threshold = bimodality_coefficient

    return int(binary_threshold), detection_threshold
def mrun_determine_optimal_thresholds():
    pass
#if __name__ == "__main__":
    cur_region_image = cv2.imread("data/0_gitignore/frame_region.png")
    binary_threshold, detection_threshold = determine_optimal_thresholds(cur_region_image)
    print(f"Binary threshold: {binary_threshold}")
    print(f"Detection threshold: {detection_threshold}")

### VIDEO PROCESSING
def extract_frames_and_perform_ocr(
    video_path,
    start_time_seconds,
    end_time_seconds,
    frame_interval,
    regions,
    per_region_params,
    common_profiles_path
):
    """
    Extracts frames from a video file and performs OCR with region-specific parameters.
    
    :param video_path: string of the path to the video file.
    :param frame_interval: float of time in seconds between frame captures.
    :param frame_similarity_threshold: float between 0 and 1 indicating the similarity threshold.
    :param start_time_seconds: float of the start time in seconds.
    :param end_time_seconds: float of the end time in seconds.
    :param regions: dictionary of region definitions.
    :param per_region_params: dictionary of OCR parameters per region.
    :param common_profiles_path: string path to common profiles file.
    :return: dictionary mapping timestamps to OCR results per region.
    """
    from core.fileops import track_progress
    
    if regions is None:
        raise ValueError("At least one region must be specified for OCR processing.")
    
    # Initialize target region and profile tracking
    target_region = None  # Start with no target region
    current_profile = 'undetermined'
    previous_region_frames = {name: None for name in regions.keys()}
    
    # Initialize default per_region_params if none provided
    if per_region_params is None:
        per_region_params = {name: {} for name in regions.keys()}

    print(f"\nStarting frame extraction and OCR from {video_path}")
    print(f"Processing frames every {frame_interval} second(s)")
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"Cannot open video file {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_secs = total_frames / fps
    
    # Set start and end frames based on timestamps
    start_frame = int(start_time_seconds * fps) if start_time_seconds else 0
    end_frame = int(end_time_seconds * fps) if end_time_seconds else total_frames - 1
    
    frame_interval_frames = int(frame_interval * fps)
    frame_count = start_frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    
    print(f"Video FPS: {fps:.2f}")
    print(f"Total frames in video: {total_frames:,} ({duration_secs:.1f} seconds)")
    print(f"Processing frames from {start_time_seconds or 0}s to {end_time_seconds or duration_secs}s")
    total_frames_to_process = (end_frame - start_frame) // frame_interval_frames + 1
    print(f"Will analyze approximately {total_frames_to_process:,} frames at {frame_interval}-second intervals")
    
    ocr_results = {}
    previous_frame = None
    last_percentage = 0
    start_time = time.time()
    
    # Initialize speaker string tracking per region
    last_speaker_strings = {name: None for name in regions.keys()}
    speaker_string_counts = {name: 0 for name in regions.keys()}
    
    while frame_count <= end_frame:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count)
        ret, frame = cap.read()
        if not ret:
            break
        
        timestamp = frame_count / fps
        
        # Process each region independently
        region_texts = {}
        for name, region in regions.items():
            x_start_pct, y_start_pct, x_end_pct, y_end_pct = region
            height, width = frame.shape[:2]
            x_start = int(x_start_pct * width)
            y_start = int(y_start_pct * height)
            x_end = int(x_end_pct * width)
            y_end = int(y_end_pct * height)
            region_frame = frame[y_start:y_end, x_start:x_end]
            
            # Compare with previous region frame
            region_similar = False
            if previous_region_frames[name] is not None:
                similarity = calculate_region_similarity(
                    previous_region_frames[name],
                    region_frame,
                    name,
                    per_region_params
                )
                similarity_threshold = per_region_params.get(name, {}).get('similarity_threshold', 0.95)
                if similarity >= similarity_threshold:
                    region_similar = True

            if not region_similar:
                # Scale up the cropped region if needed
                scale_factor = per_region_params.get(name, {}).get('scale_factor', 1)
                if scale_factor != 1:
                    region_frame = cv2.resize(region_frame, None, 
                                          fx=scale_factor, 
                                          fy=scale_factor, 
                                          interpolation=cv2.INTER_LINEAR)
                
                # Get region-specific parameters
                region_params = per_region_params.get(name, {})
                mode = region_params.get('mode', 'binary')
                binary_threshold = region_params.get('binary_threshold', None)

                # Check for detection_threshold and apply is_white_text_on_black_background
                detection_threshold = region_params.get('detection_threshold', None)
                if detection_threshold is not None:
                    if not is_white_text_on_black_background(region_frame, detection_threshold):
                        # Set OCR result to empty string and continue to next region
                        region_texts[name] = ''
                        previous_region_frames[name] = region_frame.copy()
                        continue

                # Call perform_ocr_on_region
                region_text = perform_ocr_on_region(region_frame, mode=mode, binary_threshold=binary_threshold).strip()
                region_texts[name] = region_text
            else:
                # Use last known text
                region_texts[name] = last_speaker_strings.get(name, '')

            # Update previous region frame
            previous_region_frames[name] = region_frame.copy()

        # Update target_region and current_profile based on OCR results
        target_region, current_profile = update_target_region(region_texts, common_profiles_path)
        region_texts['profile'] = current_profile
        region_texts['status'] = 'OCR' if not all(region_similar for name in regions.keys()) else 'REPEAT'

        # Store last speaker strings
        for name in regions.keys():
            last_speaker_strings[name] = region_texts.get(name, '')

        # Store OCR results
        ocr_results[int(timestamp)] = region_texts
        
        previous_frame = frame
        frame_count += frame_interval_frames
        
        # Progress update
        frames_processed = (frame_count - start_frame) // frame_interval_frames
        last_percentage = track_progress(frames_processed, total_frames_to_process,
            start_time, last_percentage, "frames")
    
    cap.release()
    print(f"\nFrame extraction and OCR complete! Processed {len(ocr_results):,} frames")
    return ocr_results

def calculate_region_similarity(region_frame1, region_frame2, region_name, per_region_params):
    """
    Calculates the similarity between two region frames using region-specific parameters.

    :param region_frame1: The previous frame of the region.
    :param region_frame2: The current frame of the region.
    :param region_name: Name of the region.
    :param per_region_params: Dictionary of region-specific parameters.
    :return: Similarity score between 0 and 1.
    """
    # Get parameters if needed
    # For simplicity, using the same histogram comparison as before

    # Convert to grayscale
    gray1 = cv2.cvtColor(region_frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(region_frame2, cv2.COLOR_BGR2GRAY)

    # Calculate histograms
    hist1 = cv2.calcHist([gray1], [0], None, [256], [0, 256])
    hist2 = cv2.calcHist([gray2], [0], None, [256], [0, 256])

    # Normalize histograms
    cv2.normalize(hist1, hist1)
    cv2.normalize(hist2, hist2)

    # Compute correlation
    similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
    return similarity

def clean_text_alphanumeric(text):
    """
    Cleans OCR text by keeping only alphanumeric characters and spaces.
    Multiple spaces are reduced to a single space and leading/trailing spaces are removed.
    
    :param text: string of text to clean
    :return: cleaned string containing only alphanumeric characters and single spaces
    """
    if not text:
        return ""
    
    # Keep only alphanumeric chars and spaces, convert to single spaces
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned.strip()

def is_white_text_on_black_background(region_image, detection_threshold):
    """
    Determines if the region image contains white/bright text on a dark background.
    Uses both bimodality and intensity distribution to verify the pattern.

    :param region_image: numpy array of the region image.
    :param detection_threshold: float, threshold value for bimodality detection.
    :return: boolean, True if white text on dark background, False otherwise.
    """
    # Convert to grayscale
    gray = cv2.cvtColor(region_image, cv2.COLOR_BGR2GRAY)
    pixels = gray.flatten()

    # Check bimodality first
    skewness = scipy.stats.skew(pixels)
    kurtosis = scipy.stats.kurtosis(pixels, fisher=False)
    if kurtosis == 0:
        bimodality_coefficient = 0
    else:
        bimodality_coefficient = (skewness ** 2 + 1) / kurtosis

    # If not bimodal enough, return False
    if bimodality_coefficient < detection_threshold:
        return False

    # Use Otsu's method to find optimal threshold
    thresh, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Count pixels above and below threshold
    bright_pixels = np.sum(pixels > thresh)
    dark_pixels = np.sum(pixels <= thresh)
    
    # Calculate mean intensities with safety checks
    bright_pixels_mask = pixels > thresh
    dark_pixels_mask = pixels <= thresh
    
    if not np.any(bright_pixels_mask) or not np.any(dark_pixels_mask):
        return False  # No clear separation between bright and dark regions
    
    bright_mean = np.mean(pixels[bright_pixels_mask])
    dark_mean = np.mean(pixels[dark_pixels_mask])
    
    # Conditions for white text on dark background
    is_text_sparse = bright_pixels < dark_pixels
    has_good_contrast = (bright_mean - dark_mean) > 50
    is_background_dark = dark_mean < 128

    return is_text_sparse and has_good_contrast and is_background_dark
def mrun_is_white_text_on_black_background():
    pass
#if __name__ == "__main__":
    cur_region_image = cv2.imread("data/0_gitignore/frame_region.png")
    cur_detection_threshold = TC_PER_REGION_PARAMS['C']['detection_threshold']
    result = is_white_text_on_black_background(cur_region_image, detection_threshold=cur_detection_threshold)
    print("Is white text on black background: ", result)

def perform_ocr_on_region(region_image, mode='binary', binary_threshold=None):
    """
    Performs OCR on a region image using specified processing parameters.

    :param region_image: numpy array of the region image.
    :param mode: string, 'binary' or 'grayscale' processing mode.
    :param binary_threshold: int, binary threshold value (used if mode is 'binary').
    :return: string of the extracted text.
    """
    # Convert to grayscale if not already
    gray = cv2.cvtColor(region_image, cv2.COLOR_BGR2GRAY)

    if mode == 'binary':
        # Apply binary thresholding
        if binary_threshold is not None:
            _, processed_image = cv2.threshold(gray, binary_threshold, 255, cv2.THRESH_BINARY)
        else:
            # Use Otsu's thresholding if no threshold is provided
            _, processed_image = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    elif mode == 'grayscale':
        processed_image = gray
    else:
        raise ValueError("Invalid mode specified. Use 'binary' or 'grayscale'.")

    # Convert back to RGB as required by pytesseract
    rgb = cv2.cvtColor(processed_image, cv2.COLOR_GRAY2RGB)

    # Get OCR text and clean it
    text = pytesseract.image_to_string(rgb)
    return clean_text_alphanumeric(text)

def find_best_profile_match(text, common_profiles, match_ratio_threshold=0.5):
    """
    Finds the best matching profile from common_profiles using fuzzy string matching.
    
    :param text: string to match against common profiles
    :param common_profiles: list of profile strings to match against
    :param match_ratio_threshold: minimum ratio required for a match (default 0.5)
    :return: tuple of (best_matching_profile, match_ratio)
    """
    best_match = text
    highest_ratio = 0.0
    
    for profile in common_profiles:
        ratio = SequenceMatcher(None, text.lower(), profile.lower()).ratio()
        if ratio > highest_ratio:
            highest_ratio = ratio
            best_match = profile
            
    # Only return the match if it meets the threshold
    if highest_ratio >= match_ratio_threshold:
        return best_match, highest_ratio
    return text, highest_ratio

def update_target_region(ocr_results, common_profiles_path):
    """
    Determines the new target region based on OCR results and assigns the profile.

    :param ocr_results: Dictionary of OCR results from all regions.
    :param common_profiles_path: Path to file containing common profiles (one per line).
    :return: Tuple of (new_target_region, assigned_profile)
    """
    # Initialize common_profiles as empty list
    common_profiles = []
    
    # Try to read common profiles if path is provided
    if common_profiles_path:
        try:
            with open(common_profiles_path, 'r', encoding='utf-8') as f:
                common_profiles = [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f"Warning: Could not read common profiles from {common_profiles_path}: {e}")
            # Continue with empty common_profiles list
    
    # Logic Part 1: If only one region has text
    non_empty_regions = [name for name, text in ocr_results.items() if text]
    if len(non_empty_regions) == 1:
        target_region = non_empty_regions[0]
        text = ocr_results[target_region]
        # Only attempt profile matching if we have common profiles
        if common_profiles:
            best_profile, _ = find_best_profile_match(text, common_profiles)
            return target_region, best_profile
        return target_region, text

    # Logic Part 2: If more than one region has text
    elif len(non_empty_regions) > 1:
        best_match = None
        highest_ratio = 0
        for region_name in non_empty_regions:
            text = ocr_results[region_name]
            profile, ratio = find_best_profile_match(text, common_profiles)
            if ratio > highest_ratio:
                highest_ratio = ratio
                best_match = (region_name, profile)
        if best_match:
            return best_match[0], best_match[1]

    # Logic Part 3: If one region has proper capitalization
    for region_name in non_empty_regions:
        text = ocr_results[region_name]
        if text.istitle():
            return region_name, text

    # Logic Part 4: If still undetermined
    return None, 'UNDETERMINED'

def map_and_condense_ocr_results(ocr_results):
    """
    Maps timestamps to OCR text results and condenses the data by removing consecutive duplicates.

    :param ocr_results: Dictionary mapping timestamps to OCR text dictionaries per region.
    :return: Condensed dictionary mapping timestamps to OCR texts with 'profile'.
    """
    processed_results = {}
    prev_data = None

    for timestamp in sorted(ocr_results.keys()):
        region_texts = ocr_results[timestamp]
        data = {}

        # Extract profile and region texts
        profile = region_texts.get('profile', 'undetermined')
        data['profile'] = profile

        any_text_found = False
        for name, text in region_texts.items():
            if name in ['profile', 'status']:
                continue
            if text:
                any_text_found = True
            data[name] = text

        # Skip if data is the same as previous
        if prev_data is not None:
            texts_match = all(
                data.get(name, '') == prev_data.get(name, '')
                for name in data.keys()
                if name != 'seconds' and name != 'timestamp'
            )
            if texts_match and data['profile'] == prev_data['profile']:
                continue  # Skip adding this data as it is a duplicate

        processed_results[timestamp] = data
        prev_data = data

    print(f"Condensed results contain {len(processed_results)} entries after removing duplicates.")
    return processed_results

def remove_consecutive_profile_repeats(input_csv_path, output_csv_path=None):
    """
    Creates a new CSV file with consecutive profile repeats removed.
    
    :param input_csv_path: string, path to the input CSV file
    :param output_csv_path: string, path to save the output CSV file. If None, overwrites input file
    :return: string, path to the output CSV file
    """
    if output_csv_path is None:
        output_csv_path = input_csv_path + '.temp'
        overwrite = True
    else:
        overwrite = False
        
    with open(input_csv_path, 'r', newline='', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        
        with open(output_csv_path, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)
            writer.writeheader()
            
            previous_profile = None
            for row in reader:
                current_profile = row['profile']
                if current_profile != previous_profile:
                    writer.writerow(row)
                    previous_profile = current_profile
    
    if overwrite:
        os.replace(output_csv_path, input_csv_path)
        return input_csv_path
    
    return output_csv_path


### VIDEO FUNCTIONS
def extract_profiles_from_video(
    video_source,
    start_time_seconds=0,
    end_time_seconds=None,
    output_folder='data/0_gitignore',
    output_title='video_extracted_profiles',
    frame_interval=1,
    frame_similarity_threshold=0.95,
    regions={'LL': REGION_LL, 'C':  REGION_C, 'UR': REGION_UR},
    text_repeat_threshold=3,
    per_region_params=TC_PER_REGION_PARAMS,
    common_profiles_path=None
):
    """
    Downloads a video from YouTube or uses a local video file, processes frames for OCR text extraction, 
    and saves results to two CSV files, a detailed version and the main version without consecutive profile repeats.
    
    :param video_source: string, either a YouTube URL or local file path of the video to process.
    :param common_profiles_path: string, path to the common profiles file.
    :return: tuple, path to the main CSV file.
    """
    from core.fileops import convert_seconds_to_timestamp
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # If video_source is a URL, download it, otherwise use the provided file path
    if video_source.startswith(('http://', 'https://', 'www.')):
        video_file_path = download_video_from_youtube(video_source, output_title)
    else:
        video_file_path = video_source
    
    # Process frames and perform OCR without saving frames to disk
    ocr_results = extract_frames_and_perform_ocr(
        video_file_path,
        start_time_seconds=start_time_seconds,
        end_time_seconds=end_time_seconds,
        frame_interval=frame_interval,
        regions=regions,
        per_region_params=per_region_params,
        common_profiles_path=common_profiles_path  # Pass through the parameter
    )

    # Map time to OCR text and detail the results
    detailed_results = map_and_condense_ocr_results(ocr_results)

    # Save detailed results to CSV in output folder
    detailed_csv_path = os.path.join(output_folder, f'{output_title}_detailed.csv')
    with open(detailed_csv_path, 'w', newline='', encoding='utf-8') as detailed_csvfile:
        fieldnames = ['seconds', 'timestamp', 'profile'] + [f'ocr_text_region_{name}' for name in regions.keys()]
        writer = csv.DictWriter(detailed_csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for timestamp_seconds, data in sorted(detailed_results.items()):
            timestamp = convert_seconds_to_timestamp(timestamp_seconds)
            row = {
                'seconds': timestamp_seconds,
                'timestamp': timestamp,
                'profile': data.get('profile', 'undetermined'),
            }
            for name in regions.keys():
                ocr_text = data.get(name, '')
                row[f'ocr_text_region_{name}'] = ocr_text
            writer.writerow(row)

    print(f"Detailed OCR text mapping saved to {detailed_csv_path}")

    # Create main version without consecutive profile repeats
    main_csv_path = os.path.join(output_folder, f'{output_title}.csv')
    main_csv_path = remove_consecutive_profile_repeats(detailed_csv_path, main_csv_path)
    print(f"Main OCR text mapping (without profile repeats) saved to {main_csv_path}")
    
    return main_csv_path
def mrun_extract_profiles_from_video():
    pass
if __name__ == "__main__":
    #video_source = "data/0_gitignore/video_2024-10-30_PV-TC.mkv"
    video_source = "/Users/randytrue/Documents/Focus on Foundations/OurKarlPopper Zoom w Aaron and Logan.mp4"
    start_time = 0*60
    end_time = 10*60 #None
    
    main_csv_path = extract_profiles_from_video(video_source)#, start_time, end_time)

def apply_common_profiles_csv(profiles_csv_path, common_profiles_path):
    """
    Reprocesses the profiles CSV file using the updated common profiles for fuzzy matching.
    
    :param profiles_csv_path: string, path to the '_profiles.csv' file.
    :param common_profiles_path: string, path to the updated common profiles file.
    :return: None
    """
    # Read common profiles from file
    try:
        with open(common_profiles_path, 'r', encoding='utf-8') as f:
            common_profiles = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Error reading common profiles from {common_profiles_path}: {e}")
        return

    # Read the profiles CSV and update profiles
    temp_csv_path = profiles_csv_path + '.temp'
    with open(profiles_csv_path, 'r', newline='', encoding='utf-8') as infile, \
         open(temp_csv_path, 'w', newline='', encoding='utf-8') as outfile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in reader:
            original_profile = row['profile']
            best_match, _ = find_best_profile_match(original_profile, common_profiles, match_ratio_threshold=0.7)
            row['profile'] = best_match
            writer.writerow(row)

    # Replace the original CSV with the reprocessed one
    os.replace(temp_csv_path, profiles_csv_path)
    
    # Remove consecutive profile repeats
    remove_consecutive_profile_repeats(profiles_csv_path)
    print(f"  Apply common profiles CSV saved to {profiles_csv_path}")
def mrun_apply_common_profiles_csv():
    pass
#if __name__ == "__main__":
    profiles_csv_path = 'data/pv/meetings_tc_2024/2024-10-23_PV-TC_profiles.csv'
    common_profiles_path = 'data/pv/meetings_tc_2024/common_profiles_pv-tc.md'
    apply_common_profiles_csv(profiles_csv_path, common_profiles_path)

def extract_profiles_from_transcript_file(transcript_file_path, common_profiles_path):
    """
    Processes a transcript file to extract video speaker profiles.
    
    :param transcript_file_path: string, the relative path to the transcript markdown file.
    :param common_profiles_path: string, the path to the common profiles file.
    :return: None
    """
    from core.fileops import read_metadata_field_from_file

    # Get the 'link' field from the metadata
    _, youtube_link = read_metadata_field_from_file(transcript_file_path, 'link')

    if not youtube_link:
        print(f"No 'link' field found in metadata of {transcript_file_path}")
        return

    # Call 'extract_profiles_from_video' with the YouTube link
    main_csv_path = extract_profiles_from_video(
        video_source=youtube_link,
        common_profiles_path=common_profiles_path  # Only pass non-default parameters
    )

    # Construct the new filename by replacing the suffix with '_profiles.csv'
    transcript_dir, transcript_filename = os.path.split(transcript_file_path)
    transcript_base = os.path.splitext(transcript_filename)[0]

    if '_' in transcript_base:
        parts = transcript_base.split('_')
        parts[-1] = 'profiles'
        new_base_name = '_'.join(parts)
    else:
        new_base_name = transcript_base + '_profiles'

    new_filename = new_base_name + '.csv'
    target_path = os.path.join(transcript_dir, new_filename)

    # Move and rename the main CSV file to the target path
    shutil.move(main_csv_path, target_path)

    print(f"Moved and renamed main CSV to {target_path}")
def mrun_extract_profiles_from_transcript_file():
    pass
#if __name__ == "__main__":
    cur_transcript_file_path = 'data/pv/meetings_wpc/2022-03-01_PV-WPC_dgwhspm.md'
    common_profiles_path = 'data/pv/meetings_tc_2024/common_profiles_pv-tc.md'
    extract_profiles_from_transcript_file(cur_transcript_file_path, common_profiles_path)

def process_folder_for_profiles(folder_path, common_profiles_path, apply_common_profiles_only=False):
    """
    Process all markdown files in a folder that don't have corresponding _profiles.csv files.
    If apply_common_profiles_only is True, only reprocess existing profile CSVs with updated common profiles.
    
    :param folder_path: string path to the folder containing markdown files
    :param common_profiles_path: string path to the common profiles file
    :param apply_common_profiles_only: boolean to only reprocess existing profile CSVs
    :return: None
    """
    from core.fileops import sub_suffix_in_str, remove_all_suffixes_in_str, get_suffix
    
    if apply_common_profiles_only:
        # Get all markdown files and convert to profile CSV patterns
        md_files = glob.glob(os.path.join(folder_path, '*.md'))
        profile_csvs = []
        
        for md_file in sorted(md_files):
            base_with_profiles = sub_suffix_in_str(os.path.basename(md_file), '_profiles')
            profile_csv = os.path.splitext(base_with_profiles)[0] + '.csv'
            profile_csv_path = os.path.join(folder_path, profile_csv)
            if os.path.exists(profile_csv_path):
                profile_csvs.append(profile_csv_path)
        
        if profile_csvs:
            print(f"\nApplying common profiles to {len(profile_csvs)} existing CSV files:")
            for i, file in enumerate(sorted(profile_csvs), 1):
                print(f"  [{i}/{len(profile_csvs)}] {os.path.basename(file)}")
                apply_common_profiles_csv(file, common_profiles_path)
        else:
            print(f"No profile CSV files found in {folder_path}")
        return

    # Handle new profile extraction
    md_files = glob.glob(os.path.join(folder_path, '*.md'))
    files_to_extract = []
    
    # Define preferred suffix order
    preferred_suffixes = ['_pub', '_pubWIP', '_cemanual', '_cemanualRT', '_cemanualBA', '_cemanualWIP', '_spfix', '_spasgn']
    
    # Group files by their base name (excluding all suffixes)
    base_name_groups = {}
    for md_file in sorted(md_files):
        # Skip files with '_profiles' in the name
        if '_profiles' in md_file:
            continue
            
        # Get base filename without extension and remove all suffixes
        base_name = os.path.splitext(os.path.basename(md_file))[0]
        base_name = remove_all_suffixes_in_str(base_name)
        
        # Add file to its base name group
        if base_name not in base_name_groups:
            base_name_groups[base_name] = []
        base_name_groups[base_name].append(md_file)
    
    files_to_extract = []
    # Select preferred file from each group
    for base_name, group_files in base_name_groups.items():
        selected_file = None
        
        # Try to find a file with preferred suffixes in order
        for suffix in preferred_suffixes:
            for file in group_files:
                file_base = os.path.splitext(os.path.basename(file))[0]
                if get_suffix(file_base) == suffix[1:]:  # Remove leading underscore for comparison
                    selected_file = file
                    break
            if selected_file:
                break
        
        # If no preferred suffix found, take the first file alphabetically
        if not selected_file:
            selected_file = sorted(group_files)[0]
        
        # Check if corresponding _profiles.csv exists
        base_with_profiles = sub_suffix_in_str(os.path.basename(selected_file), 'profiles')
        profile_csv = os.path.splitext(base_with_profiles)[0] + '.csv'
        profile_csv_path = os.path.join(folder_path, profile_csv)
        if not os.path.exists(profile_csv_path):
            files_to_extract.append(selected_file)
    
    if files_to_extract:
        print(f"\nFound {len(files_to_extract)} files needing profile extraction:")
        for file in files_to_extract:
            print(f"  {os.path.basename(file)}")
        
        for i, file_path in enumerate(files_to_extract, 1):
            print(f"\nProcessing file {i}/{len(files_to_extract)}: {os.path.basename(file_path)}")
            extract_profiles_from_transcript_file(file_path, common_profiles_path)
    else:
        print(f"No files found needing profile extraction in {folder_path}")
def mrun_process_folder_for_profiles():     
    pass
#if __name__ == "__main__":
    folder_path = 'data/pv/meetings_tc_2023'
    common_profiles_path = 'data/pv/meetings_tc_2024/common_profiles_pv-tc.md'
    process_folder_for_profiles(folder_path, common_profiles_path, apply_common_profiles_only=False)


#url = 'https://youtu.be/BuUAVFFfKD8'  # 2024-10-14 ASCC 24min
#url = 'https://youtu.be/hVf8v_64MVk'  # 2022-03-01 WPC


    # Example usage:
    # Assuming you have a function to extract frames and regions
    # For each frame in the video between start_time and end_time:
    #     for region_name, coords in regions.items():
    #         region_image = extract_region(frame, coords)
    #         params = per_region_params.get(region_name, {})
    #         # Check for detection_threshold
    #         detection_threshold = params.get('detection_threshold')
    #         if detection_threshold is not None:
    #             if not is_white_text_on_black_background(region_image, detection_threshold):
    #                 # Skip OCR for this region
    #                 ocr_results[region_name] = ''
    #                 continue
    #         # Perform OCR
    #         mode = params.get('mode', 'binary')
    #         binary_threshold = params.get('binary_threshold')
    #         text = perform_ocr_on_region(region_image, mode=mode, binary_threshold=binary_threshold)
    #         ocr_results[region_name] = text

# ===== END OF FILE core/video.py =====
