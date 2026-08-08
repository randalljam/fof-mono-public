import os
import glob
import csv
import re
import warnings
import inspect
from datetime import datetime, timedelta
import pytz
import time
import shutil
import json
import inspect
from termcolor import colored
# Library of functions and execution code to do support tasks on files

# Naming Conventions - see Coding Log - 2024 gdoc for WIP version
# https://docs.google.com/document/d/1y2zuy5L15b_9KCleT1Fcw31q6yyWz-F7czJLVC0h678/edit?usp=sharing

### INITIAL
def custom_formatwarning(msg, category, filename, lineno, line=None):
    """
    DO NOT CALL - only used to define the custom format
    """
    return f"{category.__name__}: {msg}\n"
# Set the warnings format to use the custom format
warnings.formatwarning = custom_formatwarning
# USAGE: warnings.warn(f"Insert warning message here") 
def verbose_print(verbose, *messages):
    """
    Helper function to pass on bool verbose and make verbose printing cleaner
    
    :param verbose: boolean for whether to print the messages.
    :param messages: tuple of variable-length argument list.
    :return: None
    """
    if not isinstance(verbose, bool):
        raise TypeError("The first parameter 'verbose' must be of type bool.")
    if not messages:
        raise ValueError("At least one message must be provided.")
    if verbose:
        print(*messages)
def check_file_exists(file_path, operation_name):
    """
    Checks file existence and raises a ValueError if not found, which stops execution.

    :param file_path: string of file path which can be absolute or relative.
    :param operation_name: string of the message that the ValueError will print, typically the function name - optional message.
    :return: bool, True if file exists, False otherwise.
    """
    if not os.path.isfile(file_path):
        raise ValueError(f"VALUE ERROR in {operation_name}: input file does not exist for {file_path}")
    return True
def warn_file_overwrite(file_path):
    """
    Checks if a file already exists and issues a warning if it does.

    :param file_path: string representing the path of the file to be checked.
    :return: bool, True if file exists, False otherwise.
    """
    # Get the name of the calling function
    func_name = inspect.currentframe().f_back.f_code.co_name
    if os.path.isfile(file_path):
        warnings.warn(f"The function: {func_name} is overwriting a file that already exists, file: '{file_path}'")
        return True
    return False

### SUFFIX
def get_suffix(file_str, delimiter='_'):
    """
    Extracts the suffix from a given file string based on a specified delimiter.

    :param file_str: string of the file name from which to extract the suffix.
    :param delimiter: string representing the delimiter used to separate the suffix from the rest of the file string. Default is "_".
    :return: string of the extracted suffix or None if no valid suffix is found.
    """
    # Count the occurrences of the file extension delimiter (.) only in the end portion of the string before a '/'
    file_base = os.path.basename(file_str)
    period_count = file_base.count('.')
    # Throw a ValueError if there's more than one period
    if period_count > 1:
        raise ValueError("in get_suffix: More than one period found in the input file string.")

    # Find the last occurrence of the delimiter
    delimiter_index = file_base.rfind(delimiter)
    # Find the last occurrence of the file extension delimiter (.)
    extension_index = file_base.rfind('.')

    # Check if the delimiter is found and before the extension, or if there is no extension
    if delimiter_index != -1 and (extension_index == -1 or delimiter_index < extension_index):
        # Check if the part of the file string preceding the delimiter is a date in the format 'YYYY-MM-DD'
        preceding_str = file_base[:delimiter_index]
        #print(f"DEBUG preceeding_str: {preceding_str}")
        if re.match(r'\d{4}-\d{2}-\d{2}$', preceding_str):
            return None  # Return None if the preceding part is a date

        # Extract and return the suffix including the delimiter
        suffix_end_index = extension_index if extension_index != -1 else len(file_base)
        suffix = file_base[delimiter_index:suffix_end_index]
        # Throw a ValueError if the extracted suffix contains invalid characters
        if not all(char.isalnum() or char == '-' for char in suffix.strip(delimiter)):
            # Return None if the extracted suffix contains a space
            if ' ' in suffix:
                return None
            else:
                raise ValueError("in get_suffix: The extracted suffix contains invalid characters.")

        return suffix
    else:
        return None
def add_suffix_in_str(file_str, suffix_add):
    """
    Adds a suffix to a given file string.

    :param file_str: string of the file name to which the suffix will be added.
    :param suffix_add: string of the suffix to be added to the file string.
    :return: string of the file name with the added suffix.
    """
    # Find the last occurrence of the file extension delimiter (.)
    extension_index = file_str.rfind('.')
    
    # If there is no extension, append the suffix to the end of the string
    if extension_index == -1:
        return file_str + suffix_add
    
    # Insert the suffix and delimiter before the extension
    return file_str[:extension_index] + suffix_add + file_str[extension_index:]
def sub_suffix_in_str(file_str, suffix_sub, delimiter='_'):
    """
    Replaces the existing suffix in a file string with a new suffix.

    :param file_str: string of the file name from which to replace the suffix.
    :param suffix_sub: string of the new suffix to replace the existing one.
    :param delimiter: string representing the delimiter used to separate the suffix from the rest of the file string. Default is "_".
    :return: string of the file name with the replaced suffix or the original file string if no valid suffix is found.
    """
    # Use the get_suffix function to determine if there is a valid suffix
    existing_suffix = get_suffix(file_str, delimiter)
    
    # Find the last occurrence of the file extension delimiter (.)
    extension_index = file_str.rfind('.')
    
    # If there is an existing valid suffix, replace it with the new suffix
    if existing_suffix is not None:
        suffix_start_index = file_str.rfind(existing_suffix)
        return file_str[:suffix_start_index] + suffix_sub + file_str[extension_index:]
    else:
        # If no existing suffix, add the new suffix before the extension
        if extension_index != -1:
            return file_str[:extension_index] + suffix_sub + file_str[extension_index:]
        else:
            # If no extension, just append the new suffix
            return file_str + suffix_sub
def remove_all_suffixes_in_str(file_str, delimiter='_'): # DS, cat 1, unitests 7 - no mock
    """
    Removes all suffixes from a given file string based on a specified delimiter while retaining the original file extension.

    :param file_str: string of the file name from which to remove all suffixes.
    :param delimiter: string representing the delimiter used to separate the suffixes from the rest of the file string. Default is "_".
    :return: string of the file name with all suffixes removed but with the original extension preserved.
    """
    # Find the last occurrence of the file extension delimiter (.)
    extension_index = file_str.rfind('.')
    # Extract the extension if it exists
    extension = file_str[extension_index:] if extension_index != -1 else ''
    
    # Remove the extension from the file string to avoid removing it as a suffix
    file_str_without_extension = file_str[:extension_index] if extension_index != -1 else file_str
    
    # Continuously strip suffixes until no more can be stripped
    while True:
        # Use get_suffix to get the current suffix
        current_suffix = get_suffix(file_str_without_extension, delimiter)
        # If there is a suffix, remove it
        if current_suffix:
            # Find the index of the suffix to be removed
            suffix_index = file_str_without_extension.rfind(current_suffix)
            # Update file_str_without_extension by removing the current suffix
            file_str_without_extension = file_str_without_extension[:suffix_index].rstrip(delimiter)
        else:
            # If no more suffixes, break out of the loop
            break

    # Reattach the original extension to the file string
    return file_str_without_extension + extension
def copy_file_and_append_suffix(file_path, suffix_new):
    """
    Copies the file with a new suffix added before the file extension.

    :param file_path: string of the path to the original file.
    :param suffix_new: string of the suffix to be appended to the original filename before the file extension.
    :return: string of the path to the newly created file with the new suffix.
    """
    if not os.path.isfile(file_path):
        raise ValueError(f"The file path does not exist or is invalid for {file_path}.")

    # Split the file path into directory, base name, and extension
    file_dir, file_base = os.path.split(file_path)
    file_name, file_ext = os.path.splitext(file_base)

    # Create the new file path with the suffix added before the file extension
    new_file_base = f"{file_name}{suffix_new}{file_ext}"
    new_file_path = os.path.join(file_dir, new_file_base)

    # Copy the original file to the new file path
    shutil.copy(file_path, new_file_path)

    return new_file_path
def sub_suffix_in_file(file_path, suffix_new):
    """
    Substitutes the suffix in the file name of the given file path with a new suffix.
    If new_suffix is empty '' then it will remove the last suffix of the file.

    :param file_path: string, the path to the original file.
    :param suffix_new: string, the new suffix to replace the existing one in the file name.
    :return: string, the path to the newly created file with the substituted suffix.
    """
    # Check if the original file exists
    if not os.path.isfile(file_path):
        raise ValueError(f"The file path does not exist or is invalid for {file_path}.")

    # Split the file path into directory, base name, and extension
    file_dir, file_base = os.path.split(file_path)
    file_name, file_ext = os.path.splitext(file_base)

    # Substitute the suffix in the file name using the sub_suffix_in_str function
    new_file_base = sub_suffix_in_str(file_name + file_ext, suffix_new)
    new_file_path = os.path.join(file_dir, new_file_base)

    # Rename the original file to the new file path
    os.rename(file_path, new_file_path)

    return new_file_path
def count_suffixes_in_folder(folder_path):
    """
    Analyzes all the files in the specified folder and prints the number of files for each unique suffix, alphabetized.

    :param folder_path: string of the folder path to search for files and analyze suffixes.
    :return: None. The function prints the suffixes and their counts.
    """
    if not os.path.isdir(folder_path):
        raise ValueError(f"The directory does not exist: {folder_path}")

    suffix_counts = {}
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
        if os.path.isfile(file_path):
            suffix = get_suffix(file_name)
            if suffix:
                suffix_counts[suffix] = suffix_counts.get(suffix, 0) + 1

    # Sort the suffixes alphabetically and print the counts
    for suffix in sorted(suffix_counts):
        print(f"SUFFIX COUNT for {suffix}: {suffix_counts[suffix]}")

### FOLDER
def get_files_in_folder(folder_path, suffixpat_include=None, suffixpat_exclude=None, include_subfolders=False):
    """
    Retrieves a list of file paths from the specified folder, sorted in alphabetical order.
    Optionally filters by suffix pattern and includes subfolders.

    :param folder_path: string of the path to the folder from which to retrieve files.
    :param suffixpat_include: string of the suffix pattern that included files must have.
    :param suffixpat_exclude: string of the suffix pattern that files must not have to be included.
    :param include_subfolders: boolean indicating whether to include files from subfolders.
    :return: list of strings of the file paths that meet the specified criteria.
    """
    if not os.path.isdir(folder_path):
        raise ValueError(f"VALUE ERROR in get_files_in_folder: folder does not exist.")
    if suffixpat_include is not None and suffixpat_exclude is not None:
        raise ValueError("Both suffixpat_include and suffixpat_exclude are provided.")
    
    all_file_paths = []
    if include_subfolders:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                all_file_paths.append(os.path.join(root, file))
    else:
        all_file_paths = glob.glob(os.path.join(folder_path, "*"))

    filtered_file_paths = []
    for file_path in all_file_paths:
        if os.path.isfile(file_path):
            # Suffix pattern handling
            if suffixpat_include:
                if '.' in suffixpat_include:
                    if not file_path.endswith(suffixpat_include):
                        continue
                else:
                    file_suffix = get_suffix(file_path)
                    if file_suffix != suffixpat_include:
                        continue
            if suffixpat_exclude:
                if '.' in suffixpat_exclude:
                    if file_path.endswith(suffixpat_exclude):
                        continue
                else:
                    file_suffix = get_suffix(file_path)
                    if file_suffix == suffixpat_exclude:
                        continue
            filtered_file_paths.append(file_path)
    
    filtered_file_paths.sort()
    return filtered_file_paths
def apply_to_folder(worker_function, folder_path, *args, suffixpat_include=None, suffixpat_exclude=None, include_subfolders=False, verbose=False, **kwargs):
    """
    Controller function that applies a specified worker function to each file in a folder.
    The worker function must operate on a single file.
    If it needs the folder name, that can be extracted from the file path.
    If it's creating or writing to another file, that filename or path can be given as another argument.

    :param worker_function: worker function name to apply to each file, not a string so do not use quotes.
    :param folder_path: string of the path to the folder from which to retrieve files.
    :param args: additional arguments to pass to the function.
    :param suffixpat_include: string of the suffix pattern that included files must have.
    :param suffixpat_exclude: string of the suffix pattern that files must not have to be included.
    :param include_subfolders: boolean of whether to include files from subfolders.
    :param verbose: boolean for printing verbose messages. Defaults to True.
    :param kwargs: additional keyword arguments to pass to the function.
    :return: a dictionary with file paths as keys and function return values as values.
    """
    verbose_print(verbose, f"\nRUNNING apply_to_folder with {worker_function}", f"FOLDER: {folder_path}")

    # Call get_files_in_folder to retrieve the list of files - it handles errors
    file_paths = get_files_in_folder(folder_path, suffixpat_include=suffixpat_include, suffixpat_exclude=suffixpat_exclude, include_subfolders=include_subfolders)
    file_paths.sort()
    verbose_print(verbose, f"NUMBER OF FILES RUN with apply_to_folder: {len(file_paths)}")
    
    results = {}  # Dictionary to store file names and function return values
    for file_path in file_paths:
        try:
            result = worker_function(file_path, *args, verbose=verbose, **kwargs)  # Try passing verbose
        except TypeError:
            result = worker_function(file_path, *args, **kwargs)  # Fallback if verbose is not accepted
        results[file_path] = result

    return results

### READ WRITE
def read_complete_text(file_path):
    """
    Reads the entire text from a file.

    :param file_path: string of the file path which can be absolute or relative.
    :return: string of the complete text read from the file.
    """
    if not os.path.isfile(file_path):
        raise ValueError(f"The file path does not exist or is invalid for {file_path}.")
    
    with open(file_path, 'r') as file:
        complete_text = file.read()
    return complete_text
def read_metadata_and_content_NEW(file_path):
    """
    Reads the text from a file and splits it into the metadata and content sections if present.
    If no metadata is found, returns (None, complete_text).

    :param file_path: string of the file path which can be absolute or relative.
    :return: tuple, the metadata and content as two separate strings. If no metadata, returns (None, complete_text).
    """
    if not os.path.isfile(file_path):
        raise ValueError(f"The file path does not exist or is invalid for {file_path}.")
    
    with open(file_path, 'r') as file:
        complete_text = file.read()

    # Check for Format 1: ## metadata and ## content
    metadata_start = complete_text.find('## metadata')
    content_start = complete_text.find('## content')
    
    if metadata_start != -1 and content_start != -1:
        metadata = complete_text[metadata_start:content_start].strip()
        content = complete_text[content_start:].strip()
        return metadata.rstrip('\n'), content

    # Check for Format 2: METADATA and CONTENT
    metadata_start = complete_text.find('METADATA')
    content_start = complete_text.find('CONTENT')
    
    if metadata_start != -1 and content_start != -1:
        metadata = complete_text[metadata_start + len('METADATA'):content_start].strip()
        content = complete_text[content_start:].strip()
        return metadata.rstrip('\n'), content

    # If no metadata found, return None for metadata and the complete text as content
    return None, complete_text.strip()
def read_metadata_and_content(file_path):
    """
    Reads the text from a file and splits it into the metadata and content sections.
    Gives a ValueError if both metadata and content are not present in one of the 2 formats.
    Format 1: ## metadata and ## content
    Format 2: METADATA and CONTENT
    Strips all leading and trailing newlines from the metadata string.
    The content string starts with the content delimiter.

    :param file_path: string of the file path which can be absolute or relative.
    :return: tuple, the metadata and content as two separate strings.
    """
    if not os.path.isfile(file_path):
        raise ValueError(f"The file path does not exist or is invalid for {file_path}.")
    with open(file_path, 'r') as file:
        complete_text = file.read()

    # Check for Format 1: ## metadata and ## content
    metadata_start = complete_text.find('## metadata')
    content_start = complete_text.find('## content')
    
    if metadata_start != -1 and content_start != -1:
        metadata = complete_text[metadata_start:content_start].strip()
        content = complete_text[content_start:].strip()
    else:
        # Check for Format 2: METADATA and CONTENT
        metadata_start = complete_text.find('METADATA')
        content_start = complete_text.find('CONTENT')
        
        if metadata_start != -1 and content_start != -1:
            metadata = complete_text[metadata_start + len('METADATA'):content_start].strip()
            content = complete_text[content_start:].strip()
        else:
            raise ValueError(f"File does not contain both metadata and content sections in the required format.\n{file_path}")

    return metadata.rstrip('\n'), content
''' Overwrite Logic Table:
Overwrite   Prompt
Argument    Response    Output Files	    Case Description
no          NA	        _orig + _orig_new	Keep both
no-sub	    NA	        _orig + _new	    Keep both and substitute suffix in new file
replace	    NA	        _orig_new	        Replace orig file
replace-sub	NA	        _new	            Replace orig file with new and substitute suffix in new file
yes	        NA	        _orig	            Overwrite without prompt
prompt      y/yes       _orig	            Prompt=Y to overwrite
prompt      n/no        _orig + _orig_new	Prompt= N to keep both
prompt	    s/sub	    _orig + _new	    Prompt=S to keep both and substitute suffix in new file
prompt	    x/anyother  re-prompt
x/anyother  ValueError
'''
def handle_overwrite_prompt(file_path, file_path_opfunc, verbose=True):
    """
    Handles user prompt for overwriting a file.

    :param file_path: string of the original file path.
    :param file_path_opfunc: string of the new file path.
    :param verbose: boolean for whether to print verbose messages. Default is True.
    :return: string of the path to the file that was kept.
    """
    # Check if both files exist before proceeding
    if not os.path.isfile(file_path):
        raise ValueError(f"The file path does not exist or is invalid for {file_path}.")
    if not os.path.isfile(file_path_opfunc):
        raise ValueError(f"The file path does not exist or is invalid for {file_path_opfunc}.")
    
    
    while True:
        user_input = input(f"Do you want to overwrite? [Y/yes, N/no, S/sub (substitute suffix)]: ").strip().lower()
        if user_input.startswith("y"):
            verbose_print(verbose, "File operation with overwrite=prompt+yes - overwrite original file.")
            os.remove(file_path)
            os.rename(file_path_opfunc, file_path)
            return file_path
        elif user_input.startswith("n"):
            verbose_print(verbose, f"File operation with overwrite=prompt+no - keep original file and new file.")
            return file_path_opfunc
        elif user_input.startswith("s"):
            verbose_print(verbose, f"File operation with overwrite=prompt+sub - keep original file and new file with substituted suffix.")
            file_path_sub = sub_suffix_in_str(file_path, get_suffix(file_path_opfunc, "_"), delimiter='_')
            os.rename(file_path_opfunc, file_path_sub)
            return file_path_sub
        else:
            print("Invalid input. Please enter 'Y' for yes, 'N' for no, or 'S' to substitute suffix.")
def manage_file_overwrite(original_path, suffix_new, overwrite, verbose=False):
    """
    Handle file overwriting based on the specified mode.
    
    :param original_path: string, the path to the original file.
    :param suffix_new: string, the suffix to be appended to the original filename for the new file.
    :param overwrite: string, the overwrite mode ('no', 'no-sub', 'replace', 'replace-sub', 'yes', 'prompt').
    :param verbose: boolean, whether to print verbose messages.
    :return: string, the final path of the file after applying overwrite logic.
    """
    new_path = add_suffix_in_str(original_path, suffix_new)
    
    if overwrite == "no":
        verbose_print(verbose, f"manage_file_overwrite in mode: '{overwrite}' - Keeping both original and new files.")
        return new_path
    elif overwrite == "no-sub":
        verbose_print(verbose, f"manage_file_overwrite in mode: '{overwrite}' - Keeping both files and substituting suffix in new file.")
        final_path = sub_suffix_in_str(original_path, suffix_new)
        os.rename(new_path, final_path)
        return final_path
    elif overwrite == "replace":
        verbose_print(verbose, f"manage_file_overwrite in mode: '{overwrite}' - Replacing original file with new file.")
        if os.path.exists(original_path):
            os.remove(original_path)
        os.rename(new_path, original_path)
        return original_path
    elif overwrite == "replace-sub":
        verbose_print(verbose, f"manage_file_overwrite in mode: '{overwrite}' - Replacing original file with new file and substituting suffix.")
        if os.path.exists(original_path):
            os.remove(original_path)
        final_path = sub_suffix_in_str(original_path, suffix_new)
        os.rename(new_path, final_path)
        return final_path
    elif overwrite == "yes":
        verbose_print(verbose, f"manage_file_overwrite in mode: '{overwrite}' - Overwriting original file.")
        if os.path.exists(original_path):
            os.remove(original_path)
        os.rename(new_path, original_path)
        return original_path
    elif overwrite == "prompt":
        verbose_print(verbose, f"manage_file_overwrite in mode: '{overwrite}' - Prompting user.")
        return handle_overwrite_prompt(original_path, new_path, verbose)
    else:
        raise ValueError(f"Invalid overwrite mode: {overwrite}")
def write_complete_text(file_path, complete_text, suffix_new='_temp', overwrite='no', verbose=False):
    """
    Writes the complete text to a new file with a specified suffix and handles overwrite logic.

    :param file_path: string, the path to the original file.
    :param complete_text: string, the complete text to be written to the new file.
    :param suffix_new: string, the suffix to be appended to the original filename for the new file.
    :param overwrite: string, the overwrite mode. Default is "no".
    :param verbose: boolean, whether to print verbose messages. Default is False.
    :return: string, the path to the final file after applying overwrite logic.
    """
    # Add suffix to create new file path
    new_file_path = add_suffix_in_str(file_path, suffix_new)
    if verbose:
        if os.path.isfile(new_file_path):
            print(f"BEFORE OVERWRITE write_complete_text new_file_path does exist.")
            warn_file_overwrite(new_file_path)
        else:
            print(f"BEFORE OVERWRITE write_complete_text new_file_path does NOT exist (note this file may be an intermediate file that is deleted or renamed by manage_file_overwrite).")
            
    # Write the complete text to the new file
    with open(new_file_path, "w") as file:
        file.write(complete_text)

    # Manage file overwrite
    final_file_path = manage_file_overwrite(file_path, suffix_new, overwrite, verbose)

    return final_file_path
def write_metadata_and_content(file_path, metadata, content, suffix_new='_temp', overwrite='no', verbose=False):
    """
    Writes the metadata and content text to a new file with a specified suffix and handles overwrite logic.
    Insert 2 blank lines between the metadata and adds a newline at the end of the content.

    :param file_path: string, the path to the original file.
    :param metadata: string, the metadata section to be written to the new file, inclusive of '## metadata' or 'METADATA'.
    :param content: string, the content section to be written to the new file, inclusive of '## content' or 'CONTENT'.
    :param suffix_new: string, the suffix to be appended to the original filename for the new file.
    :param overwrite: string, the overwrite mode. Default is "no".
    :param verbose: boolean, whether to print verbose messages. Default is False.
    :return: string, the path to the final file after applying overwrite logic.
    """
    # implement new convention to include 2 blank lines between metadata and content
    # strips all newlines from metadata before adding 3 back
    complete_text = metadata.rstrip('\n') + '\n\n\n' + content + '\n'

    return write_complete_text(file_path, complete_text, suffix_new, overwrite, verbose)

### MISC FILE
def rename_file(file_path, new_filebase):
    """
    Renames the file base portion for the file given at the argument file path.

    :param file_path: string, the path to the file to be renamed.
    :param new_filebase: string, the new base name for the file without the extension.
    :return: string, the new file path after renaming, or an error if the operation fails.
    """
    # Check if the original file exists and is valid
    if not os.path.isfile(file_path):
        raise ValueError(f"The file path does not exist or is invalid for {file_path}.")

    # Split the file path into directory, base name, and extension
    file_dir, file_base = os.path.split(file_path)
    file_ext = os.path.splitext(file_base)[1]

    # Create the new file path with the new file base
    new_file_path = os.path.join(file_dir, new_filebase + file_ext)

    # Rename the original file to the new file path
    try:
        os.rename(file_path, new_file_path)
        return new_file_path  # Return the new file path if the file was successfully renamed
    except OSError as e:
        return e  # Return the exception if an error occurred
def rename_file_extension(file_path, new_extension):
    """
    Renames the file extension for the file given at the argument file path.

    :param file_path: string, the path to the file to be renamed.
    :param new_extension: string, the new extension for the file (including the dot).
    :return: string, the new file path after renaming, or an error if the operation fails.
    """
    # Check if the original file exists and is valid
    if not os.path.isfile(file_path):
        raise ValueError(f"The file path does not exist or is invalid for {file_path}.")

    # Split the file path into directory, base name, and extension
    file_dir, file_base = os.path.split(file_path)
    file_name = os.path.splitext(file_base)[0]

    # Create the new file path with the new extension
    new_file_path = os.path.join(file_dir, file_name + new_extension)

    # Rename the original file to the new file path
    try:
        os.rename(file_path, new_file_path)
        return new_file_path  # Return the new file path if the file was successfully renamed
    except OSError as e:
        return e  # Return the exception if an error occurred
def delete_file(file_path):
    """
    Deletes a file at the specified file path.

    :param file_path: string, the path to the file to be deleted.
    :return: None. The function does not return any value.
    """
    try:
        os.remove(file_path)
        return True  # Return True if the file was successfully deleted
    except OSError as e:
        return e  # Return the exception if an error occurred
def delete_files_with_suffix(folder, suffixpat_include, verbose=False):  # omit unittests
    """
    Deletes all files in a given folder that end with a specified suffix.

    :param folder_path: string, the path to the folder where files are to be deleted.
    :param suffixpat_include: string, the suffix pattern of the files to be deleted.
    :param verbose: boolean, if True, the function will print verbose messages. Default is False.
    :return: None. The function does not return any value.
    """
    # Use apply_to_folder to delete files
    return apply_to_folder(delete_file, folder, suffixpat_include=suffixpat_include, include_subfolders=False, verbose=verbose)
def move_file(file_path, destination_folder): # cat 3a, unittest 3 - mocks
    """
    Moves a file to the specified destination folder.

    :param file_path: string, the path to the file to be moved.
    :param destination_folder: string, the path to the destination folder.
    :return: string, the new file path after moving, or an error if the operation fails.
    """
    # Check if the original file exists
    if not os.path.isfile(file_path):
        raise ValueError(f"The file path does not exist or is invalid for {file_path}.")

    # Check if the destination folder exists, if not, create it
    if not os.path.isdir(destination_folder):
        os.makedirs(destination_folder)

    # Create the new file path with the destination folder
    file_name = os.path.basename(file_path)
    new_file_path = os.path.join(destination_folder, file_name)

    # Move the original file to the new file path
    try:
        shutil.move(file_path, new_file_path)
        return new_file_path  # Return the new file path if the file was successfully moved
    except OSError as e:
        return e  # Return the exception if an error occurred
def move_files_with_suffix(source_folder, destination_folder, suffixpat_include, verbose=False): # omit unittest
    """
    Moves all files in a given folder that end with a specified suffix to the destination folder.

    :param source_folder: string, the path to the source folder where files are to be moved from.
    :param destination_folder: string, the path to the destination folder where files are to be moved to.
    :param suffixpat_include: string, the suffix pattern of the files to be moved.
    :param verbose: boolean, if True, the function will print verbose messages. Default is False.
    :return: list, the new file paths after moving, or an error if the operation fails.
    """
    # Use apply_to_folder to move files
    return apply_to_folder(move_file, source_folder, destination_folder, suffixpat_include=suffixpat_include, include_subfolders=False, verbose=verbose)
def tune_title(title):
    """
    Removes any special characters from the given title.

    :param title: string, the title from which special characters are to be removed.
    :return: string, the updated title with special characters removed.
    """
    # Remove any special characters from title_filename
    return re.sub(r'[^\w\s\-\(\)\.]', '', title)
def create_full_path(title_or_path, new_suffix_ext, default_folder=None):
    """
    Creates a full file path from a given title or path, a new suffix extension, and an optional default folder.

    :param title_or_path: string, the title or path of the file.
    :param new_suffix_ext: string, the new suffix extension to be added to the file.
    :param default_folder: string, the default folder to be used if no folder is specified in title_or_path. Default is None.
    :return: string, the newly created full file path.
    """
    # Extract file_stem, file_ext, and folder_path
    file_stem, file_ext = os.path.splitext(os.path.basename(title_or_path))
    folder_path = os.path.dirname(title_or_path)
    # Check if the file title or path argument includes a path
    if folder_path == '':
        if default_folder is not None:
            folder_path = default_folder
        else:
            raise ValueError("in create_full_path: no folder in title_or_path and default_folder is None.")
            
    # Remove special characters and apply naming conventions
    file_stem = tune_title(file_stem)

    # Construct the new file name with the new suffix and extension
    cur_suffix = get_suffix(file_stem)
    if cur_suffix is not None and cur_suffix + file_ext == new_suffix_ext:
        new_file_base = file_stem + file_ext
    else:
        new_file_base = file_stem + new_suffix_ext

    # Create the full path
    new_file_path = os.path.join(folder_path, new_file_base)

    return new_file_path
def find_file_in_folders(file_path, folder_paths):
    """
    Searches for a file within a list of folder paths and returns the first match.

    :param file_path: string of the file name to search for.
    :param folder_paths: list of strings of folder paths where the file will be searched.
    :return: string of the full path to the file if found, otherwise None.
    """
    if not os.path.isfile(file_path):
        for folder in folder_paths:
            potential_path = os.path.join(folder, os.path.basename(file_path))
            if os.path.isfile(potential_path):
                return potential_path
        return None
    else:
        warnings.warn(f"file_paths exists at this path - find_file_in_folders erroneously called")
        return file_path
def zip_files_in_folders(folder_paths, suffixpat_include, zip_file_path, include_subfolders=True):
    """
    Zips files in the specified folders that match the given suffix into a single zip file.

    :param folder_paths: list of strings, the paths to the folders where files will be zipped.
    :param suffixpat_include: string, the suffix pattern that included files must have.
    :param zip_file_path: string, the path where the single zip file will be created.
    :param include_subfolders: boolean, indicates whether to include files from subfolders.
    :return: None
    """
    import zipfile
    import os

    # Ensure the directory path for the zip file exists
    os.makedirs(os.path.dirname(zip_file_path), exist_ok=True)

    # Create a single zip file to store all files
    with zipfile.ZipFile(zip_file_path, 'w') as zipf:
        for folder_path in folder_paths:
            if os.path.isdir(folder_path):
                if include_subfolders:
                    # Include files from subfolders
                    for root, dirs, files in os.walk(folder_path):
                        for file in files:
                            file_name, file_extension = os.path.splitext(file)
                            if file_name.endswith(suffixpat_include):
                                file_path = os.path.join(root, file)
                                # Preserve the folder structure relative to the folder path
                                arcname = os.path.relpath(file_path, start=os.path.dirname(folder_path))
                                zipf.write(file_path, arcname)
                else:
                    # Only include files from the top-level directory
                    for file in os.listdir(folder_path):
                        if file.endswith(suffixpat_include) and os.path.isfile(os.path.join(folder_path, file)):
                            file_path = os.path.join(folder_path, file)
                            zipf.write(file_path, file)
            else:
                print(f"Folder does not exist: {folder_path}")

    print(f"Created zip at {zip_file_path} containing files from folders: {folder_paths}")
def compare_files_text(file1_path, file2_path):
    """
    Compares the content of two files.

    :param file1_path: string, the path to the first file to be compared.
    :param file2_path: string, the path to the second file to be compared.
    :return: boolean, True if the content of the files is exactly the same, False otherwise.
    """
    text1 = read_complete_text(file1_path)
    text2 = read_complete_text(file2_path)
    if text1 == text2:
        print("TRUE for compare_file_text - the content of the files is exactly the same.")
        return True
    else:
        print("FALSE for compare_file_text - the content of the files is different.")
        return False
def get_text_between_delimiters(full_text, delimiter_start, delimiter_end=None):
    """
    Extracts a substring from the given text between specified start and end delimiters.

    :param full_text: string of the text from which to extract the substring.
    :param delimiter_start: string of the delimiter indicating the start of the substring.
    :param delimiter_end: string of the delimiter indicating the end of the substring. If None, the end of the text is used. Default is None.
    :return: string of the extracted substring (inclusive of delimiter_start), or None if the start delimiter is not found.
    """
    start_index = full_text.find(delimiter_start)
    if start_index == -1:
        warnings.warn(f"in get_text_between_delimiters - no text found with delimiter_start: {delimiter_start} using the function: get_text_between_delimiters")
        return None
    end_index = len(full_text) if delimiter_end is None else full_text.find(delimiter_end, start_index + len(delimiter_start))
    if end_index == -1:
        end_index = len(full_text)

    extracted_text = full_text[start_index:end_index].rstrip('\n').rstrip(' \t')
    return extracted_text + '\n'
    # assumes that both delimiters are unique in the content string
    # return string inclusive of the delimiter_start but exclusive of the delimiter_end
    # return string has any blank lines stripped and ending with a single newline character
    # return None if delimiter_start not found


### TIME AND TIMESTAMP
def convert_seconds_to_timestamp(seconds):
    """
    Converts a given number of seconds into a timestamp in the format hh:mm:ss or mm:ss.

    :param seconds: integer or float representing the number of seconds to be converted.
    :return: string representing the timestamp in the format hh:mm:ss or mm:ss.
    """
    if not isinstance(seconds, (int, float)):
        raise TypeError("Input must be an integer or float representing seconds.")
    if seconds < 0:
        raise ValueError("Input must be a non-negative number of seconds.")

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)  # This will always round down

    # If hours exist
    if hours > 0:
        return f"{hours}:{minutes:02}:{seconds:02}"
    # If minutes exist
    elif minutes > 0:
        return f"{minutes}:{seconds:02}"
    else:
        return f"0:{seconds:02}"
def convert_timestamp_to_seconds(timestamp):
    """
    Converts a timestamp in the format hh:mm:ss or mm:ss into seconds.

    :param timestamp: string representing the timestamp in the format hh:mm:ss or mm:ss.
    :return: integer representing the total number of seconds.
    """
    if not isinstance(timestamp, str):
        raise TypeError("Timestamp must be a string in the format hh:mm:ss or mm:ss")

    time_components = timestamp.split(':')

    if not all(component.isdigit() for component in time_components):
        raise ValueError("Invalid timestamp: Non-numeric characters found")

    if len(time_components) == 3:
        hours, minutes, seconds = map(int, time_components)
    elif len(time_components) == 2:
        hours = 0
        minutes, seconds = map(int, time_components)
    else:
        raise ValueError("Invalid timestamp format. Expected hh:mm:ss or mm:ss")

    if not (0 <= hours <= 99):
        raise ValueError("Invalid timestamp: Hours must be in the range 0-99")

    if not (0 <= minutes <= 59):
        raise ValueError("Invalid timestamp: Minutes must be in the range 0-59")

    if not (0 <= seconds <= 59):
        raise ValueError("Invalid timestamp: Seconds must be in the range 0-59")

    total_seconds = seconds + minutes * 60 + hours * 3600
    return total_seconds
def change_timestamp(timestamp, delta_seconds):
    """
    Changes a given timestamp by a specified number of seconds. Uncomment line in tune_timestamp

    :param timestamp: string representing the timestamp in the format hh:mm:ss or mm:ss.
    :param delta_seconds: integer representing the number of seconds to change the timestamp by.
    :return: string representing the new timestamp after the change.
    """
    if timestamp is None:
        raise ValueError("No timestamp provided. Cannot change timestamp.")
    modified_seconds = convert_timestamp_to_seconds(timestamp) + delta_seconds
    if modified_seconds < 0: 
        raise ValueError("Resulting time cannot be less than zero.")
    return convert_seconds_to_timestamp(modified_seconds)
def tune_timestamp(timestamp):
    """
    Converts a given timestamp to a standard format with respect to digits and leading zeros.

    :param timestamp: string representing the timestamp in the format hh:mm:ss or mm:ss.
    :return: string representing the tuned timestamp or None if the input timestamp is None.
    """
    # convert a timestamp to our standard with respect to digits and leading zeros
    if timestamp is None: # not sure if it was intentional to not raise ValueError but leave it
        return None
    # timestamp = change_timestamp(timestamp, 0)  # CAUTION - only include to shift the timestamps
    secs = convert_timestamp_to_seconds(timestamp)
    tuned_timestamp = convert_seconds_to_timestamp(secs)
    #print(f"Original timestamp: '{timestamp}'  Tuned timestamp: '{tuned_timestamp}'") 
    return tuned_timestamp
def get_timestamp(line, print_line=False, max_words=8):
    """
    Extracts a timestamp from a given line of text.

    :param line: string representing the line of text to search for a timestamp.
    :param print_line: boolean indicating whether to print the line where the timestamp was found. Default is False.
    :param max_words: integer representing the maximum number of words allowed before and after the timestamp. Default is 5.
    :return: tuple containing the extracted timestamp as a string and its index in the line, or (None, None) if no valid timestamp is found.
    """
    # Maximum number of words allowed before and after the timestamp, increase for assign speaker_names
    line = line.rstrip('\n') # Strip newline characters if present at the end

    # Regex to match timestamps in various formats including those in square brackets
    # followed by a link in parentheses. The restriction on what follows the timestamp and link has been removed.
    timestamp_regex = r"\b(?:\d{1,2}:)?\d{1,2}:\d{2}\b"
    link_regex = r"\[\s*([^\]]*)\]\(\s*([^)]+)\s*\)"
    #combined_regex = timestamp_regex + r"(?:" + link_regex + r")?"
    combined_regex = r"(" + timestamp_regex + r")" + r"(?:" + link_regex + r")?"

    match = re.search(combined_regex, line)
    if match:
        timestamp = match.group().rstrip()
        # Check if there are more than max words before the timestamp
        words_before_timestamp = line[:match.start()].split()
        if len(words_before_timestamp) > max_words:
            return None, None
        # Check if the string preceding the timestamp is 'length:' followed by any white space
        if ''.join(words_before_timestamp).lower() == 'length:':
            return None, None

        # Use the start of the timestamp as the index
        index = match.start()
        # Check if the character before the index is a starting square bracket
        if index > 0 and line[index - 1] == '[':
            index -= 1
        string_after_index = line[match.end():].split()

        # Check if there are more than max words after the timestamp
        # Exclude the check if the timestamp starts the line
        if len(string_after_index) > max_words and index != 0:
            return None, None

        # Extract just the timestamp without any brackets or links
        pure_timestamp_match = re.search(timestamp_regex, timestamp)
        if pure_timestamp_match:
            #timestamp = pure_timestamp_match.group()
            timestamp = match.group(1).rstrip()  # Group 1 is the timestamp

        # Check for timestamp overflow using the convert_timestamp_to_seconds function
        try:
            convert_timestamp_to_seconds(timestamp)
        except ValueError as ve:
            raise ValueError(f"Invalid timestamp: {timestamp}. Minutes or seconds exceed 59!") from ve

        if print_line:
            print(f"Timestamp found in line: {line} with timestamp = {timestamp} and index = {index}")

        return timestamp, index
    else:
        return None, None
def get_current_datetime_humanfriendly(timezone='America/Los_Angeles', include_timezone=True):
    """
    Returns the current date and time as a string for a given timezone, optionally including the timezone abbreviation and UTC offset.

    :param timezone: string representing the timezone to use for the current time.
    :param include_timezone: boolean indicating whether to include the timezone abbreviation and UTC offset in the returned string.
    :return: string representing the current date and time in the specified timezone, optionally followed by the timezone abbreviation and UTC offset.
        """
    tz = pytz.timezone(timezone)
    current_time = datetime.now(tz)
    datetime_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
    if include_timezone:
        #timezone_abbr = current_time.strftime('%Z')  # remove using the abbr such as PDT PST to avoid complication 5-4-24 RT
        utc_offset = tz.utcoffset(current_time.replace(tzinfo=None)).total_seconds() / 3600
        datetime_str += f" UTC{int(utc_offset):+03d}:00 {timezone}"
    return datetime_str
# TODO needs unittests
def get_current_datetime_filefriendly(location='America/Los_Angeles', include_utc=False):
    """
    Returns the current date and time as a filename-friendly string for a given timezone, optionally including only the UTC offset.

    :param location: string representing the timezone to use for the current time.
    :param include_utc: boolean indicating whether to include the UTC offset in the returned string.
    :return: string representing the current date and time in the specified timezone, formatted for filenames, optionally followed by the UTC offset.
        """
    datetime_str = get_current_datetime_humanfriendly(location, include_timezone=True)
    # Remove colons and replace spaces with underscores
    filename_friendly_datetime = datetime_str.replace(':', '').replace(' ', '_')
    if include_utc:
        # Extract UTC offset and format it
        utc_offset = filename_friendly_datetime.split('_UTC')[1].split('_')[0]
        utc_offset = utc_offset.replace('+', '').replace(':', '')
        # Include only the UTC offset in the filename
        filename_friendly_datetime = filename_friendly_datetime.split('_UTC')[0] + '_UTC' + utc_offset
    else:
        # Remove UTC part if not included
        filename_friendly_datetime = filename_friendly_datetime.split('_UTC')[0]
    return filename_friendly_datetime
# TODO Consider adding more flexibility to date and time formats
def convert_to_epoch_seconds(datetime_flex, timezone='America/Los_Angeles', verbose=False):
    """
    Converts a human-readable time to the number of seconds since the Unix epoch (1970-01-01 00:00:00 UTC).
    The function assumes the input format is 'YYYY-MM-DD_HH:MM:SS [optional UTC offset] [optional timezone]', 
    where the date and time are separated by an underscore or space,
    and the time may be followed by another underscore or space and a UTC offset string, and optionally a timezone string.

    :param datetime_flex: string representing the time, which can be in 'YYYY-MM-DD_HH:MM:SS' format or 'YYYY-MM-DD HH:MM:SS [UTC offset] [timezone]'.
    :param default_timezone: string representing the default timezone if not specified in datetime_flex. Defaults to 'America/Los_Angeles'.
    :return: float representing the number of seconds since the Unix epoch.
    """
    # Define delimiters for splitting the input string
    first_delimiter_index = re.search(r'[ _]', datetime_flex).start()
    date_part = datetime_flex[:first_delimiter_index]
    remainder = datetime_flex[first_delimiter_index + 1:]

    next_delimiter_index = re.search(r'[ _]', remainder)
    if next_delimiter_index:
        next_delimiter_index = next_delimiter_index.start()
        time_part = remainder[:next_delimiter_index]
        remainder = remainder[next_delimiter_index + 1:]
    else:
        time_part = remainder
        remainder = ''

    utc_offset_part = ''
    timezone_part = ''
    utc_index = remainder.find('UTC')
    if utc_index != -1:
        utc_end_index = re.search(r'[ _]', remainder[utc_index:])
        if utc_end_index:
            utc_end_index = utc_end_index.start() + utc_index
            utc_offset_part = remainder[utc_index:utc_end_index]
            timezone_part = remainder[utc_end_index + 1:]
        else:
            utc_offset_part = remainder[utc_index:]
            timezone_part = ''
    else:
        timezone_part = remainder

    verbose_print(verbose, f"Date part: {date_part}")
    verbose_print(verbose, f"Time part: {time_part}")
    verbose_print(verbose, f"UTC offset part: '{utc_offset_part}'")
    verbose_print(verbose, f"Timezone part: '{timezone_part}'")
    # Validate date part format
    try:
        datetime.strptime(date_part, '%Y-%m-%d')
    except ValueError:
        raise ValueError(f"Date format not recognized: {date_part}. Expected format: YYYY-MM-DD")

    # Validate and format the time part
    if len(time_part) == 6 and time_part.isdigit():
        time_part = time_part[:2] + ':' + time_part[2:4] + ':' + time_part[4:]
        verbose_print(verbose, f"Formatted time part: {time_part}")
    elif len(time_part) == 8 and re.match(r'\d{2}:\d{2}:\d{2}', time_part):
        verbose_print(verbose, f"Time part already formatted: {time_part}")
    else:
        raise ValueError(f"Time format not recognized: {time_part}. Expected formats: HHMMSS (6 digits) or HH:MM:SS")

    # Use the provided UTC offset if available, otherwise use extracted timezone part, then if neither of those exist then use the default timezone
    if utc_offset_part.strip():
        utc_offset_match = re.search(r'([-+]?\d{2}):?(\d{2})', utc_offset_part)
        if utc_offset_match:
            hours = int(utc_offset_match.group(1))
            minutes = int(utc_offset_match.group(2))
            utc_offset_minutes = hours * 60 + minutes
            tz = pytz.FixedOffset(utc_offset_minutes)  # Create timezone from UTC offset in minutes
            verbose_print(verbose, f"Using extracted UTC offset: {utc_offset_part}")
        else:
            raise ValueError(f"Invalid UTC offset format: {utc_offset_part}")
    elif timezone_part:
        verbose_print(verbose, f"Using extracted timezone part: {timezone_part}")
        tz = pytz.timezone(timezone_part)
    else:
        verbose_print(verbose, f"No valid UTC offset or timezone part extracted, using default timezone: {timezone}")
        tz = pytz.timezone(timezone)

    # Combine date and time parts and parse them
    datetime_str = f"{date_part} {time_part}"
    try:
        naive_time = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
        localized_time = tz.localize(naive_time)
        epoch_time = (localized_time - datetime(1970, 1, 1, tzinfo=pytz.utc)).total_seconds()
        return epoch_time
    except ValueError:
        raise ValueError(f"Time format not recognized: {datetime_str}")
def get_elapsed_seconds(start_time_epoch_seconds):
    """
    Calculates the time elapsed since the start_time and returns it in seconds.

    :param start_time: float, the start time in seconds since the epoch (as returned by time.time())
    :param return_format: string ('minutes' or 'timestamp') for the return value format - 'timestamp' for H:MM:SS or minutes with one decimal place
    :return: integer of the number of seconds
    """
    current_time = time.time()
    return int(round(current_time - start_time_epoch_seconds))

### TIMESTAMP LINKS
def remove_timestamp_links_from_content(content):
    """
    Removes markdown timestamp links from the content and returns the modified content.

    :param content: string of the content from which to remove markdown timestamp links.
    :return: string of the content with markdown timestamp links removed.
    """
    content_lines = content.splitlines()
    processed_lines = [re.sub(r'\[(.*?)\]\(.*?\)', r'\1', line) for line in content_lines]
    return '\n'.join(processed_lines)+"\n"  # explicitly add extra newline to avoid stripping one
# TODO Update to auto detect whether the file path has metadata and content by. First trying to read the file as metadata and content. And so I'm going to need to adjust that function to probably to return something that will indicate to branch.
def remove_timestamp_links(file_path):
    """
    Removes markdown timestamp links and overwrites the file.

    :param file_path: string of the path to the original file.
    :return: none.
    """
    metadata, content = read_metadata_and_content_NEW(file_path)
    new_content = remove_timestamp_links_from_content(content)
    
    if metadata is None:
        write_complete_text(file_path, new_content, overwrite='yes')
    else:
        write_metadata_and_content(file_path, metadata, new_content, suffix_new='_temp', overwrite='yes')
def generate_timestamp_link(base_link, timestamp):
    """
    Helper function to generate a timestamp link for a given base link and timestamp.
    It uses a dictionary to map domains to their respective timestamp formats.
    For Vimeo, the timestamp is converted to milliseconds.
    
    :param base_link: string of the base URL to which the timestamp will be appended.
    :param timestamp: string of the timestamp to be converted and appended to the base URL.
    :return: string of the complete URL with the timestamp appended in the appropriate format.
    """
    # Dictionary mapping domains to their timestamp formats
    domain_timestamp_formats = {
        "youtube.com": "&t={}",
        "youtu.be": "&t={}",
        "spotify.com": "&t={}",
        "vimeo.com": "?ts={}"
    }

    # Determine the domain format based on the base link
    for domain, format_string in domain_timestamp_formats.items():
        if domain in base_link:
            domain_timestamp_format = format_string
            break
    else:
        domain_timestamp_format = "&t={}"  # Default format if domain not found

    # Convert the timestamp to the appropriate format
    if "?ts={}" in domain_timestamp_format:
        # Vimeo uses milliseconds
        timestamp_seconds = convert_timestamp_to_seconds(timestamp) * 1000
    else:
        # Other domains use seconds
        timestamp_seconds = convert_timestamp_to_seconds(timestamp)

    # Create the new timestamp link
    timestamp_link = f"[{timestamp}]({base_link}{domain_timestamp_format.format(timestamp_seconds)})"
    return timestamp_link
def add_timestamp_links_to_content(content, base_link):
    """
    Adds timestamp links to the content using the provided base link.

    :param content: string of the content where timestamp links will be added.
    :param base_link: string of the base URL to which the timestamp will be appended.
    :return: string of the content with timestamp links added.
    """
    # Processes each line of the content to add timestamp links using the base link
    content_lines = content.splitlines()
    processed_lines = []
    for line in content_lines:
        timestamp, index = get_timestamp(line)
        if timestamp:
            tuned_timestamp = tune_timestamp(timestamp)
            if tuned_timestamp and index is not None:
                timestamp_link = generate_timestamp_link(base_link, tuned_timestamp)
                line_with_link = line[:index] + timestamp_link + line[index + len(timestamp):]
            else:
                line_with_link = line
        else:
            line_with_link = line
        processed_lines.append(line_with_link)
    return '\n'.join(processed_lines)+"\n"  # explicitly add extra newline to avoid stripping one
def add_timestamp_links(file_path):
    """
    Adds markdown timestamp links and overwrites the file.

    :param file_path: string, the path to the file where timestamp links will be added.
    :return: none
    """
    metadata, content = read_metadata_and_content(file_path)
    _, base_link = read_metadata_field_from_file(file_path, "link")
    
    # First, remove any existing timestamp links from the content
    content_without_links = remove_timestamp_links_from_content(content)
    # Then, add new timestamp links to the content
    new_content = add_timestamp_links_to_content(content_without_links, base_link)

    write_metadata_and_content(file_path, metadata, new_content, suffix_new='_temp', overwrite='yes')

### FIND AND REPLACE
def count_num_instances(file_path, find_str):
    """
    Counts the number of instances of a specific string in the text of the file.
    Is case-sensitive.

    :param file_path: string, the path to the file where the search will be performed.
    :param find_str: string, the string to find in the file content.
    :return: int, the number of instances found, or zero if no instances are found.
        """
    complete_text = read_complete_text(file_path)
    count = complete_text.count(find_str)
    print(f"Number instances: {count} of {find_str} found in {file_path}")
    return count
def find_and_replace_pairs(file_path, find_replace_pairs, use_regex=False):
    """
    Finds and replaces multiple specified strings or regex patterns in the file and overwrites the original file.

    :param file_path: string, the path to the file where the find and replace operations will be performed.
    :param find_replace_pairs: list of tuples, each containing a string or regex pattern to be found and a string to replace it with.
    :param use_regex: boolean for whether to use regex patterns for finding. Default is False (use exact string matching).
    :return: int, the total number of replacements made.
    """
    metadata, content = read_metadata_and_content_NEW(file_path)

    total_replacements = 0
    for find_str, replace_str in find_replace_pairs:
        if use_regex:
            regex = re.compile(find_str, re.DOTALL)
            content, count = regex.subn(replace_str, content)
        else:
            content, count = re.subn(re.escape(find_str), replace_str, content, flags=re.DOTALL)
        total_replacements += count

    if metadata is None:
        write_complete_text(file_path, content, overwrite='yes')
    else:
        write_metadata_and_content(file_path, metadata, content, overwrite='yes')

    return total_replacements
# TODO reconsider the flexibility of the space before the comma so that we can use pairs with leading or trailing spaces, maybe have a warning confirmation message if the csv has a pair with a leading space
def parse_csv_for_find_replace(csv_file):
    """
    Parses a CSV file to extract find and replace pairs.
    Returns a list of the find_
    """
    pairs = []
    with open(csv_file, mode='r', newline='') as csvfile:
        csvreader = csv.reader(csvfile)
        first_row = next(csvreader)
        if not (first_row and ','.join(first_row).strip().startswith('find')):
            warnings.warn("CSV does not start with 'find, replace' header. Processing the first row as data.")
            pairs.append((first_row[0].strip(), first_row[1].strip()))
        for row in csvreader:
            if row and not row[0].strip().startswith('#'):
                try:
                    find_str, replace_str = row[0].strip(), row[1].strip()
                    pairs.append((find_str, replace_str))
                except IndexError as e:
                    print(f"Error processing row: {row} - {str(e)}")
    return pairs
# TODO needs unittest
def find_and_replace_from_csv(folder_path, find_replace_csv, suffixpat_include=None, verbose=False):
    """
    Applies find and replace operations on all files in a specified folder based on pairs defined in a CSV file.
    Overwrite is fixed at 'yes' so you have to copy the files before running.
    IMPORTANT csv file cannot be in the same folder if suffixpat_include=None
    Good practice is to always include a suffixpat_include even if those are the only type of file in the folder.

    :param folder_path: string, the path to the folder where the files are located.
    :param find_replace_csv: string, the path to the CSV file containing find and replace pairs.
    :param suffixpat_include: string, the suffix pattern that included files must have. If None, all files will be processed.
    :param verbose: boolean, if True prints verbose messages.
    :return: None
    """
    # Parse the CSV to get find and replace pairs
    find_replace_pairs = parse_csv_for_find_replace(find_replace_csv)
    
    # Apply find and replace operations to all files in the folder
    results = apply_to_folder(find_and_replace_pairs, folder_path, find_replace_pairs, suffixpat_include=suffixpat_include, verbose=verbose)

    # Print the total number of replacements in all files
    total_replacements = sum(results.values())
    print(f"{total_replacements} REPLACEMENTS IN {len(results)} files run.")

    # If verbose is True, print the number of replacements for each file
    if verbose:
        for file_path, num_replacements in results.items():
            print(f"{num_replacements} replacements in file: {file_path}  {num_replacements} replacements")

### HEADINGS
def get_heading_level(heading):
    """
    Determines the level of a markdown heading.

    :param heading: string, the markdown heading including '#' characters.
    :return: int, the level of the heading.
    """
    return len(heading) - len(heading.lstrip('#'))
def get_heading_pattern(heading):
    """
    Creates a regex pattern to match a heading and its content, including subheadings.

    :param heading: string, the markdown heading including '#' characters.
    :return: compiled regex pattern or None if heading is empty
    """
    if not heading:
        return None

    heading_level = get_heading_level(heading)
    
    # Escape special characters in the heading
    escaped_heading = re.escape(heading)
    
    # Define the end delimiter as any markdown heading of equal or higher order
    delimiter_end_pattern = r'(?=^#{1,' + str(heading_level) + r'}\s|\Z)'
    
    # Construct the full pattern
    full_pattern = f"({escaped_heading}.*?){delimiter_end_pattern}"
    
    return re.compile(full_pattern, re.MULTILINE | re.DOTALL)
def find_heading_text(full_text, heading):
    """
    Finds the heading text, including its subheadings, inclusive of the heading itself.

    :param text: string, the text to search in.
    :param heading: string, the markdown heading to find.
    :return: tuple (start_index, end_index) or None if not found.
    """
    pattern = get_heading_pattern(heading)
    if pattern is None:
        return None
    match = pattern.search(full_text)
    if match:
        return match.start(), match.end()
    return None
def get_heading(file_path, heading):
    """
    Extracts the markdown heading and its associated text from a file, including any subheadings of equal or lower order.
    Uses the complete text and does not parse the metadata and content sections.

    :param file_path: string, the path to the file to be read.
    :param heading: string, the markdown heading to be extracted, including the '#' characters and the following space.
    :return: string, the markdown heading and its associated text, including any subheadings of equal or lower order.
    """
    complete_text = read_complete_text(file_path)
    result = find_heading_text(complete_text, heading)
    if result:
        start, end = result
        return complete_text[start:end]
    return None
def set_heading(file_path, new_text, heading):
    """
    Sets the heading and following text associated with a markdown heading and overwrites the file.
    Replaces if the heading already exists. Adds if it does not exist.
    New line characters must be included in the new_text (e.g., "\nHere's new text\n\n").
    
    :param file_path: string, the path to the file where the heading text will be set.
    :param new_text: string, the new text to be associated with the markdown heading, inclusive of newlines.
    :param heading: string, the markdown heading whose text will be set, including the '#' characters and the following space.
    :return: None
    """
    metadata, content = read_metadata_and_content(file_path)
    
    new_text_with_heading = f"{heading}\n{new_text}"
    if not new_text_with_heading.endswith('\n'):
        new_text_with_heading += '\n'
    
    result = find_heading_text(content, heading)
    
    if result:
        start, end = result
        new_content = content[:start] + new_text_with_heading + content[end:]
    else:
        # Add new heading at the top of the content section
        content_lines = content.split('\n')
        if content.strip():  # Check if content is not empty
            if len(content_lines) > 1:
                # Find the position of the first non-blank line after the first line
                insert_position = 1
                while insert_position < len(content_lines) and content_lines[insert_position].strip() == '':
                    insert_position += 1
                # Strip a single newline from the end of new_text_with_heading if present
                new_text_to_insert = new_text_with_heading[:-1] if new_text_with_heading.endswith('\n') else new_text_with_heading
                # Insert the new heading and text
                content_lines.insert(insert_position, new_text_to_insert)
                new_content = '\n'.join(content_lines)
            else:
                # If content has only one line, append the new heading and text
                new_content = f"{content.rstrip()}\n\n{new_text_with_heading}"
        else:
            # If content is empty, just use the new heading and text
            new_content = new_text_with_heading
    
    # Write the updated content back to the file
    write_metadata_and_content(file_path, metadata, new_content, suffix_new='_temp', overwrite='yes')
def delete_heading(file_path, heading):
    """
    Deletes the specified markdown heading and its following text, including subheadings, and overwrites the file.
    If the heading does not exist, a warning is issued and no action is taken.

    :param file_path: string of the path to the file from which the heading will be deleted.
    :param heading: string of the markdown heading to be deleted, including the '#' characters and the following space.
    """
    metadata, content = read_metadata_and_content(file_path)
    
    result = find_heading_text(content, heading)
    
    if result:
        start, end = result
        new_content = content[:start] + content[end:]
        new_content = re.sub(r'\n{3,}', '\n\n', new_content)
        
        write_metadata_and_content(file_path, metadata, new_content, suffix_new='_temp', overwrite='yes')
    else:
        warnings.warn("in delete_heading: trying to delete heading that does not exist - no action")
def append_heading_to_file(source_file_path, target_file_path, heading, include_filename=True):
    """
    Appends the text under a specified heading from a source file to a target file, optionally including the source filename as a heading.

    :param source_file_path: string of the path to the source file.
    :param target_file_path: string of the path to the target file where the text will be appended.
    :param heading: string of the markdown heading to be appended.
    :param include_filename: boolean indicating whether to include the source filename as a heading. Defaults to True.
    :return: string of the appended text or None if the heading is not found in the source file.
    """
    new_text = get_heading(source_file_path, heading)
    if new_text is not None:
        if include_filename:
            # Extract the file name from the source file path
            filename = os.path.basename(source_file_path)
            # Determine the markdown heading level for the filename (one less than the heading level)
            heading_level = '#' * (heading.count('#') - 1 if heading.count('#') > 1 else 1)
            # Add the filename as a heading above the new_text
            new_text = f"{heading_level} {filename}\n{new_text}"
        
        # Check if the target file path has a folder component; if not, use the folder from the source file path
        target_folder = os.path.dirname(target_file_path)
        if not target_folder:
            source_folder = os.path.dirname(source_file_path)
            target_file_path = os.path.join(source_folder, os.path.basename(target_file_path))
 
        if os.path.exists(target_file_path):
            text = read_complete_text(target_file_path)
            text += '\n' + new_text

        write_complete_text(target_file_path, text, suffix_new='_temp', overwrite='yes')
        return new_text
    else:
        return None
def create_new_file_from_heading(file_path, heading, suffix_new='_headingonly', remove_heading=False):
    """
    Extracts text under a specified heading from a file and writes it to a new file with a specified suffix.

    :param file_path: string of the path to the file.
    :param heading: string of the markdown heading to be processed.
    :param suffix_new: string of the suffix to be appended to the new file. Defaults to "_headingonly".
    :param remove_heading: boolean indicating whether to remove the heading from the extracted text. Defaults to False.
    :return: string of the path to the newly created file.
    """
    heading_text = get_heading(file_path, heading)
    
    if heading_text is None:
        heading_text = ""  # Set to empty string if heading not found or file is empty
    else:
        if remove_heading:
            # Remove the markdown heading line and any blank lines that follow it
            lines = heading_text.split('\n')
            non_empty_index = next((i for i, line in enumerate(lines) if line.strip() and not line.startswith('#')), len(lines))
            heading_text = '\n'.join(lines[non_empty_index:])
        else:
            # Strip the markdown heading from the beginning of the complete text
            heading_text = heading_text.lstrip(heading).lstrip('\n')
    
    return write_complete_text(file_path, heading_text, suffix_new)

### METADATA
def set_metadata_field(metadata, field, value):
    """
    Sets or updates a metadata field with a given value.

    :param metadata: string, the metadata from which a metadata field is to be set or updated.
    :param field: string, the metadata field to be set or updated without the : and space.
    :param value: string, the value to be set for the metadata field.
    :return: string, the updated metadata with the set or updated metadata field.
    """
    # Split the metadata text into lines
    lines = metadata.split('\n')
    field_line = None
    field_exists = False
    insert_index = -1  # Default insert index to the end of the metadata

    # Check if the field already exists and find the insert index after '## metadata'
    metadata_start_found = False
    for i, line in enumerate(lines):
        if '## metadata' in line:
            metadata_start_found = True
            metadata_index = i
        elif metadata_start_found and line.strip() == '':
            insert_index = i  # Set insert index to the first blank line after '## metadata'
            break
        if line.startswith(f"{field}:"):
            field_exists = True
            field_line = i
            break

    # If the field exists, update it
    if field_exists:
        lines[field_line] = f"{field}: {value}"
    else:
        # If the field does not exist, add it at the insert index
        if insert_index == -1:  # If no blank line was found, append it after the metadata heading
            lines.insert(metadata_index + 1, f"{field}: {value}")
        else:
            lines.insert(insert_index, f"{field}: {value}")

    # Reassemble the metadata text
    updated_metadata = '\n'.join(lines)

    return updated_metadata
def remove_metadata_field(metadata, field):
    """
    Removes a specified metadata field from the metadata.

    :param metadata: string, the metadata from which a metadata field is to be removed.
    :param field: string, the metadata field to be removed.
    :return: string, the updated metadata with the removed metadata field.
    """
    # Removes a specified metadata field from the metadata
    lines = metadata.split('\n')
    updated_lines = [line for line in lines if not line.startswith(f"{field}:")]
    updated_metadata = '\n'.join(updated_lines)
    # DONE fill in code utilizing code from @add_metadata_field to delete the provided field
    return updated_metadata
def create_initial_metadata():
    """
    Creates an initial metadata for a file.

    :return: string, the initial metadata for a file.
    """
    metadata = "## metadata\nlast updated: \n"  # newlines will
    return metadata
def set_last_updated(metadata, new_last_updated_value, use_today=True):
    """
    Updates the 'last updated' metadata field in the metadata with a new value.

    :param metadata: string, the metadata from which the 'last updated' metadata field is to be updated.
    :param new_last_updated_value: string, the new value for the 'last updated' metadata field.
    :param use_today: boolean, if True, today's date is prepended to the new_last_updated_value. Default is True.
    :return: string, the updated metadata with the new 'last updated' value.
    """
    if use_today:
        date_today = datetime.now().strftime("%m-%d-%Y") # Assign today's date in format MM-DD-YYY
        new_last_updated_value = f"{date_today} {new_last_updated_value}"
    return set_metadata_field(metadata, 'last updated', new_last_updated_value)
def read_metadata_field_from_file(file_path, field):
    """
    Reads a specific metadata field from a file.

    :param file_path: string, the path to the file to be read.
    :param field: string, the metadata field to be read from the file.
    :return: tuple, the line number of the field and the value of the field.
    """
    metadata, _ = read_metadata_and_content(file_path)
    metadata_start = metadata.find('## metadata')
    metadata_end = metadata.find('##', metadata_start + len('## metadata'))
    if metadata_end == -1:  # If there's no second '##', use the end of the string
        metadata_end = len(metadata)
    metadata_selection = metadata[metadata_start:metadata_end].strip()
    field_search = f"{field}: "
    field_start = metadata_selection.find(field_search)
    if field_start != -1:
        field_line = metadata_selection[:field_start].count('\n') + 2  # +2 because we start counting from 1 and there's the '## metadata' line
        field_start += len(field_search)
        field_end = metadata_selection.find('\n', field_start)
        if field_end == -1:  # If it's the last field in the metadata
            field_end = len(metadata_selection)
        field_value = metadata_selection[field_start:field_end].strip()
        return field_line, field_value
    return None
def set_metadata_fields_from_csv(folder_path, csv_file_path, suffix_extension):
    """
    Sets metadata fields for all files in a folder based on a CSV file.

    :param folder_path: string of the path to the folder containing the files.
    :param csv_file_path: string of the path to the CSV file with metadata fields and values.
    :param suffix_extension: string of the file extension to be appended to file bases.
    :return: None, but prints the number of files processed successfully and the total in the CSV excluding empty rows.
    """
    # Read the CSV file and extract the metadata fields and values
    with open(csv_file_path, mode='r', encoding='utf-8') as csvfile:
        csv_reader = csv.reader(csvfile)
        metadata_fields = next(csv_reader)  # First row contains metadata field names
        metadata_values = [row for row in csv_reader if row]  # Remaining rows contain metadata values, excluding empty rows

    total_files_in_csv = len(metadata_values)  # Count only non-empty rows
    successfully_processed_files = 0

    # Iterate over each row in the CSV to update files
    for row_index, row in enumerate(metadata_values, start=1):  # Start counting rows from 1
        if len(row) < len(metadata_fields):  # Check if the row has enough columns
            print(f"Row {row_index} in CSV does not have enough columns. Expected {len(metadata_fields)}, got {len(row)}.")
            continue

        file_base = row[0] + suffix_extension
        file_path = os.path.join(folder_path, file_base)
        # Map fields to values
        metadata_dict = dict(zip(metadata_fields[1:], row[1:]))

        try:
            # Read the header and content from the file
            metadata, content = read_metadata_and_content(file_path)

            # Update the metadata fields from the CSV
            for field, value in metadata_dict.items():
                metadata = set_metadata_field(metadata, field, value)

            write_metadata_and_content(file_path, metadata, content, suffix_new='_temp', overwrite='yes')

            successfully_processed_files += 1
        except Exception as e:
            print(f"Failed to process file {file_base}: {e}")

    print(f"Total files in CSV excluding empty rows: {total_files_in_csv}")
    print(f"Successfully processed files: {successfully_processed_files}")
# TODO update the filename variables to follow our naming conventions
def create_csv_from_fields(folder_path, fields):
    """
    Generates a CSV file from all markdown files in a specified folder.

    :param folder_path: string, the path to the folder containing the markdown files.
    :param fields: list, the fields to be extracted from the markdown files.
    :return: string of the path to the created csv file.
    """
    # Generates a CSV file from all files in the specified folder
    folder_name = os.path.basename(os.path.normpath(folder_path))
    csv_filename = os.path.join(folder_path, f'{folder_name}.csv')

    # Check if the CSV file already exists and prompt for action
    if os.path.exists(csv_filename):
        user_input = input(f"The file {csv_filename} already exists. Overwrite? (y/n): ").strip().lower()
        if user_input == 'n':
            base, ext = os.path.splitext(csv_filename)
            csv_filename = f"{base}(1){ext}"

    with open(csv_filename, 'w', newline='') as csvfile:
        # Adjust field names by removing ":" and "#" and any leading/trailing spaces
        adjusted_fields = ['file_name', 'title'] + [field.strip().replace(':', '').replace('#', '') for field in fields]
        csv_writer = csv.DictWriter(csvfile, fieldnames=adjusted_fields)
        csv_writer.writeheader()

        # Iterate over each file in the folder
        for filename in sorted(os.listdir(folder_path)):
            if filename.endswith('.md'):  # Assuming markdown files
                file_path = os.path.join(folder_path, filename)
                with open(file_path, 'r') as file:
                    content = file.read()

                # Initialize a dictionary to store extracted data
                data = {'file_name': filename, 'title': os.path.splitext(filename)[0]}
                for field in fields:
                    adjusted_field = field.strip().replace(':', '').replace('#', '')
                    if field.endswith(':'):
                        # Field is a metadata line
                        match = re.search(rf'^{field}\s+(.*)', content, re.MULTILINE)
                        if match:
                            data[adjusted_field] = match.group(1).strip()
                    elif field.startswith('#'):
                        # Field is a markdown heading
                        heading_text = get_heading(file_path, field)
                        if heading_text:
                            # Remove the heading line itself
                            field_content = re.sub(rf'^{re.escape(field)}.*\n?', '', heading_text, flags=re.MULTILINE)
                            # Remove leading and trailing whitespace
                            field_content = field_content.strip()
                            # Remove multiple blank lines
                            field_content = re.sub(r'\n\s*\n', '\n', field_content)
                            data[adjusted_field] = field_content

                # Write the extracted data to the CSV
                csv_writer.writerow(data)

    print(f"CSV file created at {csv_filename}")
    return csv_filename
def create_csv_matrix_from_triples(triples_text, target_file_path):
    """
    Converts multiline text of triples into a csv matrix file where each entry is the number for that row and column.

    :param triples_text: string of multiline text containing rows of data separated by newlines, each row containing two strings and a number separated by commas.
    :param target_file_path: string of the path to the target csv file.
    :return: string of the path to the created csv file.
    """
    import csv
    from collections import defaultdict

    # Parse the triples text into a list of tuples
    triples = []
    for line in triples_text.strip().split('\n'):
        if line:
            items = line.split(', ')
            if len(items) != 3:
                raise ValueError(f"Line does not contain exactly three items: {line}")
            triples.append(items)

    # Extract unique row titles and column headers, and sort them
    row_titles = sorted(set(row[0] for row in triples), key=lambda s: s.lower())
    column_headers = sorted(set(row[1] for row in triples))

    # Create a default dictionary to hold the numbers, with a default of 0
    matrix = defaultdict(lambda: defaultdict(int))
    for row_title, col_header, number in triples:
        matrix[row_title][col_header] = int(number)

    # Write to CSV
    with open(target_file_path, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['row title'] + column_headers)
        row_count = 0
        for row_title in row_titles:
            row_data = [matrix[row_title][col_header] for col_header in column_headers]
            csv_writer.writerow([row_title] + row_data)
            row_count += 1

    print(f"CSV file with {row_count} rows created at {target_file_path}")
    return target_file_path

### JSON
def pretty_print_json_structure(json_file_path, level_limit=None, save_to_file=False):
    """
    Prints the structure of a JSON file and optionally saves it to a file with a '.pretty' extension.

    :param json_file_path: string of the path to the json file.
    :param level_limit: integer of the maximum level of nesting to print. None means no limit.
    :param save_to_file: boolean indicating whether to save the output to a file. defaults to true.
    :return: None.
    """
    # Define colors for different levels of JSON structure with high contrast
    colors = ['green', 'blue', 'red', 'magenta', 'yellow', 'white', 'grey']
    output_lines = []

    if not os.path.exists(json_file_path):
        warnings.warn(f"File {json_file_path} does not exist.")
        return

    def print_json_structure(data, indent=0, parent_key='', level=0):
        # Stop printing if the current level exceeds the level limit
        if level_limit is not None and level > level_limit:
            return

        # Select color based on the current level, cycling through the colors list
        color = colors[level % len(colors)]

        if isinstance(data, dict):
            for key in data:
                if isinstance(data[key], list):
                    # Print list information with the selected color
                    line = ' ' * indent + f"{key} (list of {len(data[key])} items)"
                    print(colored(line, color))
                    output_lines.append(line)
                    if data[key]:
                        print_json_structure(data[key][0], indent + 4, key, level + 1)
                else:
                    # Print dictionary keys with the selected color
                    line = ' ' * indent + str(key)
                    print(colored(line, color))
                    output_lines.append(line)
                    print_json_structure(data[key], indent + 4, key, level + 1)
        elif isinstance(data, list) and parent_key != '':
            if data:
                print_json_structure(data[0], indent, parent_key, level)

    with open(json_file_path, 'r') as file:
        data = json.load(file)
        print_json_structure(data)

    if save_to_file:
        output_file_path = json_file_path + '.pretty'
        with open(output_file_path, 'w') as output_file:
            for line in output_lines:
                output_file.write(line + '\n')
        print(f"Saved pretty printed JSON structure to {output_file_path}")
def write_json_file_from_object(json_object, file_path, overwrite="no"):
    """ 
    Writes a JSON object to a file at the specified path.

    :param json_object: dictionary or list to be written as JSON.
    :param file_path: string of the path where the JSON file will be written.
    :param overwrite: string of either "yes" or "no" to determine if existing files should be overwritten. default is "no".
    :return: None.
    """
    if overwrite not in ["yes", "no"]:
        raise ValueError("The 'overwrite' parameter must be 'yes' or 'no'.")

    if overwrite == "no" and os.path.exists(file_path):
        raise FileExistsError(f"The file {file_path} already exists and will not be overwritten.")

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as json_file:
        json.dump(json_object, json_file, indent=4)
def read_json_object_from_file(file_path):  # consider moving to fileops
    """ 
    Reads a JSON object from a file at the specified path.

    :param file_path: string of the path to the JSON file to be read.
    :return: dictionary or list representing the JSON object read from the file.
    """
    with open(file_path, 'r') as json_file:
        json_object = json.load(json_file)
    return json_object
