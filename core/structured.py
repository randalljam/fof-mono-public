# ===== START OF FILE core/structured.py =====
# Library for structured processing of QA files

import os
import re
import csv
import subprocess
import pyperclip
import pyautogui
import time
import warnings
from collections import defaultdict
from datetime import datetime

from core.fileops import *


# ---START OF SYNCED CODE--- only code below will be synchronized with chalicelib.

# Set the warnings to use a custom format
warnings.formatwarning = custom_formatwarning
# USAGE: warnings.warn(f"Insert warning message here")

### BLOCK PROCESSING
def get_blocks_from_file(file_path, heading="### qa"):
    """
    Extracts and validates blocks of text from a file.

    :param qa_file_path: string of the path to the file to be read.
    :param verbose: boolean, if True, prints verbose messages. Default is False.
    :return: list of valid blocks from the file.
        """
    from core.fileops import get_heading
    
    block_delimiter = "\n\n"  
    text = get_heading(file_path, heading)
    if text is None:
        raise ValueError(f"Heading '{heading}' not found in file {file_path}")
        
    text = re.sub(r'^#.*\n?', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    blocks_list = []

    blocks = text.split(block_delimiter)
    for block in blocks:
        if block.strip():
            blocks_list.append(block.strip())
            
    return blocks_list

def delete_fields_from_text(text, delete_fields):
    """
    Removes specified fields from a text block, including multi-line field values.
    Field boundary rules:
    1. Two consecutive newlines
    2. A newline followed by an all-caps field name and colon (e.g. 'STARS:')
    
    :param text: string of the text to process
    :param delete_fields: list of field names to delete
    :return: string of text with specified fields removed
    """
    lines = text.split('\n')
    filtered_lines = []
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        should_keep = True
        
        # Check if line starts with any field to delete
        for field in delete_fields:
            if line.startswith(field + ":"):
                should_keep = False
                # Skip all subsequent lines until we find another field or empty line
                i += 1
                while i < len(lines):  # Only proceed if we haven't hit the end
                    next_line = lines[i].strip()
                    # Check if next line is a new field (all caps before colon)
                    is_new_field = False
                    if ': ' in next_line:
                        field_name = next_line.split(':', 1)[0]
                        is_new_field = field_name.isupper()
                    
                    if (not next_line  # Empty line
                        or is_new_field  # All caps field name
                        or (i + 1 < len(lines) and not lines[i + 1].strip())):  # Two newlines
                        i -= 1  # Back up one line since the while loop will increment
                        break
                    i += 1
                if i >= len(lines):  # If we hit the end during multi-line processing
                    i = len(lines) - 1  # Reset to last line
                break
                
        if should_keep:  # Keep all non-deleted lines
            filtered_lines.append(lines[i])
        i += 1
        
    return '\n'.join(filtered_lines)
CUR_MULTI_LINE_BLOCK = '''
QUESTION NUMBER: 1
QUESTION: What are the topics covered in 2024 wildfire preparedness presentation?
TIMESTAMP: [0:00](https://youtu.be/CMflj9am38Q&t=0)
ANSWER: The 2024 wildfire preparedness presentation agenda covers the Big 5
Immediate Action Response Protocols, PVSD Wildfire Emergency Response Plan, evacuations, school closures, decision checklists, 
handling fast-approaching fires with shelter-in-place, protocols for controlled student release at both schools, 
decision checklist for school closure, wildfire risk mitigation efforts, communication and situational awareness, 
and information about poor air quality and high heat guidance from the County Office of Education.
QUESTION NAME: IMPLIED
ANSWER NAME: Roberta Zarea (PVSD Superintendent)
STATUS: 
TOPICS: 
STARS: 

'''
def mrun_delete_fields_from_text():
    pass
#if __name__ == "__main__":
    print(delete_fields_from_text(CUR_MULTI_LINE_BLOCK, ["QUESTION NUMBER", "TOPICS", "ANSWER"]))

def get_field_value(block, field):
    """
    Extracts the content of a specified field from a block of text, including multi-line values.
    Field boundary rules:
    1. Two consecutive newlines
    2. A newline followed by a field name and colon where the field name:
       - is in all caps
       - may contain spaces, underscores, or dashes
       - will be treated as a boundary even if the field is empty
       (Updated empty field handling - RT 2024-03-19)
    
    :param block: string of the block of text to be processed.
    :param field: string of the field to be extracted from the block.
    :return: the content of the field in its appropriate data type, or None if the field is not found.
    """
    lines = block.split('\n')
    for i, line in enumerate(lines):
        if line.strip().startswith(field + ":"):
            # Extract initial content after the colon and space
            field_content = [line[len(field) + 2:].strip()]
            
            # Check for multi-line content
            next_idx = i + 1
            while next_idx < len(lines):
                next_line = lines[next_idx].strip()
                
                # Check if next line is a new field (allowing spaces, underscores, dashes in field names)
                is_new_field = False
                if ':' in next_line:  # Changed from ': ' to ':' to catch empty fields
                    field_name = next_line.split(':', 1)[0].strip()
                    # Check if field name contains only uppercase letters, spaces, underscores, and dashes
                    cleaned_field = field_name.replace(' ', '').replace('_', '').replace('-', '')
                    is_new_field = cleaned_field.isupper() and cleaned_field.isalnum()
                
                # Stop if we hit field boundaries
                if (not next_line  # Empty line
                    or is_new_field  # Field name matching our criteria
                    or (next_idx + 1 < len(lines) and not lines[next_idx + 1].strip())):  # Two newlines
                    break
                
                field_content.append(next_line)
                next_idx += 1
            
            # Join multi-line content with newlines to preserve formatting
            combined_content = '\n'.join(field_content).strip()
            
            # Handle special field types
            if field in ["STARS", "TRANSCRIPT START POSITION", "TRANSCRIPT END POSITION"]:
                return int(combined_content) if combined_content else None
            elif field == "TOPICS":
                return [topic.strip() for topic in combined_content.split(',')] if combined_content else []
            else:
                return combined_content
            
    return None
def mrun_get_field_value():
    pass
#if __name__ == "__main__":
    print(get_field_value(CUR_MULTI_LINE_BLOCK, "QUESTION"))

def get_all_fields_dict(block):
    """
    Extracts all fields and their contents from a block of text.

    :param block: string of the block of text to be processed.
    :return: dictionary of fields and their contents in their appropriate data types.
    """
    lines = block.split('\n')
    fields_dict = {}
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Check if line contains a field (has a colon)
        if ':' in line:
            parts = line.split(':', 1)
            field = parts[0].strip()
            # Only process if it's an uppercase field name
            if field.isupper():
                field_content = [parts[1].strip()]
                
                # Check for multi-line content
                next_idx = i + 1
                while next_idx < len(lines):
                    next_line = lines[next_idx].strip()
                    
                    # Check if next line is a new field (all caps before colon)
                    is_new_field = False
                    if ':' in next_line:
                        field_name = next_line.split(':', 1)[0]
                        is_new_field = field_name.isupper()
                    
                    # Stop if we hit field boundaries
                    if (not next_line  # Empty line
                        or is_new_field  # All caps field name
                        or (next_idx + 1 < len(lines) and not lines[next_idx + 1].strip())):  # Two newlines
                        break
                    
                    field_content.append(next_line)
                    next_idx += 1
                
                # Join multi-line content with newlines
                combined_content = '\n'.join(field_content).strip()
                
                # Handle special field types - COMMENTED OUT SO THESE ARE STRINGS
                # if field in ["STARS", "TRANSCRIPT START POSITION", "TRANSCRIPT END POSITION"]:
                #     fields_dict[field] = int(combined_content) if combined_content else None
                if field == "TOPICS":
                    fields_dict[field] = [topic.strip() for topic in combined_content.split(',')] if combined_content else []
                else:
                    fields_dict[field] = combined_content
                
                i = next_idx - 1  # Adjust index to account for multi-line processing
        i += 1
    
    return fields_dict
def mrun_get_all_fields_dict():
    pass
#if __name__ == "__main__":
    fields_dict = get_all_fields_dict(CUR_MULTI_LINE_BLOCK)
    print('{' + '\n'.join(f"    {repr(key)}: {repr(value)}," for key, value in fields_dict.items())[:-1] + '\n}')

def count_blocks(file_path, heading="## content"):  # quick way is to use find on a field
    """
    Counts the number of blocks in a specific section of a file, skipping comment lines.

    :param file_path: string of the path to the file to be processed.
    :param heading: string of the markdown heading to search for. Default is "## content".
    :return: integer representing the total number of blocks found.
    """
    content = get_heading(file_path, heading)
    
    if content is None:
        return 0
    
    # Remove comment lines (lines starting with # or whitespace followed by #)
    content_lines = [line for line in content.split('\n') if not line.lstrip().startswith('#')]
    content_without_comments = '\n'.join(content_lines)
    
    # Split the content into blocks (separated by blank lines)
    blocks = content_without_comments.split('\n\n')
    
    # Count non-empty blocks
    total_blocks = sum(1 for block in blocks if block.strip())
    
    return total_blocks
def mtest_count_blocks():
    pass
#if __name__ == "__main__":        
    cur_file_path = "data/floodlamp/reg/fda-townhalls/dev/2020-12-09_Virtual Town Hall 36_qa-incremental_7-21_6_25 blocks 1 review.md"
    print(count_blocks(cur_file_path))

def propagate_fields_by_subheading(file_path, full_fields, required_fields, delete_fields=[], heading="### qa", keep_only_heading=True):
    """
    Propagates fields defined under markdown subheadings to all blocks within those subheadings.


    :param file_path: Path to the input QA markdown file.
    :param full_fields: List of all possible fields for reference and ordering.
    :param required_fields: List of fields that must be present in every QA block.
    :param delete_fields: List of fields to delete from every QA block.
    :param heading: The markdown heading to process. Default is "### qa".
    :return: The relative file path of the new file with propagated fields.
    """
    from core.fileops import get_heading, set_heading, sub_suffix_in_str
    from core.structured import get_all_fields_dict, delete_fields_from_text
    
    # Get the text under the specified heading
    heading_text = get_heading(file_path, heading)
    # print("DEBUG first 5 lines of get_heading returned text:")
    # for line in text.splitlines()[:5]:
    #     print(f"'{line}'")
    if not heading_text:
        raise ValueError(f"Heading '{heading}' not found in file '{file_path}'")
    
    # Define QA-specific fields that should not be treated as propagated fields
    qa_fields = ["QUESTION", "ANSWER"]

    # Split text into lines for processing
    heading_lines = heading_text.splitlines()

    # Prepare regex patterns for headings
    heading_pattern = re.compile(r'^(#{3,6})\s+(.*)')  # Matches headings level 3 to 6

    # Initialize active_fields as a regular dict
    active_fields = {}

    # List to store the modified lines
    modified_heading_lines = []

    i = 0
    while i < len(heading_lines):
        line = heading_lines[i].rstrip('\n')
        heading_match = heading_pattern.match(line)

        if heading_match:
            # It's a heading - add it and exactly one blank line
            if modified_heading_lines and not modified_heading_lines[-1] == '':
                modified_heading_lines.append('')
            if len(modified_heading_lines) < 2 or modified_heading_lines[-2] != '':
                modified_heading_lines.append('')
            
            modified_heading_lines.append(line)
            modified_heading_lines.append('')

            # Get heading level and title
            level = len(heading_match.group(1))  # Keep as integer

            # Clear any higher-level heading fields
            active_fields = {k: v for k, v in active_fields.items() if k < level}

            # Initialize the level if not exists
            if level not in active_fields:
                active_fields[level] = {}

            # Move to the next line after the heading
            i += 1

            # Skip any blank lines that follow the heading
            while i < len(heading_lines) and not heading_lines[i].strip():
                i += 1

            # Check for propagated fields under the heading
            while i < len(heading_lines):
                current_line = heading_lines[i].strip()
                # Stop if a blank line, another heading, or a QA block is encountered
                if (not current_line or
                    heading_pattern.match(current_line) or
                    re.match(r'^(QUESTION|ANSWER):\s*', current_line)):
                    break

                # Attempt to match a field
                field_match = re.match(r'^([^:]+):\s*(.*)$', current_line)
                if field_match:
                    field_name, field_value = field_match.groups()
                    field_name = field_name.strip().upper()
                    field_value = field_value.strip()

                    # **Error Check:** Propagated fields should never include QA fields
                    if field_name in qa_fields:
                        raise ValueError(f"Field '{field_name}' cannot be propagated under a heading in file '{file_path}'.")

                    if field_name in full_fields:
                        active_fields.setdefault(level, {})[field_name] = field_value
                    else:
                        # Field is not in full_fields; ignore
                        pass
                    i += 1
                else:
                    # Line does not match a field pattern; stop collecting propagated fields
                    break
            continue

        # Check if the line starts a QA block
        qa_block_start = re.match(r'^QUESTION:\s*', line)
        if qa_block_start:
            # Start processing the QA block
            qa_block_lines = [line]
            i += 1
            while i < len(heading_lines) and heading_lines[i].strip() != '':
                qa_block_lines.append(heading_lines[i].rstrip('\n'))
                i += 1

            # Join lines into a block
            qa_block = '\n'.join(qa_block_lines)
            
            # Parse remaining fields from the block and filter out deleted fields
            qa_fields_in_block = {k: v for k, v in get_all_fields_dict(qa_block).items()
                                if k not in delete_fields}

            # Determine which fields to propagate based on current active headings
            propagated_fields = {}
            for lvl in sorted(active_fields.keys()):
                level_fields = active_fields[lvl].copy()
                propagated_fields.update(level_fields)

            # Merge propagated fields with QA block fields (QA block fields take precedence)
            merged_fields = propagated_fields.copy()
            merged_fields.update(qa_fields_in_block)

            # Ensure required fields are present
            for req_field in required_fields:
                if req_field not in merged_fields or not merged_fields[req_field]:
                    merged_fields[req_field] = ''

            # Reconstruct the QA block
            reconstructed_block_lines = []

            # Create uppercase set for full_fields comparison
            full_fields_upper = set(f.strip().upper() for f in full_fields)

            # Add fields in the specified order from full_fields
            for field in full_fields:
                if field in merged_fields:
                    if field == 'QUESTION':
                        reconstructed_block_lines.append(f"QUESTION: {qa_fields_in_block.get('QUESTION', '')}")
                    elif field == 'ANSWER':
                        reconstructed_block_lines.append(f"ANSWER: {qa_fields_in_block.get('ANSWER', '')}")
                    else:
                        reconstructed_block_lines.append(f"{field}: {merged_fields[field]}")

            # Add any remaining fields not in full_fields
            for field in sorted(merged_fields.keys()):
                field_upper = field.strip().upper()
                if field_upper not in full_fields_upper:
                    reconstructed_block_lines.append(f"{field}: {merged_fields[field]}")

            # Append the reconstructed block to modified_lines
            modified_heading_lines.extend(reconstructed_block_lines)
            modified_heading_lines.append('')
            continue

        # For all other lines, append as is
        if line.strip() or not (modified_heading_lines and modified_heading_lines[-1] == ''):
            modified_heading_lines.append(line)
        i += 1

    # Reconstruct the modified content
    modified_heading_text = '\n'.join(modified_heading_lines)
    # Remove any leading blank lines while preserving other formatting
    modified_heading_text = re.sub(r'^\n+', '', modified_heading_text) + '\n'
    
    # Delete specified fields from the entire content
    modified_heading_text = delete_fields_from_text(modified_heading_text, delete_fields)
    # print("DEBUG first 5 lines of modified_heading_text:")
    # for line in modified_heading_text.splitlines()[:5]:
    #     print(f"'{line}'")
    # print("DEBUG checking for '### notes' heading:", '### notes' in modified_heading_text)

    # Create a copy of the original file
    suffix_new = '_qaprop'

    # Set the modified content under the same heading in the new file
    if keep_only_heading:
        print("Keeping only heading - reading metadata and writing modified content")
        metadata, _ = read_metadata_and_content(file_path)
        new_content = "## content\n\n" + modified_heading_text
        new_file_path = write_metadata_and_content(file_path, metadata, new_content, suffix_new=suffix_new, overwrite='no-sub')
    else:   
        print("Keeping all content - copying file and setting heading")
        new_file_path = sub_suffix_in_str(file_path, suffix_new)
        shutil.copy2(file_path, new_file_path)
        set_heading(new_file_path, modified_heading_text, heading)
    set_last_updated(new_file_path, "Created by propagate fields on qa")

    print(f"Propagated fields saved to {new_file_path}")

    return new_file_path  # Return the relative file path of the new file

def select_blocks_top_stars(blocks_list, num_blocks=5):
    """
    Selects the top num_blocks from the list based on stars count, with timestamp as a tiebreaker.
    Blocks with no stars or equal stars are sorted by earliest timestamp.

    :param blocks_list: list of text blocks to process
    :param num_blocks: int, number of top blocks to return
    :return: list of the top num_blocks blocks sorted by stars (desc) and timestamp (asc)
    """
    def get_block_sort_values(block):
        # Get stars value, defaulting to 0 if missing or invalid
        stars = get_field_value(block, "STARS")
        try:
            stars = int(stars) if stars is not None else 0
        except (ValueError, TypeError):
            stars = 0
            
        # Get timestamp value, defaulting to max value if missing or invalid
        timestamp = get_field_value(block, "TIMESTAMP")
        try:
            if timestamp:
                # Remove any markdown link formatting
                timestamp = re.sub(r'\[([^\]]+)\].*', r'\1', timestamp)
                seconds = convert_timestamp_to_seconds(timestamp)
            else:
                seconds = float('inf')
        except (ValueError, TypeError):
            seconds = float('inf')
            
        # Return tuple for sorting (stars descending, timestamp ascending)
        return (-stars, seconds)
            
    return sorted(blocks_list, key=get_block_sort_values)[:num_blocks]
def create_qa_top_stars_file(qa_file_path, suffix_new="_qa-topstars", num_blocks=5):
    """
    Creates a new file with the top num_blocks from the list of blocks based on the number of stars.
    """
    blocks_list = get_blocks_from_file(qa_file_path)
    top_blocks = select_blocks_top_stars(blocks_list, num_blocks)
    top_text = '\n\n'.join(top_blocks)
    new_qa_file_path = copy_file_and_replace_suffix(qa_file_path, suffix_new)
    set_heading(new_qa_file_path, "\n" + top_text, "### qa")
    return new_qa_file_path
def create_transcript_top_stars_file(qa_top_stars_file_path, suffix_orig="_vrb", suffix_new="_vrb-topstars", debug=False):
    """
    Creates a new transcript file containing only the speaker segments related to the top-starred QA pairs.

    :param qa_top_stars_file_path: string, path to the QA top stars file
    :param suffix_orig: string, suffix of the original transcript file
    :param suffix_new: string, suffix for the new transcript file
    :param debug: boolean, if True prints debug information
    :return: string, path to the newly created transcript file
    """
    # Get the original transcript file path
    transcript_file_path = sub_suffix_in_str(qa_top_stars_file_path, suffix_orig)
    
    # Get QA timestamps from the TIMESTAMP: lines
    qa_blocks = get_blocks_from_file(qa_top_stars_file_path, "### qa")
    qa_timestamps = []
    for block in qa_blocks:
        for line in block.split('\n'):
            if line.startswith('TIMESTAMP:'):
                # Get the timestamp string after "TIMESTAMP: "
                qa_timestamp = line[len('TIMESTAMP:'):].strip()
                if qa_timestamp:
                    qa_timestamps.append(qa_timestamp)
    
    verbose_print(debug, "\nQA timestamps:", qa_timestamps)
    verbose_print(debug, "\nAnalyzing transcript blocks:")
    
    # Get all transcript blocks
    transcript_blocks = get_blocks_from_file(transcript_file_path, "### transcript")
    
    # Filter transcript blocks based on timestamps
    selected_blocks = []
    
    for i in range(len(transcript_blocks)):
        current_block = transcript_blocks[i]
        next_block = transcript_blocks[i + 1] if i + 1 < len(transcript_blocks) else None
        
        # Get first lines of current and next blocks
        current_first_line = current_block.split('\n')[0] if current_block else ""
        next_first_line = next_block.split('\n')[0] if next_block else ""
        
        # Check if either current or next block has matching timestamp
        current_has_match = any(timestamp in current_first_line for timestamp in qa_timestamps)
        next_has_match = any(timestamp in next_first_line for timestamp in qa_timestamps)
        
        verbose_print(debug, f"\nAnalyzing block: {current_first_line}")
        verbose_print(debug, f"  Current block has matching timestamp? {current_has_match}")
        verbose_print(debug, f"  Next block has matching timestamp? {next_has_match}")
        
        if current_has_match or next_has_match:
            verbose_print(debug, "  Keeping this block")
            selected_blocks.append(current_block)
    
    verbose_print(debug, f"\nTotal blocks selected: {len(selected_blocks)}")
    
    # Create new file with selected blocks
    new_transcript_file_path = copy_file_and_replace_suffix(transcript_file_path, suffix_new)
    selected_text = '\n\n'.join(selected_blocks)
    set_heading(new_transcript_file_path, "\n" + selected_text, "### transcript")
    
    return new_transcript_file_path
def mtest_create_top_stars_files_single():
    pass
#if __name__ == "__main__":
    qa_file_path = "data/deutsch/f8_done_qafixed_and_vrb/2011-08-01_On Point with Tom Ashbrook_qafixed.md"
    qa_top_stars_file_path = create_qa_top_stars_file(qa_file_path)
    print(f"QA top stars file: {qa_top_stars_file_path}")
    print(f"Transcript top stars file: {create_transcript_top_stars_file(qa_top_stars_file_path)}")


### BLOCK VALIDATION
def validate_stars(stars_str):
    if not stars_str.strip():  # Check if the string is blank or just whitespace
        return True
    try:
        stars = int(stars_str)
        return True  # Accept any integer, including negative numbers
    except ValueError:
        return False  # Return False if the string can't be converted to an integer
def validate_topics(topics_str):
    if ",  " in topics_str or re.search(r',(?![ ])', topics_str):
        return False
    topics = re.split(r',\s*', topics_str.strip())
    return all(topic.strip() == topic for topic in topics)
def validate_blocks(blocks_list, required_fields, custom_validators=None, show_only_first_invalid=True):
    """
    Validates the structure and content of QA blocks against required fields.

    :param blocks_list: List of QA blocks where each block is a string of text representing a qa entry.
    :param required_fields: List of required field names.
    :param custom_validators: Dictionary of field names and their corresponding validation functions.
    :param show_only_first_invalid: If True, only shows the first invalid block. If False, shows all invalid blocks.
    :return: The number of valid blocks if all are valid, or the negative count of invalid blocks.
    """
    custom_validators = custom_validators or {}
    invalid_blocks_count = 0
    total_blocks = len(blocks_list)
    has_shown_block = False  # Only used when show_only_first_invalid is True

    for block in blocks_list:
        block_errors = []
        
        # Use get_all_fields_dict to parse the block
        try:
            block_dict = get_all_fields_dict(block)
            block_fields = set(block_dict.keys())  # Get just the field names
        except Exception as e:
            block_errors.append(f"Error parsing block: {str(e)}")
            block_fields = set()

        # Check for required fields
        for field in required_fields:
            if field not in block_fields:
                block_errors.append(f"Missing required field: {field}")

        # Get raw field values for validation by splitting on first colon
        raw_field_values = {}
        for line in block.split('\n'):
            if ':' in line:
                field, value = line.split(':', 1)
                field = field.strip()
                if field.isupper():  # Only process uppercase field names
                    raw_field_values[field] = value.strip()

        # Validate field contents using custom validators
        for field, validator in custom_validators.items():
            if field in raw_field_values:
                try:
                    if not validator(raw_field_values[field]):
                        block_errors.append(f"Custom validation failed for field: {field}")
                except Exception as e:
                    block_errors.append(f"Error in custom validator for field {field}: {str(e)}")

        # Update validation statistics and show block if invalid
        if block_errors:
            invalid_blocks_count += 1
            if not show_only_first_invalid or (show_only_first_invalid and not has_shown_block):
                print("\nValidationErrors found in block:")
                for error in block_errors:
                    print(f"- {error}")
                print("\nInvalid block:")
                print(block)
                print()
                has_shown_block = True

    return total_blocks if invalid_blocks_count == 0 else -invalid_blocks_count
def validate_blocks_in_file(file_path, required_fields, custom_validators, verbose=False):
    """
    Function to validate QA blocks in a file and return True if all blocks are valid

    :param file_path: string of the path to the file to be validated
    :param required_fields: List of required field names.
    :param custom_validators: Dictionary of field names and their corresponding validation functions.
    :param verbose: boolean to control verbose output
    :return: boolean indicating whether all blocks in the file are valid
    """
    from core.structured import get_blocks_from_file
    blocks = get_blocks_from_file(file_path)
    valid_blocks = validate_blocks(blocks, required_fields, custom_validators)
    if valid_blocks < 0:
        print(f"FAIL - INVALID blocks for file: {file_path}\n\n\n")
        return False
    if verbose:
        print(f"VALID blocks for file: {file_path}")
    return True
def validate_blocks_in_folders(folder_paths, required_fields, custom_validators, suffixpat_include="_qafixed"):
    """
    Validates QA blocks in all files within specified folders, printing the number of valid files in each folder
    and statistics about required and optional fields.

    :param folder_paths: list of strings of folder paths to search for files.
    :param required_fields: List of required field names.
    :param custom_validators: Dictionary of field names and their corresponding validation functions.
    :param suffixpat_include: string of the suffix to include in file search. Default is "_qafixed".
    :return: string of the path of the first file with invalid QA blocks if any; None if all files are valid.
    """
    total_valid_files = 0
    total_files = 0
    optional_fields_stats = defaultdict(lambda: {'files': set(), 'blocks': 0})

    for folder_path in folder_paths:
        file_paths = get_files_in_folder(folder_path, suffixpat_include=suffixpat_include)
        valid_files_count = 0
        
        for file_path in file_paths:
            total_files += 1
            blocks = get_blocks_from_file(file_path)
            
            # Modify the validation to handle numbered questions
            modified_required_fields = required_fields.copy()
            if "QUESTION" in modified_required_fields:
                # We'll handle QUESTION validation separately
                modified_required_fields.remove("QUESTION")
            
            if validate_blocks_in_file(file_path, modified_required_fields, custom_validators):
                # Additional check for QUESTION field with numbers
                if "QUESTION" in required_fields:
                    has_invalid_block = False
                    for block in blocks:
                        # Check if the block has any field starting with "QUESTION" (possibly followed by a number)
                        has_question_field = False
                        for line in block.split('\n'):
                            if ':' in line:
                                field_part = line.split(':', 1)[0].strip()
                                if field_part == "QUESTION" or (field_part.startswith("QUESTION ") and field_part[9:].strip().isdigit()):
                                    has_question_field = True
                                    break
                        
                        if not has_question_field:
                            print(f"ValidationErrors found in block:")
                            print(f"- Missing required field: QUESTION")
                            print("\nInvalid block:")
                            print(block)
                            print()
                            has_invalid_block = True
                            break
                    
                    if has_invalid_block:
                        print(f"Number of validated files: {valid_files_count} in {folder_path}: ")
                        print(f"INVALID file: {file_path}")
                        return file_path
                
                valid_files_count += 1
                total_valid_files += 1
                
                # Count optional fields using get_all_fields_dict
                for block in blocks:
                    try:
                        # Parse block lines to handle numbered questions
                        block_fields_dict = {}
                        for line in block.split('\n'):
                            if ':' in line:
                                field_part, value = line.split(':', 1)
                                # Strip whitespace from field part and value
                                field_part = field_part.strip()
                                value = value.strip()
                                
                                # Extract base field name without number for QUESTION fields
                                if field_part.startswith("QUESTION ") and field_part[9:].strip().isdigit():
                                    field_part = "QUESTION"
                                
                                block_fields_dict[field_part] = value
                                
                        for field in block_fields_dict.keys():
                            if field not in required_fields:
                                optional_fields_stats[field]['files'].add(file_path)
                                optional_fields_stats[field]['blocks'] += 1
                    except Exception as e:
                        warnings.warn(f"Error parsing block in file {file_path}: {str(e)}")
            else:
                print(f"Number of validated files: {valid_files_count} in {folder_path}: ")
                print(f"INVALID file: {file_path}")
                return file_path

        print(f"Number of valid files in {folder_path}: {valid_files_count}")

    print(colored(f"\nTotal valid files across all folders: {total_valid_files}/{total_files}", "green"))
    print(f"\nRequired fields: {', '.join(required_fields)}")
    print("\nOptional fields statistics:")
    for field, stats in optional_fields_stats.items():
        print(f"  {field}: appears in {len(stats['files'])} files and {stats['blocks']} blocks")

    return None
def validate_qa_blocks_townhall_OLD(blocks_list):
    """
    Validates the structure and content of QA blocks against required and optional fields.

    :param blocks_list: list of qa blocks where each block is a string of text representing a qa entry.
    :return: the number of valid blocks if all are valid, or the negative count of invalid blocks.
    """
    required_fields = ["QUESTION", "ANSWER", "QUESTION SPEAKER", "ANSWER SPEAKER", "TOPICS", "STARS"]
    optional_fields = ["NOTES", "ORIGINAL QUESTION", "ALTERNATE QUESTION", "ADDITIONAL QUESTION"]

    all_fields = set(required_fields + optional_fields)
    invalid_blocks_count = 0

    for block in blocks_list:
        block_lines = block.strip().split("\n")
        block_fields = {}
        block_is_valid = True  # Track validity of individual block
        for line in block_lines:
            if line:
                try:
                    key, value = line.split(":", 1)
                    block_fields[key.strip()] = value.strip()  # Ensure that the key is stripped of whitespace
                except ValueError as e:
                    warnings.warn(f"Error splitting line '{line}' in block:\n{block}\nError: {e}")
                    block_is_valid = False
                    break
            else:
                warnings.warn(f"Block contains a blank line:\n{block}")
                block_is_valid = False
                break

        # Check for invalid fields
        for field in block_fields:
            if field not in all_fields:
                warnings.warn(f"Invalid field '{field}' in block:\n{block}\n\n")
                block_is_valid = False

        # Check required fields
        for field in required_fields:
            if field not in block_fields:
                warnings.warn(f"Missing required field '{field}' in block:\n{block}")
                block_is_valid = False
            else:
                if field == "STARS":
                    stars_str = block_fields[field]
                    stars = int(stars_str) if stars_str.isdigit() else 0
                    if stars < 0:
                        warnings.warn(f"Invalid format for STARS field.")
                        block_is_valid = False
                elif field == "TOPICS":
                    topics_line = block_fields[field]
                    # Check for incorrect delimiters and print a warning if necessary
                    if ",  " in topics_line:
                        warnings.warn(f"Double space after comma in topics line '{topics_line}'")
                        block_is_valid = False
                    elif re.search(r',(?![ ])', topics_line):
                        warnings.warn(f"Missing space after comma in topics line '{topics_line}'")
                        block_is_valid = False
                    # Split the topics by comma, accounting for optional spaces and removing trailing whitespace
                    topics = re.split(r',\s*', topics_line.strip())
                    # Remove any leading or trailing whitespace from each topic and filter out empty strings
                    cleaned_topics = [topic.strip() for topic in topics if topic.strip()]
                    # Check for and warn about trailing whitespace in the original topic strings
                    for topic, cleaned_topic in zip(topics, cleaned_topics):
                        if topic != cleaned_topic:
                            warnings.warn(f"Incorrect whitespace in topic '{topic}'")
                            block_is_valid = False

        # Check optional fields
        for field in optional_fields:
            if field in block_fields and not block_fields[field]:
                warnings.warn(f"Optional field '{field}' is present but blank in block:\n{block}")
                block_is_valid = False

        if not block_is_valid:
            invalid_blocks_count += 1
            
    if invalid_blocks_count == 0:
        return len(blocks_list)
    else:
        return (0 - invalid_blocks_count)
def validate_iso_dates_in_filename(folder_paths, suffixpat_include):
    """
    Validates that filenames in specified folders start with valid ISO dates (YYYY-MM-DD).

    :param folder_paths: list of strings of folder paths to search for files.
    :param suffixpat_include: string of the suffix to include in file search. Default is "_qafixed".
    :return: boolean indicating whether all files have valid ISO dates (True) or not (False).
    """
    total_valid_files = 0
    total_files = 0

    for folder_path in folder_paths:
        file_paths = get_files_in_folder(folder_path, suffixpat_include=suffixpat_include)
        valid_files_count = 0
        
        for file_path in file_paths:
            total_files += 1
            file_name = os.path.basename(file_path)
            date_str = file_name.split('_')[0]
            
            try:
                # Try to parse the date string - this will validate format and ranges
                datetime.strptime(date_str, '%Y-%m-%d')
                valid_files_count += 1
                total_valid_files += 1
            except ValueError:
                print(f"Number of validated files: {valid_files_count} in {folder_path}: ")
                print(colored(f"INVALID date in filename: {file_path}", "red"))
                return False

        print(f"Number of valid files in {folder_path}: {valid_files_count}")

    print(colored(f"All files have valid ISO dates in filenames: {total_valid_files}/{total_files}", "green"))
    return True

### TOPICS
# TODO try on townhall qa files - may need to update for alternate METADATA and CONTENT format
def extract_topic_counts_triples(qa_file_path, verbose=False):
    """
    Extracts topics from QA blocks in a file and counts their occurrences. 

    :param qa_file_path: string of the path to the QA file.
    :param verbose: boolean, if True, prints additional information during execution. Default is False.
    :return: string of CSV lines with each line in the format "topic, file_stem, count".
    """
    # Get the blocks from the file
    blocks = get_blocks_from_file(qa_file_path)
    
    # Initialize a dictionary to keep track of topics and their occurrences
    topic_dict = {}
    
    # Iterate through each block to extract topics and count their occurrences
    for block in blocks:
        # Use the helper function to get a list of topics from the block
        topics = get_field_value(block, "TOPICS")
        if topics:
            # Iterate through the topics and update their count in the dictionary
            for topic in topics:
                if topic:  # Ensure that the topic is not an empty string
                    topic_dict[topic] = topic_dict.get(topic, 0) + 1
                else:
                    warnings.warn(f"Warning: TOPIC is blank and should have been previously validated before calling this function for file {qa_file_path}\n{block}\n\n")
    
    # Get the file stem (filename without extension)
    file_stem = os.path.splitext(os.path.basename(qa_file_path))[0]
    
    # Build the result text with the required format
    topic_counts_csv_lines = "\n".join([f"{topic}, {file_stem}, {count}" for topic, count in topic_dict.items()])
    
    return topic_counts_csv_lines
def create_topics_matrix(folder_paths, target_file_path="topics_matrix.csv", suffixpat_include="_qafixed"):
    """
    Collects topics from files in specified folders and creates a CSV matrix file at the target file path.

    :param folder_paths: list of strings of folder paths to search for files.
    :param target_file_path: string of the path where the resulting CSV file will be created. If no folder is provided in the path, the parent folder of the first folder in the folder_paths list will be used.
    :param suffix_include: string of the suffix to include in file search. Default is "_qafixed".
    :return: string of the path to the created csv file.
    """
    from core.fileops import apply_to_folder, create_csv_matrix_from_triples
    
    all_topics_results = []  # Initialize an empty list to collect all topics from all folders

    # Iterate over each folder path and process files within
    for folder_path in folder_paths:
        # Use apply_to_folder to process files and get topics
        topics_results = apply_to_folder(extract_topic_counts_triples, folder_path, suffixpat_include=suffixpat_include)
        # Append the topics from the current folder to the all_topics_results list
        all_topics_results.extend(topics_results.values())

    triples_text = "\n".join(all_topics_results)  # no need to srt because that's done by create_csv_matrix_from_triples

    # Check if the target file path has a folder component
    if not os.path.dirname(target_file_path):
        # If not, use the parent folder of the first folder in folder_paths
        parent_folder = os.path.dirname(folder_paths[0])
        target_file_path = os.path.join(parent_folder, os.path.basename(target_file_path))

    # Call the create_csv_from_triples function to create the CSV file
    return create_csv_matrix_from_triples(triples_text, target_file_path)  # function is in fileops
def mtest_create_topics_matrix():
    pass
#if __name__ == "__main__":
    cur_folder_paths = ["data/f_c7_done_early", "data/f_c8_qafixed_talks", "data/f_c6_done_after_dq", "data/f_c5_done_after_dq" ]   
    create_topics_matrix(cur_folder_paths)
def change_topic_in_file(file_path, find_topic, replace_topic):
    """
    Replaces a specified topic with another in a single file.

    :param file_path: string of the file path to process.
    :param find_topic: string of the topic to find.
    :param replace_topic: string of the topic to use as a replacement.
    :return: tuple of (int, int) representing (replacements_in_file, total_replacements)
    """
    if find_topic == replace_topic:
        print(f"Aborting: find_topic '{find_topic}' and replace_topic '{replace_topic}' are the same.")
        return 0

    from core.fileops import read_metadata_and_content, write_metadata_and_content

    metadata, content = read_metadata_and_content(file_path)
    
    blocks = get_blocks_from_file(file_path)
    content_lines = content.split('\n')
    replacements_in_file = 0
    for i, line in enumerate(content_lines):
        if line.startswith("TOPICS:"):
            topics = line[len("TOPICS:"):].strip().split(', ')
            if find_topic in topics:
                topics = [replace_topic if topic == find_topic else topic for topic in topics]
                new_line = 'TOPICS: ' + ', '.join(topics)
                content_lines[i] = new_line
                replacements_in_file += topics.count(replace_topic)
    
    if replacements_in_file > 0:
        new_content = '\n'.join(content_lines)
        write_metadata_and_content(file_path, metadata, new_content, overwrite='yes')
    
    return replacements_in_file
def change_topic_in_folders(folder_paths, find_topic, replace_topic, suffixpat_include="_qafixed"):
    """
    Replaces a specified topic with another across files in given folders.

    :param folder_paths: list of strings of folder paths to search for files.
    :param find_topic: string of the topic to find.
    :param replace_topic: string of the topic to use as a replacement.
    :param suffix_include: string of the suffix to include in file search.
    :return: None.
    """
    from core.fileops import apply_to_folder
    
    total_replacements = 0
    files_with_replacements = []

    def process_file(file_path):
        nonlocal total_replacements, files_with_replacements
        replacements_in_file = change_topic_in_file(file_path, find_topic, replace_topic)
        if replacements_in_file > 0:
            total_replacements += replacements_in_file
            files_with_replacements.append((file_path, replacements_in_file))

    for folder_path in folder_paths:
        apply_to_folder(process_file, folder_path, suffixpat_include=suffixpat_include)

    print(f"Total replacements done: {total_replacements}")

    for file_path, count in files_with_replacements:
        file_name = os.path.basename(file_path)
        print(f"{count} {file_name}")
def review_singlet_topic_SONNET(folder_paths, matrix_csv_file_path, starting_letter="a"):
    # Read the CSV file
    with open(matrix_csv_file_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        topics = {row['row title']: sum(int(count) for count in row.values() if count.isdigit()) for row in reader}

    # Filter singlet topics
    singlet_topics = {topic: None for topic, count in topics.items() if count == 1 and topic.lower().startswith(starting_letter)}

    # Read the CSV file again to find files containing singlet topics
    with open(matrix_csv_file_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for topic in singlet_topics.keys():
            # Find the file that contains the topic
            csvfile.seek(0)  # Reset file pointer before each search
            file_with_topic = next((col for col in reader.fieldnames[1:] if any(int(row[col]) > 0 for row in reader if row['row title'] == topic)), None)
            csvfile.seek(0)  # Reset file pointer after each search
            
            if file_with_topic:
                # Search for the file within the given folder paths
                file_path = None
                for folder in folder_paths:
                    potential_path = os.path.join(folder, file_with_topic)
                    if os.path.exists(potential_path):
                        file_path = potential_path
                        break
                
                if file_path is None:
                    print(f"Could not find file '{file_with_topic}' in any of the provided folders.")
                    continue
                # Open the file in VS Code and search for the topic
                subprocess.run(['code', '--goto', f'{file_path}:1', '--search', topic])
                
                # Prompt user for action
                action = input(f"Topic '{topic}' found in {file_with_topic}. Enter 'DEL' to delete, press Enter to skip, or enter a new topic name to change: ")
                
                if action.upper() == 'DEL':
                    # Delete the topic
                    change_topic_in_file(file_path, topic, '')
                    print(f"Topic '{topic}' deleted from {file_with_topic}")
                elif action and action.upper() != 'd':  # use single lowercase 'd' for delete
                    # Change the topic
                    change_topic_in_file(file_path, topic, action)
                    print(f"Topic '{topic}' changed to '{action}' in {file_with_topic}")
                else:
                    print(f"Skipped topic '{topic}' in {file_with_topic}")
            else:
                print(f"Could not find file for topic '{topic}'")

    print("Review of singlet topics completed.")
def review_singlet_topic(folder_paths, matrix_csv_file_path, starting_letter="a"):
    # Step 1: Read the CSV file and build the data structures
    topic_counts = {}  # Mapping from topic to total count
    topic_file_stems = {}  # Mapping from topic to list of file stems

    print(f"Reading topics from CSV file: {matrix_csv_file_path}")
    with open(matrix_csv_file_path, newline='', encoding='utf-8') as csvfile:
        csvreader = csv.reader(csvfile)
        headers = next(csvreader)  # Get the headers (first row)
        if not headers:
            print("CSV file is empty or missing headers.")
            return

        # The first column is assumed to be 'row title' or similar
        file_stems = headers[1:]  # Exclude the first column header
        print(f"File stems extracted: {file_stems}")

        for row in csvreader:
            if len(row) < 2:
                continue  # Skip invalid rows
            topic = row[0].strip()
            counts = [int(count.strip()) for count in row[1:]]

            total_count = sum(counts)
            topic_counts[topic] = total_count

            # Find the indices where the topic occurs
            file_indices = [i for i, count in enumerate(counts) if count > 0]
            if topic not in topic_file_stems:
                topic_file_stems[topic] = []
            for idx in file_indices:
                file_stem = file_stems[idx]
                topic_file_stems[topic].append(file_stem)

    print(f"Total topics read: {len(topic_counts)}")

    # Step 2: Build mapping from file stems to full file paths
    file_stem_to_path = {}  # Mapping from file stem to full file path

    print("Building file stem to path mapping...")
    for folder_path in folder_paths:
        for root, dirs, files in os.walk(folder_path):
            for filename in files:
                stem, ext = os.path.splitext(filename)
                full_path = os.path.join(root, filename)
                if stem not in file_stem_to_path:
                    file_stem_to_path[stem] = full_path

    # Step 3: Process topics with total count == 1 and starting with starting_letter (case-insensitive)
    matching_topics = [topic for topic in topic_counts if topic_counts[topic] == 1 and topic.lower().startswith(starting_letter.lower())]
    print(f"Total topics with count == 1 and starting with '{starting_letter}' (case-insensitive): {len(matching_topics)}")

    if not matching_topics:
        print("No topics to process.")
        return

    for topic in sorted(matching_topics):
        total_count = topic_counts[topic]
        file_stems = topic_file_stems[topic]
        if len(file_stems) != 1:
            print(f"Warning: Topic '{topic}' occurs in multiple files but total count is 1.")
            continue
        file_stem = file_stems[0]
        file_path = file_stem_to_path.get(file_stem)
        if not file_path:
            print(f"File for file stem '{file_stem}' not found.")
            continue

        print(f"\nProcessing topic '{topic}' in file '{file_path}'")

        # Open the file in VS Code and perform search
        try:
            subprocess.run(['code', file_path])

            # Copy the topic to the clipboard
            pyperclip.copy(topic)

            # Wait a moment to ensure VS Code has focus
            time.sleep(3)  # Adjust the sleep time if necessary

            # Simulate Ctrl+F to open the find dialog
            pyautogui.hotkey('command', 'f')

            # Paste the topic into the find dialog
            pyautogui.hotkey('command', 'v')

        except Exception as e:
            print(f"Error opening file in VS Code: {e}")
            continue

        print(f"Opened file '{file_path}' in VS Code. Please search for topic '{topic}' using the search tool.")

        # Prompt the user for action
        user_input = input("Type 'DEL' to delete the topic, type new topic to replace, or press Enter to keep: ").strip()

        if user_input.upper() == 'DEL':
            # Delete the topic
            print(f"Deleting topic '{topic}' in file '{file_path}'")
            change_topic_in_file(file_path, topic, '')
        elif user_input == '':
            # Do nothing
            print(f"Keeping topic '{topic}'")
        else:
            # Replace topic
            new_topic = user_input
            print(f"Replacing topic '{topic}' with '{new_topic}' in file '{file_path}'")
            change_topic_in_file(file_path, topic, new_topic)


### QA
def compare_fields(file_path, field1, field2, print_same_exceptions=False, print_different=True):
    """
    Compare two fields in a file and print the differences.

    :param file_path: string, the file path to process.
    :param field1: string, the first field to compare.
    :param field2: string, the second field to compare.
    :param print_same_exceptions: bool, whether to print blocks that are same with exceptions.
    :param print_different: bool, whether to print blocks that are different.
    :return: None.
    """
    # Define exceptions that should be considered "same"
    exceptions = [
        ('same_with_quotes', lambda x, y: x.replace('"', "'") == y.replace('"', "'"))
    ]
    
    # Get all blocks from the file
    blocks = get_blocks_from_file(file_path)
    total_blocks = len(blocks)
    
    # Count blocks by category
    identical_count = 0
    same_with_exceptions = []
    different_blocks = []
    
    for i, block in enumerate(blocks, 1):
        fields_dict = get_all_fields_dict(block)
        value1 = fields_dict.get(field1)
        value2 = fields_dict.get(field2)
        
        if value1 == value2:
            identical_count += 1
        else:
            # Check if differences are due to known exceptions
            is_exception = False
            for exc_name, exc_func in exceptions:
                if exc_func(value1, value2):
                    same_with_exceptions.append((exc_name, i, value1, value2))
                    is_exception = True
                    break
            
            if not is_exception:
                different_blocks.append((i, value1, value2))
    
    # Calculate counts
    exception_count = len(same_with_exceptions)
    different_count = len(different_blocks)
    
    # Print summary with aligned numbers and percentages
    print(f"\nComparing {field1} with {field2}:")
    print(f"{'Identical:':<22} {identical_count:>5} ({identical_count/total_blocks*100:>6.1f}%)")
    print(f"{'Same with exceptions:':<22} {exception_count:>5} ({exception_count/total_blocks*100:>6.1f}%)")
    print(f"{'Different:':<22} {different_count:>5} ({different_count/total_blocks*100:>6.1f}%)")
    print(f"{'Total blocks:':<22} {total_blocks:>5}")

    # Print blocks that are same with exceptions (if enabled)
    if same_with_exceptions and print_same_exceptions:
        print("\nBlocks that are same with exceptions:")
        for exc_type, block_num, val1, val2 in same_with_exceptions:
            print(f"\nQA Block {block_num} ({exc_type})")
            print(f"{field1}: {val1}")
            print(f"{field2}: {val2}")
    
    # Print differing blocks (if enabled)
    if different_blocks and print_different:
        print("\nDiffering blocks:")
        for block_num, val1, val2 in different_blocks:
            print(f"\nQA Block {block_num}")
            print(f"{field1}: {val1}")
            print(f"{field2}: {val2}")
def mrun_compare_fields():
    pass
#if __name__ == "__main__":
    #cur_file_path = "data/misc_books/Sovereign Child/Sovereign Child_qa-qonly.md"
    cur_file_path = "data/misc_books/Sovereign Child/2025-01-17_Tim Ferriss Show - Naval and Aaron Stupple on Sovereign Child_qa-qonly.md"
    compare_fields(cur_file_path, "CLARIFIED QUESTION", "VERBATIM QUESTION")
def write_blocks_to_heading(file_path, blocks, heading):
    """
    Write blocks of text under a specified heading in a file, converting any field containing a list of strings 
    to a comma-separated format.

    :param file_path: string, path to the file to write to
    :param blocks: list of strings, each string being a block of text
    :param heading: string, the heading to write under (including # markers)
    :return: None
    """
    # Process each block to convert list formats if present
    processed_blocks = []
    for block in blocks:
        lines = block.split('\n')
        processed_lines = []
        for line in lines:
            # Check if line contains a field with a list (starts with [ after the colon)
            if ': [' in line:
                field_name, field_value = line.split(':', 1)
                field_value = field_value.strip()
                if field_value.startswith('[') and field_value.endswith(']'):
                    # Extract values from list format and join with commas
                    values_str = field_value[1:-1].replace("'", "").replace('"', "")
                    processed_lines.append(f'{field_name}: {values_str.strip()}')
                else:
                    processed_lines.append(line)
            else:
                processed_lines.append(line)
        processed_blocks.append('\n'.join(processed_lines))
    
    # Join blocks with double newlines to maintain block separation
    modified_text = '\n\n'.join(processed_blocks)
    
    # Ensure the text ends with a newline
    if not modified_text.endswith('\n'):
        modified_text += '\n'
        
    try:
        set_heading(file_path, modified_text, heading)
    except Exception as e:
        raise ValueError(f"Error writing blocks to heading: {str(e)}")
def remap_fields(file_path, rename_fields, delete_fields=[]):
    """
    Remap fields in a file based on tuples of old field names to new field names.

    :param file_path: string, path to the file to process
    :param rename_fields: list of tuples (old_field, new_field) for renaming
    :param delete_fields: list of fields to delete
    :return: None
    """
    # Create case-mapping dictionaries to preserve original case
    rename_case_map = {}
    for old, new in rename_fields:
        old_stripped = old.rstrip(':')
        new_stripped = new.rstrip(':')
        rename_case_map[old_stripped.upper()] = new_stripped
    
    delete_fields = [field.rstrip(':').upper() for field in delete_fields]
    
    # Get blocks from file
    try:
        blocks = get_blocks_from_file(file_path)
    except Exception as e:
        raise ValueError(f"Error reading blocks from file: {str(e)}")
    
    if not blocks:
        raise ValueError(f"No blocks found in file: {file_path}")
        
    # Get the heading above the first block
    first_block = blocks[0]
    heading = get_heading_above(file_path, first_block)
    if not heading:
        raise ValueError(f"Could not find heading above blocks in file: {file_path}")
    
    # Process each block
    modified_blocks = []
    for block in blocks:
        fields_dict = get_all_fields_dict(block)
        
        # Verify all old field names exist in at least one block
        missing_fields = [old for old, _ in rename_fields if old.rstrip(':').upper() not in fields_dict]
        if missing_fields:
            raise ValueError(f"Fields not found in block: {', '.join(missing_fields)}")
        
        # Create new block with renamed and deleted fields
        new_block_lines = []
        for field, value in fields_dict.items():
            # Skip deleted fields
            if field in delete_fields:
                continue
                
            # Rename field if it's in rename_fields, preserving case from new field name
            new_field = rename_case_map.get(field, field)
            new_block_lines.append(f"{new_field}: {value}")
            
        modified_blocks.append('\n'.join(new_block_lines))
    
    # Write the modified blocks back to the file
    write_blocks_to_heading(file_path, modified_blocks, heading)
def mrun_remap_fields():
    pass
#if __name__ == "__main__":
    cur_file_path = "data/misc_books/Sovereign Child/The Sovereign Child_qa-qonly.md"
    rename_fields = [("CLARIFIED QUESTION", "QUESTION"), ("VERBATIM ANSWER", "ANSWER")]
    delete_fields = ["CLARIFIED ANSWER", "VERBATIM QUESTION", "SPEAKER QUESTION", "SPEAKER ANSWER"]
    remap_fields(cur_file_path, rename_fields, delete_fields)
def renumber_multi_qa(qa_file_path, verbose=False):
    """
    Renumber the questions in a multi-question QA file sequentially.
    
    Finds all lines starting with "QUESTION" followed by a number and renumbers them.
    Numbering restarts at 1 for each block (blocks are separated by blank lines).
    This is useful when questions have been deleted or are out of order.

    :param qa_file_path: string, path to the QA file to process
    :return: string, path to the updated file
    """
    qa_text = get_heading(qa_file_path, "### qa")
    if not qa_text:
        warnings.warn(f"No QA section found in file: {qa_file_path}")
        return qa_file_path
    
    # Split the text into lines for processing
    lines = qa_text.split('\n')
    
    # Pattern to match lines starting with "QUESTION" followed by a number
    question_pattern = re.compile(r'^QUESTION\s+(\d+):', re.IGNORECASE)
    
    # Counter for question numbering
    question_counter = 1
    # Counter for total questions renumbered
    total_renumbered = 0
    
    # Process each line
    i = 0
    while i < len(lines):
        # Check if current line is blank - reset counter if it is
        if not lines[i].strip():
            question_counter = 1
            i += 1
            continue
            
        match = question_pattern.match(lines[i])
        if match:
            # Replace the old number with the new counter value
            lines[i] = f"QUESTION {question_counter}:" + lines[i][match.end():]
            question_counter += 1
            total_renumbered += 1
        
        i += 1
    
    # Join the lines back together
    modified_qa_text = '\n'.join(lines)
    
    # Update the file with the modified content
    set_heading(qa_file_path, modified_qa_text, "### qa")
    
    verbose_print(verbose, f"Renumbered {total_renumbered} questions in {qa_file_path}")
    return qa_file_path
def mrun_renumber_multi_qa():
    pass
#if __name__ == "__main__":
    cur_file_path = "data/deutsch/f8_qafixed_talks/2007-01-27_Why Are Flowers Beautiful_qa-multi.md"
    renumber_multi_qa(cur_file_path, verbose=True)
def get_num_questions_multi_qa(qa_file_path):
    """
    Counts the number of questions in a multi-question QA file.

    :param qa_file_path: string, path to the QA file to process
    :return: int, number of questions in the file
    """
    qa_text = get_heading(qa_file_path, "### qa")
    if not qa_text:
        warnings.warn(f"No QA section found in file: {qa_file_path}")
        return 0
    
    # Split the text into lines for processing  
    lines = qa_text.split('\n')
    
    # Count lines starting with "QUESTION" followed by a number
    question_count = 0
    for line in lines:
        if line.strip().startswith("QUESTION"):  # TODO: make case insensitive
            question_count += 1
    
    return question_count
def mrun_get_num_questions_multi_qa():
    pass
if __name__ == "__main__":
    cur_file_path = "data/deutsch/f8_qafixed_talks/2007-01-27_Why Are Flowers Beautiful_qa-multi.md"
    print(get_num_questions_multi_qa(cur_file_path))


# ===== END OF FILE core/structured.py =====
