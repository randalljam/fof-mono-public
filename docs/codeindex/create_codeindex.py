# ===== START OF FILE docs/codeindex/create_codeindex.py =====

import os
import re
import ast
import networkx as nx
import json
import logging
import sys
import warnings

# Get the current file's name and directory
current_file = os.path.basename(__file__)
current_dir = os.path.dirname(__file__)

# Create the log file name
log_file = os.path.join(current_dir, f"{os.path.splitext(current_file)[0]}_log.txt")

# Configure logging to write only to file
file_handler = logging.FileHandler(log_file, mode='w')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# Create logger and add only the file handler
logger = logging.getLogger('')
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)

# Create a custom stream to capture print statements
class PrintCapture:
    def __init__(self, original_stdout):
        self.original_stdout = original_stdout
        self.buffer = ''

    def write(self, msg):
        self.buffer += msg
        if '\n' in self.buffer:
            lines = self.buffer.split('\n')
            for line in lines[:-1]:
                if line.strip():
                    self.original_stdout.write(line + '\n')
                    logger.info(f"PRINT: {line.strip()}")
            self.buffer = lines[-1]

    def flush(self):
        if self.buffer:
            if self.buffer.strip():
                self.original_stdout.write(self.buffer)
                logger.info(f"PRINT: {self.buffer.strip()}")
            self.buffer = ''
        self.original_stdout.flush()

# Redirect stdout to our custom stream
sys.stdout = PrintCapture(sys.stdout)

# Capture warnings
def warning_capture(message, category, filename, lineno, file=None, line=None):
    print(f'WARNING: {message}')  # Print to console
    logger.warning(f'WARNING: {message}')  # Log to file

warnings.showwarning = warning_capture

from core.fileops import *
from core.transcribe import *
from core.llm import *
from core.aws import *
from core.aws_valid import *
from core.rag import *
from core.vectordb import *
from core.rag_prompts_routes import *
from core.video import *
from core.webflow_api import *
from core.dbgen import *
from docs.vis.codebase_graph_vis import *

CONTROLLER_FUNCTIONS = ['apply_to_folder']
SKIP_FUNCTIONS = ['mrun', 'mtest']

### CORE FUNCTION CALL EXTRACTION USING AST PACKAGE
def find_user_defined_functions(ast_node, module_name, exclude_nested=True):
    '''
    Find user-defined functions in an AST ast_node and prefix them with the module name.
    
    :param ast_node: AST node to search
    :param module_name: name of the module being processed
    :param exclude_nested: if True, exclude nested function definitions
    :return: list of function names prefixed with module name
    '''
    module_noext = module_name.rsplit('.', 1)[0]  # remove extension, e.g filops.py -> fileops
    functions = []
    
    # First pass: collect all function nodes and their parents
    function_nodes = {}
    for node in ast.walk(ast_node):
        if isinstance(node, ast.FunctionDef):
            # Find the parent function if it exists
            parent_func = None
            for parent in ast.walk(ast_node):
                if (isinstance(parent, ast.FunctionDef) and 
                    parent.lineno < node.lineno and 
                    parent.end_lineno > node.lineno):
                    parent_func = parent
                    break
            
            # Skip functions that start with any of the SKIP_FUNCTIONS prefixes
            if any(node.name.startswith(skip) for skip in SKIP_FUNCTIONS):
                continue
            
            # Check if this function is nested
            if exclude_nested and parent_func is not None:
                print(f"Excluding nested function: {node.name} (nested in {parent_func.name}) in {module_name}")
                continue
            
            functions.append(f"{module_noext}.{node.name}")
    
    return functions

def get_full_call_line(source_code, parent_function_name, child_function_name):
    '''
    Get the entire line of code where a function call occurs within the source code string.
    
    :param source_code: The source code as a string.
    :param parent_function_name: The name of the parent function containing the call.
    :param child_function_name: The name or ID of the child function being called.
    :return: The full line of code containing the function call, or None if not found.
    '''
    # Parse the source code into an AST
    tree = ast.parse(source_code)
    
    # Find the parent function ast_node first
    parent_function_ast_node = None
    for child in ast.walk(tree):
        if isinstance(child, ast.FunctionDef) and child.name == parent_function_name:
            parent_function_ast_node = child
            break

    if not parent_function_ast_node:
        return None

    # Now, walk through the parent function ast_node to find the call
    for ast_node in ast.walk(parent_function_ast_node):
        if isinstance(ast_node, ast.Call):
            if ((hasattr(ast_node.func, 'id') and ast_node.func.id == child_function_name) or
                (hasattr(ast_node.func, 'attr') and ast_node.func.attr == child_function_name)):
                # Get the source line number for the call
                lineno = ast_node.lineno
                # Extract the line of code from the source code string
                lines = source_code.splitlines()
                return lines[lineno - 1].strip()  # Line numbers are 1-indexed in Python
    return None

def get_first_argument(full_call_line):
    '''
    Extract and return the first argument from the full call line of a function call.
    
    :param full_call_line: The full line of code containing the function call.
    :return: The first argument as a string, or None if no arguments are found.
    '''
    # Find the opening and closing parentheses of the function call
    start_index = full_call_line.find('(')
    end_index = full_call_line.find(')')
    
    # If parentheses are not found, return None
    if start_index == -1 or end_index == -1 or end_index <= start_index:
        return None
    
    # Extract the arguments string between the parentheses
    arguments_str = full_call_line[start_index + 1:end_index].strip()
    
    # Split the arguments by comma and return the first one, if it exists
    arguments_list = arguments_str.split(',')
    if arguments_list:
        return arguments_list[0].strip()
    
    return None

def find_function_children(all_source_code, ast_node, user_defined_functions, function_name=None):
    logging.info(f"Processing function: {getattr(ast_node, 'name', 'Unknown')}")
    calls = set()
    parent_function_name = None
    if hasattr(ast_node, 'name'):
        parent_function_name = ast_node.name

    for child in ast.walk(ast_node):
        if isinstance(child, ast.Call):
            logging.debug(f"Processing call: {ast.dump(child)}")
            func_name = None
            if isinstance(child.func, ast.Name):
                func_name = child.func.id
            elif isinstance(child.func, ast.Attribute):
                func_name = child.func.attr
            elif isinstance(child.func, ast.Call):
                # Handle nested function calls
                func_name = "nested_call"
            
            if func_name is None:
                logging.warning(f"Couldn't determine function name for call: {ast.dump(child)}")
                continue

            # Check if the function name includes the module prefix
            full_func_name = [f for f in user_defined_functions if f.endswith('.' + func_name)]
            logging.debug(f"Full function name matches: {full_func_name}")
            if full_func_name and (function_name is None or func_name == function_name):
                full_func_name = full_func_name[0]  # Take the first match
                logging.debug(f"Selected full function name: {full_func_name}")
                if func_name in CONTROLLER_FUNCTIONS:
                    # Get the full call line
                    func_full_call_line = get_full_call_line(all_source_code, parent_function_name, func_name)
                    logging.debug(f"Full call line: {func_full_call_line}")
                    first_argument = get_first_argument(func_full_call_line)
                    logging.debug(f"First argument: {first_argument}")
                    # Find the module name using the first argument
                    module_name = [f.split('.')[0] for f in user_defined_functions if f.endswith('.' + first_argument)]
                    if module_name:
                        module_name = module_name[0]  # Take the first match
                        logging.debug(f"Module name: {module_name}")
                        calls.add(f"{full_func_name} WITH {module_name}.{first_argument}")
                    else:
                        logging.warning(f"Module name for first argument '{first_argument}' not found.")
                else:
                    # Append the path to the function name
                    calls.add(full_func_name)
    logging.debug(f"Final calls set: {calls}")
    return sorted(calls)

def find_functions_parents(all_source_code, ast_node, user_defined_functions, function_name):
    '''Find functions that call a specific function, remove duplicates and sort alphabetically.'''
    callers = set()
    for child in ast.walk(ast_node):
        if isinstance(child, ast.FunctionDef):
            calls = find_function_children(all_source_code, child, user_defined_functions, function_name)
            if calls:
                # Extract the module name from the full function name
                # Assuming full function names are in the format 'module_name.function_name'
                full_function_name = [f for f in user_defined_functions if f.endswith('.' + child.name)]
                if full_function_name:
                    full_function_name = full_function_name[0]  # Take the first match
                    callers.add(full_function_name)
    return sorted(callers)


### CREATE CODEINDEX MD FILES FROM LIST OF ALL .PY FILE PATHS
def process_files_for_user_defined_functions_and_asts(file_paths):
    all_user_defined_functions = []
    ast_trees = []
    module_names = []
    for file_path in file_paths:
        with open(file_path, 'r') as file:
            source = file.read()
            tree = ast.parse(source)
            ast_trees.append(tree)
            # Extract module name from file path
            module_name = os.path.splitext(os.path.basename(file_path))[0] + '.py'
            module_names.append(module_name)
            user_defined_functions = find_user_defined_functions(tree, module_name)
            all_user_defined_functions.extend(user_defined_functions)
    print(f"Module_names: {module_names}")
    print(f"Number of modules: {len(module_names)}")
    print(f"Total user-defined functions found: {len(all_user_defined_functions)}")
    return all_user_defined_functions, ast_trees, module_names

def find_function_definition(function_name, source_code):
    '''
    Find the exact function definition line and ensure it appears only once.
    :return: the start position of the function definition.
    '''
    #print(f"DEBUG: function_name received: {function_name}")  # Debug print
    
    # Split into module and function name
    parts = function_name.split('.')
    func_name = parts[-1]  # Take last part in case of duplicated names
    
    pattern = rf"def {re.escape(func_name)}\s*\("
    matches = list(re.finditer(pattern, source_code))

    # Check if the function name is found exactly once
    if len(matches) != 1:
        raise ValueError(f"Function '{function_name}' should appear exactly once in the source code.")

    # Get the position of the function definition
    return matches[0].start()

def get_heading_from_function(function_name, source_code, heading_delimiter='\n### '):
    # Get the position of the function definition
    func_def_start = find_function_definition(function_name, source_code)

    # Extract the source code up to the function definition
    preceding_code = source_code[:func_def_start]

    # Find the last occurrence of the heading delimiter before the function definition
    last_heading_pos = preceding_code.rfind(heading_delimiter)
    if last_heading_pos == -1:
        raise ValueError(f"No heading found before the function '{function_name}'.")

    # Extract the heading line
    heading_start = last_heading_pos + len(heading_delimiter)
    heading_end = preceding_code.find('\n', heading_start)
    heading = preceding_code[heading_start:heading_end].strip()

    return heading

def get_function_def_line(function_name, source_code):
    # Use the new function to find the function definition start
    func_def_start = find_function_definition(function_name, source_code)

    # Extract the line containing the function definition start
    source_lines = source_code.split('\n')
    line_number = source_code[:func_def_start].count('\n')
    line = source_lines[line_number].strip()

    # Now, extract the entire function definition including parameters
    func_def = line
    open_parens = line.count('(')
    close_parens = line.count(')')
    current_line = line_number

    # Continue to the next lines if parentheses are not balanced
    while open_parens > close_parens:
        current_line += 1
        next_line = source_lines[current_line].strip()
        func_def += ' ' + next_line
        open_parens += next_line.count('(')
        close_parens += next_line.count(')')

    return func_def

def get_docstring_from_function(function_name, source_code):
    '''
    Extracts the docstring of a specified function from the source code.
    :return: The docstring of the function with double quotes replaced by single quotes.
    '''
    # Find the start position of the function definition
    func_def_start = find_function_definition(function_name, source_code)

    # Extract the source code starting from the function definition
    function_code = source_code[func_def_start:]

    # Pattern to find docstring enclosed in triple single quotes or triple double quotes
    pattern = r'(\'\'\'|\"\"\")(.*?)(\'\'\'|\"\"\")'
    match = re.search(pattern, function_code, re.DOTALL)

    if match:
        # Extract the docstring and replace double quotes with single quotes
        docstring = match.group(2).replace('"', "'")
        return docstring.strip()
    else:
        print(f"No docstring found for the function '{function_name}'.")
        return ""

def check_strings_in_markdown(file_path, strings_list):
    """
    Compares strings in a markdown file with a given list of strings.
    Strips off markdown headings and blank lines at the beginning of the file,
    extracts text enclosed in single quotes, sorts both lists, and prints the differences.

    :param file_path: Path to the markdown file.
    :param strings_list: List of strings to compare with the markdown file content.
    """
    try:
        with open(file_path, 'r') as file:
            # Read and clean the markdown content
            markdown_content = file.readlines()
            markdown_content = [line.strip() for line in markdown_content if line.strip() and not line.startswith('#')]

        # Extract text enclosed in single quotes
        file_strings = []
        for line in markdown_content:
            matches = re.findall(r"'(.*?)'", line)
            file_strings.extend(matches)

        # Sort both lists
        file_strings_sorted = sorted(file_strings)
        strings_list_sorted = sorted(strings_list)

        # Compare the lists and print differences
        file_strings_set = set(file_strings_sorted)
        strings_list_set = set(strings_list_sorted)

        only_in_file = file_strings_set - strings_list_set
        only_in_input = strings_list_set - file_strings_set

        if only_in_file:
            print("Strings only in the file:")
            for string in sorted(only_in_file):
                print(f"'{string}'")
        else:
            print("No strings found only in the file.")

        if only_in_input:
            print("Strings only in the input list:")
            for string in sorted(only_in_input):
                print(f"'{string}'")
        else:
            print("No strings found only in the input list.")

    except FileNotFoundError:
        print(f"The file {file_path} does not exist.")
    except Exception as e:
        print(f"An error occurred: {e}")

def generate_graph_data(all_source_code, ast_trees, user_defined_functions, module_names):
    graph_nodes = []
    graph_edges = []
    special_edge_count = 0
    invalid_node_id_count = 0

    # Instead of walking the AST again, iterate through user_defined_functions
    for function in user_defined_functions:
        module_noext, func_name = function.rsplit('.', 1)
        module_name = module_noext + '.py'
        
        node_data = {
            "id": function,
            "label": func_name,
            "group": 'function',
            "module": module_name,
            "submodule": get_heading_from_function(function, all_source_code),
            "def": get_function_def_line(function, all_source_code),
            "line": None,
            "docstring": get_docstring_from_function(function, all_source_code)
        }
        graph_nodes.append(node_data)

    # Process edges using the existing AST walk for function calls
    for tree, module_name in zip(ast_trees, module_names):
        for ast_node in ast.walk(tree):
            if isinstance(ast_node, ast.FunctionDef):
                module_noext = module_name.rsplit('.', 1)[0]
                node_id = f"{module_noext}.{ast_node.name}"
                # Only process edges for functions that are in our filtered list
                if node_id in user_defined_functions:
                    called_functions = find_function_children(all_source_code, ast_node, user_defined_functions)
                    for called_func in called_functions:
                        edge_data = {"from": node_id}
                        if " WITH " in called_func:
                            controller_func, worker_func = called_func.split(" WITH ")
                            edge_data["from"] = controller_func
                            edge_data["to"] = worker_func
                            edge_data["type"] = "controller_to_worker"
                            edge_data["applies_to_functions"] = [node_id]
                            special_edge_count += 1
                            graph_edges.append({"from": node_id, "to": controller_func})
                        else:
                            edge_data["to"] = called_func
                        graph_edges.append(edge_data)

    print(f"Number of special edges: {special_edge_count}")
    print(f"Number of invalid node IDs: {invalid_node_id_count}")
    return {"nodes": graph_nodes, "edges": graph_edges}

def get_all_source_code(file_paths):
    '''Concatenate the source code from each file in the file paths list into a single string, editing lines starting with '# ' and adding a markdown heading with the relative file path.'''
    from core.llm import add_token_counts_to_headings
    all_source_code = "all_source_code\n\n"
    base_path = ""
    for file_path in file_paths:
        with open(file_path, 'r') as file:
            source_code = file.readlines()
        # Update the pattern to handle any amount of whitespace after #
        edited_source_code = [line.replace(re.match(r'#\s+', line).group(), '#') if re.match(r'#\s+', line) else line for line in source_code]
        relative_path = file_path.replace(base_path, "")
        headering1 = f"## {relative_path}\n"  # Markdown level one header with the relative file path
        all_source_code += headering1 + ''.join(edited_source_code) + '\n\n\n\n'
    return all_source_code.strip()

def get_all_source_defs_docstrings(all_source_code):
    from core.llm import add_token_counts_to_headings
    
    # Replace '# all_source_code\n\n' with '# all_source_defs_docstring\n\n'
    new_text = all_source_code.replace('all_source_code\n\n', '', 1)

    lines = new_text.split('\n')
    filtered_lines = []
    in_docstring = False
    docstring_content = []
    
    for line in lines:
        # Keep strict markdown headings
        if re.match(r'^#{1,6}\s', line):
            # Add blank line before each module heading (level 2)
            if line.startswith('## '):
                filtered_lines.append('')  # Add blank line before module heading
            filtered_lines.append(line)
        # Keep function definitions
        elif line.strip().startswith('def '):
            filtered_lines.append(line)
        # Handle docstrings
        elif '"""' in line:
            if not in_docstring:
                # Start of docstring
                in_docstring = True
                docstring_content = [line]
            else:
                # End of docstring
                in_docstring = False
                docstring_content.append(line)
                filtered_lines.extend(docstring_content)
        elif in_docstring:
            # Collect lines inside docstring
            docstring_content.append(line)
    
    text = 'all_source_defs_docstring\n\n' + '\n'.join(filtered_lines)
    
    return add_token_counts_to_headings(text)

def get_function_children_and_parents(all_source_code, all_user_defined_functions, ast_trees, target_function_name):
    ''' returns a string of the former print lines'''
    target_function = None
    output_lines = []

    # Check if the target function is in the accumulated ASTs
    for tree in ast_trees:
        for func in ast.walk(tree):
            if isinstance(func, ast.FunctionDef) and func.name == target_function_name:
                target_function = func
                break
        if target_function:
            break

    # If the target function was not found in any of the files, raise an error
    if target_function is None:
        raise ValueError(f"Function {target_function_name} not found in the provided file paths")

    # Find functions called by the target function
    called_functions = find_function_children(all_source_code, target_function, all_user_defined_functions)
    output_lines.append(f'  CHILD FUNCTIONS that the function above calls:\n')
    for func in called_functions:
        output_lines.append(f'    < {func}\n')

    # Find functions that call the target function across all files
    output_lines.append(f'  PARENT FUNCTIONS that call the function above:\n')
    for tree in ast_trees:
        callers = find_functions_parents(all_source_code, tree, all_user_defined_functions, target_function_name)
        for caller in callers:
            output_lines.append(f'    > {caller}\n')

    return ''.join(output_lines)

def save_all_source_code_versions(save_folder_path, suffix, all_source_code, ast_trees, user_defined_functions, module_names):
    # Save all_user_defined_functions to a markdown file
    with open(os.path.join(save_folder_path, 'all_user_defined_functions' + suffix + '.md'), 'w') as f:
        for function in user_defined_functions:
            f.write(function + '\n')

    # Save all_source_code to a markdown file
    with open(os.path.join(save_folder_path, 'all_source_code' + suffix + '.md'), 'w') as f:
        f.write(all_source_code)

    # Save all_source_defs_docstrings to a markdown file
    all_source_defs_docstrings = get_all_source_defs_docstrings(all_source_code)
    with open(os.path.join(save_folder_path, 'all_source_defs_docstrings' + suffix + '.md'), 'w') as f:
        f.write(all_source_defs_docstrings)

    # Save ast_trees to a markdown file
    with open(os.path.join(save_folder_path, 'all_ast_trees' + suffix + '.md'), 'w') as f:
        for tree in ast_trees:
            f.write(ast.dump(tree) + '\n\n')
    
    # Generate and save graph data
    graph_data = generate_graph_data(all_source_code, ast_trees, user_defined_functions, module_names)
    
    with open(os.path.join(save_folder_path, 'all_graph' + suffix + '.json'), 'w') as f:
        json.dump(graph_data, f, indent=2)

def combine_codeindex_module_files(module_file_paths, output_folder, new_file_suffix):
    """Combines multiple codeindex markdown files into a single file."""
    combined_content = ""

    for md_file_path in module_file_paths:
        # Extract the filename from the file path
        filename = os.path.basename(md_file_path)
        # Create a Markdown heading with the filename
        combined_content += f"## {filename}\n\n"
        # Read the content of the Markdown file
        with open(md_file_path, 'r') as file:
            content = file.read()
            combined_content += content + "\n\n"
        # Add two blank lines between files
        combined_content += "\n\n"
    
    # Create a new markdown file to store the combined content in the output folder
    output_file_path = os.path.join(output_folder, f"codeindex_0combined{new_file_suffix}.md")
    with open(output_file_path, 'w') as file:
        file.write(combined_content)
    
    # Print the created file path
    print(f"Created {os.path.relpath(output_file_path)}")
    
    # Return the file path to the new markdown file
    return output_file_path

def create_codeindex_and_graph_files(file_paths, skip_modules=False, dev_mode=False):
    new_file_prefix = "codeindex_"
    if dev_mode:
        new_file_suffix = "_dev"
        output_folder = "docs/codeindex/"  # folder for dev files
    else:
        new_file_suffix = "_" + get_current_datetime_filefriendly()
        # Create a new subfolder in the archive with the current timestamp
        archive_subfolder = f"codeindex{new_file_suffix}"
        output_folder = os.path.join("docs/codeindex/_archive", archive_subfolder)
        os.makedirs(output_folder, exist_ok=True)

    created_module_files = []  # List to store paths of newly created module markdown files

    user_defined_functions, ast_trees, module_names = process_files_for_user_defined_functions_and_asts(file_paths)
    all_source_code = get_all_source_code(file_paths)
    save_all_source_code_versions(output_folder, new_file_suffix, all_source_code, ast_trees, user_defined_functions, module_names)
    
    if not skip_modules:
        # Copies .py files and processes them as markdown files
        for file_path in file_paths:
            if file_path.endswith('.py'):
                # Create a copy of the file with 'codeindex_' prefix and .md extension in the output folder
                new_file_path = os.path.join(output_folder, new_file_prefix + os.path.splitext(os.path.basename(file_path))[0] + new_file_suffix + '.md')
                created_module_files.append(new_file_path)  # Add the new file path to the list
                print(f"Created {new_file_path}")  # Print the created file path
                with open(file_path, 'r') as original_file, open(new_file_path, 'w') as new_file:
                    inside_function = False
                    function_name = ''
                    inside_block_comment = False
                    for line in original_file:
                        # Retain lines that start with two or more pound signs, and convert code comments that start with 1 # to italics with enclosing _
                        if re.match(r"^(# )(?![#]).*", line):
                            comment_text = line.lstrip('# ').rstrip()
                            new_file.write(f"_{comment_text}_\n")
                        elif re.match(r"^(#{2,4} ).*", line):
                            new_file.write(line)
                        # Skip lines that are not function definition lines and not comment lines as defined above
                        elif not line.lstrip().startswith('def ') and not inside_function:
                            continue
                        # Retain function definition lines and modify them for markdown
                        elif line.lstrip().startswith('def '):
                            function_name = line.split('(')[0].replace('def ', '').strip()
                            arguments = line.split('(')[1]
                            # Check if there is a comment on the same line as the function definition
                            if '#' in arguments:
                                arguments, comment = arguments.split('#', 1)
                                arguments = arguments.rstrip('): \n')
                                comment = comment.strip()
                                new_file.write(f"<{function_name}> ({arguments}):  _{comment}_\n")
                            else:
                                arguments = arguments.rstrip('):\n')
                                new_file.write(f"<{function_name}> ({arguments}):\n")
                            inside_function = True
                        # Replace the body of functions with the get_function_children_and_parents output
                        elif inside_function:
                            if line.strip() == '':
                                inside_function = False
                                # Write the calls and callers for the function
                                return_string = get_function_children_and_parents(all_source_code, user_defined_functions, ast_trees, function_name)
                                new_file.write(return_string)
                                new_file.write('\n')
                            elif line.strip().startswith('def '):  # New function definition starts
                                # Write the calls and callers for the previous function
                                return_string = get_function_children_and_parents(all_source_code, user_defined_functions, ast_trees, function_name)
                                new_file.write(return_string)
                                # Start processing the new function
                                function_name = line.split('(')[0].replace('def ', '').strip()
                                arguments = line.split('(')[1]
                                # Check if there is a comment on the same line as the function definition
                                if '#' in arguments:
                                    arguments, comment = arguments.split('#', 1)
                                    arguments = arguments.rstrip('): \n')
                                    comment = comment.strip()
                                    new_file.write(f"\n<{function_name}> ({arguments}):  _{comment}_\n")
                                else:
                                    arguments = arguments.rstrip('):\n')
                                    new_file.write(f"\n<{function_name}> ({arguments}):\n")
                            else:
                                continue  # Ignore the body of the function
                    if function_name:
                        return_string = get_function_children_and_parents(all_source_code, user_defined_functions, ast_trees, function_name)
                        new_file.write(return_string)
        # Combine the updated module files
        combine_file = combine_codeindex_module_files(created_module_files, output_folder, new_file_suffix)

        # Add token counts to each created module file
        for module_file in created_module_files:
            with open(module_file, 'r') as file:
                content = file.read()
            updated_content = add_token_counts_to_headings(content)
            with open(module_file, 'w') as file:
                file.write(updated_content)

        # Add token counts to the combined file
        with open(combine_file, 'r') as file:
            combined_content = file.read()
        updated_combined_content = add_token_counts_to_headings(combined_content)
        with open(combine_file, 'w') as file:
            file.write(updated_combined_content)
    else:
        # Delete existing codeindex module dev files
        for file in os.listdir(output_folder):
            if file.startswith("codeindex_") and file.endswith("_dev.md"):
                file_path = os.path.join(output_folder, file)
                os.remove(file_path)
        print("Deleted codeindex dev md files to avoid them being behind all sources files.")

    # Add token counts to the all_source_code file
    all_source_code_file = next((f for f in os.listdir(output_folder) if f.startswith('all_source_code')), None)
    if all_source_code_file:
        all_source_code_path = os.path.join(output_folder, all_source_code_file)
        with open(all_source_code_path, 'r') as file:
            all_source_content = file.read()
        updated_all_source_content = add_token_counts_to_headings(all_source_content)
        with open(all_source_code_path, 'w') as file:
            file.write(updated_all_source_content)
        print(f"Added token counts to headings in {all_source_code_file}")
    else:
        print("No all_source_code file found in the output folder.")

if __name__ == "__main__": 
    cur_file_paths = [
        'core/fileops.py',
        'core/transcribe.py',
        'core/llm.py',
        'core/vectordb.py',
        'core/rag.py',
        'core/conversion.py',
        'core/structured.py',
        'core/corpuses.py',
        'core/aws.py',
        'core/aws_valid.py',
        'core/rag_prompts_routes.py',
        'core/video.py',
        'core/webflow_api.py',
        'core/dbgen.py',
        #'core/speakerid.py'
        ]  # NOTE - All of these files must be imported at the top of this file as well.   
    # TEST CODE FOR A SINGLE FUNCTION
    # cur_target_function = 'get_suffix'
    # print(cur_target_function)
    # print(get_function_children_and_parents(cur_file_paths, cur_target_function))

    # CREATE THE CODEINDEX FILES
    create_codeindex_and_graph_files(cur_file_paths, skip_modules=True, dev_mode=True)


# current (7-24-24 RT) create_codeindex_log.txt is not included in timestamp archive - need to review this log file

''' OUTPUT EXAMPLE
<get_youtube_title_length> (url):  _DS, cat 1, unittests 1_
  CHILD FUNCTIONS that the function above calls:
        < fileops.tune_timestamp
  PARENT FUNCTIONS that call the function above:
        > transcribe.create_youtube_md
        > transcribe.download_link_list_to_mp3s
        > transcribe.get_media_length
''' 

'''
consider All of this code and then review the current output format and the desired output format at the end. What I want to do is add the module names and a dot for the function strings. So where is the best place in this code to do that and give me the modified function. Hopefully it'll just involve a single function. The all user-defined functions should also include this format, which has the file name and a dot, and then the function string.
'''
# ===== END OF FILE docs/codeindex/create_codeindex.py =====
