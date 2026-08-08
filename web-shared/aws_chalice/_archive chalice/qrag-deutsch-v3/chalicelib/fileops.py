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


# Override the default formatwarning
def custom_formatwarning(msg, category, filename, lineno, line=None):
    ''' DO NOT CALL - only used to define the custom format'''
    return f"{category.__name__}: {msg}\n"
# Set the warnings format to use the custom format
warnings.formatwarning = custom_formatwarning
# USAGE: warnings.warn(f"")

""" Naming Conventions:
last updated: SUBSTITITUE WHEN DONE WITH REFACTOR
see Coding Log - 2024 gdoc for WIP version
https://docs.google.com/document/d/1y2zuy5L15b_9KCleT1Fcw31q6yyWz-F7czJLVC0h678/edit?usp=sharing

"""
### INITIAL FUNCTIONS CALLED BY FLEX FILE OP AND FOLDER FUNCTIONS
def verbose_print(verbose, *messages):  # DS, cat 1a, unittests 6 (mocks print)
    """
    Helper function to pass on bool verbose and make verbose printing cleaner
    
    :param verbose: boolean for whether to print the messages.
    :param messages: tuple of variable-length argument list.
    :return: None

    :category: 1a non file function that only prints
    :heading: INITIAL FUNCTIONS CALLED BY FLEX FILE OP AND FOLDER FUNCTIONS
    :usage: verbose_print(verbose, f"ERROR in my_function: {e}")
    """
    if not isinstance(verbose, bool):
        raise TypeError("The first parameter 'verbose' must be of type bool.")
    if not messages:
        raise ValueError("At least one message must be provided.")
    if verbose:
        print(*messages)

def check_file_exists(file_path, operation_name):  # DS, cat 3a, unittests 2x2=4 (mock and real) - mocks isfile
    """
    Checks file existence and raises a ValueError if not found, which stops execution.

    :param file_path: string of file path which can be absolute or relative.
    :param operatrion_name: string of the message that the ValueError will print, typically the function name - optional message.
    :return: None

    :category: 3a non ffop file function
    :heading: INITIAL FUNCTIONS CALLED BY FLEX FILE OP AND FOLDER FUNCTIONS
    :usage: check_file_exists(cur_file_path, "my_func - optional message")
    """
    if not os.path.isfile(file_path):
        raise ValueError(f"VALUE ERROR in {operation_name}: input file does not exist for {file_path}")

def print_chars_with_indices(input_str, num_chars):  # DS, cat 1a, unittests 5 - mocks sys.stdout
    """ 
    Prints the first 'num_chars' characters of 'input_str' along with their indices.

    :param input_str: string to be printed.
    :param num_chars: number of characters to be printed from the input string.
    :return: None

    :category: 1a
    :heading: INITIAL FUNCTIONS CALLED BY FLEX FILE OP AND FOLDER FUNCTIONS
    :usage: print_chars_with_indices('Hello, World!', 5)
    """
    # Ensure num_chars is within the length of the string
    num_chars = min(num_chars, len(input_str))

    # Print the characters up to the specified num_chars
    print("\n")
    for char in input_str[:num_chars]:
        print(f"{char}  ", end="")
    print()  # Newline after the last character

    # Print the index below each character
    for i in range(num_chars):
        # Adjust spacing for single-digit indices
        space = "" if i == 0 else "  " if i < 11 else " "
        print(f"{space}{i}", end="")
    print()  # Newline after the last index
    
def get_suffix(file_str, delimiter="_"):  # DS, cat 1, unitests 15 - no mock
    """ 
    Extracts the suffix from a given file string based on a specified delimiter.

    :param file_str: string of the file name from which to extract the suffix.
    :param delimiter: string representing the delimiter used to separate the suffix from the rest of the file string. Default is "_".
    :return: string of the extracted suffix or None if no valid suffix is found.

    :category: 1
    :heading: INITIAL FUNCTIONS CALLED BY FLEX FILE OP AND FOLDER FUNCTIONS
    :usage: print(get_suffix('filename_suffix.txt', '_'))
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

def sub_suffix_in_str(file_str, suffix_sub, delimiter="_"):  # DS, cat 1, unitests 4 - need further testing of different delimters
    """ 
    Replaces the existing suffix in a file string with a new suffix.

    :param file_str: string of the file name from which to replace the suffix.
    :param suffix_sub: string of the new suffix to replace the existing one.
    :param delimiter: string representing the delimiter used to separate the suffix from the rest of the file string. Default is "_".
    :return: string of the file name with the replaced suffix or the original file string if no valid suffix is found.

    :category: 1
    :heading: INITIAL FUNCTIONS CALLED BY FLEX FILE OP AND FOLDER FUNCTIONS
    :usage: print(sub_suffix_in_str('filename_suffix.txt', '_newSuffix', '_'))
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

def remove_all_suffixes_in_str(file_str, delimiter="_"): # DS, cat 1, unitests 7 - no mock
    """ 
    Removes all suffixes from a given file string based on a specified delimiter while retaining the original file extension.

    :param file_str: string of the file name from which to remove all suffixes.
    :param delimiter: string representing the delimiter used to separate the suffixes from the rest of the file string. Default is "_".
    :return: string of the file name with all suffixes removed but with the original extension preserved.

    :category: 1
    :heading: INITIAL FUNCTIONS CALLED BY FLEX FILE OP AND FOLDER FUNCTIONS
    :usage: print(remove_all_suffixes_in_str('filename_suffix1_suffix2.txt', '_'))
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

def add_suffix_in_str(file_str, suffix_add):  # DS, cat 1, unitests 3 - no mock
    """ 
    Adds a suffix to a given file string.

    :param file_str: string of the file name to which the suffix will be added.
    :param suffix_add: string of the suffix to be added to the file string.
    :return: string of the file name with the added suffix.

    :category: 1
    :heading: INITIAL FUNCTIONS CALLED BY FLEX FILE OP AND FOLDER FUNCTIONS
    :usage: print(add_suffix_in_str('filename.txt', '_newSuffix'))
    """
    # Find the last occurrence of the file extension delimiter (.)
    extension_index = file_str.rfind('.')
    
    # If there is no extension, append the suffix to the end of the string
    if extension_index == -1:
        return file_str + suffix_add
    
    # Insert the suffix and delimiter before the extension
    return file_str[:extension_index] + suffix_add + file_str[extension_index:]

def handle_overwrite_prompt(file_path, file_path_opfunc, verbose=True):  # DS, cat 3a, unittests 4x2=8 (mock and real)
    """ 
    Handles user prompt for overwriting a file.

    :param file_path: string of the original file path.
    :param file_path_opfunc: string of the new file path.
    :param verbose: boolean for whether to print verbose messages. Default is True.
    :return: string of the path to the file that was kept.

    :category: 3a non ffop file function
    :heading: INITIAL FUNCTIONS CALLED BY FLEX FILE OP AND FOLDER FUNCTIONS
    :usage: print(handle_overwrite_prompt('path/to/original/file.txt', 'path/to/new/file.txt', True))
    """
    # Check if both files exist before proceeding
    check_file_exists(file_path, "handle_overwrite_prompt - original file")
    check_file_exists(file_path_opfunc, "handle_overwrite_prompt - new file")
    
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
            file_path_sub = sub_suffix_in_str(file_path, get_suffix(file_path_opfunc, "_"), delimiter="_")
            os.rename(file_path_opfunc, file_path_sub)
            return file_path_sub
        else:
            print("Invalid input. Please enter 'Y' for yes, 'N' for no, or 'S' to substitute suffix.")

def check_and_warn_file_overwrite(file_path):  # DS, cat 3a, unittests 2 - mocks isfile
    """ 
    Checks if a file already exists and issues a warning if it does.

    :param file_path: string representing the path of the file to be checked.
    :return: None

    :category: 3a non ffop file function
    :heading: INITIAL FUNCTIONS CALLED BY FLEX FILE OP AND FOLDER FUNCTIONS
    :usage: check_and_warn_file_overwrite('path/to/your/file.txt')
    """
    # Get the name of the calling function
    func_name = inspect.currentframe().f_back.f_code.co_name
    if os.path.isfile(file_path):
        warnings.warn(f"The function: {func_name} is overwriting a file that already exists, file: '{file_path}'")

def add_text_above_ffop(file_path, add_text, suffix_new="_addtextabove"):  # DS, cat 2a, unitests 3 - no mock (except warning)
    """ 
    Adds specified text above the existing content of a file and saves it with a new suffix.

    :param file_path: string of the path to the original file.
    :param add_text: string containing the text to be added above the existing content of the file.
    :param suffix_new: string of the suffix to be appended to the original filename for the new file. Defaults to "_addtextabove".
    :return: string of the path to the newly created file with the added text.

    :category: 2a flat ffop - does not call another ffop
    :heading: INITIAL FUNCTIONS CALLED BY FLEX FILE OP AND FOLDER FUNCTIONS
    :usage: add_text_above_ffop(cur_file_path, "New top line.\nAnd 2nd line")
    """

    # add_text is added above the current content of the file with a newline following the added text
    new_file_path = add_suffix_in_str(file_path, suffix_new)
    # Check if the new file already exists and print a warning if it does
    check_and_warn_file_overwrite(new_file_path)

    # Insert the add_text at the top of the file and save it as a new file
    with open(file_path, 'r') as src_file:
        original_content = src_file.read()
    with open(new_file_path, 'w') as dst_file:
        dst_file.write(add_text + '\n' + original_content)

    return new_file_path

### FLEX FILE OP AND FOLDER FUNCTIONS
""" do_ffop Purpose:
1) only for single file
2) error handling - file does not exist, (could add something like multiple extensions)
3) overwrite file - no, no-sub, yes, replace, replace-sub, prompt (yes/no/sub)

do_folder Purpose
1) for folder of many files (only accept a folder_path)
2) if there are subfolders in the folder_path, prompt user to include subfolders
3) include or exclude suffix files from folder (not both), 
4) calls do_ffop
5) overwrite argument is passed to do_ffop, first user selection will apply to all files
6) if error from file_op, ask user to continue or abort
"""

""" do_ffop Overwrite Logic Table:
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
"""

# If parent function is ffop (nested ffop), call the ffop inside the function without do_ffop and include 'suffix_new' as argument - review the TODO to reconsider forbidding overwrite default in a ffop in set_various_transcript_headings_ffop 
# If parent function is not ffop, call the ffop inside with do_ffop because the error checks need to be done. suffix_new and overwrite can be hardcoded or passed as args.
def do_ffop(ffop_func, file_path, *args, overwrite="no", verbose=False, **kwargs): # DS, unitests 12 - no mock (except input)
    """
    Performs a flexible file operation on a single file using the provided file operation function.
    The flexible file operation (ffop) must always return the path of the newly created file which has the suffix_new appended.
    This do_ffop handles the overwrite option which includes handling the new suffix.

    :param ffop_func: function name of the flexible file operation to be applied to the file.
    :param file_path: string of file path which can be absolute or relative.
    :param args: additional positional arguments to pass to the file operation function.
    :param overwrite: string that controls file overwriting. Defaults to "no". Also "yes", "no-sub", "replace", "replace-sub", "prompt" (yes, no, sub)
                        no              _orig + _orig_new
                        no-sub	        _orig + _new
                        replace	        _orig_new
                        replace-sub	    _new
                        yes	            _orig
                        prompt yes      _orig
                        prompt no       _orig + _orig_new
                        prompt sub	    _orig + _new
    :param verbose: boolean for printing verbose messages. Defaults to True.
    :param kwargs: additional keyword arguments to pass to the file operation function.
    :return: either the string of new_file_path or a tuple with that string as first element. depends on the overwrite argument. inherits absolute or relative from ffop_func.

    :category: 4 wrapper
    :heading: FLEX FILE OP AND FOLDER FUNCTIONS
    :usage: do_ffop(add_text_above_ffop, cur_file_path, "Here is the added first line.")
    """
    # print(f"DEBUG Verbose in do_ffop: {verbose}")
    # Check if 'verbose' is a valid parameter for the ffop_func
    params = inspect.signature(ffop_func).parameters
    if 'verbose' in params:
        kwargs['verbose'] = verbose
    verbose_print(verbose, f"\nRUNNING do_ffop with op function: {ffop_func}", f"FILE: {file_path}")
    check_file_exists(file_path, "do_ffop")
    
    try:
        result = ffop_func(file_path, *args, **kwargs)
        if isinstance(result, tuple):
            file_path_opfunc, *additional_values = result
        else:
            file_path_opfunc, additional_values = result, None

        if file_path_opfunc is None:
            raise ValueError("in do_ffop: return value of file operation function is None.")
        check_file_exists(file_path_opfunc, "do_ffop")

        # Overwrite logic
        file_path_new = None
        if overwrite.lower() == "no":
            verbose_print(verbose, "File operation with overwrite=no - keep original file and new file.")
            file_path_new = file_path_opfunc
        elif overwrite.lower() == "no-sub":
            verbose_print(verbose, "File operation with overwrite=no-sub - keep original file and new file with substituted suffix.")
            file_path_new = sub_suffix_in_str(file_path, get_suffix(file_path_opfunc, "_"), delimiter="_")
            os.rename(file_path_opfunc, file_path_new)
        elif overwrite.lower() == "replace":
            verbose_print(verbose, "File operation with overwrite=replace - replace original file with new file.")
            os.remove(file_path)
            file_path_new = file_path_opfunc
        elif overwrite.lower() == "replace-sub":
            verbose_print(verbose, "File operation with overwrite=replace-sub - replace original file with new file with substituted suffix.")
            file_path_new = sub_suffix_in_str(file_path, get_suffix(file_path_opfunc, "_"), delimiter="_")
            os.remove(file_path)
            os.rename(file_path_opfunc, file_path_new)
        elif overwrite.lower() == "yes":
            verbose_print(verbose, "File operation with overwrite=yes - overwrite original file.")
            os.remove(file_path)
            os.rename(file_path_opfunc, file_path)
            file_path_new = file_path
        elif overwrite.lower() == "prompt":
            file_path_new = handle_overwrite_prompt(file_path, file_path_opfunc, verbose)
        else:
            valid_options = ['no', 'no-sub', 'replace', 'replace-sub', 'yes', 'prompt']
            raise ValueError(f"VALUE ERROR in do_ffop: invalid overwrite argument: '{overwrite}'. Valid options are: {', '.join(valid_options)}")

        return (file_path_new,) + tuple(additional_values) if additional_values else file_path_new

    except Exception as e:
        verbose_print(verbose, f"ERROR in do_ffop: {e}")
        raise  # Re-raise the exception to propagate it

def get_files_in_folder(folder_path, suffix_include=None, suffix_exclude=None, include_subfolders=False):  # DS, unittests 7 - no mock
    """
    Retrieves a list of file paths from the specified folder, optionally filtering by suffix and including subfolders.

    EXTENSIONS ARE IGNORED

    :param folder_path: string of the path to the folder from which to retrieve files.
    :param suffix_include: string of the suffix that included files must have.
    :param suffix_exclude: string of the suffix that files must not have to be included.
    :param include_subfolders: boolean indicating whether to include files from subfolders.
    :return: list of strings of the file paths that meet the specified criteria.

    :category: 3b any non any non file function - that is not a wrapper
    :heading: FLEX FILE OP AND FOLDER FUNCTIONS
    :usage: print(get_files_in_folder(cur_folder, suffix_include='_prepqa'))
    """
    if not os.path.isdir(folder_path):
        raise ValueError(f"VALUE ERROR in get_files_in_folder: folder does not exist.")
    if suffix_include is not None and suffix_exclude is not None:
        raise ValueError("in get_files_in_folder: Both suffix_include and suffix_exclude are provided.")
    
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
            # Suffix handling
            file_suffix = get_suffix(file_path)
            if suffix_include and not file_suffix == suffix_include:
                continue
            if suffix_exclude and file_suffix == suffix_exclude:
                continue
            filtered_file_paths.append(file_path)
    
    return filtered_file_paths

def do_ffop_on_folder(ffop_func, folder_path, *args, overwrite="no", suffix_include=None, suffix_exclude=None, include_subfolders=False, verbose=False, **kwargs):  # DS, unitests 10 - no mock
    """
    Applies a flexible file operation function to all files in a specified folder.

    :param ffop_func: function name of the flexible file operation to be applied to the file.
    :param folder_path: string of the path to the folder from which to retrieve files.
    :param args: additional arguments to pass to the file operation function.
    :param overwrite: string that controls file overwriting. Defaults to 'no'. Options are 'no', 'no-sub', 'replace', 'replace-sub', 'yes', 'prompt'.
    :param suffix_include: string of the suffix that included files must have.
    :param suffix_exclude: string of the suffix that files must not have to be included.
    :param include_subfolders: boolean of whether to include files from subfolders.
    :param verbose: boolean for printing verbose messages. Defaults to True.
    :param kwargs: additional keyword arguments to pass to the file operation function.
    :return: the number of files processed.

    :category: 4 wrapper
    :heading: FLEX FILE OP AND FOLDER FUNCTIONS
    :usage: do_ffop_on_folder(add_text_above_ffop, cur_folder, "HERE", overwrite="yes")
    """
    print(f"DEBUG Verbose in do_ffop_on_folder: {verbose}")
    verbose_print(verbose, f"\nRUNNING do_ffop_on_folder with ffop {ffop_func}", f"FOLDER: {folder_path}")
    
    # Call get_files_in_folder to retrieve the list of files - it handles 2 errors
    file_paths = get_files_in_folder(folder_path, suffix_include=suffix_include, suffix_exclude=suffix_exclude, include_subfolders=include_subfolders)
    
    processed_files_count = 0
    for file_path in file_paths:
        # Call do_ffop for each file, passing overwrite options
        kwargs['verbose'] = verbose  # Ensure verbose is explicitly included in kwargs
        do_ffop(ffop_func, file_path, *args, overwrite=overwrite, **kwargs)
        processed_files_count += 1

    if verbose:
        verbose_print(verbose, f"Total files run with do_ffop: {processed_files_count}")
    
    return processed_files_count

def any_func_on_folder(any_func, folder_path, *args, suffix_include=None, suffix_exclude=None, include_subfolders=False, verbose=False, **kwargs):  # DS, unitests 5 - no mock
    """
    Applies a specified function to each file in a folder.
    The function any_func must operate on a single file.
    If it needs the folder name, that can be extracted from the file path.
    If it's creating or writing to another file, that filename or path can be given as another argument.

    :param any_func: function name to apply to each file.
    :param folder_path: string of the path to the folder from which to retrieve files.
    :param args: additional arguments to pass to the function.
    :param suffix_include: string of the suffix that included files must have.
    :param suffix_exclude: string of the suffix that files must not have to be included.
    :param include_subfolders: boolean of whether to include files from subfolders.
    :param verbose: boolean for printing verbose messages. Defaults to True.
    :param kwargs: additional keyword arguments to pass to the function.
    :return: a dictionary with file paths as keys and function return values as values.

    :category: 4 wrapper
    :heading: FLEX FILE OP AND FOLDER FUNCTIONS
    :usage: print(any_func_on_folder(my_any_func, cur_folder))
    """
    verbose_print(verbose, f"\nRUNNING any_func_on_folder with {any_func}", f"FOLDER: {folder_path}")

    # Call get_files_in_folder to retrieve the list of files - it handles errors
    results = {}  # Dictionary to store file names and function return values
    file_paths = get_files_in_folder(folder_path, suffix_include=suffix_include, suffix_exclude=suffix_exclude, include_subfolders=include_subfolders)
    verbose_print(verbose, f"NUMBER OF FILES RUN with any_func_on_folder: {len(file_paths)}")
    
    results = {}
    for file_path in file_paths:
        try:
            result = any_func(file_path, *args, verbose=verbose, **kwargs)  # Try passing verbose
        except TypeError:
            result = any_func(file_path, *args, **kwargs)  # Fallback if verbose is not accepted
        results[file_path] = result

    return results


### TIME AND TIMESTAMP SUPPORT FUNCTIONS
def convert_seconds_to_timestamp(seconds):  # DS, cat 1, unitests 8
    """ 
    Converts a given number of seconds into a timestamp in the format hh:mm:ss or mm:ss.

    :param seconds: integer or float representing the number of seconds to be converted.
    :return: string representing the timestamp in the format hh:mm:ss or mm:ss.

    :category: 1
    :heading: TIME AND TIMESTAMP SUPPORT FUNCTIONS
    :usage: print(convert_seconds_to_timestamp(3661))
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

def convert_timestamp_to_seconds(timestamp):  # DS, cat 1, unitests 8
    """ 
    Converts a timestamp in the format hh:mm:ss or mm:ss into seconds.

    :param timestamp: string representing the timestamp in the format hh:mm:ss or mm:ss.
    :return: integer representing the total number of seconds.

    :category: 1
    :heading: TIME AND TIMESTAMP SUPPORT FUNCTIONS
    :usage: print(convert_timestamp_to_seconds('01:23:45'))
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

def change_timestamp(timestamp, delta_seconds):  # DS, cat 1, unitests 6
    """ 
    Changes a given timestamp by a specified number of seconds. Uncomment line in tune_timestamp

    :param timestamp: string representing the timestamp in the format hh:mm:ss or mm:ss.
    :param delta_seconds: integer representing the number of seconds to change the timestamp by.
    :return: string representing the new timestamp after the change.

    :category: 1
    :heading: TIME AND TIMESTAMP SUPPORT FUNCTIONS
    :usage: timestamp = change_timestamp(timestamp, -20)
    """
    if timestamp is None:
        raise ValueError("No timestamp provided. Cannot change timestamp.")
    modified_seconds = convert_timestamp_to_seconds(timestamp) + delta_seconds
    if modified_seconds < 0: 
        raise ValueError("Resulting time cannot be less than zero.")
    return convert_seconds_to_timestamp(modified_seconds)

def tune_timestamp(timestamp):  # DS, cat 1, unitests 5
    """ 
    Converts a given timestamp to a standard format with respect to digits and leading zeros.

    :param timestamp: string representing the timestamp in the format hh:mm:ss or mm:ss.
    :return: string representing the tuned timestamp or None if the input timestamp is None.

    :category: 1
    :heading: TIME AND TIMESTAMP SUPPORT FUNCTIONS
    :usage: print(tune_timestamp('01:23:45'))
    """
    # convert a timestamp to our standard with respect to digits and leading zeros
    if timestamp is None: # not sure if it was intentional to not raise ValueError but leave it
        return None
    # timestamp = change_timestamp(timestamp, 0)  # CAUTION - only include to shift the timestamps
    secs = convert_timestamp_to_seconds(timestamp)
    tuned_timestamp = convert_seconds_to_timestamp(secs)
    #print(f"Original timestamp: '{timestamp}'  Tuned timestamp: '{tuned_timestamp}'") 
    return tuned_timestamp

def get_timestamp(line, print_line=False, max_words=8):  # DS, cat 1, unitests 7
    """ 
    Extracts a timestamp from a given line of text.

    :param line: string representing the line of text to search for a timestamp.
    :param print_line: boolean indicating whether to print the line where the timestamp was found. Default is False.
    :param max_words: integer representing the maximum number of words allowed before and after the timestamp. Default is 5.
    :return: tuple containing the extracted timestamp as a string and its index in the line, or (None, None) if no valid timestamp is found.

    :category: 1
    :heading: TIME AND TIMESTAMP SUPPORT FUNCTIONS
    :usage: print(get_timestamp('This is a test line with timestamp 01:23:45', True, 5))
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

def get_current_datetime_humanfriendly(timezone='America/Los_Angeles', include_timezone=True):  # DS, cat 1, unittests 4
    """
    Returns the current date and time as a string for a given timezone, optionally including the timezone abbreviation and UTC offset.

    :param timezone: string representing the timezone to use for the current time.
    :param include_timezone: boolean indicating whether to include the timezone abbreviation and UTC offset in the returned string.
    :return: string representing the current date and time in the specified timezone, optionally followed by the timezone abbreviation and UTC offset.
    
    :category: 1
    :heading: TIME AND TIMESTAMP SUPPORT FUNCTIONS
    :usage: print(get_current_datetime_humanfriendly())  # expected 2024-05-04 05:55:56    2024-05-04 05:55:56 PDT UTC-07:00
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
def get_current_datetime_filefriendly(location='America/Los_Angeles', include_utc=False):  # DS, cat 1
    """
    Returns the current date and time as a filename-friendly string for a given timezone, optionally including only the UTC offset.

    :param location: string representing the timezone to use for the current time.
    :param include_utc: boolean indicating whether to include the UTC offset in the returned string.
    :return: string representing the current date and time in the specified timezone, formatted for filenames, optionally followed by the UTC offset.
    
    :category: 1
    :heading: TIME AND TIMESTAMP SUPPORT FUNCTIONS
    :usage: print(get_current_datetime_filefriendly())  # expected  2024-05-04_055556     2024-05-04_055556_UTC-0700
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

    :category: 1
    :heading: TIME AND TIMESTAMP SUPPORT FUNCTIONS
    :usage: print(convert_to_epoch_seconds("2024-03-07 06:52:18 -0700"))
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

def get_elapsed_seconds(start_time_epoch_seconds):  # DS, cat 1, unittests 3
    '''
    Calculates the time elapsed since the start_time and returns it in seconds.

    :param start_time: float, the start time in seconds since the epoch (as returned by time.time())
    :param return_format: string ('minutes' or 'timestamp') for the return value format - 'timestamp' for H:MM:SS or minutes with one decimal place
    :return: integer of the number of seconds
    
    :category: 1
    :heading: TIME AND TIMESTAMP SUPPORT FUNCTIONS
    :usage: print(get_elapsed_time(convert_to_epoch_seconds("2024-03-07 06:52:18 PST")))
    '''
    from primary.fileops import convert_seconds_to_timestamp, convert_timestamp_to_seconds, tune_timestamp
    
    current_time = time.time()
    return int(round(current_time - start_time_epoch_seconds))


### READ AND METADATA FUNCTIONS
def read_complete_text_from_file(file_path):  # DS, cat 3a, unitests 2
    """ 
    Reads the entire text from a file.

    :param file_path: string of the file path which can be absolute or relative.
    :return: string of the complete text read from the file.

    :category: 3a non ffop file function
    :heading: READ AND METADATA FUNCTIONS
    :usage: print(read_complete_text_from_file('path/to/your/file.txt'))
    """
    if not os.path.exists(file_path):
        raise ValueError(f"The file path does not exist for {file_path}")
    with open(file_path, 'r') as file:
        complete_text = file.read()
    return complete_text

""" METADATA AND HEADER NOTES
The definition of metadata and headers is a bit confusing and could probably be improved. But for now here it is:
The metadata typically includes information such as the title, author, and timestamps.
The header contains this structured metadata and is separated from the main content by a delimiter which is currently '## content'.
So the header, as it's defined, contains the delimiter '## content' which is why for the add_metadata_field you cannot just add to the end of the header.
The relationship between the metadata, header, and content is pivotal, as it dictates how the data is parsed and processed.
Changes to this structure could have far-reaching implications for the parsing logic and downstream processes.
Therefore, any modifications to the metadata and header handling should be considered carefully to maintain compatibility with existing systems and to facilitate future enhancements.

All that being said, what we can consider doing is changing the structure to be metadata and content and eliminating the concept of the header. Then the metadata would start out with the markdown heading lines '## metadata' and the content would start out with '## content'. All the functions of process metadata and content would just need to ignore those heading lines. I think they already would for the most part. But that would need to be checked.
"""
def split_header_and_content(text, delimiter):  # DS, cat 1, unitests 5
    """ 
    Splits the given text into header and content based on the provided delimiter.

    :param text: string, the text to be split into header and content.
    :param delimiter: string, the delimiter used to split the text.
    :return: tuple, the header and content as two separate strings.

    :category: 1
    :heading: READ AND METADATA FUNCTIONS
    :usage: header, content = split_header_and_content(text, delimiter)
    """
    # Extracts header and content from text using delimiter, trims leading blank lines from content
    # Header includes the blank line, delimiter, and any trailing blank links '\n\n## content\n\n'
    text_index = text.find(delimiter)
    header = ""
    content = text
    if text_index != -1:
        header_end_index = text.find('\n', text_index)
        if header_end_index == -1:  # If no newline is found, set the end index to the end of the text
            header_end_index = len(text)
        else:
            header_end_index += 1  # Include the newline character in the header
        header = text[:header_end_index].strip() + "\n\n"  # convention is one blank line after ## content, not 2
        content = text[header_end_index:].lstrip('\n') # convention is for content to start with the text not '## content\n\n'
    # print("DEBUG split_header_and_content")
    # print(repr(header))
    return header, content

def read_header_and_content_from_file(file_path, delimiter="## content"):  # DS, cat 3a, unitests 3
    """ 
    Reads a file and splits its content into header and content based on a provided delimiter.

    :param file_path: string, the path to the file to be read.
    :param delimiter: string, the delimiter used to split the file content into header and content. Default is '## content'.
    :return: tuple, the header and content as two separate strings.

    :category: 3a non ffop file function
    :heading: READ AND METADATA FUNCTIONS
    :usage: header, content = read_header_and_content_from_file('path/to/your/file.txt', '## content')
    """
    if not os.path.exists(file_path):
        raise ValueError(f"The file path does not exist for {file_path}")
    with open(file_path, 'r') as file:
        text = file.read() 
    return split_header_and_content(text, delimiter)

def read_metadata_field_from_file(file_path, field):  # DS, cat 3a, unittest 3
    """ 
    Reads a specific metadata field from a file.

    :param file_path: string, the path to the file to be read.
    :param field: string, the metadata field to be read from the file.
    :return: tuple, the line number of the field and the value of the field.

    :category: 3a non ffop file function
    :heading: READ AND METADATA FUNCTIONS
    :usage: line, value = read_metadata_field_from_file('path/to/your/file.txt', 'desired_field')
    """
    header, _ = read_header_and_content_from_file(file_path, delimiter="## content")
    metadata_start = header.find('## metadata')
    metadata_end = header.find('##', metadata_start + len('## metadata'))
    metadata_content = header[metadata_start:metadata_end].strip()
    field_search = f"{field}: "
    field_start = metadata_content.find(field_search)
    if field_start != -1:
        field_line = metadata_content[:field_start].count('\n') + 1
        field_start += len(field_search)
        field_value = metadata_content[field_start:].split('\n', 1)[0].strip()
        return field_line, field_value
    # DONE fill in code to start searching input text 'header' from '## metadata' until next '##'
    # DONE fill in code to search for string field followed by ': ' then extract characters that follow before a newline


### WRITE FUNCTIONS        
def write_complete_text_ffop(file_path, complete_text, suffix_new="_writecompletetext"):  # DS, cat 2a, unittests 3
    """ 
    Writes the complete text to a new file with a specified suffix.

    :param file_path: string, the path to the original file.
    :param complete_text: string, the complete text to be written to the new file.
    :param suffix_new: string, the suffix to be appended to the original filename for the new file. Default is "_writecompletetext".
    :return: string, the path to the newly created file.

    :category: 2a flat ffop - does not call another ffop
    :heading: WRITE FUNCTIONS 
    :usage: new_file_path = write_complete_text_ffop('path/to/your/file.txt', 'Your complete text', '_newsuffix')
    """
    new_file_path = add_suffix_in_str(file_path, suffix_new)
    # Check if the new file already exists and print a warning if it does
    check_and_warn_file_overwrite(new_file_path)
    
    with open(new_file_path, "w") as file:
        file.write(complete_text)
    return new_file_path

def write_header_and_content_ffop(file_path, header, content, suffix_new="_writeheaderandcontent"):  # DS, cat 2a, unittests 3
    """ 
    Writes a header and content to a new file with a specified suffix.

    :param file_path: string, the path to the original file.
    :param header: string, the header to be written to the new file.
    :param content: string, the content to be written to the new file.
    :param suffix_new: string, the suffix to be appended to the original filename for the new file. Default is "_writeheaderandcontent".
    :return: string, the path to the newly created file.

    :category: 2a flat ffop - does not call another ffop
    :heading: WRITE FUNCTIONS 
    :usage: new_file_path = write_header_and_content_ffop('path/to/your/file.txt', 'Your header', 'Your content', '_newsuffix')
    """
    new_file_path = add_suffix_in_str(file_path, suffix_new)
    # Check if the new file already exists and print a warning if it does
    check_and_warn_file_overwrite(new_file_path)

    # Assume delimiter and trailing balnk line is already included in header
    complete_text = header + content

    with open(new_file_path, "w") as file:
        file.write(complete_text)
    return new_file_path


### MISC FILE FUNCTIONS
def rename_file(file_path, new_filebase):  # DS, cat 3a, unittest 3 - mocks
    """
    Renames the file base portion for the file given at the argument file path.

    :param file_path: string, the path to the file to be renamed.
    :param new_filebase: string, the new base name for the file without the extension.
    :return: string, the new file path after renaming, or an error if the operation fails.

    :category: 3a
    :heading: MISC FILE FUNCTIONS
    :usage: new_file_path = rename_file('path/to/your/oldfile.txt', 'newfile')
    """
    # Check if the original file exists
    if not os.path.isfile(file_path):
        raise ValueError(f"The file does not exist: {file_path}")

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

def delete_file(file_path):  # DS, cat 3a, omit unittests - simple os.remove call
    """ 
    Deletes a file at the specified file path.

    :param file_path: string, the path to the file to be deleted.
    :return: None. The function does not return any value.

    :category: 3
    :heading: MISC FILE FUNCTIONS
    :usage: delete_file('path/to/your/file.txt')
    """
    try:
        os.remove(file_path)
        return True  # Return True if the file was successfully deleted
    except OSError as e:
        return e  # Return the exception if an error occurred

def delete_files_with_suffix(folder, suffix_include, verbose=False):  # DS, cat 3e, omit unittests
    """ 
    Deletes all files in a given folder that end with a specified suffix.

    :param folder_path: string, the path to the folder where files are to be deleted.
    :param suffix_include: string, the suffix of the files to be deleted.
    :param verbose: boolean, if True, the function will print verbose messages. Default is False.
    :return: None. The function does not return any value.

    :category: 3e
    :heading: MISC FILE FUNCTIONS
    :usage: delete_files_with_suffix('path/to/your/folder', '.txt')
    """
    # Use any_func_on_folder to delete files
    return any_func_on_folder(delete_file, folder, suffix_include=suffix_include, include_subfolders=False, verbose=verbose)

def move_file(file_path, destination_folder): # cat 3a, unittest 3 - mocks
    """
    Moves a file to the specified destination folder.

    :param file_path: string, the path to the file to be moved.
    :param destination_folder: string, the path to the destination folder.
    :return: string, the new file path after moving, or an error if the operation fails.

    :category: 3a
    :heading: MISC FILE FUNCTIONS
    :usage: new_file_path = move_file('path/to/your/oldfile.txt', 'path/to/your/destination/folder')
    """
    # Check if the original file exists
    if not os.path.isfile(file_path):
        raise ValueError(f"The file does not exist: {file_path}")

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

def move_files_with_suffix(source_folder, destination_folder, suffix_include, verbose=False): # DS, cat 3e, omit unittest
    """
    Moves all files in a given folder that end with a specified suffix to the destination folder.

    :param source_folder: string, the path to the source folder where files are to be moved from.
    :param destination_folder: string, the path to the destination folder where files are to be moved to.
    :param suffix_include: string, the suffix of the files to be moved.
    :param verbose: boolean, if True, the function will print verbose messages. Default is False.
    :return: list, the new file paths after moving, or an error if the operation fails.

    :category: 3e
    :heading: MISC FILE FUNCTIONS
    :usage: move_files_with_suffix('path/to/your/source/folder', 'path/to/your/destination/folder', '.txt')
    """
    # Use any_func_on_folder to move files
    return any_func_on_folder(move_file, source_folder, destination_folder, suffix_include=suffix_include, include_subfolders=False, verbose=verbose)

def tune_title(title):  # DS, cat 1, unittests 9
    """ 
    Removes any special characters from the given title.

    :param title: string, the title from which special characters are to be removed.
    :return: string, the updated title with special characters removed.

    :category: 1
    :heading: MISC FILE FUNCTIONS
    :usage: print(tune_title('Your Title Here'))
    """
    # Remove any special characters from title_filename
    return re.sub(r'[^\w\s\-\(\)\.]', '', title)

def create_full_path(title_or_path, new_suffix_ext, default_folder=None):  # DS, cat 1, unittests 10
    """ 
    Creates a full file path from a given title or path, a new suffix extension, and an optional default folder.

    :param title_or_path: string, the title or path of the file.
    :param new_suffix_ext: string, the new suffix extension to be added to the file.
    :param default_folder: string, the default folder to be used if no folder is specified in title_or_path. Default is None.
    :return: string, the newly created full file path.

    :category: 1
    :heading: MISC FILE FUNCTIONS
    :usage: print(create_full_path('your_file', '.txt', '/path/to/your/folder'))
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

def find_file_in_folders(file_path, folder_paths):  # DS, cat 3a, unittests 3
    """ 
    Searches for a file within a list of folder paths and returns the first match.

    :param file_path: string of the file name to search for.
    :param folder_paths: list of strings of folder paths where the file will be searched.
    :return: string of the full path to the file if found, otherwise None.

    :category: 3a non ffop file operation
    :heading: MISC FILE FUNCTIONS
    :usage: found_path = find_file_in_folders('example.txt', ['/path/to/folder1', '/path/to/folder2'])
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

def copy_file_and_append_suffix(file_path, suffix_new):  # DS, cat 3a, unittests 2
    """ 
    Copies the file to a new location with a new suffix added before the file extension.

    :param file_path: string of the path to the original file.
    :param suffix_new: string of the suffix to be appended to the original filename before the file extension.
    :return: string of the path to the newly created file with the new suffix.

    :category: 3a non ffop file function
    :heading: WRITE FUNCTIONS
    :usage: print(copy_file_and_append_suffix('path/to/your/file.txt', '_backup'))
    """
    # Check if the original file exists
    if not os.path.isfile(file_path):
        raise ValueError(f"the file does not exist: {file_path}")

    # Split the file path into directory, base name, and extension
    file_dir, file_base = os.path.split(file_path)
    file_name, file_ext = os.path.splitext(file_base)

    # Create the new file path with the suffix added before the file extension
    new_file_base = f"{file_name}{suffix_new}{file_ext}"
    new_file_path = os.path.join(file_dir, new_file_base)

    # Copy the original file to the new file path
    shutil.copy(file_path, new_file_path)

    return new_file_path

def sub_suffix_in_file(file_path, suffix_new):  # DS, cat 3a, unittests 5 - mocks temps
    """ 
    Substitutes the suffix in the file name of the given file path with a new suffix.
    If new_suffix is empty '' then it will remove the last suffix of the file.

    :param file_path: string, the path to the original file.
    :param suffix_new: string, the new suffix to replace the existing one in the file name.
    :return: string, the path to the newly created file with the substituted suffix.

    :category: 3a non ffop file function
    :heading: WRITE FUNCTIONS
    :usage: print(sub_suffix_in_file('path/to/your/file.txt', '_newSuffix'))
    """
    # Check if the original file exists
    if not os.path.isfile(file_path):
        raise ValueError(f"The file does not exist: {file_path}")

    # Split the file path into directory, base name, and extension
    file_dir, file_base = os.path.split(file_path)
    file_name, file_ext = os.path.splitext(file_base)

    # Substitute the suffix in the file name using the sub_suffix_in_str function
    new_file_base = sub_suffix_in_str(file_name + file_ext, suffix_new)
    new_file_path = os.path.join(file_dir, new_file_base)

    # Rename the original file to the new file path
    os.rename(file_path, new_file_path)

    return new_file_path

def count_suffixes_in_folder(folder_path):  # DS, cat 3e, unittest 3 - mocks temps
    """ 
    Analyzes all the files in the specified folder and prints the number of files for each unique suffix, alphabetized.

    :param folder_path: string of the folder path to search for files and analyze suffixes.
    :return: None. The function prints the suffixes and their counts.

    :category: 3e non ffop file operation on folder
    :heading: MISC FILE FUNCTIONS
    :usage: get_suffixes_in_folder('/path/to/folder')
    """
    if not os.path.isdir(folder_path):
        raise ValueError(f"the directory does not exist: {folder_path}")

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

def zip_files_in_folders(folder_paths, suffix_include, zip_file_path, include_subfolders=True):
    """
    Zips files in the specified folders that match the given suffix into a single zip file.

    :param folder_paths: list of strings, the paths to the folders where files will be zipped.
    :param suffix_include: string, the suffix that included files must have.
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
                            if file_name.endswith(suffix_include):
                                file_path = os.path.join(root, file)
                                # Preserve the folder structure relative to the folder path
                                arcname = os.path.relpath(file_path, start=os.path.dirname(folder_path))
                                zipf.write(file_path, arcname)
                else:
                    # Only include files from the top-level directory
                    for file in os.listdir(folder_path):
                        if file.endswith(suffix_include) and os.path.isfile(os.path.join(folder_path, file)):
                            file_path = os.path.join(folder_path, file)
                            zipf.write(file_path, file)
            else:
                print(f"Folder does not exist: {folder_path}")

    print(f"Created zip at {zip_file_path} containing files from folders: {folder_paths}")



### TIMESTAMP LINKS FILE FUNCTIONS
def remove_timestamp_links_from_content(content):  # DS, cat 1, unittests 4
    """ 
    Removes markdown timestamp links from the content and returns the modified content.

    :param content: string of the content from which to remove markdown timestamp links.
    :return: string of the content with markdown timestamp links removed.

    :category: 1
    :heading: TIMESTAMP LINKS FILE FUNCTIONS
    :usage: print(remove_timestamp_links_from_content(content))
    """
    content_lines = content.splitlines()
    processed_lines = [re.sub(r'\[(.*?)\]\(.*?\)', r'\1', line) for line in content_lines]
    return '\n'.join(processed_lines)+"\n"  # explicitly add extra newline to avoid stripping one

def remove_timestamp_links_ffop(file_path, suffix_new="_removetimestamplinks"):  # DS, cat 2b, unittests 2 - could add more
    """ 
    Adds specified text above the existing content of a file and saves it with a new suffix.
    No need for the new_file_path or the warning check because another ffop is called below

    :param file_path: string of the path to the original file.
    :param suffix_new: string of the suffix to be appended to the original filename for the new file. Defaults to "_addtextabove".
    :return: string of the path to the newly created file with the added text.

    :category: 2b nested ffop - calls write_header_and_content_ffop without do_ffop
    :heading: ### TIMESTAMP LINKS FILE FUNCTIONS
    :usage: remove_file_path = do_ffop(remove_timestamp_links_ffop, cur_file_path, overwrite="no")
    """
    header, content = read_header_and_content_from_file(file_path, delimiter="## content")
    new_content = remove_timestamp_links_from_content(content)
    return write_header_and_content_ffop(file_path, header, new_content, suffix_new)
    # notice this call is with the original file_path and the suffix_new, not a new_file_path

def generate_timestamp_link(base_link, timestamp):  # DS, cat 1, unittests 4
    """
    Helper function to generate a timestamp link for a given base link and timestamp.
    It uses a dictionary to map domains to their respective timestamp formats.
    For Vimeo, the timestamp is converted to milliseconds.
    
    :param base_link: string of the base URL to which the timestamp will be appended.
    :param timestamp: string of the timestamp to be converted and appended to the base URL.
    :return: string of the complete URL with the timestamp appended in the appropriate format.

    :category: 1
    :heading: ### TIMESTAMP LINKS FILE FUNCTIONS
    :usage: print(generate_timestamp_link('https://www.youtube.com/watch?v=dQw4w9WgXcQ', '1:30'))
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

def add_timestamp_links_to_content(content, base_link):  # DS, cat 1, unittests 7
    """ 
    Adds timestamp links to the content using the provided base link.

    :param content: string of the content where timestamp links will be added.
    :param base_link: string of the base URL to which the timestamp will be appended.
    :return: string of the content with timestamp links added.

    :category: 1
    :heading: TIMESTAMP LINKS FILE FUNCTIONS
    :usage: print(add_timestamp_links_to_content('Here is some content with timestamps.', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'))
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

def add_timestamp_links_ffop(file_path, suffix_new="_addtimestamplinks"):  # DS, cat 2b, unittests 3
    """ 
    Adds timestamp links to the content of a file.

    :param file_path: string, the path to the file where timestamp links will be added.
    :param suffix_new: string, the suffix to be appended to the original filename for the new file. Default is "_addtimestamplinks".
    :return: string, the path to the newly created file with timestamp links added.

    :category: 2b nested ffop - calls write_header_and_content_ffop without do_ffop
    :heading: TIMESTAMP LINKS FILE FUNCTIONS
    :usage: print(add_timestamp_links_ffop('path/to/your/file.txt', '_newsuffix'))
    """
    # no need for the new_file_path or the warning check because another ffop is called below
    header, content = read_header_and_content_from_file(file_path, delimiter="## content")
    _, base_link = read_metadata_field_from_file(file_path, "link")
    
    # First, remove any existing timestamp links from the content
    content_without_links = remove_timestamp_links_from_content(content)
    # Then, add new timestamp links to the content
    new_content = add_timestamp_links_to_content(content_without_links, base_link)


    # Write the processed content back to the new file path
    return write_header_and_content_ffop(file_path, header, new_content, suffix_new)
    # notice this call is with the original file_path and the suffix_new, not a new_file_path

def compare_files_text(file1_path, file2_path):  # DS, cat 3, omit unittests - used for mtest of remove and add timestamp links
    """ 
    Compares the content of two files.

    :param file1_path: string, the path to the first file to be compared.
    :param file2_path: string, the path to the second file to be compared.
    :return: boolean, True if the content of the files is exactly the same, False otherwise.

    :category: 3
    :heading: TIMESTAMP LINKS FILE FUNCTIONS
    :usage: print(compare_files_text('path/to/your/first_file.txt', 'path/to/your/second_file.txt'))
    """
    text1 = read_complete_text_from_file(file1_path)
    text2 = read_complete_text_from_file(file2_path)
    if text1 == text2:
        print("TRUE for compare_file_text - the content of the files is exactly the same.")
        return True
    else:
        print("FALSE for compare_file_text - the content of the files is different.")
        return False


### CONTENT PROCESSING
def count_num_instances(file_path, find_str):  # DS, cat 3a, unittest 4
    """
    Counts the number of instances of a specific string in the text of the file.
    Is case-sensitive.

    :param file_path: string, the path to the file where the search will be performed.
    :param find_str: string, the string to find in the file content.
    :return: int, the number of instances found, or zero if no instances are found.
    
    :category: 3a non ffop file function
    :heading: CONTENT PROCESSING
    :usage: if count_num_instances(file_path) > 0:
    """
    complete_text = read_complete_text_from_file(file_path)
    count = complete_text.count(find_str)
    print(f"Number instances: {count} of {find_str} found in {file_path}")
    return count

def find_and_replace_ffop(file_path, find_str, replace_str, content_only=False, suffix_new="_findandreplace", verbose=False):  # DS, cat 2b, unittests 3
    """ 
    Finds and replaces a specified string in the either the entire file or only in content.

    :param file_path: string, the path to the file where the find and replace operation will be performed.
    :param find_str: string to be found in the file content.
    :param replace_str: string to replace the found string in the file content.
    :param content_only: boolean for whether to do entire file or only content.
    :param suffix_new: string, the suffix to be appended to the original filename for the new file. Default is "_findandreplace".
    :param verbose: boolean where if True prints the number of replacements and the file path. Default is True.
    :return: string, the path to the newly created file with the replaced content.

    :category: 2b nested ffop - calls write_header_and_content_ffop without do_ffop
    :heading: CONTENT PROCESSING
    :usage: print(find_and_replace_ffop('path/to/your/file.txt', 'find_this_string', 'replace_with_this_string', True, '_newsuffix', True))
    """
    # print(f"DEBUG Verbose in find_and_replace_ffop: {verbose}")
    # no need for the new_file_path or the warning check because another ffop is called below
    if content_only:
        header, text = read_header_and_content_from_file(file_path, delimiter="## content")
    else:
        text = read_complete_text_from_file(file_path)
    new_text = text.replace(find_str, replace_str)
    num_replacements = text.count(find_str)
    
    if num_replacements > 0:
        verbose_print(verbose, f"{num_replacements} Replacements on file_path: {os.path.basename(file_path)}")
    else:
        verbose_print(verbose, f"No Replacements on file_path: {os.path.basename(file_path)}")
    
    if content_only:
        return write_header_and_content_ffop(file_path, header, new_text, suffix_new)
    else:
        return write_complete_text_ffop(file_path, new_text, suffix_new)
    # notice this call is with the original file_path and the suffix_new, not a new_file_path

# TODO reconsider the flexibility of the space before the comma so that we can use pairs with leading or trailing spaces, maybe have a warning confirmation message if the csv has a pair with a leading space
def parse_csv_for_find_replace(csv_file):
    """ Parses a CSV file to extract find and replace pairs. """
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

def find_and_replace_from_csv(folder_path, find_replace_csv, overwrite="yes", suffix_include=None, verbose=False):  # DS, cat 3e
    """
    Applies find and replace operations on all files in a specified folder based on pairs defined in a CSV file.
    IMPORTANT csv file cannot be in the same folder if suffix_include=None

    :param folder_path: string, the path to the folder where the files are located.
    :param find_replace_csv: string, the path to the CSV file containing find and replace pairs.
    :param overwrite: string, controls file overwriting. Defaults to 'yes'.
    :param suffix_include: string, the suffix that included files must have. If None, all files will be processed.
    :param verbose: boolean, if True prints verbose messages.
    :return: None

    :category: 3e non ffop file operation on folder
    :heading: CONTENT PROCESSING
    :usage: find_and_replace_from_csv(cur_folder, cur_find_replace_csv, suffix_include="_dgwhspm", verbose=True)
    """
    # Parse the CSV to get find and replace pairs
    find_replace_pairs = parse_csv_for_find_replace(find_replace_csv)
    
    for find_str, replace_str in find_replace_pairs:
        verbose_print(verbose, f"find: {find_str}  replace: {replace_str}")
        do_ffop_on_folder(find_and_replace_ffop, folder_path, find_str, replace_str, overwrite=overwrite, suffix_include=suffix_include, verbose=verbose)

def get_text_between_delimiters(full_text, delimiter_start, delimiter_end=None):  # DS, cat 1, unittests 5
    """ 
    Extracts a substring from the given text between specified start and end delimiters.

    :param full_text: string of the text from which to extract the substring.
    :param delimiter_start: string of the delimiter indicating the start of the substring.
    :param delimiter_end: string of the delimiter indicating the end of the substring. If None, the end of the text is used. Default is None.
    :return: string of the extracted substring (inclusive of delimiter_start), or None if the start delimiter is not found.

    :category: 1
    :heading: CONTENT PROCESSING
    :usage: extracted_text = get_text_between_delimiters(full_text, delimiter_start, delimiter_end)
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

def get_heading_from_file(file_path, heading): # DS, cat 3a, unittests 4
    """
    Extracts the text associated with a markdown heading from a file, including any subheadings of equal or lower order.

    :param file_path: string, the path to the file to be read.
    :param heading: string, the markdown heading to be extracted, including the '#' characters and the following space.
    :return: string, the text associated with the markdown heading and its subheadings of equal or lower order.

    :category: 3a non ffop file function
    :heading: READ AND METADATA FUNCTIONS
    :usage: print(get_heading_from_file(cur_file_path, "### summaries"))
    """
    # Read the complete text from the file
    complete_text = read_complete_text_from_file(file_path)
    
    # Determine the order (level) of the heading based on the number of '#' characters
    heading_level = len(heading) - len(heading.lstrip('#'))
    
    # Define the end delimiter as any markdown heading of equal or higher order (lower number of '#')
    delimiter_end_pattern = r'(?m)^#{1,' + str(heading_level) + r'}\s'
    
    # Find the index of the heading to extract from the complete text
    heading_start_index = complete_text.find(heading)
    if heading_start_index == -1:
        return None  # Heading not found
    
    # Find the index of the next heading of equal or higher order
    next_heading_match = re.search(delimiter_end_pattern, complete_text[heading_start_index + len(heading):])
    if next_heading_match:
        heading_end_index = next_heading_match.start() + heading_start_index + len(heading)
    else:
        heading_end_index = len(complete_text)
    
    # Extract the text associated with the heading - previously used rstrip(' \n\t') + "\n" but this caused the text not to be replaced in set_heading because an exact match is required
    return complete_text[heading_start_index:heading_end_index]

def set_heading_ffop(file_path, new_heading_and_text, heading, suffix_new="_setheading"):  # DS, cat 2b, unittests 3
    """
    Sets the heading and following text associated with a markdown heading in a file.
    Replaces if the heading already exists. Adds if it does not exist.
    NOTE - heading should be passed as a variable like this (new_heading + "\nHere's new text\n")

    :param file_path: string, the path to the file where the heading text will be set.
    :param new_heading_and_text: string, the new text to be associated with the markdown heading, inclusive of heading line
    :param heading: string, the markdown heading whose text will be set, including the '#' characters and the following space.
    :param suffix_new: string, the suffix to be appended to the original filename for the new file. Default is "_setheading".
    :return: string, the path to the newly created file with the updated heading text.

    :category: 2b nested ffop - calls write_header_and_content_ffop without do_ffop
    :heading: CONTENT PROCESSING
    :usage: print(do_ffop(set_heading_ffop, cur_file_path, new_heading+"Here's new text\n", new_heading, overwrite="no"))
    """
    # Read the header and content from the file
    header, content = read_header_and_content_from_file(file_path, delimiter="## content")
    
    # Get the existing text associated with the heading
    existing_heading_and_text = get_heading_from_file(file_path, heading)
    
    # If new_heading_and_text is an empty string, remove the heading and its following text
    if new_heading_and_text == "":
        print("DEBUG - empty new_heading_and_text")
        if existing_heading_and_text is None:
            raise ValueError("in set_heading_ffop - called with invalid params: empty new_heading_and_text and heading does not exist (use delete_heading_ffop or to insert a new heading with no text, pass new_heading_and_text=heading)")
        # Remove the existing heading and its following text
        new_content = content.replace(existing_heading_and_text, '')
    elif existing_heading_and_text is not None:
        # Replace the existing text with the new text and ensure it ends with a newline
        if not new_heading_and_text.endswith('\n'):
            new_heading_and_text += '\n'
        # print(f"\nDEBUG existing_heading_and_text:\n{repr(existing_heading_and_text)}")
        # print(f"\nDEBUG new_heading_and_text:\n{repr(new_heading_and_text)}")
        # print(f"\nDEBUG content before replacing existing_heading_and_text with new_heading_and_text:\n{repr(content)}")
        new_content = content.replace(existing_heading_and_text, new_heading_and_text)
        # print(f"\nDEBUG content after replacing existing_heading_and_text with new_heading_and_text:\n{repr(content)}")
    else:
        # If the heading does not exist, add the heading and new text to the content
        new_content = new_heading_and_text + "\n" + content

    # Write the updated content back to the new file path
    return write_header_and_content_ffop(file_path, header, new_content, suffix_new)

def delete_heading_ffop(file_path, heading, suffix_new="_deleteheading"):  # DS, cat 2b, unittests 3
    """
    Deletes the specified markdown heading and its following text from a file.
    If the heading does not exist, the original file is copied with a new suffix.

    :param file_path: string of the path to the file from which the heading will be deleted.
    :param heading: string of the markdown heading to be deleted, including the '#' characters and the following space.
    :param suffix_new: string of the suffix to be appended to the original filename for the new file. Defaults to "_deleteheading".
    :return: string of the path to the newly created file with the heading deleted, or the original file if the heading was not found.

    :category: 2b nested ffop - calls write_header_and_content_ffop without do_ffop
    :heading: CONTENT PROCESSING
    :usage: print(delete_heading_ffop(cur_file_path, "## Heading to delete"))
    """
    # Check if the heading exists in the file
    existing_heading_and_text = get_heading_from_file(file_path, heading)
    if existing_heading_and_text is None:
        warnings.warn(f"in delete_heading_ffop: trying to delete heading that does not exist - original file copied")
        # If the heading does not exist, copy the file with the new suffix
        return copy_file_and_append_suffix(file_path, suffix_new)
    else:
        # If the heading exists, proceed to delete it
        return set_heading_ffop(file_path, "", heading, suffix_new)

def append_heading_to_file(source_file_path, target_file_path, heading, include_filename=True):  # DS, cat 3d, unittests 2
    """
    Appends the text under a specified heading from a source file to a target file, optionally including the source filename as a heading.

    :param source_file_path: string of the path to the source file.
    :param target_file_path: string of the path to the target file where the text will be appended.
    :param heading: string of the markdown heading to be appended.
    :param include_filename: boolean indicating whether to include the source filename as a heading. Defaults to True.
    :return: string of the appended text or None if the heading is not found in the source file.

    :category: 3d non ffop file function that writes to a compilation file
    :heading: CONTENT PROCESSING
    :usage: append_heading_to_file(cur_file_path, "mtest_combined.md", "### summaries")
    """
    new_text = get_heading_from_file(source_file_path, heading)
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
            text = read_complete_text_from_file(target_file_path)
            text += '\n' + new_text
        else:
            # TODO reconsider the need to create the new file before calling write_header_and_content_ffop and using do_ffop
            with open(target_file_path, 'w') as file:
                file.write('')
            text = new_text

        do_ffop(write_complete_text_ffop, target_file_path, text, overwrite='yes')
        return new_text
    else:
        return None

# TODO check error handling for when heading doesnt exist
# TODO check error handling for when file is empty
def heading_only_ffop(file_path, heading, suffix_new="_headingonly"):  # DS, cat 2b, unittest 2
    """ 
    Extracts text under a specified heading from a file and writes it to a new file with a specified suffix.

    :param file_path: string of the path to the file.
    :param heading: string of the markdown heading to be processed.
    :param suffix_new: string of the suffix to be appended to the new file. Defaults to "_headingonly".
    :return: string of the path to the newly created file.

    :category: 2b nested ffop - calls write_header_and_content_ffop without do_ffop
    :heading: CONTENT PROCESSING
    :usage: new_file_path = heading_only_ffop('path/to/your/file.md', '### Your Heading')
    """
    complete_text = get_heading_from_file(file_path, heading)
    # Strip the markdown heading from the beginning of the complete text
    complete_text = complete_text.lstrip(heading).lstrip('\n')
    
    return write_complete_text_ffop(file_path, complete_text, suffix_new)

# TODO update the filename variables to follow our naming conventions
def create_csv_from_fields(folder_path, fields):  # DS, cat 3d, unittest 5
    """ 
    Generates a CSV file from all markdown files in a specified folder.

    :param folder_path: string, the path to the folder containing the markdown files.
    :param fields: list, the fields to be extracted from the markdown files.
    :return: string of the path to the created csv file.

    :category: 3d non ffop file function that writes to a compilation file
    :heading: COMBINE AND CSV
    :usage: create_csv_from_folder('/path/to/your/folder', ['field1', 'field2'])
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
                        # Field is a markdown header
                        header_pattern = rf'({field}[^#]*)'
                        match = re.search(header_pattern, content, re.DOTALL)
                        if match:
                            # Remove the header line, leading and trailing blank lines
                            field_content = match.group(1).strip()
                            field_content = re.sub(rf'^{field}.*\n?', '', field_content, flags=re.MULTILINE)
                            field_content = re.sub(r'^\s*\n', '', field_content)  # Remove leading blank lines
                            field_content = re.sub(r'\n\s*\n', '\n', field_content)  # Remove multiple blank lines
                            data[adjusted_field] = field_content

                # Write the extracted data to the CSV
                csv_writer.writerow(data)

    print(f"CSV file created at {csv_filename}")
    return csv_filename
    # DONE fill in code to make a csv from all files in the folder_path
    # DONE fill in code to use the argument 'fields' list of strings as the column headers to include in the csv as the top row and data to extract from the files
    # DONE fill in code to extract 2 field types, field_metadata_line (ends with ":") and field_md_header (starts with one or more "#")
    # DONE fill in code to extract for field_metadata_line all of the text after the whitespace that follows the ":" in the matching string 
    # DONE fill in code to extract for field_md_header all lines after any blank lines following the line with the specified "#" characters up to the next line that starts with "#" and removing any trailing blank lines

def create_csv_matrix_from_triples(triples_text, target_file_path):  # DS, cat 3d, unittest 3
    """
    Converts multiline text of triples into a csv matrix file where each entry is the number for that row and column.

    :param triples_text: string of multiline text containing rows of data separated by newlines, each row containing two strings and a number separated by commas.
    :param target_file_path: string of the path to the target csv file.
    :return: string of the path to the created csv file.

    :category: 3d non ffop file function that writes to a compilation file
    :heading: COMBINE AND CSV
    :usage: create_csv_matrix_from_triples(triples_text_content, 'path/to/target_file.csv')
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

### JSON PROCESSING
def pretty_print_json_structure(json_file_path, level_limit=None, save_to_file=False):  # DS, cat 3a, unittests 10
    """
    Prints the structure of a JSON file and optionally saves it to a file with a '.pretty' extension.

    :param json_file_path: string of the path to the json file.
    :param level_limit: integer of the maximum level of nesting to print. None means no limit.
    :param save_to_file: boolean indicating whether to save the output to a file. defaults to true.
    :return: None.

    :category: 2
    :heading: JSON PROCESSING
    :usage: pretty_print_json_structure('path/to/your/file.json', level_limit=2, save_to_file=False)
    """
    # Define colors for different levels of JSON structure with high contrast
    colors = ['green', 'blue', 'red', 'magenta', 'yellow', 'white', 'grey']
    output_lines = []

    if not os.path.exists(json_file_path):
        warnings.warn(f"File {json_file_path} does not exist.")
        return

    def print_structure(data, indent=0, parent_key='', level=0):
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
                        print_structure(data[key][0], indent + 4, key, level + 1)
                else:
                    # Print dictionary keys with the selected color
                    line = ' ' * indent + str(key)
                    print(colored(line, color))
                    output_lines.append(line)
                    print_structure(data[key], indent + 4, key, level + 1)
        elif isinstance(data, list) and parent_key != '':
            if data:
                print_structure(data[0], indent, parent_key, level)

    with open(json_file_path, 'r') as file:
        data = json.load(file)
        print_structure(data)

    if save_to_file:
        output_file_path = json_file_path + '.pretty'
        with open(output_file_path, 'w') as output_file:
            for line in output_lines:
                output_file.write(line + '\n')
        print(f"Saved pretty printed JSON structure to {output_file_path}")


### MORE METADATA AND HEADER FUNCTIONS
def set_metadata_field(header, field, value):  # DS, cat 1b, unittests 3
    """ 
    Sets or updates a metadata field in the header with a given value.

    :param header: string, the header from which a metadata field is to be set or updated.
    :param field: string, the metadata field to be set or updated.
    :param value: string, the value to be set for the metadata field.
    :return: string, the updated header with the set or updated metadata field.

    :category: 1b takes header as first argument
    :heading: MORE METADATA AND HEADER FUNCTIONS
    :usage: print(set_metadata_field(cur_header, 'field_name', 'field_value'))
    """
    # Split the metadata text into lines
    lines = header.split('\n')
    field_line = None
    field_exists = False
    insert_index = -1  # Default insert index to the end of the header

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
    updated_header = '\n'.join(lines)

    return updated_header

def remove_metadata_field(header, field):  # DS, cat 1b, unittests 3
    """ 
    Removes a specified metadata field from the header.

    :param header: string, the header from which a metadata field is to be removed.
    :param field: string, the metadata field to be removed.
    :return: string, the updated header with the removed metadata field.

    :category: 1b takes header as first argument
    :heading: MORE METADATA AND HEADER FUNCTIONS
    :usage: print(remove_metadata_field(cur_header, 'field_name'))
    """
    # Removes a specified metadata field from the header
    lines = header.split('\n')
    updated_lines = [line for line in lines if not line.startswith(f"{field}:")]
    updated_header = '\n'.join(updated_lines)
    # DONE fill in code utilizing code from @add_metadata_field to delete the provided field
    return updated_header

def create_initial_header():  # DS, cat 1, omit unittest
    """ 
    Creates an initial header for a file.

    :return: string, the initial header for a file.

    :category: 1
    :heading: MORE METADATA AND HEADER FUNCTIONS
    :usage: print(create_initial_header())
    """
    header = "## metadata\nlast updated: \n\n## content\n\n"
    return header

def set_last_updated(header, new_last_updated_value, use_today=True):  # DS, cat 1b, unittests 3
    """ 
    Updates the 'last updated' metadata field in the header with a new value.

    :param header: string, the header from which the 'last updated' metadata field is to be updated.
    :param new_last_updated_value: string, the new value for the 'last updated' metadata field.
    :param use_today: boolean, if True, today's date is prepended to the new_last_updated_value. Default is True.
    :return: string, the updated header with the new 'last updated' value.

    :category: 1b takes header as first argument
    :heading: MORE METADATA AND HEADER FUNCTIONS
    :usage: print(set_last_updated(cur_header, 'new_last_updated_value'))
    """
    if use_today:
        date_today = datetime.now().strftime("%m-%d-%Y") # Assign today's date in format MM-DD-YYY
        new_last_updated_value = f"{date_today} {new_last_updated_value}"
    return set_metadata_field(header, 'last updated', new_last_updated_value)

def set_metadata_fields_from_csv(folder_path, csv_file_path, suffix_extension):  # DS, cat 3e, unittest 3
    """
    Sets metadata fields for all files in a folder based on a CSV file.

    :param folder_path: string of the path to the folder containing the files.
    :param csv_file_path: string of the path to the CSV file with metadata fields and values.
    :param suffix_extension: string of the file extension to be appended to file bases.
    :return: None, but prints the number of files processed successfully and the total in the CSV excluding empty rows.

    :category: 3e non ffop file function on folder
    :heading: MORE METADATA AND HEADER FUNCTIONS
    :usage: set_metadata_fields_from_csv('path/to/folder', 'path/to/metadata.csv', '.md')
    """
    # Read the CSV file and extract the metadata fields and values
    with open(csv_file_path, mode='r', encoding='utf-8') as csvfile:
        csv_reader = csv.reader(csvfile)
        header_fields = next(csv_reader)  # First row contains metadata field names
        metadata_values = [row for row in csv_reader if row]  # Remaining rows contain metadata values, excluding empty rows

    total_files_in_csv = len(metadata_values)  # Count only non-empty rows
    successfully_processed_files = 0

    # Iterate over each row in the CSV to update files
    for row_index, row in enumerate(metadata_values, start=1):  # Start counting rows from 1
        if len(row) < len(header_fields):  # Check if the row has enough columns
            print(f"Row {row_index} in CSV does not have enough columns. Expected {len(header_fields)}, got {len(row)}.")
            continue

        file_base = row[0] + suffix_extension
        file_path = os.path.join(folder_path, file_base)
        # Map fields to values
        metadata_dict = dict(zip(header_fields[1:], row[1:]))

        try:
            # Read the header and content from the file
            header, content = read_header_and_content_from_file(file_path)

            # Check if the header already has the metadata block
            if '## metadata' not in header:
                # Create an initial header if the metadata block is not there
                header = create_initial_header()
                # Insert the 'last updated' field
                header = set_last_updated(header, datetime.now().strftime("%Y-%m-%d"), use_today=False)

            # Update the header with metadata fields from the CSV
            for field, value in metadata_dict.items():
                header = set_metadata_field(header, field, value)

            # Write the updated header and content back to the file
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(header + "\n" + content)

            successfully_processed_files += 1
        except Exception as e:
            print(f"Failed to process file {file_base}: {e}")

    print(f"Total files in CSV excluding empty rows: {total_files_in_csv}")
    print(f"Successfully processed files: {successfully_processed_files}")
   

### *** BELOW GETS MOVED OUT OF FILEOPS ***

### QUOTES *** MOVE TO TRANCRIBE - REDO AFTER MERGING BRANCH TO USE DOUBLE QUOTE MARKS ***
def extract_quotes(file_path):
    with open(file_path, 'r') as file:
        # Read the content of the file line by line
        lines = file.readlines()
        # Iterate through the lines of the file
        for i, line in enumerate(lines):
            # Find all instances of text within single quotes in the line
            start_index = 0
            while True:
                # Find the start of a quote
                start_quote = line.find(" '", start_index)
                # If no start is found, we break out of the loop
                if start_quote == -1:
                    break
                # Adjust the start index to skip the leading space and quote
                start_quote += 2
                # Find the end of the quote
                end_quote = line.find("' ", start_quote)
                # If no end is found, we break out of the loop
                if end_quote == -1:
                    break
                # Extract the quote and a few words on either side
                context_start = max(line.rfind(' ', 0, start_quote - 2), 0)
                context_end = min(line.find(' ', end_quote + 2), len(line))
                context = line[context_start:context_end]
                # Print the line above the line that the quote was found in its entirety
                if i > 0:
                    print(f"{lines[i - 1].strip()}")
                else:
                    print("ERROR - No timestamp line")
                print(context)
                # Update the start index to search for the next quote
                start_index = end_quote + 2
                print("\n")

# THIS IS STILL BUGGY- SOME EDGE CASES ARE NOT BEING REMOVED - redo now that we're using double quote marks
def remove_quotes(file_path):
    # Create a new file with a suffix after it where all the " '" and "' " characters are removed if found in a pair
    # Ensure that the new file does not overwrite an existing file
    # Avoid removing apostrophes at the end of words like "Brandons'"
    new_file_path = file_path.replace(os.file_path.splitext(file_path)[1], "_noquotes" + os.file_path.splitext(file_path)[1])
    if not os.file_path.exists(new_file_path):  # Check if the file already exists
        with open(file_path, 'r') as file:
            lines = file.readlines()
            new_lines = []
            for line in lines:
                new_line = []
                i = 0
                while i < len(line):
                    if line[i:i+2] == " '":  # Found the beginning of a quote
                        end_quote_index = i + 2
                        while end_quote_index < len(line) and line[end_quote_index:end_quote_index+2] != "' ":
                            if line[end_quote_index:end_quote_index+2] == " '":  # Found the beginning of another quote before the end of the current one
                                break
                            end_quote_index += 1
                        if end_quote_index < len(line) and line[end_quote_index:end_quote_index+2] == "' ":  # Found the end of the quote
                            i = end_quote_index + 2  # Skip past the end quote
                        else:
                            new_line.append(line[i])  # The end quote was not found, keep the beginning quote
                            i += 1
                    elif line[i:i+2] == "' " and (i + 2 < len(line) and line[i+2:i+4] != " '"):  # Found an end quote and there's no immediate start of another quote
                        i += 2  # Remove the end quote
                    else:
                        new_line.append(line[i])  # Keep the current character
                        i += 1
                new_lines.append(''.join(new_line))
        with open(new_file_path, 'w') as new_file:
            new_file.writelines(new_lines)
        return new_file_path
    else:
        raise FileExistsError(f"The file {new_file_path} already exists.")
