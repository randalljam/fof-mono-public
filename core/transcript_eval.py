# ===== START OF FILE core/transcript_eval.py =====
# Library of functions and execution code to evaluate transcripts in several categories  

import os
import sys
import re
import csv
import json
from difflib import SequenceMatcher
import Levenshtein  # pip install python-Levenshtein
import nltk
from nltk.corpus import words
import warnings
from contextlib import contextmanager
import shutil
import time

from core.fileops import *
from core.conversion import *

# --- ElevenLabs Scribe disabled (2026-07-21): not required for transcript eval.
# Re-enable by uncommenting these imports / env load AND the ### ELEVENLABS SCRIBE
# section at the bottom of this file (needs `elevenlabs` package + ELEVENLABS_API_KEY).
# from elevenlabs.client import ElevenLabs
# from io import BytesIO
# from dotenv import load_dotenv
# from core.transcribe import *  # only used by ElevenLabs helpers below
# load_dotenv(override=True)
# ELEVENLABS_API_KEY = os.environ["ELEVENLABS_API_KEY"]

# ---START OF SYNCED CODE--- only code below will be synchronized with chalicelib.

# import of spacy is in the try/except block below - run 'pip install spacy' first
# after installing spacy, also run from bash terminal:'python -m spacy download en_core_web_lg'

# Suppress specific numpy warnings
warnings.filterwarnings('ignore', category=UserWarning, message='.*NumPy 1.x.*')

@contextmanager
def suppress_stdout_stderr():
    """Context manager to suppress stdout and stderr"""
    # Save current stdout/stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    null_fd = open(os.devnull, 'w')
    
    try:
        sys.stdout = null_fd
        sys.stderr = null_fd
        yield
    finally:
        # Restore stdout/stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        null_fd.close()

# Pre-import spacy with error handling and suppressed output
# *** MAKE SURE TO RUN THIS FIRST: python -m spacy download en_core_web_lg ***
try:
    with suppress_stdout_stderr():
        import spacy
        _SPACY_AVAILABLE = True
        _spacy_nlp_model = spacy.load("en_core_web_lg")
except Exception:
    _SPACY_AVAILABLE = False
    _spacy_nlp_model = None

### TRANSCRIPTS BASICS
def replace_colon_for_non_speaker(text):
    """
    Replaces colons that do not form part of speaker names with a space and a dash.

    :param text: string of the transcript text that needs cleaning.
    :return: string of the cleaned transcript text.
    """
    # List of words that precede a colon but are not speaker names
    non_speaker_words = ['question', 'up', 'this']
    
    # Iterate over the non_speaker_words and replace each occurrence of "word:" with "word -"
    for word in non_speaker_words:
        text = text.replace(f"{word}:", f"{word} -")
    
    return text
def reformat_transcript_text(original_text):
    """
    Reformats and cleans transcript text by separating speaker names from their dialogue.

    This function performs the following operations:
    1. Removes parentheses from the text.
    2. Replaces colons in non-speaker contexts.
    3. Identifies speaker names and separates them from their dialogue.
    4. Formats the text so that each speaker name is on its own line, followed by their dialogue.
    5. Removes extra spaces and ensures consistent formatting.

    :param original_text: string of the raw transcript text to be cleaned and reformatted.
    :return: string of the cleaned and restructured transcript text, with speaker names clearly separated from dialogue.
    """
    # Pattern that matches speaker names followed by a colon, possibly with spaces after,
    # and captures the speaker name and the dialogue in separate groups
    speaker_dialogue_pattern = re.compile(r"^([^\d]*[a-zA-Z\d]+[^\d]*):\s*(.*)$", re.MULTILINE)
    
    # Pattern that matches time formats, e.g., "12:15", "3:00".
    time_reject_pattern = re.compile(r".*\d:\d.*", re.MULTILINE)
    
    # Remove '(' and ')' characters
    processed_text = original_text.replace('(', '').replace(')', '')
    
    # Replace colons that are not part of speaker names
    processed_text = replace_colon_for_non_speaker(processed_text)
    
    # Split the text into lines for processing
    lines = processed_text.splitlines()
    
    # Initialize variables for the cleaned text and a flag to mark when we're accumulating dialogue lines
    fixed_lines = []
    current_speaker = None
    current_dialogue = []
    
    def flush_current_dialogue():
        """Helper function to flush the current dialogue to the fixed_lines."""
        if current_speaker:
            fixed_lines.append(f"{current_speaker}:")
            fixed_lines.append(" ".join(current_dialogue).strip() + "\n")
    
    for line in lines:
        match = speaker_dialogue_pattern.match(line)
        if match:
            if time_reject_pattern.match(line):
                current_dialogue.append(line)
            else:
                # Flush the previous dialogue if there was one
                flush_current_dialogue()
                
                # Start a new dialogue block
                current_speaker, dialogue_part = match.groups()
                current_dialogue = [dialogue_part] if dialogue_part else []
        else:
            # If it's not a speaker line, accumulate dialogue lines
            if current_speaker:
                current_dialogue.append(line)
    
    # Don't forget to flush the last speaker's dialogue
    flush_current_dialogue()
    
    rejoined_text = "\n".join(fixed_lines)
    # Compresses 2 or more spaces into a single space
    final_text = re.sub(r' {2,}', ' ', rejoined_text)
    return final_text
# TODO consider refactor by creating new function to determine if a line is a speaker line get_speaker_name(line) and return None if not speaker line but consider what to do if speaker line is invalid
# TODO sync this with validate qa
def validate_transcript(file_path, verbose=False):
    """
    Validates the speaker segments in a single transcript file by checking the format of speaker segments.

    :param file_path: string of path to the transcript file.
    :param verbose: boolean indicating whether to print detailed response text
    :return: boolean indicating whether the file passed the validation.
    """
    from core.fileops import get_heading, verbose_print
    
    transcript = get_heading(file_path, '### transcript')
    banned_characters = [':']
    valid_format = True

    lines = transcript.split('\n')
    line_number = 2  # Skip the first 2 lines

    while line_number < len(lines):
        line = lines[line_number].strip()

        # Check if line contains a speaker name
        if ':' in line:
            speaker, text_spoken = line.split(':', 1)
            speaker = speaker.strip()

            if not speaker:
                verbose_print(verbose, f'FAILED VALIDATION -  Empty speaker name at line:\n{line}')
                valid_format = False

            # Check the next line for banned characters
            if line_number + 1 < len(lines):
                text_line = lines[line_number + 1].strip()
                for char in banned_characters:
                    if char in text_line:
                        # Check if the banned character is a colon and if it's part of a time reference
                        if char == ':' and re.search(r'\d:\d{2}', text_line):
                            continue
                        verbose_print(verbose, f'FAILED VALIDATION -  Banned character "{char}" found in transcript at line:\n{line}')
                        valid_format = False
            else:
                verbose_print(verbose, f'FAILED VALIDATION -  Missing transcription after speaker name at line:\n{line}')
                valid_format = False

            # Check for an empty line after the text spoken
            if line_number + 2 >= len(lines) or lines[line_number + 2].strip():
                verbose_print(verbose, f'FAILED VALIDATION -  Missing empty line after segment at line:\n{line}')
                valid_format = False

            line_number += 3
        else:
            verbose_print(verbose, f'FAILED VALIDATION -  Invalid format (missing speaker name) at line:\n{line}')
            valid_format = False
            line_number += 1  # Move to the next line to continue checking

    if valid_format:
        verbose_print(verbose, f'PASSED validation of speaker segments for file: {file_path}')
        return True
    else:
        verbose_print(verbose, f'FAILED validation of speaker segments for file: {file_path}')
        return False
def extract_transcript_data(file_path, save_csv=False, fields_to_omit=[]):
    """
    Extracts detailed transcript information into a list of dictionaries.
    Each dictionary contains speaker_name, speaker_role, timestamp, timestamp_link, and dialogue.
    Speaker lines can end in a colon (FDA Townhalls) or include a timestamp (Deutsch, PV).
    Speaker role is extracted from text within parentheses preceding the colon or timestamp.

    :param file_path: string of the path to the file to be processed.
    :param save_csv: boolean indicating whether to save the transcript data as CSV (default: False)
    :return: list of dictionaries with keys ['speaker_full', 'speaker_name', 'speaker_role', 'timestamp', 'timestamp_link', 'dialogue'].
    """
    from core.fileops import get_heading, get_timestamp
    
    transcript_data = []
    transcript_text = get_heading(file_path, '### transcript')
    if transcript_text is None:
        print(f"NO TRANSCRIPT from in extract_transcript_data on {file_path}")
        return None  
    lines = transcript_text.split('\n')
    for i in range(len(lines)):
        line = lines[i]
        data_dict = {'speaker_full': None, 'speaker_name': None, 'speaker_role': None, 'timestamp': None, 'timestamp_link': None, 'dialogue': None}
        
        # Path for lines ending with a colon
        if line.endswith(':'):
            speaker_full = line.rstrip(' :')  # Remove the colon and strip any leading/trailing whitespace
            data_dict['speaker_full'] = speaker_full
            if '(' in speaker_full and ')' in speaker_full:
                speaker_role_start = speaker_full.find('(')
                speaker_role_end = speaker_full.find(')')
                data_dict['speaker_role'] = speaker_full[speaker_role_start + 1:speaker_role_end]
                data_dict['speaker_name'] = speaker_full[:speaker_role_start].strip()
            else:
                data_dict['speaker_name'] = speaker_full
            # Assign the entire next line as dialogue if available
            if i + 1 < len(lines):
                data_dict['dialogue'] = lines[i + 1].strip()

        # Path for lines with a timestamp following the speaker name
        else:
            timestamp, index = get_timestamp(line)
            if index is not None:
                speaker_full = line[:index].strip()
                data_dict['speaker_full'] = speaker_full
                if '(' in speaker_full and ')' in speaker_full:
                    speaker_role_start = speaker_full.find('(')
                    speaker_role_end = speaker_full.find(')')
                    data_dict['speaker_role'] = speaker_full[speaker_role_start + 1:speaker_role_end]
                    data_dict['speaker_name'] = speaker_full[:speaker_role_start].strip()
                else:
                    data_dict['speaker_name'] = speaker_full
                data_dict['timestamp'] = timestamp
                # Extract the timestamp link if present
                link_start = line.find('(', index)
                link_end = line.find(')', link_start)
                if link_start != -1 and link_end != -1:
                    data_dict['timestamp_link'] = line[link_start + 1:link_end]
                # Assign the entire next line as dialogue if available
                if i + 1 < len(lines):
                    data_dict['dialogue'] = lines[i + 1].strip()

        if data_dict['speaker_name']:  # Only add to list if there's a speaker
            transcript_data.append(data_dict)

    if save_csv and transcript_data:
        # Create CSV path by replacing the file extension with .csv
        csv_path = os.path.splitext(file_path)[0] + '.csv'
        
        # Write the data to CSV
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['speaker_full', 'speaker_name', 'speaker_role', 'timestamp', 'timestamp_link', 'dialogue']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for row in transcript_data:
                writer.writerow(row)
        
        print(f"Transcript data saved to: {csv_path}")

    # Remove specified fields from each dictionary in transcript_data
    if fields_to_omit:
        for data_dict in transcript_data:
            for field in fields_to_omit:
                data_dict.pop(field, None)  # None as default prevents KeyError if field doesn't exist

    return transcript_data
def create_speaker_triples(file_path, **kwargs):  # Add **kwargs to accept and ignore extra arguments
    """
    Creates a list of speaker triples from a given file using extracted transcript data.
    Works with speaker lines that end in a colon (FDA Townhalls) or have timestamp (Deutsch, PV).
    Utilizes the extract_transcript_data function to parse the file and count occurrences of each speaker.
    Then creates a list of triples in the format "speaker name, file_stem, count"
    file_stem is the filename without extension, and count is the number of times the speaker appears in the file.

    :param file_path: string of the path to the file to be processed.
    :return: string of speaker triples separated by newlines.
    """
    from core.docwork import extract_transcript_data
    
    print(f"create_speaker_triples on {file_path}")
    transcript_data = extract_transcript_data(file_path)
    if transcript_data is None:
        print(f"NO TRANSCRIPT so create_speaker_triples is returning an empty string on {file_path}")
        return ""  # Return an empty string if no data is extracted
    speaker_dict = {}

    for entry in transcript_data:
        speaker_full = entry['speaker_full'].strip()
        if speaker_full:
            speaker_dict[speaker_full] = speaker_dict.get(speaker_full, 0) + 1

    # Get the file stem (filename without extension)
    file_stem = os.path.splitext(os.path.basename(file_path))[0]

    speaker_triples = []
    for speaker, count in speaker_dict.items():
        speaker_triples.append((speaker, file_stem, count))

    # Sort the triples by count descending, then by speaker name alphabetically if counts are the same
    speaker_triples.sort(key=lambda x: (-x[2], x[0]))

    formatted_triples = [f"{speaker}, {file_stem}, {count}" for speaker, file_stem, count in speaker_triples]
    return "\n".join(formatted_triples)
def create_speaker_matrix(folder_path, suffix_include=None, target_file_path="speaker_matrix.csv", interactive=True):
    """
    Creates a matrix of speaker names from files in a given folder and writes it to a CSV file.

    This function processes all files in the specified folder that have the specified suffix, identifies the speakers 
    and counts their occurrences. It then creates a matrix of speaker triples in the format "speaker, file_stem, count" 
    where speaker is the speaker's name, file_stem is the filename without extension, and count is the number of times 
    the speaker appears in the file. The matrix is written to a CSV file at the specified target file path.

    :param folder_path: string of the path to the folder containing the files to be processed.
    :param target_file_path: string of the path to the target CSV file. If no folder component is specified, the folder_path is used.
    :param suffix_include: string of the suffix to include in the file processing.
    :return: string of the path to the created csv file.
    """
    from core.fileops import apply_to_folder, create_csv_matrix_from_triples
    
    # Use apply_to_folder to process files and get speaker triples
    speaker_triples_results = apply_to_folder(create_speaker_triples, folder_path, suffix_include=suffix_include)
    # Join the speaker triples into a single string, filtering out any empty results
    triples_text = "\n".join(filter(None, speaker_triples_results.values()))

    # Check if the target file path has a folder component; if not, use the folder_path
    if not os.path.dirname(target_file_path):
        target_file_path = os.path.join(folder_path, os.path.basename(target_file_path))

    # Check if the target file already exists
    if os.path.exists(target_file_path):
        if not interactive:
            print(f"Skipping speaker matrix; {target_file_path} already exists.")
            return None
        overwrite = input(f"The file {target_file_path} already exists. Do you want to overwrite it? (y/n): ")
        if overwrite.lower() != 'y':
            print("Operation cancelled by the user.")
            return None

    # Call the create_csv_matrix_from_triples function to create the CSV file
    return create_csv_matrix_from_triples(triples_text, target_file_path)  # function is in fileops
def convert_audiogest_transcript(md_file_path):
    """
    Converts an audiogest transcript to a standard format.
    """
    transcript_text = get_heading(md_file_path, "### transcript")
    if not transcript_text:
        print("No transcript found.")
        return None

    lines = transcript_text.splitlines()
    converted_lines = []

    for line in lines:
        # Match the pattern "SPEAKER_XX  start_time - end_time"
        match = re.match(r"^(SPEAKER_\d+)\s+(\d+(\.\d+)?)\s*-\s*(\d+(\.\d+)?)", line)
        if match:
            # Adjust the unpacking to match the number of groups
            speaker, start_time, end_time = match.group(1, 2, 4)
            timestamp = convert_seconds_to_timestamp(float(start_time))
            dialogue = line[match.end():].strip()
            converted_lines.append(f"{speaker}  {timestamp}")
        else:
            converted_lines.append(line)
            
    new_transcript_text = "\n".join(converted_lines)
    set_heading(md_file_path, "### transcript", new_transcript_text)
def mrun_convert_audiogest_transcript():
    pass
#if __name__ == "__main__":
    cur_md_file_path = "data/deutsch/dev-eval/2024-03-06_PB_audiogest.md"
    convert_audiogest_transcript(cur_md_file_path)

### TRANSCRIPT EVAL HELPERS
def preserve_fields(segment, fields):
    for field in fields:
        if field not in segment:
            segment[field] = ''
MAX_ITEM_NAME_LEN = 35
def format_metric_percentage(numerator, denominator, metric_name, items_name, max_item_name_length=MAX_ITEM_NAME_LEN):
    """
    Formats percentage statistics for any item in a consistent format.
    
    :param numerator: Count of items meeting criteria
    :param denominator: Total possible items
    :param metric_name: Name of the metric being calculated
    :param items_name: Name of the items being counted
    :param max_item_name_length: Length to pad metric name for alignment
    :return: Tuple of (metric_name, percentage, formatted_string)
    """
    percentage = round((numerator / denominator) * 100, 0) if denominator > 0 else 0  # Round to 0 decimal place
    padding = max_item_name_length - len(metric_name)
    formatted_str = f"{metric_name}{' ' * padding}: {numerator:>3}/{denominator:<3} {items_name:<17}({percentage:>5.0f}%)"  # Changed to .1f
    return metric_name, percentage, formatted_str
def format_boolean_field_percentage(dict_list, field_name, denominator, max_len=MAX_ITEM_NAME_LEN):
    """
    Formats percentage statistics for a boolean field in a list of dictionaries.
    """
    true_count = sum(1 for segment in dict_list if segment.get(field_name))
    return format_metric_percentage(true_count, denominator, f"{field_name} == True", "segments", max_len)
    """
    Prints percentage statistics for any item in a consistent format.
    
    :param numerator: Count of items meeting criteria
    :param denominator: Total possible items
    :param item_name: Name of the item being counted
    :param max_item_name_length: Length to pad item name for alignment
    :return: Tuple of (metric_name, percentage)
    """
    percentage = (numerator / denominator) * 100 if denominator > 0 else 0
    padding = max_item_name_length - len(metric_name)
    print(f"{metric_name}{' ' * padding}: {numerator:>3}/{denominator:<3} {items_name:<17}({percentage:>5.0f}%)")
    return metric_name, percentage
def print_boolean_field_percentage(dict_list, field_name, denominator, max_len=MAX_ITEM_NAME_LEN):
    """
    Prints percentage statistics for a boolean field in a list of dictionaries.

    :param dict_list: list, list of dictionaries containing the field to analyze
    :param field_name: str, name of the boolean field to count
    :param denominator: int, total number to calculate percentage against
    :param max_len: int, maximum length for formatting field name
    :return result: tuple, contains field name and calculated percentage
    """
    true_count = sum(1 for segment in dict_list if segment.get(field_name))
    return print_metric_percentage(true_count, denominator, f"{field_name} == True", "segments", max_len)
def print_integer_field_stats(transcript_data, field_name, denominator, denom_label):
    """
    Prints the summary stats for an integer field where the count of non-zero entries is needed.
    """
    # Update to handle None values by converting them to 0
    non_zero_count = sum(1 for segment in transcript_data if (segment.get(field_name) or 0) > 0)
    total_count = denominator
    percentage = (non_zero_count / total_count) * 100 if total_count > 0 else 0
    print(f"{field_name} > 0: {non_zero_count} out of {total_count} ({denom_label}), {percentage:.1f}%")
def print_field_value_stats(transcript_data, field_name, field_name_correct=None, ordered_values=None, denominator=None):
    """
    Prints summary statistics for all values of a given field in transcript data.
    Strips any dash and following text in the values.
    
    :param transcript_data: List of dictionaries containing transcript segments
    :param field_name: Name of the field to analyze
    :param field_name_correct: Optional field name containing boolean correctness values
    :param denominator: Optional custom denominator for percentage calculation (defaults to total segments)
    :param ordered_values: Optional list of values to display first in specified order
    """
    total = denominator if denominator else len(transcript_data)
    
    # Count occurrences of each value and track correctness if specified
    value_counts = {}
    value_correct_counts = {}
    for segment in transcript_data:
        value = segment.get(field_name)
        
        # Convert integer values to strings for consistent handling
        if isinstance(value, int):
            value = str(value)
        
        # Strip anything after dash in value before counting
        if value and '-' in value:
            value = value.split('-')[0]
        value_counts[value] = value_counts.get(value, 0) + 1
        
        # Track correctness if field_name_correct is provided
        if field_name_correct and value:
            if value not in value_correct_counts:
                value_correct_counts[value] = {'total': 0, 'correct': 0}
            if segment.get(field_name_correct) is not None:
                value_correct_counts[value]['total'] += 1
                if segment.get(field_name_correct):
                    value_correct_counts[value]['correct'] += 1
    
    # Sort items, but handle ordered values first
    sorted_items = []
    
    # First add ordered values if specified
    if ordered_values:
        for value in ordered_values:
            if value in value_counts:
                sorted_items.append((value, value_counts.pop(value)))
    
    # Convert remaining values to appropriate type for sorting
    remaining_items = []
    for value, count in value_counts.items():
        if value is None:
            # Keep None as is
            sort_value = (2, None)  # Will sort after numbers but before empty string
        elif value == '':
            sort_value = (3, '')  # Will sort last
        else:
            try:
                # Try to convert to integer for numeric sorting
                sort_value = (1, int(value))
            except (ValueError, TypeError):
                # If not numeric, keep as string
                sort_value = (4, value)
        remaining_items.append((sort_value, value, count))
    
    # Sort remaining items by type priority and then by value
    remaining_items.sort(key=lambda x: (x[0][0], x[0][1]))
    sorted_items.extend((item[1], item[2]) for item in remaining_items)
    
    print(f"\n======= Summary Statistics for {field_name} =======")
    for value, count in sorted_items:
        # Handle None/empty values in display
        display_value = 'None' if value is None else '' if value == '' else value
        percentage = (count / total) * 100 if total > 0 else 0
        
        # Base output
        output = f"{field_name} == {display_value:<10}: {count:>3}/{total:<3}  segments ({percentage:>5.1f}%)"
        
        # Add correctness percentage if available
        if field_name_correct and value in value_correct_counts:
            correct_data = value_correct_counts[value]
            if correct_data['total'] > 0:
                correct_percentage = (correct_data['correct'] / correct_data['total']) * 100
                output += f" with {correct_data['correct']:>3}/{correct_data['total']:<3} correct ({correct_percentage:>5.1f}%)"
        
        print(output)
def write_non_matching_dialogues(timestamp, eval_dialogue, ref_dialogue, clear_files=False, folder_path="data/deutsch/dev-eval"):
    """
    Writes non-matching normalized dialogues to separate files for reference and evaluation transcripts.
    
    :param folder_path: Directory where the output files should be created/appended
    :param timestamp: Timestamp of the dialogue segment
    :param eval_dialogue: Normalized dialogue from evaluation transcript
    :param ref_dialogue: Normalized dialogue from reference transcript
    :param clear_files: Boolean indicating whether to clear the files before writing (default: False)
    """
    eval_file = os.path.join(folder_path, "normalized_dialog_eval.md")
    ref_file = os.path.join(folder_path, "normalized_dialog_ref.md")
    
    # Format the content to write
    content = f"{timestamp}\n{ref_dialogue}\n\n"
    eval_content = f"{timestamp}\n{eval_dialogue}\n\n"
    
    # Determine write mode based on clear_files parameter
    mode = 'w' if clear_files else 'a'
    
    # if clear_files:
    #     print(f"DEBUG: Clearing files at timestamp {timestamp}")
    
    # Write to reference file
    with open(ref_file, mode, encoding='utf-8') as f:
        f.write(content)
        
    # Write to eval file
    with open(eval_file, mode, encoding='utf-8') as f:
        f.write(eval_content)
def extract_first_n_words(text, n):  # NOT USED
    words = text.split()
    return ' '.join(words[:n])
def extract_last_n_words(text, n):  # NOT USED
    words = text.split()
    return ' '.join(words[-n:])
def count_start_match_words(eval_normalized_dialogue, ref_normalized_dialogue, max_match_words=9):
    """
    Counts the number of matching words from the start of two dialogues up to a maximum limit.

    :param eval_normalized_dialogue: str, normalized dialogue from evaluation transcript.
    :param ref_normalized_dialogue: str, normalized dialogue from reference transcript.
    :param max_match_words: int, maximum number of matching words to count (default: 9).
    :return match_count: int, number of matching words from the start of the dialogues.
    """
    eval_words = eval_normalized_dialogue.split()
    ref_words = ref_normalized_dialogue.split()
    match_count = 0
    for ew, rw in zip(eval_words, ref_words):
        if ew == rw:
            match_count += 1
            if match_count >= max_match_words:
                break
        else:
            break
    return match_count
def count_end_match_words(eval_normalized_dialogue, ref_normalized_dialogue, max_match_words=9):
    """
    Counts the number of matching words from the end of two dialogues up to a maximum limit.

    :param eval_normalized_dialogue: str, normalized dialogue from evaluation transcript.
    :param ref_normalized_dialogue: str, normalized dialogue from reference transcript.
    :param max_match_words: int, maximum number of matching words to count (default: 9).
    :return match_count: int, number of matching words from the end of the dialogues.
    """
    eval_words = eval_normalized_dialogue.split()
    ref_words = ref_normalized_dialogue.split()
    match_count = 0
    for ew, rw in zip(reversed(eval_words), reversed(ref_words)):
        if ew == rw:
            match_count += 1
            if match_count >= max_match_words:
                break
        else:
            break
    return match_count
def word_num_similar_ratio(text1, text2):  # NOT USED
    """
    Calculates a similarity ratio based on word count differences between two normalized texts.
    Returns a tuple containing:
    - ratio: value between 0 and 1, where:
        - 1.0 means the texts have the same number of words
        - 0.0 means maximum difference (one text has 2x or more words than the other)
    - diff: absolute difference in word count between the texts
    
    :param text1: First normalized text string
    :param text2: Second normalized text string
    :return: Tuple of (ratio, diff)
    """
    # Count words in each text
    words1 = len(text1.split())
    words2 = len(text2.split())
    
    # Handle empty strings
    if words1 == 0 and words2 == 0:
        return (1.0, 0)
    if words1 == 0 or words2 == 0:
        return (0.0, abs(words1 - words2))
    
    # Calculate ratio of smaller to larger count
    min_words = min(words1, words2)
    max_words = max(words1, words2)
    word_ratio = min_words / max_words
    word_diff = max_words - min_words
    
    return (word_ratio, word_diff)
def calc_similarity_ratio_difflib(text1, text2):  # NOT USED
    return SequenceMatcher(None, text1, text2).ratio()
def calc_lev_dist_ratio(text1, text2):
    """
    Calculate similarity ratio between two texts using Levenshtein distance.
    Returns a value between 0 and 1, where 1 means identical texts.
    """
    # Ensure both texts are strings
    text1 = str(text1) if text1 is not None else ''
    text2 = str(text2) if text2 is not None else ''
    
    # Handle empty strings
    if not text1 and not text2:
        return 1.0
    if not text1 or not text2:
        return 0.0
        
    return 1 - (Levenshtein.distance(text1, text2) / max(len(text1), len(text2)))

### TRANSCRIPT EVAL STEPS
def evaluate_step_segments_template(eval_transcript_data, ref_transcript_data, debug=True, verbose=True):  # NEEDS UPDATING
    # Initialize tracking variables
    eval_index = 0
    ref_index = 0
    eval_len = len(eval_transcript_data)
    ref_len = len(ref_transcript_data)

    # Get timestamp and seconds lists
    eval_timestamps = [seg['timestamp'] for seg in eval_transcript_data]
    ref_timestamps = [seg['timestamp'] for seg in ref_transcript_data]  
    eval_seconds = [convert_timestamp_to_seconds(ts) for ts in eval_timestamps]
    ref_seconds = [convert_timestamp_to_seconds(ts) for ts in ref_timestamps]

    for eval_index in range(eval_len):
        eval_segment = eval_transcript_data[eval_index]
        
        # Initialize/reset evaluation fields
        eval_fields = {
            'new_field_bool': None,      # Boolean
            'new_field_int': None,       # Int
            # add any other new fields here
        }

        # Use helper function to ensure preserved fields exist
        preserved_fields = ['manual_call']
        preserve_fields(eval_segment, preserved_fields)
        # Update segment with all fields at once
        eval_segment.update(eval_fields)

        # ===== FIRST PASS - INSERT DESCRIPTION OF FIRST PASS HERE
        verbose_print(debug, "FIRST PASS - INSERT DESCRIPTION HERE")
        # First Pass code here ...
    
        verbose_print(debug, f"DEBUG: Completed first pass.\nINSERT ANY SPECIFIC INFO HERE")

    # ===== SECOND PASS - to attempt alignment for non-aligned ref segments
    verbose_print(verbose, "SECOND PASS - INSERT DESCRIPTION HERE")
    # Second Pass code here ...

    verbose_print(debug, f"DEBUG: Completed second pass.\nINSERT ANY SPECIFIC INFO HERE")

    if verbose:
        print("\n========== {EVAL STEP NAME} Analysis Summary ==========")
        print_boolean_field_percentage(eval_transcript_data, 'new_field_bool', len(ref_transcript_data))
        print_field_value_stats(eval_transcript_data, 'new_field_int', len(ref_transcript_data))

    return eval_transcript_data
def evaluate_step_segments_align(eval_transcript_data, ref_transcript_data, debug=False, verbose=True, timestamp_threshold=1, sim_ratio_threshold=0.75, match_words=2, normalization_policy=None):
    """
    Evaluates the presence of speaker segments by comparing the evaluated transcript to the reference transcript.
    Adds evaluation fields to each segment in eval_transcript_data while preserving any existing manual fields.

    :param eval_transcript_data: List of dictionaries from the transcript being evaluated.
    :param ref_transcript_data: List of dictionaries from the reference transcript.
    :param timestamp_threshold: Threshold in seconds for considering timestamps as the same.
    :param word_ratio_threshold: Threshold for dialogue similarity to consider segments as matching.
    :return: eval_transcript_data with evaluation fields added.
    """
    # Initialize tracking variables
    eval_index = 0
    ref_index = 0
    eval_len = len(eval_transcript_data)
    ref_len = len(ref_transcript_data)
    
    # Pre-process all eval segments to add normalized_dialogue and count timestamp frequencies
    timestamp_counts = {}
    for eval_segment in eval_transcript_data:
        eval_segment['normalized_dialogue'] = normalize_dialogue(eval_segment.get('dialogue'), normalization_policy)
        ts = eval_segment.get('timestamp')
        timestamp_counts[ts] = timestamp_counts.get(ts, 0) + 1
    # Set timestamp frequency for each eval segment
    for eval_segment in eval_transcript_data:
        eval_segment['timestamp_count'] = timestamp_counts.get(eval_segment.get('timestamp'))

    # Pre-process all ref segments to add normalized_dialogue and count timestamp frequencies
    timestamp_counts = {}
    for ref_segment in ref_transcript_data:
        ref_segment['normalized_dialogue'] = normalize_dialogue(ref_segment.get('dialogue'), normalization_policy)
        ts = ref_segment.get('timestamp')
        timestamp_counts[ts] = timestamp_counts.get(ts, 0) + 1
    # Set timestamp frequency for each ref segment
    for ref_segment in ref_transcript_data:
        ref_segment['timestamp_count'] = timestamp_counts.get(ref_segment.get('timestamp'))
        ref_segment['seconds'] = convert_timestamp_to_seconds(ref_segment['timestamp'])
    
    # Define helper function at the top level of evaluate_step_segments_align
    def calc_eval_segment(eval_segment, ref_segment, match_words, sim_ratio_threshold):
        eval_segment['is_perfect'] = (eval_segment['dialogue'] == ref_segment['dialogue'])
        eval_segment['is_norm_identical'] = (eval_segment['normalized_dialogue'] == ref_segment['normalized_dialogue'])
        eval_segment['start_match_words'] = count_start_match_words(eval_segment['normalized_dialogue'], ref_segment['normalized_dialogue'])
        eval_segment['end_match_words'] = count_end_match_words(eval_segment['normalized_dialogue'], ref_segment['normalized_dialogue'])
        eval_segment['is_start_match'] = eval_segment['start_match_words'] >= match_words
        eval_segment['sim_ratio'] = calc_lev_dist_ratio(eval_segment['normalized_dialogue'], ref_segment['normalized_dialogue'])
        eval_segment['is_similar'] = eval_segment['sim_ratio'] >= sim_ratio_threshold

    for eval_index in range(eval_len):
        eval_segment = eval_transcript_data[eval_index]
        
        # Initialize/reset evaluation fields
        eval_fields = {
            'is_anchor': None,             # Boolean
            'aligned_ref_index': None,     # Int
            'aligned_ref_timestamp': None, # String
            'is_perfect': None,            # Boolean
            'is_norm_identical': None,     # Boolean
            'start_match_words': None,     # Int
            'end_match_words': None,       # Int
            'is_start_match': None,              # Boolean
            'sim_ratio': None,             # Float
            'is_similar': None,            # Boolean
            'is_aligned': None,            # Boolean
            'is_delete': None,            # Boolean
            'delta_timestamp': None,       # Int
            'call': "",                    # String
            'is_call_correct': None,       # Boolean
            'debug_msg': "",               # String
        }

        # Use helper function to ensure preserved fields exist
        preserved_fields = ['manual_call']
        preserve_fields(eval_segment, preserved_fields)
        # Update segment with all fields at once
        eval_segment.update(eval_fields)

        # =====FIRST PASS to find ANCHOR segments that 1) are unique, 2) have greater than timestamp_threshold gaps, 
        # and 3) are exact match in timestamp to ref segment
        verbose_print(debug, "FIRST PASS - to find ANCHOR segments")
        # Only consider segments with unique timestamp
        if eval_segment['timestamp_count'] == 1:
            eval_timestamp = eval_segment['timestamp']
            
            # Handle first segment
            if eval_index == 0:
                if eval_len == 1:
                    has_gap = True
                else:
                    gap_next_seconds = convert_timestamp_to_seconds(eval_transcript_data[eval_index + 1]['timestamp']) - convert_timestamp_to_seconds(eval_timestamp)
                    has_gap = gap_next_seconds > timestamp_threshold
            
            # Handle last segment
            elif eval_index == eval_len - 1:
                # Only check gap to previous segment
                gap_prev_seconds = convert_timestamp_to_seconds(eval_timestamp) - convert_timestamp_to_seconds(eval_transcript_data[eval_index - 1]['timestamp'])
                has_gap = gap_prev_seconds > timestamp_threshold
            
            # Handle middle segments
            else:
                # Check gaps on both sides
                gap_prev_seconds = convert_timestamp_to_seconds(eval_timestamp) - convert_timestamp_to_seconds(eval_transcript_data[eval_index - 1]['timestamp'])
                gap_next_seconds = convert_timestamp_to_seconds(eval_transcript_data[eval_index + 1]['timestamp']) - convert_timestamp_to_seconds(eval_timestamp)
                has_gap = gap_next_seconds > timestamp_threshold and gap_prev_seconds > timestamp_threshold
                #eval_segment['debug_msg'] = f"gap_prev: {gap_prev_seconds}  gap_next: {gap_next_seconds}"
            
            if has_gap:
                ref_match_found = False
                for ref_index in range(ref_len):
                    ref_segment = ref_transcript_data[ref_index]
                    if ref_segment['timestamp'] == eval_timestamp:
                        eval_segment['is_anchor'] = True
                        eval_segment['is_aligned'] = True
                        eval_segment['is_delete'] = False
                        eval_segment['delta_timestamp'] = 0
                        eval_segment['aligned_ref_index'] = ref_index
                        eval_segment['aligned_ref_timestamp'] = ref_segment['timestamp'] 
                        calc_eval_segment(eval_segment, ref_segment, match_words, sim_ratio_threshold)
                        ref_match_found = True
                        break
                if not ref_match_found:  # Add this check
                    eval_segment['is_anchor'] = False
                    eval_segment['debug_msg'] = "no matching ref timestamp"
            else:
                eval_segment['is_anchor'] = False
                eval_segment['debug_msg'] = "no gap"
        else:
            eval_segment['is_anchor'] = False
            eval_segment['debug_msg'] = "not unique timestamp"

    ref_indices_to_add = []  # Track ref indices that need to be added later
    if True:
        # ===== SECOND PASS - to attempt alignment for non-aligned ref segments
        verbose_print(debug, "SECOND PASS - to attempt alignment for non-aligned ref segments")
        #debug=True
        
        # Get the set of aligned ref indices
        aligned_ref_indices = set()
        for eval_segment in eval_transcript_data:
            if eval_segment['aligned_ref_index'] is not None:
                aligned_ref_indices.add(eval_segment['aligned_ref_index'])

        # Find missing indices by checking for gaps in sequence up to ref length
        missing_ref_indices = sorted(set(range(len(ref_transcript_data))) - aligned_ref_indices)
        verbose_print(debug, f"DEBUG: aligned_ref_indices len: {len(aligned_ref_indices)}  {aligned_ref_indices}")
        verbose_print(debug, f"DEBUG: missing_ref_indices len: {len(missing_ref_indices)}  {missing_ref_indices}")

        newly_aligned_ref_indices = set()  # Track indices that get aligned during this pass

        # Process each missing ref index
        i = 0
        while i < len(missing_ref_indices):
            ref_index = missing_ref_indices[i]
            # Skip if this index was already aligned in this pass
            if ref_index in newly_aligned_ref_indices:
                i += 1
                continue
                
            verbose_print(debug, f"DEBUG: Processing ref_index {ref_index}")
            ref_segment = ref_transcript_data[ref_index]
            
            # Find the next aligned ref index after this missing one
            next_aligned = None
            for j in sorted(aligned_ref_indices):
                if j > ref_index:
                    next_aligned = j
                    break
            
            # Find any interleaving non-aligned eval segments that appear before the next aligned ref index
            interleaving_eval_segments = []
            if next_aligned is not None:
                for eval_segment in eval_transcript_data:
                    if (eval_segment.get('is_aligned') != True and 
                        eval_segment.get('aligned_ref_index') is None and
                        eval_segment.get('timestamp_count', 1) >= 1):  # Only consider segments with unique timestamps
                        # Get the position of this segment in the eval data
                        eval_idx = eval_transcript_data.index(eval_segment)
                        # Find the next aligned segment after this one
                        for next_seg in eval_transcript_data[eval_idx:]:
                            if next_seg.get('aligned_ref_index') is not None:
                                if next_seg['aligned_ref_index'] == next_aligned:
                                    interleaving_eval_segments.append(eval_segment)
                                break
            
            #debug=True
            if not interleaving_eval_segments:
                verbose_print(debug, f"  DEBUG: No interleaving segments found for ref_index {ref_index}")
                i += 1
                continue

            else:
                verbose_print(debug, f"  DEBUG: Number of interleaving segments found: {len(interleaving_eval_segments)}")
                
            # Try to find a match within timestamp_threshold
            found_match = False
            non_anchor_timestamp_threshold = 3
            for delta in range(0, non_anchor_timestamp_threshold + 1):  # +1 because range is exclusive
                if found_match:
                    break
                    
                verbose_print(debug, f"  DEBUG: Checking delta {delta} for ref_index {ref_index}")
                
                # Check each interleaving segment
                for eval_segment in interleaving_eval_segments[:]:
                    eval_ts_sec = convert_timestamp_to_seconds(eval_segment['timestamp'])
                    ref_ts_sec = ref_segment['seconds']
                    
                    # Check for single interleaving eval segment and alignment within the original timestamp_threshold
                    if (len(interleaving_eval_segments) == 1 and
                        abs(convert_timestamp_to_seconds(interleaving_eval_segments[0]['timestamp']) - ref_segment['seconds']) <= timestamp_threshold):
                        eval_segment = interleaving_eval_segments[0]
                        calc_eval_segment(eval_segment, ref_segment, match_words, sim_ratio_threshold)
                        eval_segment['is_aligned'] = True
                        eval_segment['is_delete'] = False
                        eval_segment['aligned_ref_index'] = ref_index
                        eval_segment['aligned_ref_timestamp'] = ref_segment['timestamp']
                        eval_segment['delta_timestamp'] = abs(convert_timestamp_to_seconds(eval_segment['timestamp']) - ref_segment['seconds'])
                        newly_aligned_ref_indices.add(ref_index)
                        aligned_ref_indices.add(ref_index)
                        eval_segment['debug_msg'] = "2ndP-single-segment-override, " + eval_segment['debug_msg']
                        verbose_print(debug, f"    DEBUG: Single interleaving eval segment aligned with ref_index {ref_index} within threshold.")
                        found_match = True
                        break

                    elif (abs(eval_ts_sec - ref_ts_sec) == delta):
                        calc_eval_segment(eval_segment, ref_segment, match_words, sim_ratio_threshold)
                        if eval_segment['is_similar'] or eval_segment['is_start_match']:
                            verbose_print(debug, f"    DEBUG: Found match for    ref_index {ref_index} at delta {delta} ")
                            # Found a match
                            eval_segment['is_aligned'] = True
                            eval_segment['is_delete'] = False
                            eval_segment['aligned_ref_index'] = ref_index
                            eval_segment['aligned_ref_timestamp'] = ref_segment['timestamp']
                            eval_segment['delta_timestamp'] = delta
                            found_match = True
                            newly_aligned_ref_indices.add(ref_index)  # Add to newly aligned set instead of removing from missing_ref_indices
                            aligned_ref_indices.add(ref_index)
                            interleaving_eval_segments.remove(eval_segment)  # Remove matched segment
                            eval_segment['debug_msg'] = "2ndP-match, " + eval_segment['debug_msg']
                            break
                        else:
                            if False:#ref_index == 77:
                                verbose_print(True, f"    DEBUG: No match found for ref_index {ref_index} at delta {delta} due to sim_ratio {eval_segment['sim_ratio']} or start_match_words {eval_segment['start_match_words']}")
                                verbose_print(True, f"    DEBUG: eval timestamp {eval_segment['timestamp']}\neval normalized dialogue:\n{eval_segment['normalized_dialogue']}\nref timestamp {ref_segment['timestamp']}\nref normalized dialogue:\n{ref_segment['normalized_dialogue']}")
                            #eval_segment['debug_msg'] = f"2ndP-close but rejected at delta {delta} eval {eval_segment['timestamp']} ref {ref_segment['timestamp']} sim_ratio {eval_segment['sim_ratio']}, " + eval_segment['debug_msg']
                            eval_segment['debug_msg'] = f"2ndP-rejected at delta {delta}, " + eval_segment['debug_msg']

            if found_match:
                verbose_print(debug, f"    DEBUG: Match found for ref_index {ref_index} - Decrement index to re-evaluate the previous ref index")
                i -= 1  # Decrement index to re-evaluate the previous ref index
            else:
                verbose_print(debug, f"    DEBUG: No match found for ref_index {ref_index}")
                i += 1
            
            
            
        # After processing all indices, remove the newly aligned ones from missing_ref_indices
        missing_ref_indices = sorted(set(missing_ref_indices) - newly_aligned_ref_indices)
        #verbose_print(debug, f"DEBUG: After matching, missing_ref_indices len: {len(missing_ref_indices)}  {missing_ref_indices}")
        
        # COME BACK AND FIND ALL ADD REF INDICES
        
        # Process each missing ref index
        for ref_index in missing_ref_indices:
            ref_segment = ref_transcript_data[ref_index]
            
            # Find the next aligned ref index after this missing one
            next_aligned = None
            for i in sorted(aligned_ref_indices):
                if i > ref_index:
                    next_aligned = i
                    break
            
            # Find any interleavingnon-aligned eval segments that appear before the next aligned ref index
            interleaving_eval_segments = []
            if next_aligned is not None:
                for eval_segment in eval_transcript_data:
                    if (eval_segment.get('is_aligned') != True and 
                        eval_segment.get('aligned_ref_index') is None):
                        # Get the position of this segment in the eval data
                        eval_idx = eval_transcript_data.index(eval_segment)
                        # Find the next aligned segment after this one
                        for next_seg in eval_transcript_data[eval_idx:]:
                            if next_seg.get('aligned_ref_index') is not None:
                                if next_seg['aligned_ref_index'] == next_aligned:
                                    interleaving_eval_segments.append(eval_segment)
                                break
            
            if not interleaving_eval_segments:
                ref_indices_to_add.append(ref_index)
                continue
            
        # ADD_REF_INDICIES = [8, 9, 14, 15, 16, 30, 60, 61, 64, 65, 74, 75, 120, 122, 123, 124, 135, 136]  # for nova2gen, 30, 123, 124 will get aligned in 3rd pass
        # verbose_print(debug, f"\nADD LIST ANSWER {ADD_REF_INDICIES}")
        verbose_print(debug, f"\nADD LIST GOT    {ref_indices_to_add}\nDEBUG: Completed second pass.")
        # Note: Consider adding DELETE calls for remaining non-aligned eval segments here

    if True:        
        # =====THIRD PASS - to attempt alignment for remaining non-aligned eval segments
        verbose_print(debug, "THIRD PASS - to attempt alignment for remaining non-aligned eval segments")
        
        # Get all eval segments with their indices for processing
        eval_segments_with_indices = [(i, segment) for i, segment in enumerate(eval_transcript_data)]
        
        # Iterate through segments looking for non-aligned segments between consecutive alignments
        i = 0
        while i < len(eval_segments_with_indices):
            eval_segment = eval_segments_with_indices[i][1]
            
            # If this segment is already aligned, move to next
            if eval_segment['aligned_ref_index'] is not None:
                i += 1
                continue
                
            # Look ahead to find next aligned segment
            next_aligned_index = None
            next_aligned_ref_index = None
            
            for next_i, next_segment in eval_segments_with_indices[i+1:]:
                if next_segment['aligned_ref_index'] is not None:
                    next_aligned_index = next_i
                    next_aligned_ref_index = next_segment['aligned_ref_index']
                    next_segment['debug_msg'] = "3rdP-next, " + next_segment['debug_msg']
                    break
            
            # If we found a next aligned segment, check if it's consecutive with previous
            if next_aligned_index is not None:
                # Look backwards to find previous aligned segment
                prev_aligned_ref_index = None
                for prev_i in range(i-1, -1, -1):
                    if eval_transcript_data[prev_i]['aligned_ref_index'] is not None:
                        prev_aligned_ref_index = eval_transcript_data[prev_i]['aligned_ref_index']
                        eval_transcript_data[prev_i]['debug_msg'] = "3rdP-prev, " + eval_transcript_data[prev_i]['debug_msg']
                        break
                
                # If we found both previous and next, check alignment possibilities
                if prev_aligned_ref_index is not None:
                    # Case 1: Consecutive references - mark as interleaving (existing logic)
                    if next_aligned_ref_index == prev_aligned_ref_index + 1:
                        # Mark all segments between prev and next aligned segments
                        for j in range(i, next_aligned_index):
                            interleaving_eval_segment = eval_transcript_data[j]
                            if interleaving_eval_segment['aligned_ref_index'] is None:
                                interleaving_eval_segment['aligned_ref_index'] = -1
                                interleaving_eval_segment['is_aligned'] = False
                                interleaving_eval_segment['is_delete'] = True
                                interleaving_eval_segment['debug_msg'] = "3rdP-interlv, " + interleaving_eval_segment['debug_msg']
                        # Move index past all marked segments
                        i = next_aligned_index
                        continue
                    # Case 2: Intervelaving references with same-timestamp segments
                    else:
                        #debug=True
                        segments_between = eval_transcript_data[i:next_aligned_index]
                        
                        # First find all ref timestamps in the interleaving ref segments
                        ref_timestamp_groups = {}
                        for ref_index in range(prev_aligned_ref_index + 1, next_aligned_ref_index):
                            ref_timestamp = ref_transcript_data[ref_index]['timestamp']
                            ref_timestamp_groups.setdefault(ref_timestamp, []).append(ref_index)
                        
                        # Group eval segments by timestamp
                        eval_timestamp_groups = {}
                        for eval_segment in segments_between:
                            timestamp = eval_segment['timestamp']
                            if timestamp:
                                eval_timestamp_groups.setdefault(timestamp, []).append(eval_segment)
                        
                        # Case 2A: Match segments with identical timestamps
                        matched_in_group = False  # Track if we made any matches in this timestamp group
                        for timestamp, eval_segments in eval_timestamp_groups.items():
                            if len(eval_segments) > 1 and timestamp in ref_timestamp_groups:
                                ref_indices = ref_timestamp_groups[timestamp]
                                # If we have matching numbers of repeated timestamps
                                if len(ref_indices) >= len(eval_segments):
                                    verbose_print(debug, f"DEBUG: Processing timestamp group {timestamp} with {len(eval_segments)} eval segments and {len(ref_indices)} ref indices")
                                    
                                    for idx, eval_segment in enumerate(eval_segments):
                                        ref_index = ref_indices[idx]
                                        eval_segment['aligned_ref_index'] = ref_index
                                        eval_segment['aligned_ref_timestamp'] = ref_transcript_data[ref_index]['timestamp']
                                        eval_segment['delta_timestamp'] = 0
                                        eval_segment['is_aligned'] = True
                                        eval_segment['is_delete'] = False
                                        calc_eval_segment(eval_segment, ref_transcript_data[ref_index], match_words, sim_ratio_threshold)
                                        newly_aligned_ref_indices.add(ref_index)
                                        verbose_print(debug, f"DEBUG: During 3rdPass Case 2A at ref_index {ref_index}, newly_aligned_ref_indices len: {len(newly_aligned_ref_indices)}  {newly_aligned_ref_indices}")
                                        eval_segment['debug_msg'] = f"3rdP-repeats-exact-timestamp-match (ref_index={ref_index}), " + eval_segment['debug_msg']
                                    matched_in_group = True
                            
                            if matched_in_group:
                                verbose_print(debug, f"DEBUG: Successfully aligned timestamp group {timestamp}")
                                # After processing all indices in this timestamp group, remove them from ref_indices_to_add
                                ref_indices_to_add = sorted(set(ref_indices_to_add) - newly_aligned_ref_indices)
                                verbose_print(debug, f"DEBUG: After processing timestamp group {timestamp}, ref_indices_to_add len: {len(ref_indices_to_add)}  {ref_indices_to_add}")

                        # Case 2B: Handle any remaining unaligned interleaving eval segments
                        # based on dgwhspm 64 65 43:56 43:57, 97 1:07:11 1:07:13, and 121 122 123 1:20:43 1:20:48,
                        # for eval segments set is_delete = True and reg segments include in ref_indices_to_add
                        for eval_segment in segments_between:
                            if eval_segment['aligned_ref_index'] is None:
                                eval_segment['is_delete'] = True
                        
                        # Add reference segments between previous and next aligned ref index to ref_indices_to_add
                        for ref_index in range(prev_aligned_ref_index + 1, next_aligned_ref_index):
                            ref_indices_to_add.append(ref_index)
                        
                        # Remove duplicates and sort ref_indices_to_add
                        ref_indices_to_add = sorted(set(ref_indices_to_add))
            
            i += 1

    # Per-segment boundary-error classification for aligned segments: an aligned segment is
    # boundary-clean when its normalized dialogue is identical to the ref segment, or when both
    # its start and end words match the ref (text is on the correct side of both transitions).
    def _words_of(seg):
        return (seg.get('normalized_dialogue') or '').split()
    def _phrase_in(phrase_words, container_words):
        if not phrase_words or len(container_words) < len(phrase_words):
            return False
        n = len(phrase_words)
        return any(container_words[i:i + n] == phrase_words for i in range(len(container_words) - n + 1))
    for seg_idx, eval_segment in enumerate(eval_transcript_data):
        if not eval_segment.get('is_aligned'):
            eval_segment['is_boundary_error'] = None
            eval_segment['is_boundary_misplaced'] = None
            continue
        start_clean = bool(eval_segment.get('is_norm_identical')) or (eval_segment.get('start_match_words') or 0) >= match_words
        end_clean = bool(eval_segment.get('is_norm_identical')) or (eval_segment.get('end_match_words') or 0) >= match_words
        eval_segment['is_boundary_error'] = not (start_clean and end_clean)
        # Distinguish true misplaced-text boundary errors (the displaced words verifiably sit
        # across the transition) from ASR word errors at the segment edge, which no
        # segmentation repair can fix.
        misplaced = False
        r = eval_segment.get('aligned_ref_index')
        eval_words = _words_of(eval_segment)
        ref_words = _words_of(ref_transcript_data[r]) if r is not None and 0 <= r < len(ref_transcript_data) else []
        probe = match_words  # length of the phrase we look for across the transition
        if not start_clean and eval_words and ref_words:
            prev_ref_tail = _words_of(ref_transcript_data[r - 1])[-12:] if r and r - 1 >= 0 else []
            prev_eval_tail = _words_of(eval_transcript_data[seg_idx - 1])[-12:] if seg_idx > 0 else []
            # eval stole the previous ref segment's ending, or left the ref start behind in prev
            if _phrase_in(eval_words[:probe], prev_ref_tail) or _phrase_in(ref_words[:probe], prev_eval_tail):
                misplaced = True
        if not end_clean and eval_words and ref_words and not misplaced:
            next_ref_head = _words_of(ref_transcript_data[r + 1])[:12] if r is not None and r + 1 < len(ref_transcript_data) else []
            next_eval_head = _words_of(eval_transcript_data[seg_idx + 1])[:12] if seg_idx + 1 < len(eval_transcript_data) else []
            # eval kept text belonging to the next ref segment, or its ending drifted into next eval
            if _phrase_in(eval_words[-probe:], next_ref_head) or _phrase_in(ref_words[-probe:], next_eval_head):
                misplaced = True
        eval_segment['is_boundary_misplaced'] = misplaced if eval_segment['is_boundary_error'] else False

    # Absolute segment-error accounting (the interpretable core of the alignment dimension)
    seg_aligned_count = sum(1 for s in eval_transcript_data if s.get('is_aligned'))
    seg_spurious_count = sum(1 for s in eval_transcript_data if s.get('is_delete'))
    seg_boundary_error_count = sum(1 for s in eval_transcript_data if s.get('is_boundary_error'))
    seg_boundary_misplaced_count = sum(1 for s in eval_transcript_data if s.get('is_boundary_misplaced'))
    seg_missing_count = len(ref_indices_to_add)
    seg_error_count = seg_missing_count + seg_spurious_count + seg_boundary_error_count
    # Strict variant counts only segmentation defects a boundary repair could fix:
    # boundary word errors (mis-transcribed edge words) are excluded.
    seg_error_count_strict = seg_missing_count + seg_spurious_count + seg_boundary_misplaced_count
    total_ref = len(ref_transcript_data)
    seg_error_rate = round(seg_error_count / total_ref, 4) if total_ref else 0.0

    metrics_data = {}
    log_lines = [format_divider("Segment Align Analysis Summary")]

    metric_results = [
        format_boolean_field_percentage(eval_transcript_data, 'is_aligned', len(eval_transcript_data)),
        format_boolean_field_percentage(eval_transcript_data, 'is_anchor', len(eval_transcript_data)),
        format_boolean_field_percentage(eval_transcript_data, 'is_perfect', len(eval_transcript_data)),
        format_boolean_field_percentage(eval_transcript_data, 'is_norm_identical', len(eval_transcript_data)),
        format_boolean_field_percentage(eval_transcript_data, 'is_similar', len(eval_transcript_data)),
        format_boolean_field_percentage(eval_transcript_data, 'is_start_match', len(eval_transcript_data)),
        format_boolean_field_percentage(eval_transcript_data, 'is_delete', len(eval_transcript_data)),
        format_metric_percentage(len(ref_indices_to_add), len(ref_transcript_data), "ref_indices_to_add", "ref segments")
    ]

    # Collect metrics and formatted strings
    for name, value, formatted_str in metric_results:
        metrics_data[name] = value/100  # convert to decimal with 2 decimal places
        log_lines.append(formatted_str)

    # Add any additional metrics that don't need formatting
    metrics_data.update({
        "total_eval_segments": len(eval_transcript_data),
        "total_ref_segments": len(ref_transcript_data),
        "seg_aligned_count": seg_aligned_count,
        "seg_missing_count": seg_missing_count,
        "seg_spurious_count": seg_spurious_count,
        "seg_boundary_error_count": seg_boundary_error_count,
        "seg_boundary_misplaced_count": seg_boundary_misplaced_count,
        "seg_error_count": seg_error_count,
        "seg_error_count_strict": seg_error_count_strict,
        "seg_error_rate": seg_error_rate,
    })

    log_lines.append("")
    log_lines.append("Segment error accounting (absolute counts vs reference):")
    log_lines.append(f"  ref segments total          : {total_ref}")
    log_lines.append(f"  eval segments total         : {len(eval_transcript_data)}")
    log_lines.append(f"  aligned eval segments       : {seg_aligned_count}")
    log_lines.append(f"  missing ref segments        : {seg_missing_count}   (ref segment eliminated from eval)")
    log_lines.append(f"  spurious eval segments      : {seg_spurious_count}   (eval segment with no ref counterpart)")
    log_lines.append(f"  boundary-error segments     : {seg_boundary_error_count}   (aligned but start/end words on wrong side)")
    log_lines.append(f"    of which misplaced text   : {seg_boundary_misplaced_count}   (displaced words found across the transition — repairable)")
    log_lines.append(f"  TOTAL segment errors        : {seg_error_count}   (error rate {seg_error_rate:.2%} of ref segments)")
    log_lines.append(f"  STRICT segment errors       : {seg_error_count_strict}   (missing + spurious + misplaced only)")

    # Add debug information if needed
    if debug:
        log_lines.append(f"\nref_indices_to_add: {ref_indices_to_add}")
    
    log_lines.append("\n")  # Add final newline
    log_text = "\n".join(log_lines)
    
    # Print if verbose
    if verbose:
        print(log_text)
    
    return eval_transcript_data, metrics_data, log_text
def evaluate_transitions(eval_transcript_data, ref_transcript_data, verbose=False, num_bridge_words=5):  # Transitions WIP Aborted
    """
    Evaluates transitions in the evaluation transcript by comparing segment boundaries.
    Detects start and end transition errors based on exact word matches by shifting the eval transcript.
    Handles edge cases with repeated words at segment boundaries.
    """
    eval_len = len(eval_transcript_data)
    ref_len = len(ref_transcript_data)

    for idx_eval in range(eval_len):
        eval_segment = eval_transcript_data[idx_eval]
        eval_dialogue = eval_segment.get('dialogue', '')
        normalized_eval_dialogue = normalize_text(eval_dialogue)
        eval_words = normalized_eval_dialogue.split()

        # Initialize evaluation fields
        eval_segment['eval_bridge_start'] = ''
        eval_segment['ref_bridge_start'] = ''
        eval_segment['eval_bridge_end'] = ''    # Added for end transition
        eval_segment['ref_bridge_end'] = ''     # Added for end transition
        eval_segment['trans_start'] = ''
        eval_segment['trans_end'] = ''          # Added for end transition
        eval_segment['trans_call'] = ''

        # Ensure preserved fields exist
        preserved_fields = ['trans_man_call']
        for field in preserved_fields:
            if field not in eval_segment:
                eval_segment[field] = ''

        # Only add trans_correct if it doesn't exist
        if 'trans_correct' not in eval_segment:
            eval_segment['trans_correct'] = None  # Boolean

        # Only process if seg_delta_timestamp exists
        if eval_segment.get('seg_delta_timestamp') is not None:
            # Get corresponding reference segment index from eval_segment
            idx_ref = eval_segment.get('seg_pair_idx')
            if idx_ref is None or idx_ref >= ref_len:
                verbose_print(verbose, "No matching reference segment found")
                eval_segment['trans_start'] = 'NOTSIM'
                eval_segment['trans_end'] = 'NOTSIM'  # Added for end transition
                eval_segment['trans_call'] = 'NOTSIM'
                continue

            ref_segment = ref_transcript_data[idx_ref]

            verbose_print(verbose, f"\nTimestamp: {eval_segment.get('timestamp')}")

            # Get previous segments
            prev_eval_segment = eval_transcript_data[idx_eval - 1] if idx_eval - 1 >= 0 else None
            prev_eval_words = normalize_text(prev_eval_segment.get('dialogue', '')).split() if prev_eval_segment else []

            ref_words = normalize_text(ref_segment.get('dialogue', '')).split()

            # Prepare bridge start for eval and ref
            eval_bridge_start = prev_eval_words[-num_bridge_words:] + ['|**-**|'] + eval_words[:num_bridge_words]
            eval_segment['eval_bridge_start'] = ' '.join(eval_bridge_start)

            prev_ref_segment = ref_transcript_data[idx_ref - 1] if idx_ref - 1 >= 0 else None
            prev_ref_words = normalize_text(prev_ref_segment.get('dialogue', '')).split() if prev_ref_segment else []
            ref_bridge_start = prev_ref_words[-num_bridge_words:] + ['|**-**|'] + ref_words[:num_bridge_words]
            eval_segment['ref_bridge_start'] = ' '.join(ref_bridge_start)

            verbose_print(verbose, f"Eval bridge start: {eval_segment['eval_bridge_start']}")
            verbose_print(verbose, f"Ref bridge start:  {eval_segment['ref_bridge_start']}")

            # Start transition evaluation
            trans_start = 'NOTSET'

            # Define a function to perform the direct start matching
            def perform_start_matching(prev_eval_words, eval_words):
                nonlocal trans_start
                # Attempt to match the start of eval_words with ref_words
                for n in [2, 1]:
                    # Get the first n words from eval and ref
                    eval_start_snippet = eval_words[:n]
                    ref_start_snippet = ref_words[:n]
                    verbose_print(verbose, f"Checking {n} words:")
                    verbose_print(verbose, f"  Eval start snippet: {eval_start_snippet}")
                    verbose_print(verbose, f"  Ref start snippet:  {ref_start_snippet}")

                    if eval_start_snippet == ref_start_snippet:
                        # Direct match found at the start
                        verbose_print(verbose, "  MATCH - Setting trans_start to SAME")
                        trans_start = 'SAME'
                        break  # Exit the loop since a match is found

                return trans_start

            # Define a function to perform the shifting process
            def perform_shift_matching_start(prev_eval_words, eval_words):
                nonlocal trans_start
                # Attempt shifting to match the start of eval_words with ref_words
                for n in [2, 1]:
                    # Get the first n words from eval and ref
                    eval_start_snippet = eval_words[:n]
                    ref_start_snippet = ref_words[:n]
                    verbose_print(verbose, f"Checking {n} words with shifting:")
                    verbose_print(verbose, f"  Eval start snippet: {eval_start_snippet}")
                    verbose_print(verbose, f"  Ref start snippet:  {ref_start_snippet}")

                    max_shift = num_bridge_words
                    for shift in range(1, max_shift + 1):
                        match_found = False

                        # Try left shift (skip words at the start of eval_words)
                        if shift <= len(eval_words) - n:
                            shifted_eval_snippet = eval_words[shift:shift + n]
                            verbose_print(verbose, f"  Attempting LEFT shift {shift}: {shifted_eval_snippet}")
                            if shifted_eval_snippet == ref_start_snippet:
                                # Match found after left shift
                                shifted_text = ' '.join(eval_words[:shift]) + ' _' + ' '.join(shifted_eval_snippet) + '_ ' + ' '.join(eval_words[shift + n:])
                                verbose_print(verbose, f"  MATCH FOUND with LEFT shift {shift}")
                                verbose_print(verbose, f"  Shifted Eval Start: {shifted_text}")
                                trans_start = 'LEFT'
                                match_found = True
                                break  # Exit the shift loop
                        else:
                            verbose_print(verbose, f"  Skipping LEFT shift {shift}: insufficient words")

                        # Try right shift (include words from prev_eval_words)
                        if not match_found and prev_eval_words and shift <= len(prev_eval_words):
                            combined_eval_snippet = prev_eval_words[-shift:] + eval_words[:n - shift]
                            if len(combined_eval_snippet) == n:
                                verbose_print(verbose, f"  Attempting RIGHT shift {shift}: {combined_eval_snippet}")
                                if combined_eval_snippet == ref_start_snippet:
                                    # Match found after right shift
                                    shifted_text = ' '.join(prev_eval_words[:-shift]) + ' _' + ' '.join(combined_eval_snippet) + '_ ' + ' '.join(eval_words[n - shift:])
                                    verbose_print(verbose, f"  MATCH FOUND with RIGHT shift {shift}")
                                    trans_start = 'RIGHT'
                                    match_found = True
                                    break  # Exit the shift loop
                        else:
                            reason = ''
                            if not prev_eval_words:
                                reason = 'no previous words'
                            elif shift > len(prev_eval_words):
                                reason = 'insufficient words in prev_eval_words'
                            verbose_print(verbose, f"  Skipping RIGHT shift {shift}: {reason}")

                        if match_found:
                            verbose_print(verbose, f"  Match found with {trans_start} shift {shift}, moving to next n")
                            break  # Break shift loop only after trying both directions

                    if trans_start != 'NOTSET':
                        break  # Exit the n loop if a match is found

                return trans_start

            # Initialize trans_start
            trans_start = 'NOTSET'

            # Perform initial direct start matching
            perform_start_matching(prev_eval_words, eval_words)

            # If no direct match found, handle repeats at the boundary and try direct matching again
            if trans_start == 'NOTSET':
                verbose_print(verbose, "No direct match found. Checking for repeats at the boundary.")

                # Remove repeated words at the boundary
                def remove_start_boundary_repeats(prev_words, current_words):
                    # Copy the lists to avoid modifying the originals
                    prev_words = prev_words.copy()
                    current_words = current_words.copy()
                    # Check for repeated sequences at the boundary
                    max_overlap = min(len(prev_words), len(current_words))
                    for overlap_size in range(max_overlap, 0, -1):
                        if prev_words[-overlap_size:] == current_words[:overlap_size]:
                            verbose_print(verbose, f"Removing repeated words at boundary from prev_words: '{prev_words[-overlap_size:]}'")
                            prev_words = prev_words[:-overlap_size]  # Remove from prev_words only
                            # Keep current_words intact
                            break
                    return prev_words, current_words

                # Apply the function to remove repeats
                prev_eval_words, eval_words = remove_start_boundary_repeats(prev_eval_words, eval_words)

                # Reconstruct eval_bridge_start without repeats
                eval_bridge_start = prev_eval_words[-num_bridge_words:] + ['|**-**|'] + eval_words[:num_bridge_words]
                eval_segment['eval_bridge_start'] = ' '.join(eval_bridge_start)
                verbose_print(verbose, f"Updated Eval bridge start after removing repeats: {eval_segment['eval_bridge_start']}")

                # Re-run the direct matching process with modified words
                perform_start_matching(prev_eval_words, eval_words)

                # If still no match found, attempt shifting
                if trans_start == 'NOTSET':
                    verbose_print(verbose, "No match found after removing repeats. Proceeding to attempt shifting.")
                    perform_shift_matching_start(prev_eval_words, eval_words)

                if trans_start == 'NOTSET':
                    verbose_print(verbose, "No matches found after shifting - Setting trans_start to NOTSIM")
                    trans_start = 'NOTSIM'

            eval_segment['trans_start'] = trans_start

            # ========== End Transition Evaluation Section Begins Here ==========
            # Get next segments
            next_eval_segment = eval_transcript_data[idx_eval + 1] if idx_eval + 1 < eval_len else None
            next_eval_words = normalize_text(next_eval_segment.get('dialogue', '')).split() if next_eval_segment else []

            next_ref_segment = ref_transcript_data[idx_ref + 1] if idx_ref + 1 < ref_len else None
            next_ref_words = normalize_text(next_ref_segment.get('dialogue', '')).split() if next_ref_segment else []

            # Prepare bridge end for eval and ref
            eval_bridge_end = eval_words[-num_bridge_words:] + ['|**-**|'] + next_eval_words[:num_bridge_words]
            eval_segment['eval_bridge_end'] = ' '.join(eval_bridge_end)
            
            ref_bridge_end = ref_words[-num_bridge_words:] + ['|**-**|'] + next_ref_words[:num_bridge_words]
            eval_segment['ref_bridge_end'] = ' '.join(ref_bridge_end)
            
            verbose_print(verbose, f"Eval bridge end: {eval_segment['eval_bridge_end']}")
            verbose_print(verbose, f"Ref bridge end:  {eval_segment['ref_bridge_end']}")
            
            # End transition evaluation
            trans_end = 'NOTSET'

            # Define a function to perform the direct end matching
            def perform_end_matching(eval_words, next_eval_words):
                nonlocal trans_end
                # Attempt to match the end of eval_words with ref_words
                for n in [2, 1]:
                    # Get the last n words from eval and ref
                    eval_end_snippet = eval_words[-n:]
                    ref_end_snippet = ref_words[-n:]
                    verbose_print(verbose, f"Checking {n} words for end:")
                    verbose_print(verbose, f"  Eval end snippet: {eval_end_snippet}")
                    verbose_print(verbose, f"  Ref end snippet:  {ref_end_snippet}")
                    
                    if eval_end_snippet == ref_end_snippet:
                        # Direct match found at the end
                        verbose_print(verbose, "  MATCH - Setting trans_end to SAME")
                        trans_end = 'SAME'
                        break  # Exit the loop since a match is found

                return trans_end

            # Define a function to perform the shifting process for end matching
            def perform_shift_matching_end(eval_words, next_eval_words):
                nonlocal trans_end
                # Attempt shifting to match the end of eval_words with ref_words
                for n in [2, 1]:
                    # Get the last n words from eval and ref
                    eval_end_snippet = eval_words[-n:]
                    ref_end_snippet = ref_words[-n:]
                    verbose_print(verbose, f"Checking {n} words with shifting for end:")
                    verbose_print(verbose, f"  Eval end snippet: {eval_end_snippet}")
                    verbose_print(verbose, f"  Ref end snippet:  {ref_end_snippet}")

                    max_shift = num_bridge_words
                    for shift in range(1, max_shift + 1):
                        match_found = False

                        # Try left shift (skip words at the end of eval_words)
                        if shift <= len(eval_words) - n:
                            shifted_eval_snippet = eval_words[-(n + shift):-shift]
                            verbose_print(verbose, f"  Attempting LEFT shift {shift}: {shifted_eval_snippet}")
                            if shifted_eval_snippet == ref_end_snippet:
                                # Match found after left shift
                                shifted_text = ' '.join(eval_words[:-(n + shift)]) + ' _' + ' '.join(shifted_eval_snippet) + '_ ' + ' '.join(eval_words[-shift:])
                                verbose_print(verbose, f"  MATCH FOUND with LEFT shift {shift}")
                                trans_end = 'LEFT'
                                match_found = True
                                break  # Exit the shift loop
                        else:
                            verbose_print(verbose, f"  Skipping LEFT shift {shift}: insufficient words")

                        # Try right shift (include words from next_eval_words)
                        if not match_found and next_eval_words and shift <= len(next_eval_words) and shift <= n:
                            # Handle cases where (n - shift) <= 0
                            if n - shift > 0:
                                end_part = eval_words[-(n - shift):]
                            else:
                                end_part = []
                            combined_eval_snippet = end_part + next_eval_words[:shift]
                            if len(combined_eval_snippet) == n:
                                verbose_print(verbose, f"  Attempting RIGHT shift {shift}: {combined_eval_snippet}")
                                if combined_eval_snippet == ref_end_snippet:
                                    # Match found after right shift
                                    if n - shift > 0:
                                        shifted_text = ' '.join(eval_words[:-(n - shift)]) + ' _' + ' '.join(combined_eval_snippet) + '_ ' + ' '.join(next_eval_words[shift:])
                                    else:
                                        shifted_text = ' '.join(eval_words) + ' _' + ' '.join(combined_eval_snippet) + '_ ' + ' '.join(next_eval_words[shift:])
                                    verbose_print(verbose, f"  MATCH FOUND with RIGHT shift {shift}")
                                    trans_end = 'RIGHT'
                                    match_found = True
                                    break  # Exit the shift loop
                        else:
                            reason = ''
                            if not next_eval_words:
                                reason = 'no next words'
                            elif shift > len(next_eval_words):
                                reason = 'insufficient words in next_eval_words'
                            elif shift > n:
                                reason = 'shift greater than n'
                            else:
                                reason = 'n - shift negative or zero'
                            verbose_print(verbose, f"  Skipping RIGHT shift {shift}: {reason}")

                        if match_found:
                            verbose_print(verbose, f"  Match found with {trans_end} shift {shift}, moving to next n")
                            break  # Break shift loop only after trying both directions

                    if trans_end != 'NOTSET':
                        break  # Exit the n loop if a match is found

                return trans_end

            # Perform initial end matching
            perform_end_matching(eval_words, next_eval_words)

            # If no match found, handle repeats at the end boundary and try matching again before shifting
            if trans_end == 'NOTSET':
                verbose_print(verbose, "No direct match found at end. Checking for repeats at the boundary.")

                # Remove repeated words at the end boundary
                def remove_end_boundary_repeats(eval_words, next_words):
                    # Copy the lists to avoid modifying the originals
                    eval_words = eval_words.copy()
                    next_words = next_words.copy()
                    # Remove repeats from the start of next_words
                    while eval_words and next_words and eval_words[-1] == next_words[0]:
                        verbose_print(verbose, f"Removing repeated word at boundary: '{eval_words[-1]}'")
                        next_words.pop(0)
                    return eval_words, next_words

                # Apply the function to remove repeats at end boundary
                eval_words, next_eval_words = remove_end_boundary_repeats(eval_words, next_eval_words)

                # Reconstruct eval_bridge_end without repeats
                eval_bridge_end = eval_words[-num_bridge_words:] + ['|**-**|'] + next_eval_words[:num_bridge_words]
                eval_segment['eval_bridge_end'] = ' '.join(eval_bridge_end)
                verbose_print(verbose, f"Updated Eval bridge end after removing repeats: {eval_segment['eval_bridge_end']}")

                # Re-run the end matching process with modified words
                trans_end = 'NOTSET'  # Reset trans_end
                perform_end_matching(eval_words, next_eval_words)

                # If still no match found, attempt shifting
                if trans_end == 'NOTSET':
                    verbose_print(verbose, "No match found after removing repeats. Proceeding to attempt shifting.")
                    perform_shift_matching_end(eval_words, next_eval_words)

                if trans_end == 'NOTSET':
                    verbose_print(verbose, "  No matches found after shifting - Setting trans_end to NOTSIM")
                    trans_end = 'NOTSIM'

            eval_segment['trans_end'] = trans_end
            # ========== End Transition Evaluation Finishes Here ==========

            # Set trans_call based on both trans_start and trans_end
            if eval_segment.get('seg_call') in ['EXTRA', 'MISSING', 'SPLIT']:
                verbose_print(verbose, "  Segment marked as EXTRA or MISSING - Setting trans_call to SKIP")
                eval_segment['trans_call'] = 'SKIP'
            else:
                if trans_start == 'SAME' and trans_end == 'SAME':
                    verbose_print(verbose, "  Both start and end are SAME - Setting trans_call to OK")
                    eval_segment['trans_call'] = 'OK'
                elif trans_start in ['RIGHT', 'LEFT'] and trans_end in ['RIGHT', 'LEFT']:
                    verbose_print(verbose, "  Both start and end have errors - Setting trans_call to BOTH")
                    eval_segment['trans_call'] = 'BOTH'
                elif trans_start in ['RIGHT', 'LEFT']:
                    verbose_print(verbose, f"  Start is {trans_start} - Setting trans_call to START")
                    eval_segment['trans_call'] = 'START'
                elif trans_end in ['RIGHT', 'LEFT']:
                    verbose_print(verbose, f"  End is {trans_end} - Setting trans_call to END")
                    eval_segment['trans_call'] = 'END'
                else:
                    verbose_print(verbose, "  Transitions are NOTSIM - Setting trans_call to NOTSIM")
                    eval_segment['trans_call'] = 'NOTSIM'

            # Set trans_correct if manual call is available
            if 'trans_man_call' in eval_segment and eval_segment['trans_man_call']:
                eval_segment['trans_correct'] = eval_segment['trans_call'] == eval_segment['trans_man_call']
        else:
            eval_segment['trans_call'] = 'SKIP'

        # Set trans_correct if manual call is available (outside the if block)
        if 'trans_man_call' in eval_segment and eval_segment['trans_man_call']:
            eval_segment['trans_correct'] = eval_segment['trans_call'] == eval_segment['trans_man_call']

    # Print summary statistics
    print("\n========== Summary Statistics for Transitions ==========")
    total_segments = len(eval_transcript_data)
    trans_call_counts = {'OK': 0, 'START': 0, 'END': 0, 'BOTH': 0, 'SKIP': 0, 'NOTSIM': 0, '': 0}
    trans_man_call_counts = {'OK': 0, 'START': 0, 'END': 0, 'BOTH': 0, 'SKIP': 0, 'NOTSIM': 0, '': 0}
    correct_by_type = {'OK': 0, 'START': 0, 'END': 0, 'BOTH': 0, 'SKIP': 0, 'NOTSIM': 0, '': 0}
    trans_correct_count = 0
    trans_correct_total = 0

    # First pass - count all calls
    for segment in eval_transcript_data:
        trans_call = segment.get('trans_call', '')
        trans_man_call = segment.get('trans_man_call', '')
        
        # Count actual calls
        trans_call_counts[trans_call] += 1
        
        # Count manual calls only when they match the category we're counting
        if trans_man_call and trans_call == trans_man_call:
            trans_man_call_counts[trans_call] += 1
            correct_by_type[trans_call] += 1

        if 'trans_correct' in segment:
            trans_correct_total += 1
            if segment['trans_correct']:
                trans_correct_count += 1

    # Print statistics for each call type
    for call_type in [k for k in trans_call_counts.keys() if k != '']:
        count = trans_call_counts[call_type]
        man_count = sum(1 for segment in eval_transcript_data if segment.get('trans_man_call') == call_type)
        correct = correct_by_type[call_type]
        
        # Calculate percentages
        call_percentage = (count / total_segments) * 100 if total_segments > 0 else 0
        correct_percentage = (correct / man_count) * 100 if man_count > 0 else 0
        
        print(f"trans_call == {call_type:<5}: for {count:>3}/{total_segments:<3} segments ({call_percentage:>5.1f}%), {correct:>3}/{man_count:<3} correct vs manual calls ({correct_percentage:>5.1f}%)")

    if trans_correct_total > 0:
        correctness_percentage = (trans_correct_count / trans_correct_total) * 100
        print(f"\nOverall trans_correct: {trans_correct_count:>3}/{trans_correct_total:<3} segments with manual calls ({correctness_percentage:>5.1f}%)")

    return eval_transcript_data

#### WORD ERROR RATE
def evaluate_step_word_error_rate(eval_transcript_data, ref_transcript_data, debug=False, verbose=True, silent=False):
    """
    Calculates both overall and per-segment word error rates by comparing normalized dialogue.
    
    :param eval_transcript_data: List of dictionaries from the transcript being evaluated
    :param ref_transcript_data: List of dictionaries from the reference transcript
    :return: Dictionary containing word error rate metrics
    """
    verbose_print(debug, "\nStarting word error rate calculation...")
    
    # Calculate per-segment metrics first
    segment_metrics = []
    total_substitutions = 0
    total_deletions = 0 
    total_insertions = 0
    
    for eval_segment in eval_transcript_data:
        # Skip segments marked for deletion
        if eval_segment.get('seg_delete'):
            continue
            
        # Find matching reference segment
        ref_index = eval_segment.get('aligned_ref_index')
        if ref_index is None or ref_index >= len(ref_transcript_data):
            continue
            
        ref_segment = ref_transcript_data[ref_index]
        
        # Get normalized text for comparison
        eval_text = eval_segment.get('normalized_dialogue', '')
        ref_text = ref_segment.get('normalized_dialogue', '')
        
        # Split into words
        eval_words = eval_text.split()
        ref_words = ref_text.split()
        
        # Calculate Levenshtein metrics for this segment
        distance = Levenshtein.distance(eval_text, ref_text)
        
        # Calculate detailed operations using dynamic programming
        dp = [[0] * (len(ref_words) + 1) for _ in range(len(eval_words) + 1)]
        
        # Initialize matrix
        for i in range(len(eval_words) + 1):
            dp[i][0] = i
        for j in range(len(ref_words) + 1):
            dp[0][j] = j
            
        # Fill matrix
        for i in range(1, len(eval_words) + 1):
            for j in range(1, len(ref_words) + 1):
                if eval_words[i-1] == ref_words[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = min(dp[i-1][j-1] + 1,     # substitution
                                 dp[i-1][j] + 1,         # deletion
                                 dp[i][j-1] + 1)         # insertion
        
        # Count operations
        substitutions = deletions = insertions = 0
        i, j = len(eval_words), len(ref_words)
        while i > 0 and j > 0:
            if eval_words[i-1] == ref_words[j-1]:
                i -= 1
                j -= 1
            else:
                if dp[i][j] == dp[i-1][j-1] + 1:
                    substitutions += 1
                    i -= 1
                    j -= 1
                elif dp[i][j] == dp[i-1][j] + 1:
                    deletions += 1
                    i -= 1
                else:
                    insertions += 1
                    j -= 1
                    
        # Handle remaining characters
        deletions += i
        insertions += j
        
        # Calculate segment-level metrics
        total_ref_words = len(ref_words)
        word_error_rate = distance / total_ref_words if total_ref_words > 0 else 1.0
        accuracy = 1 - word_error_rate
        
        # Store segment metrics
        segment_metrics.append({
            'timestamp': eval_segment['timestamp'],
            'word_error_rate': word_error_rate,
            'accuracy': accuracy,
            'ref_words': total_ref_words,
            'eval_words': len(eval_words),
            'distance': distance,
            'substitutions': substitutions,
            'deletions': deletions,
            'insertions': insertions
        })
        
        # Add to totals
        total_substitutions += substitutions
        total_deletions += deletions
        total_insertions += insertions
    
    # Calculate overall metrics from concatenated text
    eval_text = ' '.join(seg['normalized_dialogue'] for seg in eval_transcript_data if not seg.get('seg_delete'))
    ref_text = ' '.join(seg['normalized_dialogue'] for seg in ref_transcript_data)
    
    # Split into words
    eval_words = eval_text.split()
    ref_words = ref_text.split()
    
    verbose_print(debug, f"Total words to compare - Eval: {len(eval_words):,}, Ref: {len(ref_words):,}")
    
    # Calculate Levenshtein distance
    verbose_print(debug, "Calculating Levenshtein distance...")
    start_time = time.time()
    distance = Levenshtein.distance(eval_text, ref_text)
    verbose_print(debug, f"Levenshtein calculation completed in {time.time() - start_time:.2f} seconds")
    
    # Calculate metrics
    verbose_print(debug, "Computing error metrics...")
    total_ref_words = len(ref_words)
    word_error_rate = distance / total_ref_words if total_ref_words > 0 else 1.0
    accuracy = 1 - word_error_rate
    
    # Add check for empty segment_metrics
    if not segment_metrics:
        results = {
            'word_accuracy': 0,
            'word_error_rate': 100,  # 100% error when no matches
            'substitutions': 0,
            'deletions': total_ref_words,  # All reference words counted as deletions
            'insertions': len(eval_words),  # All evaluation words counted as insertions
            'total_ref_words': total_ref_words,
            'total_eval_words': len(eval_words),
            'levenshtein_distance': distance,
            'segments_with_errors': 0,
            'average_segment_wer': 100,  # 100% error when no matches
            'worst_segment_wer': 100,
            'best_segment_wer': 100
        }
    else:
        # Create results dictionary
        results = {
            'word_error_rate': word_error_rate,
            'accuracy': accuracy,
            'total_ref_words': total_ref_words,
            'total_eval_words': len(eval_words),
            'levenshtein_distance': distance,
            'substitutions': total_substitutions,
            'deletions': total_deletions,
            'insertions': total_insertions
        }
    
    # Add segment metrics to results
    results['segment_metrics'] = segment_metrics
    results['average_segment_wer'] = sum(m['word_error_rate'] for m in segment_metrics) / len(segment_metrics) if segment_metrics else 100
    results['segment_substitutions'] = total_substitutions
    results['segment_deletions'] = total_deletions
    results['segment_insertions'] = total_insertions
    
    metrics_data = {
        'word_accuracy': accuracy,
        'word_substitutions': total_substitutions,
        'word_deletions': total_deletions,
        'word_insertions': total_insertions
    }
    
    log_lines = [format_divider("Word Error Rate Analysis Summary")]
    
    # Add percentage metrics
    NUMBER_POS = 6
    PERCENT_POS = 30
    log_lines.extend([
        f"{'Word Accuracy':<{MAX_ITEM_NAME_LEN}}:  {accuracy * 100:>{PERCENT_POS}.0f}%",
        f"{'Word Error Rate':<{MAX_ITEM_NAME_LEN}}:  {(1.0 - accuracy) * 100:>{PERCENT_POS}.0f}%"
    ])
        
    # Add error counts
    log_lines.extend([
        f"{'Substitutions':<{MAX_ITEM_NAME_LEN}}:  {total_substitutions:>{NUMBER_POS},}",
        f"{'Deletions':<{MAX_ITEM_NAME_LEN}}:  {total_deletions:>{NUMBER_POS},}",
        f"{'Insertions':<{MAX_ITEM_NAME_LEN}}:  {total_insertions:>{NUMBER_POS},}",
        f"{'Total Reference Words':<{MAX_ITEM_NAME_LEN}}:  {total_ref_words:>{NUMBER_POS},}",
        f"{'Total Evaluation Words':<{MAX_ITEM_NAME_LEN}}:  {len(eval_words):>{NUMBER_POS},}",
        f"{'Levenshtein Distance':<{MAX_ITEM_NAME_LEN}}:  {distance:>{NUMBER_POS},}"
    ])
    
    # Add segment metrics
    log_lines.extend([
        f"{'Total segments with errors':<{MAX_ITEM_NAME_LEN}}:  {len([m for m in segment_metrics if m['word_error_rate'] > 0]):>{NUMBER_POS},}",
        f"{'Average Segment Word Error Rate':<{MAX_ITEM_NAME_LEN}}:  {results['average_segment_wer'] * 100:>{PERCENT_POS}.0f}%",
        f"{'Worst segment WER':<{MAX_ITEM_NAME_LEN}}:  {max(m['word_error_rate'] for m in segment_metrics) * 100:>{PERCENT_POS}.0f}%" if segment_metrics else "",
        f"{'Best segment WER':<{MAX_ITEM_NAME_LEN}}:  {min(m['word_error_rate'] for m in segment_metrics) * 100:>{PERCENT_POS}.0f}%" if segment_metrics else ""
    ])

    log_lines.append("\n")  # Add final newline
    log_text = "\n".join(log_lines)
    
    # Print if verbose
    if verbose:
        print(log_text)
    
    return metrics_data, log_text

#### QUOTATIONS
def analyze_quotation_marks(text):
    """
    Analyzes text for both ASCII and Unicode quotation marks.
    
    :param text: string to analyze
    :return: dictionary with counts and details about found quotation marks
    """
    # Define quote characters and patterns
    ascii_quotes = {
        'ascii_left_single_quote_pattern': " '",  # ASCII 39 with leading space
        'ascii_right_single_quote_pattern': r"(?<=\w[^s])'(?=[\s.,!?;]|$)",  # Updated pattern to exclude plural possessives
        'ascii_left_double_quote_pattern': ' "',  # ASCII 34 with leading space
        'ascii_right_double_quote_pattern': '"[.,!?;\s]|"$',  # ASCII 34 followed by punct/space/end
    }
    
    unicode_quotes = {
        'left_single_quote_char': '\u2018',   # LEFT SINGLE QUOTATION MARK
        'right_single_quote_char': '\u2019',  # RIGHT SINGLE QUOTATION MARK
        'left_double_quote_char': '\u201C',   # LEFT DOUBLE QUOTATION MARK
        'right_double_quote_char': '\u201D',  # RIGHT DOUBLE QUOTATION MARK
        'guillemet_left_char': '\u00AB',      # '«'LEFT-POINTING DOUBLE ANGLE QUOTATION MARK
        'guillemet_right_char': '\u00BB',     # '»' RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK
    }
    
    results = {
        'ascii_quotes': {},
        'unicode_quotes': {name: text.count(char) for name, char in unicode_quotes.items()},
        'has_non_ascii_quotes': False,
        'non_ascii_quote_positions': []
    }
    
    # Count ASCII quotes using both direct matches and patterns
    for name, pattern in ascii_quotes.items():
        if pattern.startswith(' '):  # Simple left quote pattern
            results['ascii_quotes'][name] = text.count(pattern)
        else:  # Right quote pattern requiring regex
            results['ascii_quotes'][name] = len(re.findall(pattern, text))
    
    # Check for any Unicode quotes and record their positions
    for name, char in unicode_quotes.items():
        positions = [i for i, c in enumerate(text) if c == char]
        if positions:
            results['has_non_ascii_quotes'] = True
            for pos in positions:
                # Get some context around the quote
                start = max(0, pos - 20)
                end = min(len(text), pos + 20)
                context = text[start:end]
                results['non_ascii_quote_positions'].append({
                    'quote_type': name,
                    'position': pos,
                    'context': context,
                    'character': char
                })
    
    return results
def check_transcript_quotations_valid(transcript_data, verbose=False):
    """
    Checks the usage of quotation marks in the provided transcript data.

    :param transcript_data: list, a list of dictionaries containing dialogue segments.
    :param verbose: bool, if True, prints detailed analysis of quotation marks.
    :return: bool, True if no non-ASCII quotes are found, False otherwise.
    """
    # Concatenate all dialogue with newlines between segments
    eval_text = '\n'.join(seg.get('dialogue', '') for seg in transcript_data)
    
    # Analyze quotation marks in concatenated text
    quote_analysis_results = analyze_quotation_marks(eval_text)
    
    if verbose:
        # Print ASCII quote pattern matches
        print("\n===== ASCII Quote Patterns =====")
        print(f"Left single quotes  pattern: {quote_analysis_results['ascii_quotes']['ascii_left_single_quote_pattern']}")
        print(f"Right single quotes pattern: {quote_analysis_results['ascii_quotes']['ascii_right_single_quote_pattern']}")
        print(f"Left double quotes  pattern: {quote_analysis_results['ascii_quotes']['ascii_left_double_quote_pattern']}")
        print(f"Right double quotes pattern: {quote_analysis_results['ascii_quotes']['ascii_right_double_quote_pattern']}")
    
        # Print Unicode quote statistics if any exist
        if not quote_analysis_results['has_non_ascii_quotes']:
            print("\n===== Unicode Quotes =====")
            print("No Unicode quotes found")
        else:
            unicode_counts = quote_analysis_results['unicode_quotes']
            print(f"Left single quotes : {unicode_counts['left_single_quote_char']}")
            print(f"Right single quotes: {unicode_counts['right_single_quote_char']}")
            print(f"Left double quotes : {unicode_counts['left_double_quote_char']}")
            print(f"Right double quotes: {unicode_counts['right_double_quote_char']}")
            print(f"Left guillemets    : {unicode_counts['guillemet_left_char']}")
            print(f"Right guillemets   : {unicode_counts['guillemet_right_char']}")
    
    return not quote_analysis_results['has_non_ascii_quotes']
def extract_quotes(text):
    """
    Extracts all text between double quotes from a string.
    Only processes ASCII double quotes (") after validation.
    
    :param text: string to analyze
    :return: list of quoted strings
    """
    quotes = []
    in_quote = False
    current_quote = []
    
    for char in text:
        if char == '"':
            if in_quote:
                # End of quote - add it to list
                quotes.append(''.join(current_quote))
                current_quote = []
            in_quote = not in_quote
        elif in_quote:
            current_quote.append(char)
            
    return quotes
def evaluate_step_quotations_bysegment(eval_transcript_data, ref_transcript_data, debug=True, verbose=True):  # NOT USED
    """
    Evaluates quotation usage between evaluation and reference transcripts.
    Assumes transcripts have been validated to only contain ASCII quotes.
    """
    # Initialize tracking variables
    eval_len = len(eval_transcript_data)
    ref_len = len(ref_transcript_data)

    # Validate quotation marks first
    is_valid_quotations_eval = check_transcript_quotations_valid(eval_transcript_data)
    is_valid_quotations_ref = check_transcript_quotations_valid(ref_transcript_data)
    if not is_valid_quotations_eval or not is_valid_quotations_ref:
        print("ERROR - ABORT: Transcripts contain non-ASCII quotation marks.")
        print(f"  Eval valid quotations: {is_valid_quotations_eval}, Ref valid quotations: {is_valid_quotations_ref}")
        return False
    
    verbose_print(verbose, "FIRST PASS - Analyzing quotes in aligned segments")
    
    for eval_index in range(eval_len):
        eval_segment = eval_transcript_data[eval_index]
        
        # Initialize/reset evaluation fields
        eval_fields = {
            'num_ref_quotes': None,              # Int
            'num_eval_quotes': None,             # Int
            'quote_eval_mismatches': [],         # List of strings
            'are_quotes_match': None,            # Boolean
            'are_normalized_quotes_match': None, # Boolean
        }

        # Use helper function to ensure preserved fields exist
        preserved_fields = ['manual_call']
        preserve_fields(eval_segment, preserved_fields)
        # Update segment with all fields at once
        eval_segment.update(eval_fields)

        # Skip if segment is marked for deletion
        if eval_segment.get('seg_delete'):
            continue

        # Get corresponding reference segment
        ref_index = eval_segment.get('aligned_ref_index')
        if ref_index is None or ref_index >= ref_len:
            continue

        ref_segment = ref_transcript_data[ref_index]
        
        # Extract quotes from both segments
        eval_quotes = extract_quotes(eval_segment.get('dialogue', ''))
        ref_quotes = extract_quotes(ref_segment.get('dialogue', ''))
        
        # Store quote counts
        eval_segment['num_eval_quotes'] = len(eval_quotes)
        eval_segment['num_ref_quotes'] = len(ref_quotes)
        
        # Compare quotes directly
        eval_segment['are_quotes_match'] = (eval_quotes == ref_quotes)
        
        # Compare normalized quotes
        norm_eval_quotes = [normalize_text(q) for q in eval_quotes]
        norm_ref_quotes = [normalize_text(q) for q in ref_quotes]
        eval_segment['are_normalized_quotes_match'] = (norm_eval_quotes == norm_ref_quotes)
        
        # Record mismatches
        if not eval_segment['are_normalized_quotes_match']:
            mismatches = []
            # First check for missing quotes in eval
            for ref_quote in ref_quotes:
                if ref_quote not in eval_quotes:
                    mismatches.append(f"Missing: '{ref_quote}'")
            # Then check for extra quotes in eval
            for eval_quote in eval_quotes:
                if eval_quote not in ref_quotes:
                    mismatches.append(f"Extra: '{eval_quote}'")
            eval_segment['quote_eval_mismatches'] = mismatches
            verbose_print(debug, f"DEBUG: eval_timestamp: {eval_segment['timestamp']} - normalized quotes mismatches: {mismatches}")

        # verbose_print(debug, f"DEBUG: Segment {eval_index} - Ref quotes: {len(ref_quotes)}, "
        #                     f"Eval quotes: {len(eval_quotes)}, Match: {eval_segment['are_quotes_match']}, "
        #                     f"Norm Match: {eval_segment['are_normalized_quotes_match']}")

    # Print summary statistics
    print("\n========== Quote Analysis Summary ==========")
    print_boolean_field_percentage(eval_transcript_data, 'are_quotes_match', len(ref_transcript_data))
    print_boolean_field_percentage(eval_transcript_data, 'are_normalized_quotes_match', len(ref_transcript_data))

    # Calculate and print additional statistics
    total_eval_quotes = sum(seg['num_eval_quotes'] or 0 for seg in eval_transcript_data)
    total_ref_quotes = sum(seg['num_ref_quotes'] or 0 for seg in eval_transcript_data)
    print(f"\nTotal quotes - Eval: {total_eval_quotes}, Ref: {total_ref_quotes}")
    
    segments_with_quotes = sum(1 for seg in eval_transcript_data 
                             if seg.get('num_ref_quotes') and seg['num_ref_quotes'] > 0)
    if segments_with_quotes > 0:
        exact_matches = sum(1 for seg in eval_transcript_data 
                          if seg.get('are_quotes_match') and 
                          seg.get('num_ref_quotes') and seg['num_ref_quotes'] > 0)
        norm_matches = sum(1 for seg in eval_transcript_data 
                         if seg.get('are_normalized_quotes_match') and 
                         seg.get('num_ref_quotes') and seg['num_ref_quotes'] > 0)
        print(f"Segments with quotes: {segments_with_quotes}")
        print(f"Exact quote matches: {exact_matches}/{segments_with_quotes} "
              f"({exact_matches/segments_with_quotes*100:.1f}%)")
        print(f"Normalized quote matches: {norm_matches}/{segments_with_quotes} "
              f"({norm_matches/segments_with_quotes*100:.1f}%)")

    return eval_transcript_data        
def extract_all_quotes(transcript_data):
    """
    Extracts all quotes from the transcript data and returns a list of dictionaries.
    Each dictionary contains the timestamp, quote, and normalized quote.
    """
    quotes_list = []
    for segment in transcript_data:
        timestamp = segment.get('timestamp')
        dialogue = segment.get('dialogue', '')
        quotes_in_segment = extract_quotes(dialogue)
        for quote in quotes_in_segment:
            normalized_quote = normalize_text(quote)
            quotes_list.append({
                'timestamp': timestamp,
                'quote': quote,
                'normalized_quote': normalized_quote
            })
    return quotes_list
def evaluate_step_quotations(eval_transcript_data, ref_transcript_data, debug=False, verbose=True, sim_ratio_threshold=0.75, normalization_policy=None):  # sonnet version use this
    """
    Evaluates quotation matching between evaluation and reference transcripts.
    Extracts quotes and compares them using various matching criteria.
    
    Returns dictionary with matching statistics based on reference transcript quotes:
    - perfect_matches: Same timestamp and identical text
    - normalized_matches: Same timestamp and identical normalized text
    - fuzzy_matches: Same timestamp and similar normalized text above threshold
    - any_timestamp_matches: Similar normalized text found in any timestamp
    """
    verbose_print(debug, "Running evaluate_step_quotations (sonnet version)")
    # Extract quotes from both transcripts
    eval_quotes = []
    ref_quotes = []
    
    # Process eval transcript
    for segment in eval_transcript_data:
        timestamp = segment.get('timestamp')
        dialogue = segment.get('dialogue', '')
        quotes = extract_quotes(dialogue)
        for quote in quotes:
            eval_quotes.append({
                'timestamp': timestamp,
                'quote': quote,
                'normalized': normalize_dialogue(quote, normalization_policy)
            })
    
    # Process reference transcript
    for segment in ref_transcript_data:
        timestamp = segment.get('timestamp')
        dialogue = segment.get('dialogue', '')
        quotes = extract_quotes(dialogue)
        for quote in quotes:
            ref_quotes.append({
                'timestamp': timestamp,
                'quote': quote,
                'normalized': normalize_dialogue(quote, normalization_policy)
            })
    
    total_ref_quotes = len(ref_quotes)
    if total_ref_quotes == 0:
        metrics_data = {
            'perfect_matches': 0,
            'normalized_matches': 0,
            'fuzzy_matches': 0,
            'any_timestamp_matches': 0,
            'total_ref_quotes': 0,
            'total_eval_quotes': len(eval_quotes)
        }
        log_text = (
            format_divider("Quote Analysis Summary") + 
            "\nNo quotes found in reference transcript\nQuotes found in evaluation transcript: " + str(len(eval_quotes)) + "\n\n"
        )
        print(log_text)
        return metrics_data, log_text
    
    # Count different types of matches
    perfect_matches = 0
    normalized_matches = 0
    fuzzy_matches = 0
    any_timestamp_matches = 0
    
    # Track which eval quotes have been matched to avoid double-counting
    matched_eval_indices = set()
    
    # For each reference quote, look for matches in eval quotes
    for ref_quote in ref_quotes:
        # Look for matches at same timestamp first
        same_timestamp_quotes = [
            (i, eq) for i, eq in enumerate(eval_quotes) 
            if eq['timestamp'] == ref_quote['timestamp'] and i not in matched_eval_indices
        ]
        
        # Check for perfect matches (same timestamp)
        perfect_match_found = False
        for i, eval_quote in same_timestamp_quotes:
            if eval_quote['quote'] == ref_quote['quote']:
                perfect_matches += 1
                normalized_matches += 1
                fuzzy_matches += 1
                any_timestamp_matches += 1
                matched_eval_indices.add(i)
                perfect_match_found = True
                break
        
        if perfect_match_found:
            continue
        
        # Check for normalized matches (same timestamp)
        normalized_match_found = False
        for i, eval_quote in same_timestamp_quotes:
            if eval_quote['normalized'] == ref_quote['normalized']:
                normalized_matches += 1
                fuzzy_matches += 1
                any_timestamp_matches += 1
                matched_eval_indices.add(i)
                normalized_match_found = True
                break
        
        if normalized_match_found:
            continue
        
        # Check for fuzzy matches (same timestamp)
        fuzzy_match_found = False
        for i, eval_quote in same_timestamp_quotes:
            if calc_lev_dist_ratio(eval_quote['normalized'], ref_quote['normalized']) >= sim_ratio_threshold:
                fuzzy_matches += 1
                any_timestamp_matches += 1
                matched_eval_indices.add(i)
                fuzzy_match_found = True
                break
        
        if fuzzy_match_found:
            continue
        
        # Finally, check for matches at any timestamp
        for i, eval_quote in enumerate(eval_quotes):
            if i not in matched_eval_indices:
                if calc_lev_dist_ratio(eval_quote['normalized'], ref_quote['normalized']) >= sim_ratio_threshold:
                    any_timestamp_matches += 1
                    matched_eval_indices.add(i)
                    break
    
    metrics_data = {
        'quotes_ref': total_ref_quotes,
        'quotes_eval': len(eval_quotes),
        'quotes_perfect_matches': round(perfect_matches / total_ref_quotes * 100, 2) / 100,
        'quotes_normalized_matches': round(normalized_matches / total_ref_quotes * 100, 2) / 100,
        'quotes_fuzzy_matches': round(fuzzy_matches / total_ref_quotes * 100, 2) / 100,
        'quotes_any_timestamp_matches': round(any_timestamp_matches / total_ref_quotes * 100, 2) / 100,
    }
    
    log_lines = [format_divider("Quote Analysis Summary")]
    
    # Add metrics
    metric_results = [
        format_metric_percentage(perfect_matches, total_ref_quotes, "Perfect matches (same timestamp)", "quotes"),
        format_metric_percentage(normalized_matches, total_ref_quotes, "Normalized matches (same timestamp)", "quotes"),
        format_metric_percentage(fuzzy_matches, total_ref_quotes, "Fuzzy matches (same timestamp)", "quotes"),
        format_metric_percentage(any_timestamp_matches, total_ref_quotes, "Any timestamp matches", "quotes")
    ]
    
    # Add count metrics
    NUMBER_POS = 5
    log_lines.extend([
        f"{'Total reference quotes':<{MAX_ITEM_NAME_LEN}}:  {total_ref_quotes:>{NUMBER_POS},}",
        f"{'Total evaluation quotes':<{MAX_ITEM_NAME_LEN}}:  {len(eval_quotes):>{NUMBER_POS},}"
    ])
    
    # Add percentage metrics
    for name, value, formatted_str in metric_results:
        log_lines.append(formatted_str)
    
    log_lines.append("\n")  # Add final newline
    log_text = "\n".join(log_lines)
    
    # Print if verbose
    if verbose:
        print(log_text)
    
    return metrics_data, log_text

CUR_FILE_PATH = "data/deutsch/dev-eval/2024-03-06_PB_vrbref.md"
#### PROPER NAMES
def is_common_word(word):
    # Load the set of English words from NLTK
    english_words = set(words.words())
    # Check if word is in common English words
    # Return True if it's a common word (not a proper name)
    # Return False if it is a common word
    return word.lower() in {w.lower() for w in english_words}
def is_potential_title(words):
    """
    Check if a sequence of words could be a title based on capitalization patterns.
    Allows for articles, prepositions, and conjunctions to be lowercase.
    
    :param words: list of words to check
    :return: boolean indicating if the sequence matches title patterns
    """
    if not words or len(words) < 2:  # Require at least 2 words
        return False
        
    # Common lowercase connecting words in titles
    connecting_words = {'a', 'an', 'the', 'and', 'but', 'or', 'nor', 'for', 'yet', 'so',
                       'in', 'on', 'at', 'to', 'with', 'by', 'of', 'from', 'into'}
    
    # Common sentence starters that should not be considered part of titles
    sentence_starters = {'so', 'and', 'but', 'well', 'now', 'then', 'therefore', 'however'}
    
    # First word should be capitalized and not a common sentence starter
    if not words[0][0].isupper() or words[0].lower() in sentence_starters:
        return False
    
    # Strip punctuation from last word for checking
    last_word = words[-1].rstrip('.,!?\'\"')
    
    # Don't allow titles ending in punctuation or lowercase connecting words
    if (any(c in '.,!?\'\"' for c in words[-1]) or 
        last_word.lower() in connecting_words):
        return False
    
    # Check pattern: capital words can be separated by connecting words
    capital_word_count = 0
    for word in words:
        clean_word = word.rstrip('.,!?\'\"')  # Strip punctuation for checking
        if clean_word[0].isupper():
            capital_word_count += 1
        elif clean_word.lower() not in connecting_words:
            return False
            
    # Require at least two capitalized words
    return capital_word_count >= 2
def extract_proper_names_spacy(text, custom_proper_names_files=None, bool_include_custom=True, debug=False, verbose=False):
    """Extract proper names using spaCy's named entity recognition"""
    if not _SPACY_AVAILABLE:
        if verbose:
            print("SpaCy not available, returning empty list")
        return []
        
    try:
        # Process the text using the pre-loaded model
        doc = _spacy_nlp_model(text)
        
        # Extract proper names likely to be capitalized
        proper_names = set()
        for ent in doc.ents:
            if ent.label_ in ['PERSON', 'ORG', 'GPE', 'LOC', 'PRODUCT', 'EVENT', 'WORK_OF_ART', 'LAW', 'LANGUAGE']:
                proper_names.add(ent.text)
        
        return sorted(list(proper_names))
    except Exception as e:
        if verbose:
            print(f"SpaCy extraction failed: {str(e)}")
        return []
def extract_proper_names_caprules(text, custom_proper_names_files=None, bool_include_custom=True, debug=False, verbose=False):
    """
    Extract proper names from the input text based on capitalization and dictionaries.
    Names from custom files are used as an ADDITIONAL SOURCE of proper names.
    A name will be kept if it either:
        - Has multiple words OR
        - Is not a common English word OR
        - Appears in the custom files
    If bool_include_custom is False, results filter out any name that appears in the custom files, even if it would normally qualify as a proper name.

    :param text: string, containing the input text.
    :param custom_proper_names_files: list, paths to custom proper names files.
    :param bool_include_custom: bool, flag to include or exclude proper names from custom files.
    :param verbose: bool, flag to enable verbose output.
    :return filtered_proper_names: list, proper names identified.
    """
    # Load the set of English words from NLTK
    english_words = set(words.words())

    # Prepare to extract words
    proper_names = []
    sentences = nltk.sent_tokenize(text)
    for sentence in sentences:
        # Tokenize the sentence into words
        words_in_sentence = nltk.word_tokenize(sentence)
        
        # Combine capitalized words
        i = 0
        while i < len(words_in_sentence):
            word = words_in_sentence[i].rstrip('.,!?\'\"')  # Strip punctuation
            
            # Skip empty words or single-letter words
            if not word or len(word) < 2:
                i += 1
                continue
                
            # Start collecting if we find a capitalized word
            if word[0].isupper():
                combined_name = [word]
                look_ahead = i + 1
                
                # Look ahead for potential title or multi-word name
                while look_ahead < len(words_in_sentence):
                    next_word = words_in_sentence[look_ahead].rstrip('.,!?\'\"')
                    if not next_word:  # Skip empty words
                        look_ahead += 1
                        continue
                        
                    temp_combined = combined_name + [next_word]
                    
                    # Check if adding the next word maintains a valid title pattern
                    if is_potential_title(temp_combined):
                        combined_name.append(next_word)
                        look_ahead += 1
                    else:
                        break
                
                # Add the combined name if it's valid
                if combined_name:
                    # Only add if it's not a single common word at start of sentence
                    if not (len(combined_name) == 1 and 
                           combined_name[0].lower() in english_words and 
                           i == 0):
                        name = " ".join(combined_name)
                        proper_names.append(name)
                
                # Skip ahead past the words we've processed
                i = look_ahead
            else:
                i += 1

    proper_names = sorted(set(proper_names))

    # Load capitalized words from multiple custom lists to retain as proper names
    proper_names_in_custom_dict = set()
    if custom_proper_names_files:
        for custom_list_path in custom_proper_names_files:
            with open(custom_list_path, 'r') as file:
                for line in file:
                    line_words = line.strip().split()
                    for word in line_words:
                        if word[0].isupper():
                            proper_names_in_custom_dict.add(" ".join(line_words))
                            break

    # Load the list of erroneous non-proper name words
    not_proper_names_path = 'data/capitalized_words_not_proper_names.txt'
    with open(not_proper_names_path, 'r') as file:
        not_proper_names = {line.strip() for line in file}

    # Filter proper names, excluding known non-proper names and applying other conditions
    filtered_proper_names = [
        name for name in proper_names 
        if (len(name.split()) > 1 or name.lower() not in english_words or (bool_include_custom and name in proper_names_in_custom_dict)) 
        and name not in not_proper_names
        and not (len(name.split()) == 2 and name.split()[0].lower() in english_words and name.split()[1] == 'I')
    ]
    
    # If custom names should not be included, remove all names that are in the custom proper names dictionary
    if not bool_include_custom:
        filtered_proper_names = [name for name in filtered_proper_names if name not in proper_names_in_custom_dict]
    
    # Print the filtered common words
    common_words_removed = sorted(set(proper_names) - set(filtered_proper_names))
    verbose_print(verbose, "\n\nRemoved Common Words")
    for common_word in common_words_removed:
        verbose_print(verbose, common_word)
    verbose_print(verbose, "\n\n")

    return filtered_proper_names
def extract_proper_names_nltk(text, custom_proper_names_files=None, bool_include_custom=True, debug=False, verbose=False):
    """Extract proper names using NLTK's named entity recognition"""
    import nltk
    from nltk.chunk import ne_chunk
    from nltk.tag import pos_tag
    
    # Ensure required NLTK data is downloaded
    nltk.download('averaged_perceptron_tagger', quiet=True)
    nltk.download('maxent_ne_chunker', quiet=True)
    nltk.download('words', quiet=True)
    
    # Tokenize and tag the text
    tokens = nltk.word_tokenize(text)
    tagged = pos_tag(tokens)
    
    # Extract named entities
    named_entities = ne_chunk(tagged)
    
    # Process tree to extract proper names
    proper_names = set()
    current_name = []
    
    for chunk in named_entities:
        if hasattr(chunk, 'label'):
            if chunk.label() in ['PERSON', 'ORGANIZATION', 'GPE', 'LOC', 'PRODUCT', 'EVENT', 'WORK_OF_ART', 'LAW', 'LANGUAGE']:
                name = ' '.join([c[0] for c in chunk])
                proper_names.add(name)
    
    return sorted(list(proper_names))
EXTRACTION_METHODS = {  # Dictionary mapping method names to their functions
    'caprules': extract_proper_names_caprules,
    'spacy': extract_proper_names_spacy,
    'nltk': extract_proper_names_nltk,
}
def extract_proper_names(text, method='spacy', custom_proper_names_files=None, bool_include_custom=True, debug=False, verbose=False):
    """
    Extract proper names using the specified method.
    
    :param text: string containing the input text
    :param method: string specifying which extraction method to use ('custom', 'spacy', 'nltk')
    :param custom_proper_names_files: list of paths to custom proper names files
    :param bool_include_custom: bool flag to include custom proper names
    :param verbose: bool flag to enable verbose output
    :return: list of proper names identified
    """
    if method not in EXTRACTION_METHODS:
        raise ValueError(f"Unknown extraction method: {method}. Available methods: {', '.join(EXTRACTION_METHODS.keys())}")
    
    return EXTRACTION_METHODS[method](text, custom_proper_names_files, bool_include_custom, debug, verbose)
def analyze_lowercase_proper_names(text, proper_names_list, debug=False, verbose=True):
    """
    Find instances where proper names appear in lowercase form in the text.
    
    :param text: The text to search through
    :param proper_names_list: List of proper names to search for
    :param verbose: Whether to print detailed output
    :return: tuple (lowercase_instances, lowercase_error_instances) where lowercase_instances is a dictionary mapping proper names to lists of their lowercase occurrences, and lowercase_error_instances is a count of actual errors
    """
    lowercase_instances = {}
    lowercase_error_instances = 0  # Initialize the variable here
    verbose_print(debug, f"\n### Lowercase Review")

    for proper_name in proper_names_list:
        # Skip single-letter names
        if len(proper_name) <= 1:
            continue
            
        # Create word boundary pattern for the proper name
        # For multi-word names, we need to handle internal spaces
        name_parts = proper_name.split()
        if len(name_parts) > 1:
            # For multi-word names, use lookahead/lookbehind to ensure word boundaries
            # Updated pattern to include punctuation in lookahead
            pattern = r'(?:^|(?<=\s))' + r'\s+'.join(re.escape(part) for part in name_parts) + r'(?=[\s.,!?]|$)'
        else:
            # Single word names can use simple word boundaries
            pattern = r'\b' + re.escape(proper_name) + r'\b'
        
        # Find all exact matches (case-sensitive)
        exact_matches = set()
        for match in re.finditer(pattern, text):
            exact_matches.add(match.group())
            
        # Find all case-insensitive matches
        pattern_i = re.compile(pattern, re.IGNORECASE)
        
        # Compare positions to find mismatches
        mismatches = []
        for match in pattern_i.finditer(text):
            matched_text = match.group()
            
            # Only consider it a mismatch if:
            # 1. It's not an exact match
            # 2. It's completely lowercase
            # 3. It's not just a substring of a longer proper name
            if (matched_text not in exact_matches and 
                matched_text.lower() == matched_text and
                matched_text.lower() == proper_name.lower()):
                
                # Get surrounding context
                context_start = max(0, match.start() - 40)
                context_end = min(len(text), match.end() + 40)
                context = get_context(text=text, position=match.start(), surrounding_chars=40, complete_words=True)
                
                mismatches.append({
                    'position': match.start(),
                    'variant': matched_text,
                    'context': context
                })
        
        # Store mismatches if any found
        if mismatches:
            lowercase_instances[proper_name] = mismatches
            
            if debug:
                print(f"\nProper name: {proper_name}")
                for mismatch in mismatches:
                    print(f"  Found lowercase variant '{mismatch['variant']}' at position {mismatch['position']}")
                    print(f"    Context: ...{mismatch['context']}...")
    
    # Print summary
    if lowercase_instances:
        total_instances = sum(len(instances) for instances in lowercase_instances.values())
        lowercase_error_instances = sum(
            len(instances) 
            for name, instances in lowercase_instances.items()
            if not is_common_word(next(iter(set(m['variant'] for m in instances))))
        )
        
        verbose_print(debug, f"\nFound {len(lowercase_instances)} proper names with {total_instances} total instances of lowercase variants:")
        for name, instances in lowercase_instances.items():
            variants = set(m['variant'] for m in instances)
            verbose_print(debug, f"- {name}: {len(instances)} instance(s)")
            for variant in variants:
                verbose_print(debug, f"    {variant}  is common word: {is_common_word(variant)}")
        verbose_print(debug, f"Considering {lowercase_error_instances} instances as lowercase errors (excluding common words)")
    else:
        verbose_print(debug, "\nNo lowercase variants of proper names found.")
        
    return lowercase_instances, lowercase_error_instances
def create_proper_names_triples(file_path, heading=None, method='caprules', custom_proper_names_files=None, bool_include_custom=False, debug=False, verbose=False):
    """
    Creates a list of proper name triples from a given file using the specified extraction method.
    
    :param file_path: string path to the file to be processed
    :param heading: optional heading to extract text from
    :param method: string specifying which extraction method to use
    :param custom_proper_names_files: list of paths to custom proper names files
    :param bool_include_custom: bool flag to include custom proper names
    :param verbose: bool flag to enable verbose output
    :return: string of proper name triples separated by newlines (proper name, file stem, count)
    """
    from core.llm import count_tokens
    if heading:
        if heading == "### transcript":
            transcript_data = extract_transcript_data(file_path)
            text = "\n".join(segment['dialogue'] for segment in transcript_data if 'dialogue' in segment)
            verbose_print(verbose, f"Extracted transcript dialogue only for proper names from {file_path}\n## {os.path.basename(file_path)}")
        else:
            text = get_heading(file_path, heading)
            verbose_print(verbose, f"Reading from heading: {heading} for proper names from {file_path}")
    else:
        text = read_complete_text(file_path)
        verbose_print(verbose, f"Reading complete file text for proper names from {file_path}")
    print(f"Token count: {count_tokens(text):,}")

    proper_names_list = extract_proper_names(text, method, custom_proper_names_files, bool_include_custom, debug,verbose)
    verbose_print(debug, f"Extracted {len(proper_names_list)} proper names from {file_path}")
    lowercase_error_instances = analyze_lowercase_proper_names(text, proper_names_list, debug, verbose)

    # Find lowercase variants of proper names
    proper_name_dict = {}

    for proper_name in proper_names_list:
        proper_name_dict[proper_name] = proper_name_dict.get(proper_name, 0) + 1

    file_stem = os.path.splitext(os.path.basename(file_path))[0]
    proper_triples = []
    for proper_name, count in proper_name_dict.items():
        proper_triples.append((proper_name, file_stem, count))

    proper_triples.sort(key=lambda x: (-x[2], x[0]))
    formatted_triples = [f"{proper_name}, {file_stem}, {count}" for proper_name, file_stem, count in proper_triples]

    return "\n".join(formatted_triples)
def get_proper_names(file_path, heading=None, method='caprules', custom_proper_names_files=None, bool_include_custom=False, verbose=False, to_file="cur_proper_names.md"):
    """
    Extracts proper names from a file and writes them to an output file in sorted order.

    :param file_path: string, path to the input file to extract proper names from
    :param heading: string, optional heading section to extract text from
    :param method: string, method to use for proper name extraction
    :param custom_proper_names_files: list, paths to custom proper names files
    :param bool_include_custom: bool, whether to include custom proper names
    :param verbose: bool, whether to print verbose output
    :param to_file: string, output file path for proper names list, if None, a new file with suffix _propernames is created
    :return output_path: string, path to the output file containing proper names
    """
    proper_names_triples = create_proper_names_triples(file_path, heading, method, custom_proper_names_files, bool_include_custom, verbose)
    proper_names_list = [line.split(',')[0] for line in proper_names_triples.split('\n')]
    proper_names_list_sorted = sorted(proper_names_list)
    
    if to_file:
        output_path = os.path.join(os.path.dirname(file_path), to_file)
    else:
        output_path = add_suffix_in_str(file_path, "_propernames")
        output_path = os.path.splitext(output_path)[0] + '.md'  # Changed extension to .md
    with open(output_path, 'w') as file:
        for name in proper_names_list_sorted:
            file.write(name + '\n')
    print(f"Successfully wrote {len(proper_names_list_sorted)} proper names to {output_path} using {method} method")
def mrun_proper_names_methods():
    pass
#if __name__ == "__main__":
    cur_file_path = "data/deutsch/dev-eval/2024-03-06_PB_vrbref.md"
    # Test with different methods
    methods = ['spacy'] # ['caprules', 'spacy', 'nltk']
    for method in methods:
        print(f"\nTesting {method} method:")
        try:
            get_proper_names(
                cur_file_path, 
                heading="### transcript", 
                method=method,
                verbose=True, 
                to_file=f"cur_proper_names_{method}.txt"
            )
        except Exception as e:
            print(f"Error with {method} method: {str(e)}")
def mtest_get_proper_names():
    pass
#if __name__ == "__main__":
    cur_file_path = CUR_FILE_PATH
    #print(create_proper_names_triples(cur_file_path, heading="### transcript"))
    get_proper_names(cur_file_path, heading="### transcript", method='spacy', verbose=True, to_file=f"cur_proper_names_spacy.txt")
    
    # custom_proper_names_files = ['data/pv/cspell_dictionary_pv2.txt','data/pv/compound_proper_names.txt']
    # print(create_proper_names_triples(cur_file_path, custom_proper_names_files, True))
    # get_proper_names(cur_file_path, custom_proper_names_files, True, True)
def mrun_get_proper_names():
    pass
#if __name__ == "__main__":
    #cur_file_path = "data/deutsch/dev-eval/2024-03-06_PB_vrbref.md"
    #cur_file_path = "data/deutsch/dev-eval/2024-03-06_PB_dgwhspm.md"
    #cur_file_path = "data/deutsch/dev-eval/2024-03-06_PB_nova2gen.md"
    cur_file_path = "data/deutsch/f8_done_qafixed_and_vrb/2023-05-23_Reason Is Fun - Ep2 Physics of Inexplicit Ideas_vrb.md"
    get_proper_names(cur_file_path, heading="### transcript", method='spacy', verbose=True, to_file=None)
    print(f"\n### Changes to propernames.txt\nDELETE: \n\n### Blue Squigs\ndeutschDictionary: \nADDED: \nCHECKED AND ADDED: \n\ncommonDictionary: \nADDED: \nCHECKED AND ADDED: \n\n")
    # Run cspell check on the file
    os.system(f'cspell "{cur_file_path}"')
def evaluate_step_proper_names(eval_transcript_data, ref_transcript_data, method='spacy', sim_ratio_threshold=0.85, debug=False, verbose=True):
    """
    Evaluates proper name matching between evaluation and reference transcripts by comparing extracted names.

    :param eval_transcript_data: list, transcript segment dictionaries to evaluate
    :param ref_transcript_data: list, reference transcript segment dictionaries
    :param method: str, method to use for proper name extraction ('spacy', 'nltk', 'caprules')
    :param sim_ratio_threshold: float, threshold for fuzzy matching similarity between 0-1
    :param debug: bool, flag to enable detailed debug output
    :param verbose: bool, flag to enable progress output
    :return results: dict, statistics about proper name matches including exact, fuzzy and missing names
    """
    verbose_print(debug,"Running evaluate_step_proper_names")
    
    # Initialize results dictionary
    results = {}
    
    # Extract proper names from both transcripts
    ref_text = "\n".join(segment.get('dialogue', '') for segment in ref_transcript_data)
    eval_text = "\n".join(segment.get('dialogue', '') for segment in eval_transcript_data)
    
    # Extract proper names and save to temporary files
    ref_names = extract_proper_names(ref_text, method, debug, verbose)  # Added debug parameter
    eval_names = extract_proper_names(eval_text, method, debug, verbose)  # Added debug parameter
     
    # Create temporary files for comparison
    temp_dir = os.path.dirname(os.path.dirname(CUR_FILE_PATH))
    ref_temp_path = os.path.join(temp_dir, 'temp_ref_names.txt')
    eval_temp_path = os.path.join(temp_dir, 'temp_eval_names.txt')
    
    with open(ref_temp_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(ref_names))
    with open(eval_temp_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(eval_names))
    
    # Compare files using helper function
    missing_names, extra_names, exact_matches_list = lines_compare_files(
        ref_temp_path, eval_temp_path, print_same=False, silent=True
    )
    
    # Clean up temp files
    os.remove(ref_temp_path)
    os.remove(eval_temp_path)
    
    # Create normalized dictionaries for additional analysis
    ref_dict = {name: {
        'original': name,
        'normalized': name.lower(),
        'variants': set(),
        'lowercase_matches': [],
        'fuzzy_matches': []
    } for name in ref_names}
    
    # Track matches
    exact_matches = len(exact_matches_list)
    lowercase_ref_matches = 0
    lowercase_eval_matches = 0
    fuzzy_matches = 0
    matched_eval_names = set(exact_matches_list)
    
    # Second pass - lowercase variants
    verbose_print(debug, "\nLowercase analysis of ref missing proper names in eval:")
    lowercase_instances_ref, lowercase_errors_ref = analyze_lowercase_proper_names(
        eval_text, missing_names, debug, verbose
    )
    for ref_name, instances in lowercase_instances_ref.items():
        if ref_name in ref_dict and not ref_dict[ref_name]['variants']:
            lowercase_ref_matches += 1
            ref_dict[ref_name]['lowercase_matches'] = instances
    
    verbose_print(debug, "\nLowercase analysis - self-consistency check for eval proper names:")
    lowercase_instances_eval, lowercase_errors_eval = analyze_lowercase_proper_names(
        eval_text, eval_names, debug, verbose
    )
    inconsistent_capitalizations = {}
    for eval_name, instances in lowercase_instances_eval.items():
        if instances:  # If we found any lowercase variants
            lowercase_eval_matches += 1
            inconsistent_capitalizations[eval_name] = instances
    
    # Add error counts to results dictionary
    results['lowercase_errors_ref'] = lowercase_errors_ref
    results['lowercase_errors_eval'] = lowercase_errors_eval
    
    # Third pass - fuzzy matches for remaining unmatched names
    remaining_ref_names = [name for name in missing_names if not ref_dict[name]['lowercase_matches']]
    remaining_eval_names = [name for name in eval_names if name not in matched_eval_names]
    
    for ref_name in remaining_ref_names:
        best_ratio = 0
        best_match = None
        
        for eval_name in remaining_eval_names:
            ratio = calc_lev_dist_ratio(ref_name.lower(), eval_name.lower())
            if ratio > best_ratio and ratio >= sim_ratio_threshold:
                best_ratio = ratio
                best_match = eval_name
        
        if best_match:
            fuzzy_matches += 1
            matched_eval_names.add(best_match)
            ref_dict[ref_name]['fuzzy_matches'].append({
                'name': best_match,
                'ratio': best_ratio
            })
    
    # Calculate final metrics
    total_ref_names = len(ref_names)
    results = {
        'pn_total_ref_names': total_ref_names,
        'pn_total_eval_names': len(eval_names),
        'pn_exact_matches': (exact_matches / total_ref_names * 100) if total_ref_names > 0 else 0,
        'pn_lowercase_errors_ref': lowercase_errors_ref,
        'pn_lowercase_errors_eval': lowercase_errors_eval,
        'pn_fuzzy_matches': (fuzzy_matches / total_ref_names * 100) if total_ref_names > 0 else 0,
        'pn_total_matches': ((exact_matches + fuzzy_matches) / total_ref_names * 100) 
                        if total_ref_names > 0 else 0,
        'pn_missing_names': [name for name in missing_names 
                         if not ref_dict[name]['lowercase_matches']
                         and not ref_dict[name]['fuzzy_matches']],
        'pn_extra_names': extra_names,
        'pn_inconsistent_spellings': {name: list(data['variants']) 
                                 for name, data in ref_dict.items() 
                                 if len(data['variants']) > 1}
    }
    
    metrics_data = {
        'pn_total_ref_names': total_ref_names,
        'pn_exact_matches': round(results['pn_exact_matches'])/100,  # convert to decimal with   2 decimal places
        'pn_total_matches': round(results['pn_total_matches'])/100,
        'pn_missing_names': round(len(results['pn_missing_names']) / total_ref_names * 100, 2)/100 if total_ref_names > 0 else 0,
        'pn_extra_names': round(len(results['pn_extra_names']) / len(eval_names) * 100, 2)/100 if len(eval_names) > 0 else 0,
    }

    log_lines = [format_divider("Proper Names Analysis Summary")]
    
    # Add non-percentage metrics first
    log_lines.extend([
        f"Total reference proper names       :     {total_ref_names}",
        f"Total evaluation proper names      :     {len(eval_names)}"
    ])

    # Add percentage metrics in order
    metric_results = [
        format_metric_percentage(exact_matches, total_ref_names, "Exact matches", "ref proper names "),
    ]
    for name, value, formatted_str in metric_results:
        results[name] = value
        log_lines.append(formatted_str)
        
    # Add lowercase error counts
    log_lines.extend([
        f"{'Lowercase errors in ref names':<{MAX_ITEM_NAME_LEN}}:     {lowercase_errors_ref}",
        f"{'Lowercase errors in eval names':<{MAX_ITEM_NAME_LEN}}:     {lowercase_errors_eval}"
    ])

    # Add remaining percentage metrics
    remaining_metrics = [
        format_metric_percentage(fuzzy_matches, total_ref_names, "Fuzzy matches", "ref proper names "),
        format_metric_percentage(exact_matches + fuzzy_matches, total_ref_names, "Total matches", "ref proper names "),
        format_metric_percentage(len(results['pn_missing_names']), total_ref_names, "Missing proper names", "ref proper names "),
        format_metric_percentage(len(results['pn_extra_names']), len(eval_names), "Extra proper names", "eval proper names")
    ]
    for name, value, formatted_str in remaining_metrics:
        results[name] = value
        log_lines.append(formatted_str)
    
    # Add inconsistent spellings if any exist
    if results['pn_inconsistent_spellings']:
        log_lines.append("\nInconsistent spellings:")
        for name, variants in results['pn_inconsistent_spellings'].items():
            log_lines.append(f"  - {name}: {', '.join(variants)}")
    
    # Add missing and extra proper names
    log_lines.extend([
        f"Missing proper names: {[name for name in results['pn_missing_names']]}",
        f"Extra proper names: {[name for name in results['pn_extra_names']]}"
    ])

    log_lines.append("\n")  # Add final newline
    log_text = "\n".join(log_lines)
    
    # Print if verbose
    if verbose:
        print(log_text)
    
    return metrics_data, log_text

#### SPEAKER CONSISTENCY
def evaluate_step_speaker_consistency(eval_transcript_data, ref_transcript_data, debug=False, verbose=True):
    """
    Evaluates speaker consistency between evaluation and reference transcripts.
    Adds 'is_speaker_consistent' boolean field to eval_transcript_data segments.
    For segments where 'is_speaker_consistent' is True, adds 'mapped_speaker' field with the consistent ref speaker name.
    Considers only segments where 'is_aligned' is True.
    """
    verbose_print(debug, "Running evaluate_step_speaker_consistency")
    
    # Initialize variables
    eval_len = len(eval_transcript_data)
    total_aligned = 0
    total_consistent = 0
    
    # Build mapping from eval_speaker_label to ref_speaker_name counts
    speaker_mapping = {}  # {eval_speaker_label: {ref_speaker_name: count}}
    
    # First pass: Build the mapping
    for eval_index in range(eval_len):
        eval_segment = eval_transcript_data[eval_index]
        
        # Initialize/reset evaluation fields
        eval_fields = {
            'is_speaker_consistent': None,    # Boolean
            'mapped_speaker': '',             # String
            'ref_speaker': ''                 # String   
        }
        # Preserved fields
        preserved_fields = ['manual_call']
        preserve_fields(eval_segment, preserved_fields)
        # Update segment with all fields at once
        eval_segment.update(eval_fields)
        
        # Only consider aligned segments
        if eval_segment['is_aligned']:
            total_aligned += 1
            # Get eval speaker label
            eval_speaker = eval_segment['speaker_full']
            # Get aligned ref index
            aligned_ref_index = eval_segment['aligned_ref_index']
            if aligned_ref_index is not None and aligned_ref_index < len(ref_transcript_data):
                ref_segment = ref_transcript_data[aligned_ref_index]
                # Get ref speaker name
                ref_speaker_name = ref_segment['speaker_full']
                # Set ref_speaker field
                eval_segment['ref_speaker'] = ref_speaker_name
                if eval_speaker and ref_speaker_name:
                    # Add mapping
                    if eval_speaker not in speaker_mapping:
                        speaker_mapping[eval_speaker] = {}
                    if ref_speaker_name not in speaker_mapping[eval_speaker]:
                        speaker_mapping[eval_speaker][ref_speaker_name] = 0
                    speaker_mapping[eval_speaker][ref_speaker_name] += 1
        else:
            continue  # Skip unaligned segments

    # Determine the most frequent ref_speaker_name for each eval_speaker_label
    consistent_mappings = {}
    for eval_speaker_label, ref_speaker_counts in speaker_mapping.items():
        # Find the most frequent ref speaker name
        most_frequent_ref_speaker = max(ref_speaker_counts, key=ref_speaker_counts.get)
        consistent_mappings[eval_speaker_label] = most_frequent_ref_speaker

    # Print the mapping if verbose
    if verbose:
        print("Speaker Mapping:")
        # Find max length of speaker names
        max_speaker_len = max(len(ref_speaker) for ref_speaker in consistent_mappings.values()) + 2
        for eval_speaker_label, ref_speaker_counts in speaker_mapping.items():
            most_frequent_ref_speaker = consistent_mappings[eval_speaker_label]
            total_inconsistent = sum(ref_speaker_counts.values()) - ref_speaker_counts[most_frequent_ref_speaker]
            mapping_status = f"Inconsistent ({total_inconsistent} inconsistent)" if total_inconsistent > 0 else "Consistent"
            print(f"{eval_speaker_label} --> {most_frequent_ref_speaker}{' ' * (max_speaker_len - len(most_frequent_ref_speaker))}[{mapping_status}]")
        print("\n")

    # Second pass: Set 'is_speaker_consistent' and 'mapped_speaker' for each segment
    for eval_index in range(eval_len):
        eval_segment = eval_transcript_data[eval_index]
        # Only consider aligned segments
        if eval_segment['is_aligned']:
            # Get eval speaker label
            eval_speaker = eval_segment['speaker_full']
            # Get mapped speaker from consistent mappings
            mapped_speaker = consistent_mappings.get(eval_speaker)
            if mapped_speaker:
                # Always set mapped_speaker
                eval_segment['mapped_speaker'] = mapped_speaker
                
                # Check if the current ref speaker matches for consistency
                aligned_ref_index = eval_segment['aligned_ref_index']
                if aligned_ref_index is not None and aligned_ref_index < len(ref_transcript_data):
                    ref_segment = ref_transcript_data[aligned_ref_index]
                    ref_speaker_name = ref_segment['speaker_full']
                    if ref_speaker_name == mapped_speaker:
                        eval_segment['is_speaker_consistent'] = True
                        total_consistent += 1
                    else:
                        eval_segment['is_speaker_consistent'] = False
    eval_len = len(eval_transcript_data) or 1
    metrics_data = {
        'sc_consistent': round(total_consistent / eval_len * 100, 2) / 100,
        'sc_aligned': round(total_consistent / total_aligned * 100, 2) / 100 if total_aligned else 0
    }
    
    log_lines = [format_divider("Speaker Consistency Analysis Summary")]
    
    # Add metrics
    metric_results = [
        format_boolean_field_percentage(eval_transcript_data, 'is_speaker_consistent', len(eval_transcript_data)),
        format_metric_percentage(total_consistent, total_aligned, "Consistent speakers in aligned", "aligned segments")
    ]
    
    # Add percentage metrics
    for name, value, formatted_str in metric_results:
        log_lines.append(formatted_str)
    
    log_lines.append("\n")  # Add final newline
    log_text = "\n".join(log_lines)
    
    # Print if verbose
    if verbose:
        print(log_text)
    
    return eval_transcript_data, metrics_data, log_text


### EVAL CONFIG, NORMALIZATION, AND SCORING
EVAL_CODE_VERSION = "0.3.0"
DEFAULT_EVAL_CORPORA_CONFIG_REL = os.path.join("apps", "transcription", "stellar-transcriber", "config", "eval-corpora.json")
DEFAULT_FILLER_WORDS = ["um", "uh", "you know", "sort of", "like", "i mean", "well"]
CONTRACTIONS_MAP = {
    "don't": "do not", "doesn't": "does not", "didn't": "did not", "can't": "can not",
    "won't": "will not", "wouldn't": "would not", "shouldn't": "should not",
    "couldn't": "could not", "isn't": "is not", "aren't": "are not", "wasn't": "was not",
    "weren't": "were not", "haven't": "have not", "hasn't": "has not", "hadn't": "had not",
    "i'm": "i am", "you're": "you are", "we're": "we are", "they're": "they are",
    "it's": "it is", "that's": "that is", "what's": "what is", "who's": "who is",
    "i've": "i have", "you've": "you have", "we've": "we have", "they've": "they have",
    "i'll": "i will", "you'll": "you will", "we'll": "we will", "they'll": "they will",
    "i'd": "i would", "you'd": "you would", "we'd": "we would", "they'd": "they would",
}
def find_eval_repo_root(start_dir=None):
    """Walk up from start_dir until the eval-corpora config file is found."""
    current = os.path.abspath(start_dir or os.path.dirname(__file__))
    while True:
        if os.path.isfile(os.path.join(current, DEFAULT_EVAL_CORPORA_CONFIG_REL)):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent
def load_eval_corpus_config(config_path=None, repo_root=None):
    """Load the Stellar Transcriber eval corpus config JSON."""
    if config_path is None:
        repo_root = repo_root or find_eval_repo_root()
        if repo_root is None:
            return {"policies": {"keep-all": {"fillers": "keep", "repeats": "keep", "partial_words": "keep", "numerals": "as-is", "contractions": "as-is"}}}
        config_path = os.path.join(repo_root, DEFAULT_EVAL_CORPORA_CONFIG_REL)
    with open(config_path) as f:
        return json.load(f)
def get_corpus_profile(corpus, config=None):
    """Return the profile dict for one corpus name."""
    config = config or load_eval_corpus_config()
    return config.get(corpus, {})
def get_normalization_policy(policy_id, config=None):
    """Resolve a policy_id to its policy dict; unknown ids fall back to keep-all."""
    config = config or load_eval_corpus_config()
    policies = config.get("policies", {})
    if policy_id in policies:
        return policies[policy_id]
    return policies.get("keep-all", {"fillers": "keep", "repeats": "keep", "partial_words": "keep", "numerals": "as-is", "contractions": "as-is"})
def _policy_is_keep_all(policy):
    """True when policy should reproduce legacy normalize_text behavior exactly."""
    if not policy:
        return True
    return (policy.get("fillers") == "keep" and policy.get("repeats") == "keep"
            and policy.get("partial_words") == "keep" and policy.get("numerals") == "as-is"
            and policy.get("contractions") == "as-is")
def _strip_fillers(text, policy):
    """Remove configured filler words/phrases from text."""
    filler_words = policy.get("filler_words", DEFAULT_FILLER_WORDS)
    result = text
    for filler in sorted(filler_words, key=len, reverse=True):
        pattern = r'\b' + re.escape(filler) + r'\b'
        result = re.sub(pattern, ' ', result, flags=re.IGNORECASE)
    return re.sub(r'\s+', ' ', result).strip()
def _collapse_adjacent_repeats(text):
    """Collapse consecutive duplicate words (case-insensitive)."""
    words = text.split()
    if not words:
        return text
    collapsed = [words[0]]
    for word in words[1:]:
        if word.lower() != collapsed[-1].lower():
            collapsed.append(word)
    return ' '.join(collapsed)
def _strip_partial_words(text):
    """Remove tokens ending with a hyphen (false starts)."""
    words = text.split()
    return ' '.join(w for w in words if not w.endswith('-'))
def _expand_contractions(text):
    """Expand common English contractions to full forms."""
    result = text
    for contraction, expansion in CONTRACTIONS_MAP.items():
        pattern = r'\b' + re.escape(contraction) + r'\b'
        result = re.sub(pattern, expansion, result, flags=re.IGNORECASE)
    return result
def _normalize_numerals_to_words(text):
    """Convert standalone digit tokens to words when num2words is available."""
    try:
        from num2words import num2words
    except ImportError:
        return text
    def replacer(match):
        try:
            return num2words(int(match.group(0)))
        except (ValueError, OverflowError):
            return match.group(0)
    return re.sub(r'\b\d+\b', replacer, text)
def normalize_dialogue(text, policy=None):
    """Normalize transcript dialogue text under an eval policy; keep-all == legacy normalize_text."""
    if text is None:
        text = ''
    if _policy_is_keep_all(policy):
        return normalize_text(text)
    result = text
    if policy.get("partial_words") == "strip":
        result = _strip_partial_words(result)
    if policy.get("repeats") == "collapse-adjacent-repeats":
        result = _collapse_adjacent_repeats(result)
    if policy.get("fillers") == "strip":
        result = _strip_fillers(result, policy)
    if policy.get("contractions") == "expand":
        result = _expand_contractions(result)
    if policy.get("numerals") == "normalize-to-words":
        result = _normalize_numerals_to_words(result)
    return normalize_text(result)
def resolve_proper_names_method(requested_method):
    """Return a proper-names extraction method, falling back to caprules when spacy unavailable."""
    if requested_method == "spacy" and not _SPACY_AVAILABLE:
        print("Warning: spacy unavailable; falling back to caprules for proper names.")
        return "caprules"
    return requested_method or "caprules"
def _alignment_legacy_fraction_fallback(metrics):
    """Legacy rows: 'is_aligned == True' etc. stored as 0-1 fractions of eval segments."""
    total_eval = float(metrics.get('total_eval_segments') or 0)
    if total_eval == 0:
        return 0.0
    aligned_frac = float(metrics.get('is_aligned == True') or 0)
    delete_frac = float(metrics.get('is_delete == True') or 0)
    missing_frac = float(metrics.get('ref_indices_to_add') or 0)
    base = aligned_frac * 100.0
    delete_penalty = delete_frac * 20.0
    missing_penalty = missing_frac * 20.0
    return max(0.0, min(100.0, base - delete_penalty - missing_penalty))
def compute_subscore_alignment_loose(metrics):
    """
    LOOSE alignment subscore 0-100 (previous default):
    100 * (1 - seg_error_count / total_ref_segments), clamped to [0, 100].

    seg_error_count = missing + spurious + boundary_error, where boundary_error includes
    ASR edge-word mismatches that a boundary-repair pass cannot fix.

    Falls back to the fraction metrics for legacy rows without seg_error_count.
    """
    total_ref = float(metrics.get('total_ref_segments') or 0)
    seg_error_count = metrics.get('seg_error_count')
    if seg_error_count is not None and seg_error_count != '' and total_ref > 0:
        return max(0.0, min(100.0, (1.0 - float(seg_error_count) / total_ref) * 100.0))
    return _alignment_legacy_fraction_fallback(metrics)
def compute_subscore_alignment_strict(metrics):
    """
    STRICT alignment subscore 0-100 (active default for composite rollup):
    100 * (1 - seg_error_count_strict / total_ref_segments), clamped to [0, 100].

    seg_error_count_strict = missing + spurious + boundary_misplaced only — segmentation
    defects a boundary-repair pass can fix. Excludes ASR edge-word boundary_error.

    Falls back to the fraction metrics for legacy rows without seg_error_count_strict.
    """
    total_ref = float(metrics.get('total_ref_segments') or 0)
    seg_error_count_strict = metrics.get('seg_error_count_strict')
    if seg_error_count_strict is not None and seg_error_count_strict != '' and total_ref > 0:
        return max(0.0, min(100.0, (1.0 - float(seg_error_count_strict) / total_ref) * 100.0))
    return _alignment_legacy_fraction_fallback(metrics)
def compute_subscore_alignment(metrics):
    """Active alignment subscore — currently STRICT. Call loose explicitly to revert."""
    return compute_subscore_alignment_strict(metrics)
def compute_subscore_word_accuracy(metrics):
    """Word accuracy subscore 0-100 (word_accuracy is stored as a 0-1 fraction)."""
    wa = metrics.get('word_accuracy')
    if wa is None or wa == '':
        return 0.0
    wa = float(wa)
    if wa <= 1.0:
        wa *= 100.0
    return max(0.0, min(100.0, wa))
def compute_subscore_quotations(metrics):
    """Quotation recovery subscore 0-100; fuzzy matches count as half credit."""
    quotes_ref = float(metrics.get('quotes_ref') or 0)
    if quotes_ref == 0:
        return 100.0
    perfect = float(metrics.get('quotes_perfect_matches') or 0)
    normalized = float(metrics.get('quotes_normalized_matches') or 0)
    fuzzy = float(metrics.get('quotes_fuzzy_matches') or 0)
    recovered = perfect + normalized + fuzzy * 0.5
    return max(0.0, min(100.0, (recovered / quotes_ref) * 100.0))
def compute_subscore_proper_names(metrics):
    """Proper-names F1 subscore 0-100."""
    total_ref = float(metrics.get('pn_total_ref_names') or 0)
    if total_ref == 0:
        return 100.0
    exact = float(metrics.get('pn_exact_matches') or 0)
    extra = float(metrics.get('pn_extra_names') or 0)
    recall = exact / total_ref
    precision = exact / max(exact + extra, 1.0)
    if recall + precision == 0:
        return 0.0
    f1 = 2.0 * recall * precision / (recall + precision)
    return max(0.0, min(100.0, f1 * 100.0))
def compute_subscore_speaker(metrics):
    """Speaker consistency subscore 0-100 (sc_aligned stores aligned-segment consistency rate 0-1)."""
    rate = metrics.get('sc_aligned')
    if rate is None or rate == '':
        return 0.0
    rate = float(rate)
    if rate <= 1.0:
        return max(0.0, min(100.0, rate * 100.0))
    return max(0.0, min(100.0, rate))
def compute_composite_scores(metrics, weights=None):
    """Compute subscores and weighted overall_score; return updated metrics dict."""
    weights = weights or {}
    alignment_loose = compute_subscore_alignment_loose(metrics)
    alignment_strict = compute_subscore_alignment_strict(metrics)
    # subscore_alignment is the active rollup input — currently STRICT.
    # To revert to the previous (loose) metric: set subscore_alignment = alignment_loose below.
    subscores = {
        'subscore_alignment': alignment_strict,
        'subscore_alignment_strict': alignment_strict,
        'subscore_alignment_loose': alignment_loose,
        'subscore_word_accuracy': compute_subscore_word_accuracy(metrics),
        'subscore_quotations': compute_subscore_quotations(metrics),
        'subscore_proper_names': compute_subscore_proper_names(metrics),
        'subscore_speaker': compute_subscore_speaker(metrics),
    }
    default_weights = {'word_accuracy': 0.35, 'speaker': 0.25, 'alignment': 0.20, 'proper_names': 0.12, 'quotations': 0.08}
    w = {**default_weights, **weights}
    overall = (
        w.get('alignment', 0.20) * subscores['subscore_alignment']
        + w.get('word_accuracy', 0.35) * subscores['subscore_word_accuracy']
        + w.get('quotations', 0.08) * subscores['subscore_quotations']
        + w.get('proper_names', 0.12) * subscores['subscore_proper_names']
        + w.get('speaker', 0.25) * subscores['subscore_speaker']
    )
    subscores['overall_score'] = round(overall, 2)
    for key, val in subscores.items():
        subscores[key] = round(val, 2)
    return subscores
def rescore_metrics_csv(csv_path, config=None):
    """Recompute subscores and overall_score for every row in a metrics CSV."""
    config = config or load_eval_corpus_config()
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])
    score_fields = ['subscore_alignment', 'subscore_alignment_strict', 'subscore_alignment_loose',
                    'subscore_word_accuracy', 'subscore_quotations',
                    'subscore_proper_names', 'subscore_speaker', 'overall_score']
    for field in score_fields:
        if field not in fieldnames:
            fieldnames.append(field)
    for row in rows:
        policy_id = row.get('policy_id') or 'keep-all'
        profile_weights = None
        for corpus_name, profile in config.items():
            if corpus_name == 'policies':
                continue
            if profile.get('policy_id') == policy_id:
                profile_weights = profile.get('weights')
                break
        subscores = compute_composite_scores(row, profile_weights)
        row.update(subscores)
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    return rows


### TOP LEVEL EVAL
def reorder_and_trim_csv_fields(csv_file_path, fields_list, reorder_only=False, interactive=True):
    """
    Reorders and trims fields in a CSV file to match the specified fields list.
    If reorder_only=True, will only reorder existing fields without adding/removing any.
    
    :param csv_file_path: Path to the CSV file to modify
    :param fields_list: List of field names in desired order. Only these fields will be kept.
    :param reorder_only: If True, will only reorder fields and ensure exact field match
    :return: Path to the modified CSV file
    """
    # Read CSV data and get header
    with open(csv_file_path, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        header = next(reader)
        data = list(reader)
    
    if reorder_only:
        # Verify fields_list contains exactly the same fields as header
        header_set = set(header)
        fields_set = set(fields_list)
        
        if header_set != fields_set:
            missing_in_fields = header_set - fields_set
            missing_in_header = fields_set - header_set
            error_msg = []
            if missing_in_fields:
                error_msg.append(f"Fields missing from fields_list: {missing_in_fields}")
            if missing_in_header:
                error_msg.append(f"Fields missing from CSV header: {missing_in_header}")
            raise ValueError("\n".join(error_msg))
            
        # Create mapping from field name to column index
        field_indices = {field: header.index(field) for field in header}
        
        # Create new rows with reordered columns
        new_rows = []
        for row in data:
            new_row = {}
            for field in fields_list:
                new_row[field] = row[field_indices[field]]
            new_rows.append(new_row)
            
    else:
        # Original duplicate handling and trimming logic
        field_indices = {}
        for i, field in enumerate(header):
            if field not in field_indices:
                field_indices[field] = [i]
            else:
                field_indices[field].append(i)
        
        # Handle duplicates
        columns_to_keep = {}  # Maps field name to column index to keep
        for field, indices in field_indices.items():
            if len(indices) > 1:
                # Compare column values
                columns = []
                for idx in indices:
                    columns.append([row[idx] for row in data])
                
                # Check if all columns are identical
                all_identical = all(col == columns[0] for col in columns[1:])
                
                if all_identical:
                    print(f"Warning: Deleting duplicate column '{field}' - columns verified to be identical")
                    columns_to_keep[field] = indices[0]
                else:
                    if not interactive:
                        print(f"Warning: Non-identical duplicate columns for '{field}'; keeping first column (non-interactive mode).")
                        columns_to_keep[field] = indices[0]
                    else:
                        print(f"\nFound non-identical duplicate columns for '{field}'")
                        print("Which column do you want to preserve?")
                        for i, idx in enumerate(indices, 1):
                            print(f"{i}. Column at position {idx + 1}")
                            preview_size = min(3, len(data))
                            print("Preview:")
                            for row_idx in range(preview_size):
                                print(f"   {data[row_idx][idx]}")
                        while True:
                            try:
                                choice = int(input(f"Enter number (1-{len(indices)}): "))
                                if 1 <= choice <= len(indices):
                                    columns_to_keep[field] = indices[choice - 1]
                                    break
                            except ValueError:
                                pass
                            print(f"Please enter a number between 1 and {len(indices)}")
            else:
                columns_to_keep[field] = indices[0]
        
        # Create new rows with selected columns
        new_rows = []
        for row in data:
            new_row = {}
            for field in fields_list:
                if field in columns_to_keep:
                    new_row[field] = row[columns_to_keep[field]]
                else:
                    new_row[field] = ''  # Add empty string for fields not in original data
            new_rows.append(new_row)
    
    # Write reordered data back to file
    with open(csv_file_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fields_list)
        writer.writeheader()
        writer.writerows(new_rows)
    
    return csv_file_path
EVAL_SEG_FIELDS_ORDER = [
    'aligned_ref_index', 'aligned_ref_timestamp', 'timestamp', 'speaker_full', 
    # 'trans_start', 'trans_end', 
    # 'trans_call', 'trans_man_call', 'trans_correct',
    #'dialogue', #'normalized_dialogue',
    'is_speaker_consistent', 'ref_speaker', 'mapped_speaker',
    'is_delete', 'is_aligned', 'is_anchor', 'is_perfect', 'is_norm_identical',
    'is_boundary_error', 'is_boundary_misplaced',
    'is_similar', 'sim_ratio','is_start_match', 'start_match_words', 'end_match_words',
    'debug_msg', 'timestamp_count', 
    'delta_timestamp',
    #'call', 'manual_call', 'is_call_correct',
    #'seg_delete', 'seg_split'
]
METRICS_CSV_FIELDS_ORDER = [
    'eval_suffix', 'eval_file', 'ref_file', 'datetime', 'policy_id', 'eval_code_version',
    'overall_score', 'subscore_alignment', 'subscore_alignment_strict', 'subscore_alignment_loose',
    'subscore_word_accuracy', 'subscore_quotations',
    'subscore_proper_names', 'subscore_speaker',
    'seg_error_count', 'seg_error_count_strict', 'seg_error_rate', 'seg_missing_count', 'seg_spurious_count',
    'seg_boundary_error_count', 'seg_boundary_misplaced_count', 'seg_aligned_count',
    'is_aligned == True', 'is_perfect == True', 'is_norm_identical == True', 'is_similar == True', 'is_delete == True', 'ref_indices_to_add',
    'word_accuracy', 'quotes_any_timestamp_matches', 'pn_total_matches', 'sc_aligned',
    'total_eval_segments', 'total_ref_segments', 'is_anchor == True', 'is_start_match == True',
    'word_substitutions', 'word_deletions', 'word_insertions',
    'quotes_ref', 'quotes_eval', 'quotes_perfect_matches', 'quotes_normalized_matches', 'quotes_fuzzy_matches',
    'pn_total_ref_names', 'pn_exact_matches', 'pn_missing_names', 'pn_extra_names',
    'sc_consistent',
]
def mrun_reorder_and_trim_csv_fields():
    pass
#if __name__ == "__main__":
    # cur_csv_path = "data/deutsch/dev-eval/2024-03-06_PB_nova2gen-eval.csv"
    # reorder_and_trim_csv_fields(cur_csv_path, EVAL_SEG_FIELDS_ORDER)

    #metrics_csv_path = "data/deutsch/dev-eval/imp_results_sim/eval_metrics copy.csv"
    metrics_csv_path = "data/deutsch/dev-eval/raw_results_deutsch10_2024-11-27_052844/eval-metrics_2024-11-27_052844_reordered.csv"
    reorder_and_trim_csv_fields(metrics_csv_path, METRICS_CSV_FIELDS_ORDER, reorder_only=True)
    
def write_eval_metadata(log_file_path, datetime, version=None):
    """
    Writes metadata information to the evaluation log file.
    
    :param log_file_path: Path to the log file
    :param version: Version string for the evaluation code
    :param datetime: Datetime string
    """
    if version is None:
        version = EVAL_CODE_VERSION
    with open(log_file_path, 'w', encoding='utf-8') as f:
        f.write("## metadata\n")
        f.write(f"datetime: {datetime}\n")
        f.write(f"evaluate code version: {version}\n")
        f.write("\n")

def evaluate_transcript(eval_path, ref_path, output_dir, verbose=True, metrics_csv="eval_metrics.csv", log_file="eval_log.md", datetime=None, interactive=True, on_mismatch='prompt', normalization_policy=None, corpus_weights=None, policy_id=None, proper_names_method=None):
    """
    Evaluates a transcript against a reference transcript.
    Creates detailed CSV evaluation file and summary metrics/logs.

    :param eval_path: Path to the transcript file to be evaluated
    :param ref_path: Path to the reference (gold standard) transcript file
    :param output_dir: Directory for output files
    :param verbose: Whether to print detailed output
    :param metrics_csv: Name of metrics CSV file
    :param log_file: Name of log file
    :return: Tuple of (eval_transcript_data, all_metrics)
    """
    # Create output directories
    os.makedirs(output_dir, exist_ok=True)
    eval_seg_csv_dir = os.path.join(output_dir, "eval-seg_csv_files")
    os.makedirs(eval_seg_csv_dir, exist_ok=True)

    # Generate paths for evaluation files
    eval_filename = os.path.basename(eval_path)
    eval_name, _ = os.path.splitext(eval_filename)
    eval_seg_csv_path = os.path.join(eval_seg_csv_dir, f"{eval_name}-eval-seg.csv")
    prev_eval_seg_csv_path = os.path.join(eval_seg_csv_dir, f"{eval_name}-eval-seg_prev.csv")

    # Create backup of current evaluation file if it exists
    if os.path.exists(eval_seg_csv_path):
        shutil.copy2(eval_seg_csv_path, prev_eval_seg_csv_path)

    # Load entire previous evaluation data if it exists
    cur_csv_eval_transcript_data = []
    if os.path.exists(eval_seg_csv_path):
        with open(eval_seg_csv_path, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            cur_csv_eval_transcript_data = list(reader)
    else:
        verbose_print(verbose, "No previous evaluation CSV found.")

    # Initialize metrics dictionary with eval_suffix as first field
    eval_filename = os.path.basename(eval_path)
    eval_suffix = get_suffix(eval_filename)
    if datetime is None:
        datetime = get_current_datetime_filefriendly()
    all_metrics = {
        'eval_suffix': eval_suffix,
        'eval_file': os.path.basename(eval_path),
        'ref_file': os.path.basename(ref_path),
        'datetime': datetime,
        'policy_id': policy_id or 'keep-all',
        'eval_code_version': EVAL_CODE_VERSION,
    }
    
    # Initialize log text
    log_text = []
    files_and_timestamp = (f"## Eval: {os.path.basename(eval_path)}\nRef: {os.path.basename(ref_path)}\n{datetime}\n\n")
    verbose_print(verbose, files_and_timestamp)

    # Extract data from transcripts
    fields_to_omit = ['speaker_name', 'speaker_role', 'timestamp_link']
    eval_transcript_data = extract_transcript_data(eval_path, fields_to_omit=fields_to_omit)
    ref_transcript_data = extract_transcript_data(ref_path, fields_to_omit=fields_to_omit)
    if not eval_transcript_data or not ref_transcript_data:
        print(f"Skipping eval — missing transcript content in eval or ref file.")
        return None

    # Add normalized_dialogue to ref transcript data
    for segment in ref_transcript_data:
        segment['normalized_dialogue'] = normalize_dialogue(segment.get('dialogue', ''), normalization_policy)

    # Compare lengths and check for manual fields
    prev_length = len(cur_csv_eval_transcript_data)
    new_length = len(eval_transcript_data)
    
    # Get list of manual fields from previous data
    manual_fields = set()
    if prev_length > 0:
        manual_fields = {field for field in cur_csv_eval_transcript_data[0].keys() if 'manual_' in field}
    
    count_adds = sum(1 for row in cur_csv_eval_transcript_data if any(row.get(field) == 'ADD' for field in manual_fields))

    # Check for length mismatch
    if prev_length - count_adds != new_length and verbose:
        print(f"\nWarning: Length mismatch between previous and new evaluation data:")
        print(f"Previous evaluation length: {prev_length} with ADD segments: {count_adds}")
        print(f"New evaluation length: {new_length}")
        if manual_fields:
            print(f"\nExisting manual fields that may be lost: {', '.join(manual_fields)}")
        if not interactive:
            if on_mismatch == 'abort':
                print("Process aborted (on_mismatch=abort).")
                return None
        else:
            user_input = input("\nDo you want to continue? Press Enter to continue or type 'e' to exit: ")
            if user_input.lower() == 'e':
                print("Process aborted by the user.")
                return None

    # Copy over any 'manual_' fields from previous data
    special_values = ['ADD']
    if prev_length - count_adds == new_length:
        printed_fields = set()
        eval_idx = 0
        for prev_row in cur_csv_eval_transcript_data:
            if any(prev_row.get(field) in special_values for field in manual_fields):
                continue
            if eval_idx < new_length:
                segment = eval_transcript_data[eval_idx]
                for field, value in prev_row.items():
                    if 'manual_' in field:
                        if field not in printed_fields:
                            printed_fields.add(field)
                        segment[field] = value
                eval_idx += 1
    else:
        prev_data_by_timestamp = {row.get('timestamp'): row for row in cur_csv_eval_transcript_data if row.get('timestamp')}
        printed_fields = set()
        for segment in eval_transcript_data:
            timestamp = segment.get('timestamp')
            if timestamp and timestamp in prev_data_by_timestamp:
                prev_row = prev_data_by_timestamp[timestamp]
                special_value = next((prev_row.get(field) for field in manual_fields 
                                   if prev_row.get(field) in special_values), None)
                if special_value:
                    for field in manual_fields:
                        if field not in printed_fields:
                            print(f"Copying field from current CSV to new eval transcript: {field}")
                            printed_fields.add(field)
                        segment[field] = special_value
                else:
                    for field, value in prev_row.items():
                        if 'manual_' in field:
                            if field not in printed_fields:
                                print(f"Copying field from current CSV to new eval transcript: {field}")
                                printed_fields.add(field)
                            segment[field] = value

    def update_metrics_and_log(log_text, all_metrics, metrics_and_logs):
        """
        Updates log text and metrics with new values from a list of (metrics, log_text) tuples
        """
        for metrics, text in metrics_and_logs:
            log_text.append(text)
            # Add any new metric keys to all_metrics if they don't exist
            for key in metrics:
                if key not in all_metrics:
                    all_metrics[key] = None
            # Update values
            all_metrics.update(metrics)

    # Run evaluation steps and collect metrics/logs
    print(f"\n\nEvaluating transcript   Eval: {os.path.basename(eval_path)}    Ref: {os.path.basename(ref_path)}")
    metrics_and_logs = []
    
    # Alignment metrics
    eval_transcript_data, align_metrics, align_text = evaluate_step_segments_align(
        eval_transcript_data, ref_transcript_data, verbose=verbose, normalization_policy=normalization_policy)
    metrics_and_logs.append((align_metrics, align_text))
    
    # WER metrics
    wer_metrics, wer_text = evaluate_step_word_error_rate(eval_transcript_data, ref_transcript_data, verbose=verbose)
    metrics_and_logs.append((wer_metrics, wer_text))
    
    # Quotation metrics
    quotes_metrics, quotes_text = evaluate_step_quotations(
        eval_transcript_data, ref_transcript_data, verbose=verbose, normalization_policy=normalization_policy)
    metrics_and_logs.append((quotes_metrics, quotes_text))
    
    # Proper names metrics
    pn_method = resolve_proper_names_method(proper_names_method or 'spacy')
    pn_metrics, pn_text = evaluate_step_proper_names(
        eval_transcript_data, ref_transcript_data, method=pn_method, verbose=verbose)
    metrics_and_logs.append((pn_metrics, pn_text))
    
    # Speaker consistency metrics
    eval_transcript_data, sc_metrics, sc_text = evaluate_step_speaker_consistency(eval_transcript_data, ref_transcript_data, verbose=verbose)
    metrics_and_logs.append((sc_metrics, sc_text))

    # Update all metrics and logs at once
    update_metrics_and_log(log_text, all_metrics, metrics_and_logs)
    all_metrics.update(compute_composite_scores(all_metrics, corpus_weights))

    # Save evaluated data to CSV
    fieldnames = eval_transcript_data[0].keys()
    with open(eval_seg_csv_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(eval_transcript_data)
        
    reorder_and_trim_csv_fields(eval_seg_csv_path, EVAL_SEG_FIELDS_ORDER)

    # Write to log file
    if log_file:
        log_file_path = os.path.join(output_dir, log_file)
        is_new_log_file = not os.path.exists(log_file_path)
        if is_new_log_file:
            write_eval_metadata(log_file_path, datetime=datetime)
        with open(log_file_path, 'a', encoding='utf-8') as f:
            f.write(f"{files_and_timestamp}")
            f.write("\n".join(log_text))
            f.write("\n\n")
    
    # Write to metrics CSV
    if metrics_csv:
        metrics_csv_path = os.path.join(output_dir, metrics_csv)
        write_mode = 'a' if os.path.exists(metrics_csv_path) else 'w'
        
        # Create ordered metrics dictionary
        ordered_metrics = {}
        for field in METRICS_CSV_FIELDS_ORDER:
            ordered_metrics[field] = all_metrics.get(field, '')
            
        with open(metrics_csv_path, write_mode, newline='') as f:
            writer = csv.DictWriter(f, fieldnames=METRICS_CSV_FIELDS_ORDER)
            if write_mode == 'w':
                writer.writeheader()
            writer.writerow(ordered_metrics)

    return eval_transcript_data, all_metrics
def mrun_evaluate_transcript_dev():
    pass
#if __name__ == "__main__":
    output_dir = "data/deutsch/dev-eval/raw_results_indiv-eval-run_reordered"
    cur_ref_transcript_path = "data/deutsch/dev-eval/2024-03-06_PB_vrbref.md"
    # cur_eval_transcript_path = "data/deutsch/dev-eval/2024-03-06_PB_vrbref.md"
    # evaluate_transcript(cur_eval_transcript_path, cur_ref_transcript_path, output_dir)

    # cur_eval_transcript_path = "data/deutsch/dev-eval//2024-03-06_PB_vrbold.md"
    # evaluate_transcript(cur_eval_transcript_path, cur_ref_transcript_path, output_dir)

    # cur_eval_transcript_path = "data/deutsch/dev-eval/2024-03-06_PB_nova2gen.md"
    # evaluate_transcript(cur_eval_transcript_path, cur_ref_transcript_path, output_dir)

    cur_eval_transcript_path = "data/deutsch/dev-eval/2024-03-06_PB_dgwhspm.md"
    evaluate_transcript(cur_eval_transcript_path, cur_ref_transcript_path, output_dir)

    # cur_eval_transcript_path = "data/deutsch/dev-eval/2024-03-06_PB_audiogest.md"
    # evaluate_transcript(cur_eval_transcript_path, cur_ref_transcript_path, output_dir)

    # cur_eval_transcript_path = "data/deutsch/dev-eval/2024-03-06_PB_otter.md"
    # evaluate_transcript(cur_eval_transcript_path, cur_ref_transcript_path, output_dir)

    # cur_ref_transcript_path = "data/deutsch/dev-eval/2024-03-06_PB 30min_lol-ref.md"
    # cur_eval_transcript_path = "data/deutsch/dev-eval/2024-03-06_PB 30min_lol.md"
    # evaluate_transcript(cur_eval_transcript_path, cur_ref_transcript_path, output_dir)
def mrun_evaluate_transcript_nova_vs_whspm():
    pass
if __name__ == "__main__":
    cur_ref_transcript_path = "data/misc_books/Sovereign Child/22025-01-17_Tim Ferriss Show - Naval and Aaron Stupple on Sovereign Child_dgwhspm.md"
    cur_eval_transcript_path = "data/misc_books/Sovereign Child/22025-01-17_Tim Ferriss Show - Naval and Aaron Stupple on Sovereign Child_nova2gen.md"
    output_dir = os.path.dirname(cur_ref_transcript_path)
    evaluate_transcript(cur_eval_transcript_path, cur_ref_transcript_path, output_dir)

def evaluate_raw_transcripts(eval_ref_pairs, output_dir, verbose=False):
    """
    Evaluates multiple pairs of transcripts and generates summary reports.
    
    :param eval_ref_pairs: List of tuples (eval_path, ref_path)
    :param output_dir: Directory for output files
    :return: List of evaluation metrics dictionaries
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Setup output files
    cur_datetime = get_current_datetime_filefriendly()
    log_file = f"eval-log_{cur_datetime}.md"
    metrics_csv = f"eval-metrics_{cur_datetime}.csv"
    
    # Write metadata to log file
    log_file_path = os.path.join(output_dir, log_file)
    write_eval_metadata(log_file_path, datetime=cur_datetime)

    # Process each pair
    all_metrics = []
    for i, (eval_path, ref_path) in enumerate(eval_ref_pairs, 1):
        eval_transcript_data, metrics = evaluate_transcript(eval_path, ref_path, output_dir, verbose=verbose, metrics_csv=metrics_csv, log_file=log_file, datetime=cur_datetime)
        all_metrics.append(metrics)
        print(f"Completed {i} of {len(eval_ref_pairs)} transcript evaluations")
        #print(f"  Eval: {os.path.basename(eval_path)} vs Ref: {os.path.basename(ref_path)}")
    
    metrics_csv_path = os.path.join(output_dir, metrics_csv)
    return log_file_path, metrics_csv_path, cur_datetime
def mtest_evaluate_raw_transcripts():
    pass   
#if __name__ == "__main__":
    eval_ref_pairs = [
        #("data/deutsch/dev-eval/2024-03-06_PB_vrbold.md", "data/deutsch/dev-eval/2024-03-06_PB_vrbref.md"),
        ("data/deutsch/dev-eval/2024-03-06_PB_nova2gen.md", "data/deutsch/dev-eval/2024-03-06_PB_vrbref.md"),
        ("data/deutsch/dev-eval/2024-03-06_PB_dgwhspm.md", "data/deutsch/dev-eval/2024-03-06_PB_vrbref.md"),
    ]
    output_dir = "data/deutsch/dev-eval/raw_results_eval-dev-PB_" + get_current_datetime_filefriendly()
    #evaluate_transcript(eval_ref_pairs[0][0], eval_ref_pairs[0][1], output_dir)
    evaluate_raw_transcripts(eval_ref_pairs, output_dir)

def create_eval_ref_pairs(title_list, ref_folder, eval_folder, ref_suffixpat, eval_suffixpat_list):
    """
    Creates evaluation-reference pairs for transcript comparison.
    Verifies all files exist before returning pairs.
    
    :param title_list: List of base titles to process
    :param ref_folder: Path to reference transcripts folder
    :param ref_suffixpat: Suffix pattern for reference files
    :param eval_folder: Path to evaluation transcripts folder
    :param eval_suffixpat_list: List of suffix patterns for evaluation files
    :return: List of tuples containing (eval_path, ref_path) pairs or None if files missing
    """
    # First collect all paths we'll need
    all_paths = []
    missing_paths = []
    
    for title in title_list:
        # Check reference path
        ref_path = os.path.join(ref_folder, title + ref_suffixpat)
        all_paths.append(ref_path)
        if not os.path.exists(ref_path):
            missing_paths.append(ref_path)
        
        # Check eval paths
        for eval_suffixpat in eval_suffixpat_list:
            eval_path = os.path.join(eval_folder, title + eval_suffixpat)
            all_paths.append(eval_path)
            if not os.path.exists(eval_path):
                missing_paths.append(eval_path)
    
    # Report status
    if missing_paths:
        print(f"\nERROR: The following {len(missing_paths)} files do not exist:")
        for path in missing_paths:
            print(f"  {path}")
        return None
    else:
        print(f"\nAll {len(all_paths)} files exist")
        
        # Create and return pairs
        eval_ref_pairs = []
        for title in title_list:
            ref_path = os.path.join(ref_folder, title + ref_suffixpat)
            for eval_suffixpat in eval_suffixpat_list:
                eval_path = os.path.join(eval_folder, title + eval_suffixpat)
                eval_ref_pairs.append((eval_path, ref_path))
        
        return eval_ref_pairs
def evaluate_raw_with_std_suffixes(title_list, output_dir, ref_folder, eval_folder, ref_suffixpat="_vrb.md", eval_suffixpat_list=["_nova2gen.md", "_dgwhspm.md"]):
    eval_ref_pairs = create_eval_ref_pairs(title_list, ref_folder, eval_folder, ref_suffixpat, eval_suffixpat_list)
    if eval_ref_pairs:
        evaluate_raw_transcripts(eval_ref_pairs, output_dir)
    else:
        print("Skipping evaluation because of missing files")

BATCH_DEUTSCH_LAST_10 = [
    "2024-08-26_Reason Is Fun - Ep6 Are Feelings Ideas",
    "2024-03-06_Peter Boghossian - Ideological Contagion",
    "2024-03-31_Sagenhaft und Sonderbar der Podcast",
    "2024-03-04_Alex OConnor - The Multiverse is Real",
    "2024-01-04_Reason Is Fun - Ep5 The Art of Decision Making",
    "2024-01-01_Arjun Khemani - Free-Will TCS and Anarcho-Capitalism",
    "2023-12-23_Antisemitism in Britain",
    "2023-12-19_Steven Pinker 1 on Joe Walker - on AGI Doom and Enemies of Civilization",
    "2023-10-16_Sean Carroll Mindscape - On Science Complexity and Explanation",
    "2023-10-15_Deutsch Files 3 with Naval and Brett",
]
def mrun_evaluate_raw_with_std_suffixes():  # Run this for Deutsch10
    pass   
#if __name__ == "__main__":
    output_dir = "data/deutsch/dev-eval/raw_results_deutsch10_" + get_current_datetime_filefriendly()
    title_list = BATCH_DEUTSCH_LAST_10
    ref_folder = "data/deutsch/f8_done_qafixed_and_vrb"
    eval_folder = "data/deutsch/f9_raw"
    evaluate_raw_with_std_suffixes(title_list, output_dir, ref_folder, eval_folder)

SEARCH_FOLDERS = ["data/deutsch"]
RAW_SUFFIXPAT_LIST = ["_nova2gen.md", "_dgwhspm.md"]
REF_SUFFIXPAT = "_vrb.md"
def search_for_transcript_paths(title, search_folders, suffixpat_list, verbose=True):
    """
    Finds raw transcript files matching the given title and suffix patterns.
    Searches recursively through all subfolders.
    
    :param title: Base title to search for
    :param search_folders: List of folders to search in
    :param eval_suffixpat_list: List of suffix patterns for raw evaluation files
    :return: List of paths to matching raw transcript files
    """
    transcript_paths = []
    
    for folder in search_folders:
        for root, _, files in os.walk(folder):
            for suffix in suffixpat_list:
                potential_filename = title + suffix
                if potential_filename in files:
                    transcript_paths.append(os.path.join(root, potential_filename))
                
    if not transcript_paths:
        verbose_print(verbose,f"No raw transcripts found matching title '{title}' with suffixes {suffixpat_list}")
    else:
        print(f"Found {len(transcript_paths)} raw transcripts:")
        for path in transcript_paths:
            verbose_print(verbose,f"  {os.path.basename(path)}")
    
    return transcript_paths
def evaluate_improved_transcript(imp_path, ref_path, output_dir, raw_eval_metrics_csv_path=None, debug=True, verbose=False, metrics_csv="eval_metrics.csv", log_file="eval_log.md", datetime=None):
    """
    Evaluates an improved transcript against a reference and compares metrics with raw transcripts.
    
    :param imp_path: Path to the improved transcript file
    :param ref_path: Path to the reference transcript file
    :param output_dir: Directory for output files
    :param raw_eval_metrics_csv_path: Optional path to existing raw evaluation metrics CSV
    :return: None
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract title from improved transcript path
    imp_basename = os.path.basename(imp_path)
    imp_title = os.path.splitext(remove_all_suffixes_in_str(imp_basename))[0]
    
    metrics_csv_path = os.path.join(output_dir, metrics_csv)
    ref_basename = os.path.basename(ref_path)
    
    # Check if metrics file exists and already contains evaluations for this reference
    if os.path.exists(metrics_csv_path):
        with open(metrics_csv_path, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            if any(row['ref_file'] == ref_basename for row in reader):
                # Reference already evaluated, skip raw evaluation processing
                verbose_print(debug, f"Found existing evaluations for reference {ref_basename}")
                
                # Write metadata to log file if it's new
                if log_file:
                    log_file_path = os.path.join(output_dir, log_file)
                    is_new_log_file = not os.path.exists(log_file_path)
                    if is_new_log_file:
                        write_eval_metadata(log_file_path, datetime=datetime)
                
                # Evaluate improved transcript and add to metrics CSV
                evaluate_transcript(imp_path, ref_path, output_dir,
                    verbose=verbose, metrics_csv=metrics_csv, log_file=log_file, datetime=datetime)
                return

    # If we get here, either metrics file doesn't exist or reference not found
    if raw_eval_metrics_csv_path:
        # Read existing metrics CSV
        with open(raw_eval_metrics_csv_path, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            metrics_rows = list(reader)
        
        # Filter rows to only include those matching the improved title
        filtered_rows = [row for row in metrics_rows 
                        if row['eval_file'].startswith(imp_title)]
        
        # Verify reference file matches for all filtered rows
        mismatched_refs = [row for row in filtered_rows if row['ref_file'] != ref_basename]
        
        if mismatched_refs:
            verbose_print(debug, "Reference file mismatch found:")
            for row in mismatched_refs:
                verbose_print(debug, f"  Ref file for raw eval in provided CSV: {row['ref_file']}")
            verbose_print(debug, f"  Ref file for imp eval in current run: {ref_basename}")
            raise ValueError("Reference file in filtered rows doesn't match current reference file")
        else:
            verbose_print(debug, f"Reference file matches in all {len(filtered_rows)} filtered rows")
        
        # Write filtered rows to metrics CSV if any exist
        write_mode = 'a' if os.path.exists(metrics_csv_path) else 'w'
        if filtered_rows:
            with open(metrics_csv_path, write_mode, newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=filtered_rows[0].keys())
                if write_mode == 'w':
                    writer.writeheader()
                writer.writerows(filtered_rows)
        else:
            verbose_print(debug, f"No rows found for improved transcript {imp_title}")
    
    # Write metadata to log file if it's new
    if log_file:
        log_file_path = os.path.join(output_dir, log_file)
        is_new_log_file = not os.path.exists(log_file_path)
        if is_new_log_file:
            write_eval_metadata(log_file_path, datetime=datetime)
    
    # Evaluate improved transcript and add to metrics CSV
    evaluate_transcript(imp_path, ref_path, output_dir,
        verbose=verbose, metrics_csv=metrics_csv, log_file=log_file, datetime=datetime)
def mtest_evaluate_improved_transcript():
    pass
#if __name__ == "__main__":
    imp_path = "data/deutsch/dev-eval/2024-03-06_PB_vrbold.md"
    ref_path = "data/deutsch/dev-eval/2024-03-06_PB_vrbref.md"
    output_dir = "data/deutsch/dev-eval/imp_results"

    # ===== test with no existing metrics CSV =====
    # search_folders = ["data/deutsch/dev-eval"]
    # evaluate_improved_transcript(imp_path, ref_path, output_dir)
    # ===== will create the metrics.csv and log.md files in the output directory, not in a new raw folder =====

    # ===== test with existing metrics CSV =====
    raw_eval_metrics_csv_path = "data/deutsch/dev-eval/raw_results_eval-dev-PB_2024-11-27_054441/eval-metrics_2024-11-27_054441.csv"
    evaluate_improved_transcript(imp_path, ref_path, output_dir, raw_eval_metrics_csv_path)

FIELDS_BEST_MAP = [
    {'is_aligned == True': 'greater'},
    {'is_perfect == True': 'greater'},
    {'is_norm_identical == True': 'greater'},
    {'is_similar == True': 'greater'},
    {'is_delete == True': 'less'},
    {'ref_indices_to_add': 'less'},
    {'word_accuracy': 'greater'},
    {'quotes_any_timestamp_matches': 'greater'},
    {'pn_total_matches': 'greater'},
    {'sc_aligned': 'greater'},
    {'total_eval_segments': 'skip'},
    {'total_ref_segments': 'skip'},
    {'is_anchor == True': 'greater'},
    {'is_start_match == True': 'greater'},
    {'word_substitutions': 'less'},
    {'word_deletions': 'less'},
    {'word_insertions': 'less'},
    {'quotes_ref': 'skip'},
    {'quotes_eval': 'skip'},
    {'quotes_perfect_matches': 'greater'},
    {'quotes_normalized_matches': 'greater'},
    {'quotes_fuzzy_matches': 'greater'},
    {'pn_exact_matches': 'greater'},
    {'pn_missing_names': 'less'},
    {'pn_extra_names': 'less'},
    {'sc_consistent': 'greater'}
]
BEST_SUFFIX = "_bestraw"
def create_best_rows_in_metrics_csv(metrics_csv_path, fields_best_map=FIELDS_BEST_MAP, raw_suffixpat_list=RAW_SUFFIXPAT_LIST, debug=False):
    """
    Creates 'best' rows in metrics CSV by comparing raw transcript metrics.
    Places best row directly under the raw rows it was calculated from.
    
    :param metrics_csv_path: Path to metrics CSV file
    :param fields_best_map: List of dicts mapping field conditions to 'greater' or 'less'
    :param raw_suffixpat_list: List of raw suffix patterns (with extensions) to match
    """
    best_suffix = BEST_SUFFIX

    # Read existing CSV
    with open(metrics_csv_path, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)
        fieldnames = reader.fieldnames

    verbose_print(debug, f"\nProcessing CSV with {len(fieldnames)} fields: {fieldnames}")
    
    # Map raw suffix patterns to eval_suffix values (strip extension and leading underscore)
    raw_suffixes = [os.path.splitext(pat)[0] for pat in raw_suffixpat_list]
    verbose_print(debug, f"Raw suffixes: {raw_suffixes}")
    
    # Create mapping of field names to their comparison types
    field_comparisons = {}
    for field_map in fields_best_map:
        for field_condition, comparison in field_map.items():
            field_name = field_condition
            field_comparisons[field_name] = comparison
    
    verbose_print(debug, f"\nField comparisons map:")
    for field, comp in field_comparisons.items():
        verbose_print(debug, f"  {field}: {comp}")
    
    # Group rows by ref_file to process each transcript separately
    grouped_rows = {}
    for row in rows:
        if row['ref_file']:  # Skip empty rows
            ref_file = row['ref_file']
            if ref_file not in grouped_rows:
                grouped_rows[ref_file] = []
            grouped_rows[ref_file].append(row)

    best_rows_added = 0
    for ref_file, group in grouped_rows.items():
        verbose_print(debug, f"\nProcessing reference file: {ref_file}")
        
        # Find rows matching raw suffixes
        raw_rows = [row for row in group if any(row['eval_suffix'] == suffix for suffix in raw_suffixes)]
        verbose_print(debug, f"Found {len(raw_rows)} raw rows with suffixes: {[row['eval_suffix'] for row in raw_rows]}")
        
        if len(raw_rows) > 0:
            # Create best row with minimal initial data
            best_row = {
                'eval_suffix': best_suffix,
                'eval_file': '',  # Clear eval_file
                'ref_file': raw_rows[0]['ref_file'],
                'datetime': raw_rows[0]['datetime']
            }
            
            # Calculate best metrics for all fields in the mapping
            for field_name, comparison in field_comparisons.items():
                verbose_print(debug, f"\nProcessing field: {field_name} (comparison: {comparison})")
                
                if field_name not in fieldnames:
                    verbose_print(debug, f"  Skipping field {field_name} - not found in CSV headers")
                    continue
                    
                if comparison == 'skip':
                    best_row[field_name] = None
                    verbose_print(debug, f"  Skipping field {field_name} because comparison is 'skip'")
                    continue
                    
                try:
                    values = [float(row[field_name]) for row in raw_rows if row[field_name]]
                    verbose_print(debug, f"  Raw values found: {values}")
                    
                    if values:
                        if comparison == 'greater':
                            best_value = max(values)
                            verbose_print(debug, f"  Taking maximum value: {best_value}")
                        elif comparison == 'less':
                            best_value = min(values)
                            verbose_print(debug, f"  Taking minimum value: {best_value}")
                        else:
                            verbose_print(debug, f"  WARNING: Unknown comparison type: {comparison}")
                            best_value = max(values)
                        best_row[field_name] = str(best_value)
                    else:
                        verbose_print(debug, f"  No valid values found, raising ValueError")
                        raise ValueError(f"No valid values found for field {field_name}")
                except ValueError as e:
                    verbose_print(debug, f"  Error converting values: {e}")
                    best_row[field_name] = ''
            
            # Insert best row after raw rows
            for i, row in enumerate(rows):
                if row == raw_rows[-1]:  # Found last raw row
                    rows.insert(i + 1, best_row)
                    best_rows_added += 1
                    break

    # Write updated CSV
    with open(metrics_csv_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Added {best_rows_added} '{best_suffix}' rows to the metrics CSV")
def mtest_create_best_rows_in_metrics_csv():
    pass
#if __name__ == "__main__":
    metrics_csv_path = "data/deutsch/dev-eval/imp_results_sim_reordered/eval_metrics copy.csv"
    create_best_rows_in_metrics_csv(metrics_csv_path)

def validate_best_rows(rows, best_suffix, ref_files):
    """
    Validate that each ref_file has exactly one corresponding best row.
    Returns dict mapping ref_files to their best rows.
    """
    best_rows_by_ref = {}
    for row in rows:
        if row['eval_suffix'] == best_suffix and row['ref_file'] in ref_files:
            if row['ref_file'] in best_rows_by_ref:
                raise ValueError(f"Multiple best rows found for ref_file: {row['ref_file']}")
            best_rows_by_ref[row['ref_file']] = row
    
    missing_refs = set(ref_files) - set(best_rows_by_ref.keys())
    if missing_refs:
        raise ValueError(f"Missing best rows for ref_files: {missing_refs}")
        
    return best_rows_by_ref

def calculate_error_reduction(eval_value, best_value, comparison_type):
    """
    Calculate percent error reduction between eval and best values.
    """
    eval_value = float(eval_value)
    best_value = float(best_value)
    
    if 'greater' in comparison_type:
        error_old = 1 - best_value
        error_new = 1 - eval_value
    else:  # 'less' in comparison_type
        error_old = best_value
        error_new = eval_value
        
    if error_old == 0:
        return 0  # No error reduction possible if original error was 0
    
    return round(100 * (error_old - error_new) / error_old)

def create_percenterrorreduction_rows_in_metrics_csv(metrics_csv_path, fields_best_map=FIELDS_BEST_MAP, raw_suffixpat_list=RAW_SUFFIXPAT_LIST, debug=True):
    """
    Creates percent error reduction rows in metrics CSV by comparing improved transcript metrics against best raw metrics.
    Places reduction row directly under the improved eval row it was calculated from.
    """
    # Read existing CSV
    with open(metrics_csv_path, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)
        fieldnames = reader.fieldnames

    verbose_print(debug, f"\nProcessing CSV with {len(fieldnames)} fields: {fieldnames}")
    
    # Get rows to exclude (raw and best rows)
    raw_suffixes = [os.path.splitext(pat)[0] for pat in raw_suffixpat_list]
    exclude_suffixes = [BEST_SUFFIX] + raw_suffixes
    verbose_print(debug, f"Exclude suffixes: {exclude_suffixes}")
    
    # Get improved eval rows (all rows except excluded ones)
    eval_rows = [row for row in rows if row['eval_suffix'] not in exclude_suffixes]
    verbose_print(debug, f"Found {len(eval_rows)} improved eval rows")
    
    # Get unique ref_files from eval rows
    ref_files = {row['ref_file'] for row in eval_rows if row['ref_file']}
    
    # Validate and get best rows mapping
    try:
        best_rows_by_ref = validate_best_rows(rows, BEST_SUFFIX, ref_files)
    except ValueError as e:
        print(f"Error validating best rows: {e}")
        return
        
    # Create mapping of field names to their comparison types
    field_comparisons = {}
    for field_map in fields_best_map:
        for field_condition, comparison in field_map.items():
            field_name = field_condition
            field_comparisons[field_name] = comparison
            
    verbose_print(debug, f"\nField comparisons map:")
    for field, comp in field_comparisons.items():
        verbose_print(debug, f"  {field}: {comp}")
    
    # Process each eval row and create corresponding reduction row
    reduction_rows_added = 0
    new_rows = []
    
    for row in rows:
        new_rows.append(row)
        
        if row['eval_suffix'] not in exclude_suffixes and row['ref_file']:
            best_row = best_rows_by_ref[row['ref_file']]
            verbose_print(debug, f"\n{row['eval_suffix']} -> Found best row for this eval_suffix with ref_file {row['ref_file']} and best row suffix: {best_row['eval_suffix']}")
            
            # Create reduction row
            reduction_row = {
                'eval_suffix': f"{row['eval_suffix']}-per",
                'eval_file': row['eval_file'],
                'ref_file': row['ref_file'],
                'datetime': row['datetime']
            }
            
            # Calculate reduction percentages for all fields
            for field_name, comparison in field_comparisons.items():
                if field_name not in fieldnames:
                    verbose_print(debug, f"Skipping field {field_name} - not found in CSV headers")
                    continue
                    
                if 'skip' in comparison:
                    reduction_row[field_name] = None
                    continue
                    
                try:
                    eval_value = row[field_name]
                    best_value = best_row[field_name]
                    
                    if eval_value and best_value:
                        reduction = calculate_error_reduction(eval_value, best_value, comparison)
                        verbose_print(debug, f"  Reduction for {field_name}: {reduction} calculated from {eval_value} and {best_value} with comparison {comparison}")
                        reduction_row[field_name] = str(reduction)
                    else:
                        reduction_row[field_name] = ''
                except (ValueError, KeyError) as e:
                    verbose_print(debug, f"Error calculating reduction for {field_name}: {e}")
                    reduction_row[field_name] = ''
            
            new_rows.append(reduction_row)
            reduction_rows_added += 1
    
    # Write updated CSV
    with open(metrics_csv_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(new_rows)
        
    print(f"Added {reduction_rows_added} percent error reduction rows to the metrics CSV")
def mtest_create_percenterrorreduction_rows_in_metrics_csv():
    pass
#if __name__ == "__main__":
    metrics_csv_path = "data/deutsch/dev-eval/imp_results_sim_reordered/eval_metrics_best copy.csv"
    create_percenterrorreduction_rows_in_metrics_csv(metrics_csv_path)


def create_percenterrorreduction_rows_in_metrics_csv_STARTER(metrics_csv_path, fields_best_map=FIELDS_BEST_MAP, raw_suffixpat_list=RAW_SUFFIXPAT_LIST, debug=False):
    # Map raw suffix patterns to eval_suffix values (strip extension and leading underscore)
    raw_suffixes = [os.path.splitext(pat)[0] for pat in raw_suffixpat_list]
    exclude_suffixes = [BEST_SUFFIX] + raw_suffixes
    verbose_print(debug, f"Exclude suffixes: {exclude_suffixes}")
    # name percenterrorreduction rows = f"_per-{eval_suffix}
    # for all new 'per' rows, there will be an eval row it derives from which are all the rows except the exclude rows
    # copy fields eval_file, ref file, and datetime from eval row
    # for all fields in fields_best_map, calculate percenterrorreduction as 100 * (best_field - eval_field) / best_field which is (old- new) / old


# when have code to create improved transcripts, then will run evaluate_improved_transcript
# with existing metrics CSV that has eval of raw transcripts
def simulate_run_improve_transcripts():
    pass
#if __name__ == "__main__":
    # fake_imp_paths = [
    #     "data/deutsch/fx_archive/2024-08-26_Reason Is Fun - Ep6 Are Feelings Ideas_cemanual.md",
    #     "data/deutsch/fx_archive/2024-03-06_Peter Boghossian - Ideological Contagion_bertafteremilia.md",
    # ]
    fake_imp_paths = [
        "data/deutsch/fx_archive/2024-03-06_Peter Boghossian - Ideological Contagion_emilia.md",
    ]
    output_dir = "data/deutsch/dev-eval/imp_results_sim_reordered"
    raw_eval_metrics_csv_path = "data/deutsch/dev-eval/raw_results_deutsch10_2024-11-27_052844/eval-metrics_2024-11-27_052844_reordered.csv"
    for fake_imp_path in fake_imp_paths:
        title = remove_all_suffixes_in_str(os.path.splitext(os.path.basename(fake_imp_path))[0])
        print(f"title: {title}")
        ref_path = search_for_transcript_paths(title, SEARCH_FOLDERS, [REF_SUFFIXPAT])[0]
        evaluate_improved_transcript(fake_imp_path, ref_path, output_dir, raw_eval_metrics_csv_path)

### ELEVENLABS SCRIBE — DISABLED (2026-07-21)
# Kept in-file for revert. Re-enable: uncomment imports at top of this file, then set
# _ELEVENLABS_SCRIBE_ENABLED = True below (needs `elevenlabs` package + ELEVENLABS_API_KEY).
_ELEVENLABS_SCRIBE_ENABLED = False
def transcribe_elevenlabs_scribe(audio_file_path, language_code="eng", tag_audio_events=True, diarize=True):
    """
    Transcribe audio using ElevenLabs Scribe API
    
    Args:
        audio_file_path (str): Path to audio file
        language_code (str): Language code (default "eng")
        tag_audio_events (bool): Whether to tag audio events like laughter, applause, etc.
        diarize (bool): Whether to annotate who is speaking
        
    Returns:
        dict: Transcription result with text and raw response
    """
    if not _ELEVENLABS_SCRIBE_ENABLED:
        raise RuntimeError(
            "ElevenLabs Scribe is disabled in transcript_eval. "
            "Uncomment the ElevenLabs imports at the top of this file and set "
            "_ELEVENLABS_SCRIBE_ENABLED = True to re-enable."
        )
    print(f"Starting ElevenLabs Scribe transcription for {audio_file_path}...")
    
    # Initialize ElevenLabs client
    client = ElevenLabs(
        api_key=ELEVENLABS_API_KEY,
    )
    
    # Open audio file
    with open(audio_file_path, 'rb') as f:
        audio_data = BytesIO(f.read())
    
    # Process transcription
    try:
        transcription = client.speech_to_text.convert(
            file=audio_data,
            model_id="scribe_v1",
            tag_audio_events=tag_audio_events,
            language_code=language_code,
            diarize=diarize,
        )
        
        # Create a result dictionary with just the text
        result = {
            "text": transcription.text
        }
        
        # We'll handle the complex object conversion in the processing function
        result["_raw_response"] = transcription
        
        return result
        
    except Exception as e:
        print(f"ElevenLabs transcription error: {e}")
        if "invalid_audio_duration" in str(e) and diarize:
            print("Audio duration exceeds limit for diarization. Consider using diarize=False")
        return {"error": str(e)}
def process_elevenlabs_transcription(title, link=None, model="scribe_v1", output_dir="data/audio_inbox", skip_download=False, audio_file_path=None):
    """
    Process a full transcription workflow using ElevenLabs Scribe
    
    Args:
        title (str): Title for the transcription/output files
        link (str, optional): YouTube link to download if audio_file_path not provided
        model (str): Model to use (currently only "scribe_v1" is supported)
        output_dir (str): Directory to save files
        skip_download (bool): Whether to skip download if file exists
        audio_file_path (str, optional): Direct path to audio file
        
    Returns:
        dict: Processing result information
    """
    if not _ELEVENLABS_SCRIBE_ENABLED:
        raise RuntimeError(
            "ElevenLabs Scribe is disabled in transcript_eval. "
            "Uncomment the ElevenLabs imports at the top of this file and set "
            "_ELEVENLABS_SCRIBE_ENABLED = True to re-enable."
        )
    # Helper function to make objects JSON serializable
    def make_json_serializable(obj):
        if hasattr(obj, 'model_dump'):
            return obj.model_dump()
        elif hasattr(obj, 'dict'):
            return obj.dict()
        elif hasattr(obj, '__dict__'):
            return {k: make_json_serializable(v) for k, v in obj.__dict__.items() 
                   if not k.startswith('_')}
        elif isinstance(obj, list):
            return [make_json_serializable(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        else:
            return str(obj)
    
    # Use provided audio file or download from YouTube
    if audio_file_path is None and link:
        print(f"Downloading audio from YouTube: {link}")
        audio_file_path = download_mp3_from_youtube(link, output_title=title, output_dir=output_dir, skip_download=skip_download)
    
    if not audio_file_path or not os.path.exists(audio_file_path):
        print("Error: No valid audio file path provided")
        return {"error": "No valid audio file path provided"}
    
    print(f"Processing {audio_file_path} with ElevenLabs Scribe...")
    
    # Create output paths based on audio filename
    base_name = os.path.splitext(os.path.basename(audio_file_path))[0]
    json_file_path = os.path.join(output_dir, f"{base_name}_elevenlabs.json")
    md_file_path = os.path.join(output_dir, f"{base_name}_elevenlabs.md")
    
    # Get media length to determine if diarization will work
    from mutagen.mp3 import MP3
    try:
        audio = MP3(audio_file_path)
        duration_minutes = audio.info.length / 60
        diarize = True
        
        # Check if file is too long for diarization
        if duration_minutes > 6.5 and not force_diarize:
            print(f"Audio is {duration_minutes:.2f} minutes. Disabling diarization to prevent API errors.")
            print("Use force_diarize=True to attempt diarization anyway.")
            diarize = False
    except Exception:
        # Can't determine length, try with diarization by default
        diarize = True
    
    # Get transcription with appropriate diarization setting
    transcription_result = transcribe_elevenlabs_scribe(audio_file_path, diarize=diarize)
    
    if "error" in transcription_result:
        print(f"Error during transcription: {transcription_result['error']}")
        # Try again without diarization if there was a duration error
        if "invalid_audio_duration" in transcription_result["error"] and "diarize" in transcription_result["error"]:
            print("Retrying without diarization...")
            transcription_result = transcribe_elevenlabs_scribe(audio_file_path, diarize=False)
            if "error" in transcription_result:
                return transcription_result
    
    # Create JSON-serializable data
    try:
        # Extract the raw response
        raw_response = transcription_result.get("_raw_response")
        
        # Build serializable data
        elevenlabs_data = {
            "audio_file": audio_file_path,
            "link": link,
            "title": title,
            "model": model,
            "processed_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "text": transcription_result["text"]
        }
        
        # If we have a raw response, convert it to serializable format
        if raw_response:
            elevenlabs_data["elevenlabs"] = make_json_serializable(raw_response)
        
        # Write JSON file
        print(f"Writing JSON to {json_file_path}")
        with open(json_file_path, 'w') as f:
            json.dump(elevenlabs_data, f, indent=4)
            
    except Exception as e:
        print(f"Error creating JSON file: {e}")
        # Continue anyway to create the markdown file
    
    # Create metadata string for markdown (as YAML front matter)
    metadata_str = "---\n"
    metadata_str += f"title: {title}\n"
    metadata_str += f"date: {datetime.now().strftime('%Y-%m-%d')}\n"
    metadata_str += f"model: ElevenLabs {model}\n"
    metadata_str += f"transcript_source: elevenlabs\n"
    
    if link:
        metadata_str += f"source: {link}\n"
    
    metadata_str += "---\n\n"
    
    # Format content for markdown
    content = transcription_result["text"]
    
    # Write markdown using fileops
    print(f"Writing markdown to {md_file_path}")
    write_metadata_and_content(md_file_path, metadata_str, content, overwrite="yes")
    
    # Post-process the markdown file
    if "error" not in transcription_result:
        # Process speaker names if diarization was used
        has_speakers = raw_response and hasattr(raw_response, "speakers") and raw_response.speakers
        if has_speakers:
            print("Processing speaker names...")
            propagate_speaker_names_throughout_md(md_file_path)
        
        # Convert numbers to words for better readability
        print("Converting numbers to words...")
        convert_nums_to_words(md_file_path)
    
    # Add link to JSON metadata if JSON was successfully created
    if link and os.path.exists(json_file_path):
        add_link_to_json_metadata(json_file_path, link)
    
    return {
        "audio_file": audio_file_path,
        "json_file": json_file_path,
        "md_file": md_file_path,
        "transcription_complete": True
    }
# ===== END OF FILE core/transcript_eval.py =====
