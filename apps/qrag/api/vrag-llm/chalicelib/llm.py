import sys
import os
import json
import warnings
import requests
import tiktoken
# import anthropic  # removed 10-6 for qrag-routing
from termcolor import colored
from tenacity import retry, wait_random_exponential, stop_after_attempt

from chalicelib.fileops import *


# ---API KEYS AND SECRETS---
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
# ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY_LOCAL"]


# ---START OF SYNCED CODE--- only code below will be synchronized with chalicelib.

# OpenAI model name - comment one out
#OPENAI_MODEL = "gpt-4o-mini"
#OPENAI_MODEL = "o1"
OPENAI_MODEL = "gpt-4o-2024-11-20"
#OPENAI_MODEL = "o3-mini"

ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"


# Set the warnings to use a custom format
warnings.formatwarning = custom_formatwarning
# USAGE: warnings.warn(f"Insert warning message here")

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir) # Add the parent directory to sys.path

BLOCK_DELIMITER = '\n---\n'

### PRINT AND TOKENS
def pretty_print_function(messages, tools, print_prompts=False, print_input=True, verbose=False):
    """
    Prints messages with role-specific colors and separates function details for clarity.

    :param messages: list of dictionaries containing message role and content
    :params tools: list of tools, each containing function details, passed to pretty_print_function_descriptions
    :param print_prompts: boolean of whether to print the system prompt and function parameter descriptions, defaults to False
    :param print_input: boolean of whether to print the user input, defaults to True
    :return: a list of the print strings as [print_str_prompts, print_str_input, print_str_responses]
    """
    role_to_color = {
        "system": "red",
        "function parameter descriptions": "yellow",
        "user": "green",
        "assistant": "grey",
        "function responses": "magenta",  # Color for function details
    }
    print_str_prompts = ""
    print_str_input = ""
    print_str_responses = ""

    verbose_print(verbose, f"messages:\n{messages}")
    verbose_print(verbose, f"tools:\n{tools}")

    for index, message in enumerate(messages):
        verbose_print(verbose, f"Message {index + 1} of {len(messages)} messages")
        if message["role"] == "system" and print_prompts:
            print_str_prompts = f"System Prompt: {message['content']}\n"
            print(colored(print_str_prompts, role_to_color[message["role"]]))
            if tools is not None:
                print_str_prompts += pretty_print_function_descriptions(tools, role_to_color["function parameter descriptions"])
        if message["role"] == "user":
            print_str_input = f"User Input:\n{message['content']}\n"
            print(colored(print_str_input, role_to_color[message["role"]]))
        elif message["role"] == "assistant":
            assistant_msg_str = str(message)

            # Find the index where function details start
            function_start_idx = assistant_msg_str.find("'function': ")

            # Split the string into two parts
            assistant_msg_part = assistant_msg_str[:function_start_idx]
            function_msg_part = assistant_msg_str[function_start_idx:]

            # Print the technical assistant info but generally we don't need this so comment out 3-16-24 RT
            #print(colored(f"assistant: {assistant_msg_part}", role_to_color["assistant"]))

            # Process and print the second part (function details) in magenta
            if function_start_idx != -1:
                # Parsing the function details from the string
                function_name_start_idx = function_msg_part.find("'name': '") + len("'name': '")
                function_name_end_idx = function_msg_part.find("'", function_name_start_idx)
                function_name = function_msg_part[function_name_start_idx:function_name_end_idx]

                arguments_str = function_msg_part.split("'arguments': '{", 1)[-1].rstrip("}'}}]")
                arguments_str = arguments_str.replace("\\n", "\n").replace("\\", "").replace('"', '')
                print_str_responses = "Function Parameters Responses:\n"
                for line in arguments_str.split(","):
                    # below is simply to add a space after the colon for reasons I do not understand!
                    key_value = line.split(':', 1)
                    if len(key_value) == 2:
                        key, value = key_value
                        print_str_responses += f"  {key.strip()}: {value.strip()}\n"
                    else:
                        print_str_responses += f"  {line}\n"
                print(colored(print_str_responses, role_to_color["function responses"]))

    return [print_str_prompts, print_str_input, print_str_responses]
def pretty_print_function_descriptions(tools, print_color):
    """
    Print descriptions of functions and their properties from a list of tools.

    :param tools: a list of tools, each containing function details
    :return: a string of function names and descriptions, including properties
    """
    output_str = ""
    for tool in tools:
        if tool["type"] == "function":
            function_name = f"Function Name: {tool['function']['name']}"
            function_description = f"Function Description: {tool['function']['description']}"
            output_str += function_name + "\n" + function_description + "\n"
            print(colored(output_str, print_color))
            output_str += "Function Parameter Descriptions:\n"
            print(colored("Function Parameter Descriptions:", print_color))
            output_str += '\n'  # add newline so string matches terminal print
            
            # Extract and print each function's properties with descriptions, appending them to the output string.
            properties = tool['function']['parameters']['properties']
            for prop, details in properties.items():
                prop_description = f"  {prop}: {details['description'].strip()}"
                output_str += prop_description + "\n"
                print(colored(prop_description, print_color))
            
    return output_str
def count_tokens(input_string):  # no unittests
    """
    Counts the number of tokens in a given string using the 'cl100k_base' encoding.

    :param input_string: string of text to be tokenized.
    :return: integer representing the number of tokens in the input string.
    """
    encoding = tiktoken.get_encoding('cl100k_base')
    token_count = len(encoding.encode(input_string))
    return token_count
TOKEN_PRICE_DICT = {  # last updated 02-13-25 RT
    'gpt-4o':{'input_token_price':2.50, 'output_token_price':10.00, 'cached_input_token_price': 1.25},  # costs in $/million tokens
    'gpt-4o-mini':{'input_token_price':.15, 'output_token_price':.60, 'cached_input_token_price': 0.075},
    'o1':{'input_token_price':15.00, 'output_token_price':60.00, 'cached_input_token_price': 7.50},
    'o3-mini':{'input_token_price':1.10, 'output_token_price':4.40, 'cached_input_token_price': 0.55},
    'claude-3-5-sonnet-20241022':{'input_token_price':3.00, 'output_token_price':15.00, 'cached_input_token_price': 0.30},  # but Anthropic requires upfront explicit prompt caching and is not automatic
    'deepseek-reasoner':{'input_token_price':0.55, 'output_token_price':2.19, 'cached_input_token_price': 0.14},
    'deepseek-chat':{'input_token_price':0.27, 'output_token_price':1.10, 'cached_input_token_price': 0.07}
    }
def cost_llm_on_file(file_path, prompt, model, token_price_dict, is_cached_input=False, verbose=False, chunking_function=None, chunking_function_args=(), output_tokens_ratio=1, output_tokens_fixed=0):  # no unittests
    """
    Calculates the cost of processing a file using a language model, based on the number of input and output tokens.

    :param file_path: string of the path to the file to be processed.
    :param prompt: string of the prompt to be used for the language model.
    :param model: string of the name of the language model to be used.
    :param token_price_dict: dictionary containing the cost per token for the input and output of the model.
    :param chunking_function: function to be used for chunking the file, defaults to None.
    :param chunking_function_args: tuple of arguments to be passed to the chunking function, defaults to an empty tuple.
    :param output_tokens_ratio: ratio of input tokens to output tokens, defaults to 1.
    :param output_tokens_fixed: fixed number of output tokens per chunk, defaults to 0.
    :return: tuple of total input cost, total output cost, and total cost.
    """
    if output_tokens_ratio != 0 and output_tokens_fixed != 0:
        raise ValueError("output_tokens_ratio and output_tokens_fixed cannot both be non zero")
    
    # Default chunking function: read the entire file as a single chunk
    def default_chunking(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            return [file.read()]

    # Use the provided chunking function or the default one
    chunks = (chunking_function or default_chunking)(file_path, *chunking_function_args)

    # Setting up variables
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost = 0
    input_token_price = token_price_dict[model]['input_token_price']
    cached_input_token_price = token_price_dict[model].get('cached_input_token_price')  # Returns None if not present
    if is_cached_input:
        if cached_input_token_price is None:
            raise ValueError(f"Cached input token price is not present for model {model}")
        actual_input_token_price = cached_input_token_price
    else:
        actual_input_token_price = input_token_price
    output_token_price = token_price_dict[model]['output_token_price']
    prompt_tokens = count_tokens(prompt)
    
    # Main loop
    for chunk in chunks:
        input_tokens = prompt_tokens
        chunk_input = count_tokens(chunk)
        input_tokens += chunk_input
        if output_tokens_fixed > 0:
            output_tokens = output_tokens_fixed
        else:
            output_tokens = chunk_input * output_tokens_ratio
        total_input_tokens += input_tokens
        total_output_tokens += output_tokens

    total_input_cost = (total_input_tokens / 1000000) * actual_input_token_price
    total_output_cost = (total_output_tokens / 1000000) * output_token_price
    total_cost = total_input_cost + total_output_cost

    if verbose:
        print(file_path)
        print(f"File input tokens: {total_input_tokens:,} (Cost: ${actual_input_token_price:.4f}/1M tokens, Input token cost: ${total_input_cost:.2f}), Cached input={is_cached_input}")
        print(f"File output tokens: {total_output_tokens:,} (Cost: ${output_token_price:.4f}/1M tokens, Output token cost: ${total_output_cost:.2f})")
        print(f"File cost: ${total_cost:.2f}\n\n")

    return total_input_cost, total_output_cost, total_cost, total_input_tokens
def cost_llm_input_only(file_path, token_price_dict, is_cached_input=False):
    """
    Calculate and display input token costs for a file across all models in the token cost dictionary.

    :param file_path: string, path to the file to analyze
    :param token_price_dict: dictionary containing token cost information for different models
    :param is_cached_input: boolean, whether to use cached input token price if available
    :return: None
    """
    # Read file and count tokens
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    total_tokens = count_tokens(content)
    
    # Print header with total tokens
    print(colored(f"\nFile: {file_path}", "yellow"))
    print(f"Total tokens: {total_tokens:,}")
    print(f"Cached input: {is_cached_input}\n")
    
    # Print table header
    print(f"{'Model':<27} {'$/1M':>12} {'Cost':>10}")
    print("-" * 51)
    
    # Calculate and print costs for each model
    for model, costs in token_price_dict.items():
        input_token_price = costs['input_token_price']
        cached_input_token_price = costs.get('cached_input_token_price')  # Returns None if not present
        
        if is_cached_input:
            if cached_input_token_price is None:
                print(f"Warning: Cached input token price not available for {model}, using standard price")
                actual_input_token_price = input_token_price
            else:
                actual_input_token_price = cached_input_token_price
        else:
            actual_input_token_price = input_token_price
            
        total_cost = (total_tokens / 1000000) * actual_input_token_price
        print(f"{model:<27} {actual_input_token_price:>12.2f} {total_cost:>10.3f}")
def cost_llm_on_corpus(corpus_path, prompt, model, token_price_dict, is_cached_input=False, verbose=False, suffix_include=None, suffix_exclude=None, include_subfolders=False, chunking_function=None, chunking_function_args=(), output_tokens_ratio=1, output_tokens_fixed=0):
    """
    Calculates the cost of processing a corpus using a language model, based on the number of input and output tokens.

    :param corpus_path: string of the path to the corpus to be processed.
    :param prompt: string of the prompt to be used for the language model.
    :param model: string of the name of the language model to be used.
    :param token_price_dict: dictionary containing the cost per token for the input and output of the model.
    :param is_cached_input: boolean indicating whether to use cached input token price, defaults to False.
    :param chunking_function: function to be used for chunking the file, defaults to None.
    :param chunking_function_args: tuple of arguments to be passed to the chunking function, defaults to an empty tuple.
    :param output_tokens_ratio: ratio of input tokens to output tokens, defaults to 1.
    :param output_tokens_fixed: fixed number of output tokens per chunk, defaults to 0.
    :param suffix_include: string of the suffix that included files must have, defaults to None.
    :param suffix_exclude: string of the suffix that files must not have to be included, defaults to None.
    :param include_subfolders: boolean indicating whether to include files from subfolders, defaults to False.
    :return: tuple of total input cost, total output cost, and total cost for the entire corpus.
    """
    total_input_cost = 0
    total_output_cost = 0
    total_cost = 0
    total_input_tokens = 0
    
    # Get input token prices based on caching setting
    input_token_price = token_price_dict[model]['input_token_price']
    cached_input_token_price = token_price_dict[model].get('cached_input_token_price')
    
    if is_cached_input:
        if cached_input_token_price is None:
            print(f"Warning: Cached input token price not available for {model}, using standard price")
            actual_input_token_price = input_token_price
        else:
            actual_input_token_price = cached_input_token_price
    else:
        actual_input_token_price = input_token_price
    
    file_paths = get_files_in_folder(corpus_path, suffix_include=suffix_include, suffix_exclude=suffix_exclude, include_subfolders=include_subfolders)
    
    for file_path in file_paths:
        file_input_cost, file_output_cost, file_cost, input_tokens = cost_llm_on_file(file_path, prompt, model, token_price_dict, is_cached_input, verbose, chunking_function, chunking_function_args, output_tokens_ratio, output_tokens_fixed)
        total_input_cost += file_input_cost
        total_output_cost += file_output_cost
        total_cost += file_cost
        total_input_tokens += input_tokens
    
    print(f"\nCorpus Summary for {corpus_path}")
    print(f"Corpus input cost: {total_input_cost:.2f}")
    print(f"Corpus output cost: {total_output_cost:.2f}")
    print(f"Corpus total cost: ${total_cost:.2f}")
    print(f"Corpus total files: {len(file_paths)}, total input tokens: {total_input_tokens:,}\n")

    return total_input_cost, total_output_cost, total_cost
def add_token_counts_to_headings(text):
    """
    Adds token counts to markdown headings in the given text.

    :param text: string, the text content to process.
    :return: string, the text with token counts added to headings.
    """
    updated_lines = []
    for line in text.split('\n'):
        if re.match(r'^#{1,6}\s', line):
            heading = line.strip()
            heading_text = find_heading_text(text, heading)
            if heading_text:
                start, end = heading_text
                section_content = text[start:end]
                token_count = count_tokens(section_content)
                formatted_count = f"{token_count:,}"
                updated_line = f"{line} ({formatted_count} tokens)"
                updated_lines.append(updated_line)
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)
    
    result = '\n'.join(updated_lines)
    total_tokens = count_tokens(result)
    
    # Add total token count to the first line
    first_line, *rest = result.split('\n', 1)
    result = f"{first_line} ({total_tokens:,} tokens)\n" + (rest[0] if rest else "")
    return result

# NOT UPDATED FOR CACHED INPUTS
def print_cost_table(table_data, title=None):
    """
    Print a formatted cost table from CSV-style data.

    :param table_data: list of lists, where first row contains headers and subsequent rows contain data
    :param title: string, optional title to print before the table
    :return: None
    """
    if not table_data or not table_data[0]:
        print("No data to display")
        return

    if title:
        print(f"{title}")
        print()
    
    # Find the maximum number of columns in any row
    max_cols = max(len(row) for row in table_data)
    
    # Pad rows that are too short with empty strings
    padded_data = []
    for row in table_data:
        padded_row = row + [''] * (max_cols - len(row))
        padded_data.append(padded_row)
    
    # Get column widths based on maximum content length in each column
    col_widths = []
    for col_idx in range(max_cols):
        col_width = max(len(str(row[col_idx])) for row in padded_data)
        # Add extra padding between number columns
        if col_idx > 0:  # For $/1M and ¢ columns
            col_width += 2  # Add 2 more spaces (3 total with the default space)
        col_widths.append(max(col_width, 1))  # Ensure minimum width of 1
    
    # Print headers with proper alignment
    headers = padded_data[0]
    header_row = ""
    for header, width in zip(headers, col_widths):
        if header in ['Tokens', '$/1M', '¢']:
            header_row += f"{header:>{width}} "  # Right align numbers
        else:
            header_row += f"{header:<{width}} "  # Left align text
    print(header_row.rstrip())
    
    # Print separator line
    separator = "-" * (sum(col_widths) + len(col_widths) - 1)
    print(separator)
    
    # Print data rows
    for i, row in enumerate(padded_data[1:]):
        # Print equals separator before the last row
        if i == len(padded_data[1:]) - 1:
            print("=" * (sum(col_widths) + len(col_widths) - 1))
            
        data_row = ""
        for value, width in zip(row, col_widths):
            if isinstance(value, (int, float)) or (isinstance(value, str) and value.replace(',', '').replace('.', '').isdigit()):
                data_row += f"{value:>{width}} "  # Right align numbers
            else:
                data_row += f"{value:<{width}} "  # Left align text
        print(data_row.rstrip())
def get_reasoning_model_cost_table_from_response(response, reasoning_model, verbose=True):
    """
    Get the cost of a reasoning model response from the response object.

    :param response: dict, the response object from an API call containing usage information
    :param reasoning_model: string, the model name to use for cost calculations (default: "o3-mini")
    :param verbose: boolean, whether to print detailed cost breakdown
    :return: list of lists, the table data or None if error
    """
    try:
        usage = response['usage']
        
        # Extract token counts
        input_tokens = usage['prompt_tokens']
        output_tokens = usage['completion_tokens']
        reasoning_tokens = usage['completion_tokens_details']['reasoning_tokens']
        
        # Get costs per million tokens in dollars
        input_price_per_million = TOKEN_PRICE_DICT[reasoning_model]['input_token_price']
        output_price_per_million = TOKEN_PRICE_DICT[reasoning_model]['output_token_price']
        
        # Calculate costs in cents
        input_cost = (input_tokens / 1000000) * (input_price_per_million * 100)
        reasoning_cost = (reasoning_tokens / 1000000) * (input_price_per_million * 100)
        output_cost = (output_tokens / 1000000) * (output_price_per_million * 100)
        total_cost = input_cost + reasoning_cost + output_cost
        
        # Prepare table data regardless of verbose setting
        table_data = [
            ['Token Type', '$/1M', '¢'],
            ['Input', f"{input_price_per_million:.2f}", f"{input_cost:.1f}"],
            ['Reasoning', f"{input_price_per_million:.2f}", f"{reasoning_cost:.1f}"],
            ['Output', f"{output_price_per_million:.2f}", f"{output_cost:.1f}"],
            ['Total', "", f"{total_cost:.1f}"]
        ]
        
        if verbose:
            print(f"API Call Cost Breakdown:")
            print(f"reasoning_model: {reasoning_model}\n")
            print_cost_table(table_data)
            print()
        
        return table_data
        
    except (KeyError, TypeError) as e:
        print(f"Error parsing response object: {str(e)}")
        return None
def compare_reasoning_model_cost_table_from_response(response, reasoning_models=["o1", "o3-mini", "deepseek-reasoner"], verbose=True):
    """
    Compare the cost of two reasoning models based on the response object.

    :param response: dict, the response object from an API call containing usage information
    :param reasoning_models: list of strings, the models to compare
    :param verbose: boolean, whether to print detailed cost breakdown
    :return: list of lists, the table data
    """
    # Get table data for each model
    model_tables = {}
    for model in reasoning_models:
        table_data = get_reasoning_model_cost_table_from_response(response, model, verbose=False)
        if table_data:
            model_tables[model] = table_data

    if not model_tables:
        print("No valid table data generated for any model")
        return None

    # Create combined table starting with headers from first model
    first_model = reasoning_models[0]
    if first_model not in model_tables:
        return None
    
    # Get the base headers (Type, $/1M, ¢)
    base_headers = model_tables[first_model][0]
    
    # Create the combined table headers
    header_row = [base_headers[0]]  # Start with 'Type'
    for model in reasoning_models:
        if model in model_tables:
            header_row.extend([base_headers[1], base_headers[2], ''])  # Add $/1M and ¢ columns plus spacing
    header_row.pop()  # Remove last spacing
    
    # Create the combined table
    combined_table = [header_row]
    
    # Process each row type
    row_types = ['Input', 'Reasoning', 'Output', 'Total']
    for row_type in row_types:
        new_row = [row_type]
        for model in reasoning_models:
            if model in model_tables:
                model_data = model_tables[model]
                for row in model_data[1:]:
                    if row[0] == row_type:
                        new_row.extend([row[1], row[2], ''])  # Add data columns plus spacing
                        break
        new_row.pop()  # Remove last spacing
        combined_table.append(new_row)

    if verbose:
        print("Model Cost Comparison:\n")
        
        # Create the model header line with fixed positions
        model_line = "Model"
        positions = [24, 40, 56]  # Fixed positions for model names
        
        for i, model in enumerate(reasoning_models):
            if model in model_tables:
                # Replace deepseek-reasoner with deepseek-r1
                display_model = "deepseek-r1" if model == "deepseek-reasoner" else model
                # Calculate padding to align model name to end at position
                padding = positions[i] - len(model_line) - len(display_model) + 1
                model_line += " " * padding + display_model
        
        print(model_line)
        
        # Print the rest of the table
        print_cost_table(combined_table)
        print()

    return combined_table

def get_call_cost_from_response(response, model, token_price_dict, verbose=True):
    """
    Get the cost of a reasoning model response from the response object.

    :param response: dict or ChatCompletion object from an API call containing usage information
    :param model: string, the model name to use for cost calculations (e.g. "o3-mini")
    :param token_price_dict: dictionary containing the cost per token for the input and output of the model.
    :param verbose: bool, if True, prints detailed cost breakdown.
    :return: total call cost in pennies (integer or float, depending on the cost calculation)
    """
    # Handle both dict and ChatCompletion object responses
    if hasattr(response, 'usage'):
        usage = response.usage
    elif isinstance(response, dict):
        usage = response.get('usage')
        if usage is None:
            raise ValueError("Usage information is missing from the response.")
    else:
        raise ValueError(f"Unsupported response type: {type(response)}")

    # Determine input token breakdown
    # Case 1: DeepSeek-style response provides explicit cache hit/miss tokens
    if hasattr(usage, 'prompt_cache_hit_tokens') and hasattr(usage, 'prompt_cache_miss_tokens'):
        cached_input_tokens = usage.prompt_cache_hit_tokens
        non_cached_input_tokens = usage.prompt_cache_miss_tokens
    elif hasattr(usage, 'prompt_tokens_details') and hasattr(usage.prompt_tokens_details, 'cached_tokens'):
        cached_input_tokens = usage.prompt_tokens_details.cached_tokens
        total_prompt_tokens = getattr(usage, 'prompt_tokens', 0)
        non_cached_input_tokens = total_prompt_tokens - cached_input_tokens
    else:
        # Fallback: assume no cached tokens if not explicitly provided
        cached_input_tokens = 0
        non_cached_input_tokens = getattr(usage, 'prompt_tokens', 0)

    # Output tokens (usually the completion tokens)
    output_tokens = getattr(usage, 'completion_tokens', 0)

    # Get pricing info for the selected model
    if model not in token_price_dict:
        raise ValueError(f"Model {model} not found in token price dictionary.")
    model_prices = token_price_dict[model]
    input_token_price = model_prices['input_token_price']          # in $ per million tokens
    cached_input_token_price = model_prices.get('cached_input_token_price', input_token_price)
    output_token_price = model_prices['output_token_price']

    # Compute costs in dollars (prices are per million tokens)
    cost_non_cached_input = (non_cached_input_tokens / 1_000_000) * input_token_price
    cost_cached_input = (cached_input_tokens / 1_000_000) * cached_input_token_price
    cost_output = (output_tokens / 1_000_000) * output_token_price
    total_cost_dollars = cost_non_cached_input + cost_cached_input + cost_output

    # Convert dollars to pennies
    total_cost_pennies = round(total_cost_dollars * 100, 3)

    if verbose:
        print("Token Usage Breakdown:")
        print(f"  Non-cached input tokens: {non_cached_input_tokens:,}")
        print(f"  Cached input tokens:     {cached_input_tokens:,}")
        print(f"  Output tokens:           {output_tokens:,}")
        print("\nCost Breakdown:")
        print(f"  Non-cached input cost:   {cost_non_cached_input * 100:.1f}¢")
        print(f"  Cached input cost:       {cost_cached_input * 100:.1f}¢")
        print(f"  Output cost:             {cost_output * 100:.1f}¢")
        print(f"  Total cost:              {total_cost_pennies:.1f}¢")

    return total_cost_pennies

### SPLIT FILES
def get_line_numbers_with_match(file_path, match_str):
    """
    Retrieve line numbers from a file where the line matches a given string exactly after stripping.

    :param file_path: path to the file to be searched
    :param match_str: string of text to match on each line
    :return: list of line numbers where the match_str is found
    """
    # Check if the original file exists and is valid
    if not os.path.isfile(file_path):
        raise ValueError(f"The file path does not exist or is invalid for {file_path}.")
    
    line_numbers = []
    with open(file_path, 'r') as file:
        for line_number, line in enumerate(file, start=1):
            if line.strip() == match_str:
                line_numbers.append(line_number)
    
    return line_numbers
def get_speaker_segments(file_path, skip_string='SKIPQA'):
    """
    Extract segments from a file that do not contain a specific skip string, or all segments if skip string is None.

    :param file_path: string of the path to the file to be processed
    :param skip_string: string of the substring used to identify segments to skip, or None to include all segments
    :return: list of segments without the skip string, or all segments if skip string is None
    """
    transcript = get_heading(file_path, heading="### transcript")
    transcript = transcript.lstrip('### transcript').rstrip('\n').lstrip('\n*')
    
    segments = transcript.split("\n\n")
    if skip_string is not None:
        segments = [segment.strip() for segment in segments if skip_string not in segment]
    else:
        segments = [segment.strip() for segment in segments]
    
    return segments
def count_segment_tokens(file_path, skip_string='SKIPQA'):
    """
    Count tokens in each segment of a file and provide token statistics.

    :param file_path: string of the path to the file to be processed
    :param skip_string: string of the substring used to identify segments to skip
    :return: tuple containing (list of segments, list of token counts)
    """
    segments = get_speaker_segments(file_path, skip_string)
    segment_tokens = [count_tokens(segment) for segment in segments]
    
    total_tokens = sum(segment_tokens)
    max_tokens = max(segment_tokens)
    
    print(f"Total tokens in the file: {total_tokens:,}  x 4 for characters: {4*total_tokens:,}")
    print(f"Number of segments in the file: {len(segments)}")
    print(f"Maximum tokens in any segment: {max_tokens:,}  x 4 for characters: {4*max_tokens:,}")
    
    return segment_tokens
def plot_segment_tokens(file_path):
    """
    Create a horizontal bar chart plot of token counts for each segment and save it as a PNG file.

    :param file_path: string of the path to the file to be processed
    :return: string of the path to the saved PNG file
    """
    import matplotlib.pyplot as plt
    
    segments = get_speaker_segments(file_path)
    segment_tokens = count_segment_tokens(file_path)
    
    plt.figure(figsize=(15, 10))
    y_pos = range(len(segment_tokens))
    plt.barh(y_pos, segment_tokens)
    
    total_tokens = sum(segment_tokens)
    max_tokens = max(segment_tokens)
    num_segments = len(segment_tokens)
    
    plt.title(f"Token Distribution in Segments\n\n{file_path}\n\n"
              f"Maximum tokens in any segment: {max_tokens}\n"
              f"Number of segments: {num_segments}\n"
              f"Total tokens: {total_tokens}\n\n", loc='left', fontweight='bold', fontsize=14)
    
    plt.ylabel("Segment Index")
    plt.xlabel("Token Count")
    
    # Invert y-axis to have zero at the top
    plt.gca().invert_yaxis()

    # Save the plot as a PNG file
    base_name = os.path.basename(file_path).rsplit('.', 1)[0]
    output_path = os.path.join('logs', 'plots', f'Token_count_{base_name}.png')
    plt.savefig(output_path, bbox_inches='tight')
    plt.close()

    # Open the file using VS Code
    import subprocess
    subprocess.run(['code', output_path])

    print(f"Token count of segments plot saved to: {output_path}")
    return output_path
def group_segments_select_speaker(segments, speaker):
    """
    Groups consecutive segments not containing the specified speaker's name and selects segments where the speaker's name is found before the timestamp.
    Calls get_timestamp from fileops.py to determine if the first line in a segment is a speaker line.

    :param segments: list of text segments to be processed
    :param speaker: string of the speaker's name to select segments
    :return: list of text segments where the speaker's name is found before the timestamp
    """
    from chalicelib.fileops import get_timestamp

    final_segments = []
    temp_segments = []
    for segment in segments:
        first_line = segment.split('\n', 1)[0]  # Extract the first line of the segment
        timestamp, index = get_timestamp(first_line)
        # Check if the speaker's name is in the portion of the first line before the timestamp index
        if timestamp is not None and speaker in first_line[:index]:
            temp_segments.append(segment)
            final_segments.append('\n\n'.join(temp_segments))
            temp_segments = []
        else:
            temp_segments.append(segment)
    
    # Check if the last temp_segments should be added
    if temp_segments:
        last_segment_first_line = temp_segments[-1].split('\n', 1)[0]
        timestamp, index = get_timestamp(last_segment_first_line)
        if timestamp is not None and speaker in last_segment_first_line[:index]:
            final_segments.append('\n\n'.join(temp_segments))
    
    return [segment for segment in final_segments if segment.strip()]
def group_segments_token_cap(segments, token_cap=1000):
    """
    Groups consecutive segments without exceeding the token_cap, without splitting segments.
    Includes segments that exceed the token_cap as individual blocks.

    :param segments: list of text segments to be processed
    :param token_cap: integer of maximum number of tokens, using words = .75 tokens
    :return: list of grouped text segments without exceeding the token_cap, including oversized segments as individual blocks
    """
    final_segments = []
    temp_segments = []
    current_token_count = 0
    word_cap = token_cap / 0.75

    for segment in segments:
        words_in_segment = len(segment.split())
        if words_in_segment > word_cap:
            # If there are any segments in temp_segments, add them to final_segments
            if temp_segments:
                final_segments.append('\n\n'.join(temp_segments))
                temp_segments = []
                current_token_count = 0
            # Add the oversized segment as an individual block
            final_segments.append(segment)
        else:
            if current_token_count + (words_in_segment * 0.75) > token_cap:
                # If adding the segment would exceed the token cap, finalize the current group
                final_segments.append('\n\n'.join(temp_segments))
                temp_segments = [segment]
                current_token_count = words_in_segment * 0.75
            else:
                # Otherwise, add the segment to the current group
                temp_segments.append(segment)
                current_token_count += words_in_segment * 0.75

    # Add any remaining segments in temp_segments to final_segments
    if temp_segments:
        final_segments.append('\n\n'.join(temp_segments))

    return [segment for segment in final_segments if segment.strip()]
def split_file_select_speaker(file_path, speaker, skip_string='SKIPQA', suffix_new='_blocks'):
    """
    Add block delimiters to a file, with a block for every segment by the selected speaker and other segments grouped together.

    :param file_path: path to the file to be processed
    :param speaker: the speaker whose sections will be delimited
    :param skip_string: string to identify speaker segments to skip
    :param suffix_new: suffix for the new file with block delimiters
    :return: file_path of new file with separator delimiters ("---") with suffix_new='_blocks' by default
    """
    from chalicelib.fileops import read_metadata_and_content, write_metadata_and_content

    metadata, _ = read_metadata_and_content(file_path)
    segments = get_speaker_segments(file_path, skip_string)
    #print(f"\nDEBUG separate segments: {segments}")
    grouped_segments = group_segments_select_speaker(segments, speaker)
    # if final_segments:
    #     print(f"DEBUG: First element of final_segments: {repr(final_segments[0][:100])}")
    new_content = "## content\n\n" + BLOCK_DELIMITER.join(grouped_segments)  # Using the global variable BLOCK_DELIMITER  
    return write_metadata_and_content(file_path, metadata, new_content, suffix_new, overwrite='no')
def split_file_every_speaker(file_path, skip_string=None, suffix_new='_blocks'):
    """
    Add block delimiters to a file with one block per speaker segment regardless of speaker.

    :param file_path: path to the file to be processed
    :param skip_string: string to identify speaker segments to skip
    :param suffix_new: suffix for the new file with block delimiters
    :return: file_path of new file with separator delimiters ("---") with suffix_new='_blocks' by default
    """
    from chalicelib.fileops import read_metadata_and_content, write_metadata_and_content

    metadata, _ = read_metadata_and_content(file_path)
    segments = get_speaker_segments(file_path, skip_string)
    #print(f"\nDEBUG separate segments: {segments}")
    new_content = "## content\n\n" + BLOCK_DELIMITER.join(segments)  # Using the global variable BLOCK_DELIMITER  
    return write_metadata_and_content(file_path, metadata, new_content, suffix_new, overwrite='no')
def split_file_token_cap(file_path, token_cap, skip_string='SKIPQA', suffix_new='_blocks'):
    """
    Add block delimiters to a file with one block per speaker segment regardless of speaker.

    :param file_path: path to the file to be processed
    :param token_cap: integer of maximum number of tokens, using words = .75 tokens
    :param skip_string: string to identify speaker segments to skip
    :param suffix_new: suffix for the new file with block delimiters
    :return: file_path of new file with separator delimiters ("---") with suffix_new='_blocks' by default
    """
    from chalicelib.fileops import read_metadata_and_content, write_metadata_and_content

    metadata, _ = read_metadata_and_content(file_path)
    segments = get_speaker_segments(file_path, skip_string)
    #print(f"\nDEBUG separate segments: {segments}")
    grouped_segments = group_segments_token_cap(segments, token_cap)
    new_content = "## content\n\n" + BLOCK_DELIMITER.join(grouped_segments)  # Using the global variable BLOCK_DELIMITER  
    return write_metadata_and_content(file_path, metadata, new_content, suffix_new, overwrite='no')

### LLM PROCESSING
def save_llm_response_files(response, datetime, model, query, base_dir="exchanges/response_files/", verbose=True):
    """
    Save LLM response as both JSON and pickle files.

    :param response: object, the LLM response to save
    :param datetime: str, datetime string to use in filename
    :param model: str, model name used for the response
    :param query: str, query text to include in filename
    :param base_dir: str, base directory for saving files
    :param verbose: bool, whether to print status messages
    :return: tuple of (json_file_path, pickle_file_path) or None if save failed
    """
    try:
        if response and not isinstance(response, Exception):
            # Trim query for filename
            query_trim = query[:30] + (query[30:].split(None, 1)[0].rstrip('.,!?;:') if len(query) > 30 and not query[30].isspace() else '')
            
            # Generate filenames
            json_filename = f"chat_response_{datetime}_{model}_{query_trim}.json"
            json_file_path = base_dir + json_filename
            pickle_file_path = json_file_path.replace(".json", ".pkl")
            
            # Save JSON file
            json_data = convert_data_object_to_json_data(response, default_handler=None, verbose=False, print_analysis=False, print_values=False)
            cost_pennies_mycalc = get_call_cost_from_response(response, model, TOKEN_PRICE_DICT, verbose=False)
            verbose_print(verbose, f"Cost pennies mycalc: {cost_pennies_mycalc}")
            
            # Add cost to json_data at root level
            json_data['cost_pennies_mycalc'] = cost_pennies_mycalc
            
            write_json_file_from_json_data(json_data, json_file_path, overwrite="yes")
            verbose_print(verbose, colored(f"Response saved to JSON file: {json_file_path}", "green"))
            
            # Save pickle file
            save_object_to_pickle_file(response, pickle_file_path, verbose=False, print_object=False)   
            verbose_print(verbose, colored(f"Response saved to pickle file: {pickle_file_path}", "green"))
            
            return json_file_path, pickle_file_path
    except Exception as e:
        print(f"Error saving response files: {str(e)}")
    return None

### OPENAI LLM
def generate_openai_testcurl_command():
    """
    Generates a single-line curl command for testing the OpenAI API connection.
    Prints the command to the console for easy copy-pasting.
    """
    curl_command = (f"curl https://api.openai.com/v1/chat/completions "
                    f"-H \"Content-Type: application/json\" "
                    f"-H \"Authorization: Bearer {OPENAI_API_KEY}\" "
                    f"-d '{{\"model\": \"{OPENAI_MODEL}\", "
                    f"\"messages\": [{{\"role\": \"user\", \"content\": \"Hello!\"}}]}}'")
    
    print("Copy and paste the following curl command into your terminal:")
    print(curl_command)
def get_openai_models(api_key):
    client = OpenAI(api_key=api_key)
    
    try:
        # Get the list of models
        models = client.models.list()
        
        # Print the IDs of available models
        for model in models.data:
            print(model.id)
    except Exception as e:
        print(f"Error retrieving models: {str(e)}")
def test_openai_connection():
    try:
        response = requests.get("https://api.openai.com")
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Connection error: {e}")
def test_openai_chat(model=OPENAI_MODEL):
    try:
        messages = [{"role": "user", "content": "Tell me a knock knock joke about science."}]
        response = openai_chat_completion_request(messages, model=model)
        if response and response.status_code == 200:
            print("API chat response:", response.json()['choices'][0]['message']['content'])
        else:
            print("Failed to get a valid response from the API")
    except Exception as e:
        print(f"An error occurred: {e}")
@retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
def openai_chat_completion_request(messages, tools=None, tool_choice=None, model=OPENAI_MODEL):  # APIMOCK unittests 2
    """
    Send a chat completion request to the OpenAI API with the provided messages and optional tools and tool choice.

    :param messages: a list of message dictionaries to send in the chat completion request
    :param tools: optional list of tools to include in the request
    :param tool_choice: optional tool choice to include in the request
    :param model: the model to use for the chat completion request
    :return: the response object from the OpenAI API request
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"  # Use the global variable
    }
    json_data = {"model": model, "messages": messages}
    if tools is not None:
        json_data.update({"tools": tools})
    if tool_choice is not None:
        json_data.update({"tool_choice": tool_choice})
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=json_data,
        )
        return response
    except Exception as e:
        print("Unable to generate OpenAI Chat Completion response")
        print(f"Exception: {e}")
        return e
@retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
def openai_chat_completion_request_sdk(messages, model, tools=None, tool_choice=None, reasoning_effort=None, temperature=None, max_completion_tokens=None):
    """
    Send a chat completion request using the OpenAI SDK.

    :param messages: list of message dictionaries
    :param model: the model to use
    :param tools: optional list of tools
    :param tool_choice: optional tool choice
    :param reasoning_effort: optional float to control model reasoning effort
    :param temperature: optional float to control randomness
    :param max_completion_tokens: optional int to limit response length
    :return: the response object from the OpenAI API
    """
    if model.startswith("deepseek"):
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    else:
        client = OpenAI(api_key=OPENAI_API_KEY)
    
    request_params = {
        "model": model,
        "messages": messages,
    }
    if tools is not None:
        request_params["tools"] = tools
    if tool_choice is not None:
        request_params["tool_choice"] = tool_choice
    if reasoning_effort is not None:
        request_params["reasoning_effort"] = reasoning_effort
    if temperature is not None:
        request_params["temperature"] = temperature
    if max_completion_tokens is not None:
        # Use appropriate parameter based on model
        if model.startswith("o") or model.startswith("deepseek"):
            request_params["max_completion_tokens"] = max_completion_tokens
        else:
            request_params["max_tokens"] = max_completion_tokens

    try:
        response = client.chat.completions.create(**request_params)
        return response
    except Exception as e:
        print("Unable to generate OpenAI Chat Completion response")
        print(f"Exception: {e}")
        return e
# TODO: switch to openai_chat_completion_request_sdk carefully and redeploy lambda functions to see if they break
# TODO: refactor so calls openai_chat_completion_request, rename to remove _completion_request
@retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
def simple_openai_chat_completion_request(prompt, model):  # no unittests
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"  # Use the global variable, changed from string literal on 10-5-24 see Coding Notes
    }

    messages = [{"role": "user", "content": prompt}]

    json_data = {"model": model, "messages": messages}
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=json_data,
        )
        response_json = response.json()
        return str(response_json['choices'][0]['message']['content'])
    except Exception as e:
        print("Unable to generate ChatCompletion response")
        print(f"Exception: {e}")
        return str(e)
@retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
def openai_function_call(prompt, content, tools, model=OPENAI_MODEL, verbose=False):
    """
    Send a function call request to the OpenAI API and process the response.

    :param prompt: str, system prompt to set context for the model
    :param content: str, user content to send to the model
    :param tools: list, function definitions for tool calling
    :param model: str, OpenAI model to use for completion
    :param verbose: bool, whether to print debug information
    :return response: str or dict, processed response from the API. Fields are in tool_calls[0].function.arguments
    """
    try:
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": content}
        ]
        
        # Prepare request parameters
        request_params = {
            "messages": messages,
            "model": model
        }
        
        # Only add tools if provided and non-empty
        if tools and len(tools) > 0:
            request_params["tools"] = tools
            if isinstance(tools[0], dict) and "function" in tools[0]:
                request_params["tool_choice"] = {
                    "type": "function",
                    "function": {"name": tools[0]["function"]["name"]}
                }
        
        if verbose:
            pretty_print_function(messages, tools, verbose=verbose)
            
        response = openai_chat_completion_request(**request_params)
        
        if response and response.status_code == 200:
            response_json = response.json()
            
            if "choices" in response_json and len(response_json["choices"]) > 0:
                message = response_json["choices"][0].get("message", {})
                
                # Handle different message formats
                if isinstance(message, str):
                    return message
                elif isinstance(message, dict):
                    if "tool_calls" in message:
                        return message
                    elif "content" in message:
                        return message["content"]
                    
        return None
            
    except Exception as e:
        if verbose:
            print(f"Error in function call: {str(e)}")
        return None
TOOLS_FCALL_TEST_RHYME = [
{
    "type": "function",
    "function": {
        "name": "test_fcall_rhyme",
        "description": "Extract the timestamp and generate a two sentence rhyme",
        "strict": True,  # Add for Stuctured Output
        "parameters": {
            "type": "object",
            "properties": {
                "rhyme": {
                    "type": "string",
                    "description": """
                    Create a two-line rhyming poem based on the content of the input text. The rhyme should capture the key message or theme while maintaining a playful, poetic style. Each line should be grammatically complete and naturally flow into the next. The rhyming words should appear at the end of each line. Keep the language simple and accessible while staying true to the original meaning.
                    """,
                },
                "timestamp": {
                    "type": "string",
                    "description": """
                    The timestamp corresponding to the start of the speaker dialogue in the format H:MM:SS or MM:SS or M:SS (chose whichever is present in the input text). This timestamp is crucial for contextualizing the answer within the transcript and must be accurate to reflect the exact moment the response begins.
                    """,
                },
            },
            "required": ["rhyme","timestamp"],
            "additionalProperties": False  # Add for Stuctured Output
        },
    },
    },
]


### ANTHROPIC LLM
def anthropic_chat_completion_request(messages, model=ANTHROPIC_MODEL, system=None, tools=None, max_tokens=4096, temperature=0.7):
    """
    Make a chat completion request to Anthropic's API.

    :param messages: List of message objects representing the conversation
    :param model: The model to use for the completion
    :param system: System message to set the behavior of the assistant
    :param tools: optional list of tools for function calling
    :param max_tokens: Maximum number of tokens to generate (default: 4096)
    :param temperature: Controls randomness in the output (0 to 1, default: 0.7)
    :return: The complete message response object from Anthropic
    """
    anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Prepare the request parameters
    request_params = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    # Add system message if provided
    if system:
        request_params["system"] = system

    # Add tools if provided
    if tools:
        request_params["tools"] = tools

    # Add messages if provided, otherwise raise an exception
    if messages:
        request_params["messages"] = messages
    else:
        raise ValueError("No messages were provided for Anthropic chat completion request.")

    try:
        # Make the API call and return the full message object
        return anthropic_client.messages.create(**request_params)
    except anthropic.APIError as e:
        print(f"Anthropic API error: {str(e)}")
    except anthropic.APIConnectionError as e:
        print(f"Error connecting to Anthropic API: {str(e)}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
    
    return None
def simple_anthropic_chat(prompt, model=ANTHROPIC_MODEL):
    """
    Simplified version of chat completion that takes a single prompt string.

    :param prompt: str, the prompt to send to the model
    :param model: str, the model to use
    :return: str, the generated response content
    """
    messages = [{"role": "user", "content": prompt}]
    response = anthropic_chat_completion_request(messages=messages, model=model)
    return response.content[0].text
def anthropic_function_call(prompt, content, tools, model=ANTHROPIC_MODEL, verbose=False):
    """
    Send a function call request to the Anthropic API.

    :param prompt: str, system prompt to guide the model's behavior
    :param content: str, the content to process
    :param tools: list of tools/functions available for the model
    :param model: str, the model to use
    :param verbose: bool, whether to print detailed information
    :return: The complete function call response or None if an error occurs. Fields are in content[1].input 
    """
    try:
        messages = [
            {"role": "user", "content": content}
        ]
        
        # Prepare request parameters
        request_params = {
            "messages": messages,
            "model": model,
            "tools": tools,
            "system": prompt,
            "max_tokens": 4096,  # Added to ensure sufficient response length
        }
        
        if verbose:
            print("System:", prompt)
            print("Messages:", messages)
            print("Tools:", tools)
            
        response = anthropic_chat_completion_request(**request_params)
        
        # Return the complete response object
        if response:
            return response
                    
        return None
            
    except Exception as e:
        if verbose:
            print(f"Error in function call: {str(e)}")
        return None
TOOLS_ANT_FCALL_TEST_JOKE = [
    {
        "name": "fcall_test_joke",
        "description": "Extract the timestamp and generate a dad joke",
        "input_schema": {  # Changed from 'parameters' to 'input_schema'
            "type": "object",
            "properties": {
                "joke": {
                    "type": "string",
                    "description": """
                    Create a short, family-friendly dad joke based on the content of the input text. The joke should be in a classic setup-punchline format, incorporating elements from the input while maintaining the groan-worthy charm typical of dad jokes. Keep it simple, clean, and ideally related to the topic at hand.
                    """,
                },
                "timestamp": {
                    "type": "string",
                    "description": """
                    The timestamp corresponding to the start of the speaker dialogue in the format H:MM:SS or MM:SS or M:SS (chose whichever is present in the input text). This timestamp is crucial for contextualizing the answer within the transcript and must be accurate to reflect the exact moment the response begins.
                    """,
                },
            },
            "required": ["joke", "timestamp"]
        },
    }
]
def parse_function_call_response(response, provider="openai"):
    """
    Parse function call response from different providers into a common format.
    
    :param response: The raw response from the API
    :param provider: str, either "openai" or "anthropic"
    :return: dict containing the parsed function arguments or None
    """
    try:
        if provider == "openai":
            if response and "tool_calls" in response:
                return json.loads(response['tool_calls'][0]['function']['arguments'])
        
        elif provider == "anthropic":
            if response and response.content:
                for content_block in response.content:
                    if hasattr(content_block, 'type') and content_block.type == 'tool_use':
                        return content_block.input
        
        return None
    except Exception as e:
        print(f"Error parsing {provider} function call response: {str(e)}")
        return None
def convert_tools_to_anthropic_format(openai_tools):
    """
    Convert OpenAI tool format to Anthropic format.
    
    :param openai_tools: list of tools in OpenAI format
    :return: list of tools in Anthropic format
    """
    anthropic_tools = []
    for tool in openai_tools:
        if "function" in tool:
            anthropic_tool = {
                "name": tool["function"]["name"],
                "description": tool["function"]["description"],
                "input_schema": tool["function"]["parameters"]
            }
            anthropic_tools.append(anthropic_tool)
    return anthropic_tools
def simple_anthropic_chat_rawapi(prompt, model=ANTHROPIC_MODEL):  # Not currently used
    """
    Make a simple chat completion request to Anthropic's API.

    :param prompt: String containing the user's prompt or message
    :param model: String specifying the Anthropic model to use
    :return: String containing the generated message content, or an error message if the request fails
    """
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01"
    }

    json_data = {
        "model": model,
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=json_data,
        )
        response.raise_for_status()  # Raises an HTTPError for bad responses
        response_json = response.json()
        return str(response_json['content'][0]['text'])
    except requests.exceptions.RequestException as e:
        print("Unable to generate ChatCompletion response")
        print(f"Exception: {e}")
        return str(e)


### DEEPSEEK
def test_deepseek_connection():
    try:
        response = requests.get("https://api.deepseek.com")
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Connection error: {e}")
def test_deepseek_chat():
    """
    Tests DeepSeek-v3 API connection by requesting a dad joke.
    """
    try:
        messages = [{"role": "user", "content": "Tell me a dad joke about programming."}]
        response = openai_chat_completion_request_sdk(
            messages=messages,
            model="deepseek-chat",
            max_completion_tokens=1000
        )
        
        if isinstance(response, Exception):
            print(colored("*** ERROR ***", "red"))
            print(f"Error type: {type(response)}")
            print(f"Error message: {str(response)}")
        else:
            print(colored("Dad joke response:", "green"))
            print(response.choices[0].message.content)
                        
    except Exception as e:
        print(f"Test failed: {str(e)}")
def deepseek_chat_completion_request_sdk(messages, model="deepseek-reasoner", max_completion_tokens=None):
    """
    Send a chat completion request using the OpenAI SDK configured for DeepSeek's API.

    :param messages: list of message dictionaries
    :param model: the model to use (default is "deepseek-reasoner")
    :param max_completion_tokens: optional int to limit response length
    :return: the response object from the DeepSeek API
    """
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    
    request_params = {
        "model": model,
        "messages": messages,
    }
    
    # Add max_completion_tokens if specified
    if max_completion_tokens is not None:
        request_params["max_tokens"] = max_completion_tokens

    try:
        response = client.chat.completions.create(**request_params)
        return response
    except Exception as e:
        print("Unable to generate DeepSeek Chat Completion response")
        print(f"Exception: {e}")
        return e
def simple_deepseek_chat(prompt, model="deepseek-reasoner"):
    """
    Simplified version of chat completion that takes a single prompt string.

    :param prompt: str, the prompt to send to the model
    :param model: str, the model to use
    :return: str, the generated response content
    """
    messages = [{"role": "user", "content": prompt}]
    response = deepseek_chat_completion_request_sdk(messages=messages, model=model)
    
    # Access the content through choices[0].message.content
    return response.choices[0].message.content
def deepseek_structured_output(prompt, content, output_schema, model="deepseek-reasoner", verbose=False):
    """
    Get structured output from DeepSeek using their JSON Output feature.
    
    :param prompt: str, system prompt to guide the model's behavior
    :param content: str, the content to process
    :param output_schema: dict, the expected JSON schema structure
    :param model: str, the model to use
    :param verbose: bool, whether to print detailed information
    :return: dict containing the structured response or None if error
    """
    try:
        # Add JSON formatting instruction to prompt
        json_prompt = f"{prompt}\nPlease provide the response in the following JSON format:\n{json.dumps(output_schema, indent=2)}"
        
        messages = [
            {"role": "system", "content": json_prompt},
            {"role": "user", "content": content}
        ]
        
        request_params = {
            "messages": messages,
            "model": model,
            "response_format": {"type": "json_object"}
        }
        
        if verbose:
            print("Messages:", messages)
            
        response = deepseek_chat_completion_request_sdk(**request_params)
        
        if response and response.choices[0].message.content:
            return json.loads(response.choices[0].message.content)
                    
        return None
            
    except Exception as e:
        if verbose:
            print(f"Error in structured output: {str(e)}")
        return None


### REASONING
def reasoning_response_to_md_multipart_deepseek(prompt_parts, response, model, md_file_path, datetime, heading_level=1):
    """
    Process a Deepseek reasoningresponse with multipart prompts and write/append it to a markdown file.

    :param prompt_parts: dict, containing prompt components (query, rag_context, etc.)
    :param response: object, the Deepseek chat completion response object
    :param md_file_path: str, path to the markdown file
    :param heading_level: int, base heading level for the question
    :return: None
    """
    # Create heading markers
    q_level = '#' * heading_level
    sub_level = '#' * (heading_level + 1)
    
    # Get the first choice
    choice = response.choices[0]
    message = choice.message
    usage = response.usage

    cost_pennies_mycalc = get_call_cost_from_response(response, model, TOKEN_PRICE_DICT, verbose=False)
    print(f"Cost Pennies Mycalc: {cost_pennies_mycalc}")

    markdown_content = f"""{q_level} {prompt_parts.get('query', 'No Query Provided')}
model: {model}
date: {datetime}

{sub_level} Answer
{message.content}

{sub_level} Reasoning Content
{message.reasoning_content}

{sub_level} Response Fields
- ID: {response.id}
- Model: {response.model}
- Object: {response.object}
- Created: {response.created}
- Service Tier: {response.service_tier}
- System Fingerprint: {response.system_fingerprint}
- Cost Pennies Mycalc: {cost_pennies_mycalc}

Choice Details:
- Finish Reason: {choice.finish_reason}
- Index: {choice.index}
- Log Probs: {choice.logprobs}

Message Details:
- Role: {message.role}
- Refusal: {message.refusal}
- Audio: {message.audio}
- Function Call: {message.function_call}
- Tool Calls: {message.tool_calls}

Usage Statistics:
- Total Tokens: {usage.total_tokens}
- Completion Tokens: {usage.completion_tokens}
- Reasoning Tokens: {usage.completion_tokens_details.reasoning_tokens}
- Prompt Tokens: {usage.prompt_tokens}

Completion Tokens Details:
- Accepted Prediction Tokens: {usage.completion_tokens_details.accepted_prediction_tokens}
- Audio Tokens: {usage.completion_tokens_details.audio_tokens}
- Rejected Prediction Tokens: {usage.completion_tokens_details.rejected_prediction_tokens}

Prompt Tokens Details:
- Audio Tokens: {usage.prompt_tokens_details.audio_tokens}
- Cached Tokens: {usage.prompt_tokens_details.cached_tokens}

Cache Statistics:
- Prompt Cache Hit Tokens: {usage.prompt_cache_hit_tokens}
- Prompt Cache Miss Tokens: {usage.prompt_cache_miss_tokens}

## Prompts
### Prompt Initial
{prompt_parts.get('prompt_initial', '').strip()}

### Query Context
{prompt_parts.get('query_context', '').strip()}

### RAG Context
{prompt_parts.get('rag_context', '').strip()}

### Large Context (FILE PATH ONLY)
from file: {prompt_parts.get('large_context_file_path', 'No file path provided')}"""

    # Read existing content if file exists
    existing_content = ''
    if os.path.exists(md_file_path):
        with open(md_file_path, 'r') as f:
            existing_content = f.read()
    
    # Write new content at the top, followed by existing content
    with open(md_file_path, 'w') as f:
        f.write(markdown_content)
        if existing_content:
            f.write('\n\n\n' + existing_content)
    
    print(f"Reasoning response from deepseek saved to markdown file: {md_file_path}")
def reasoning_response_to_md_multipart_openai(prompt_parts, response, model, md_file_path, datetime, heading_level=1):
    """
    Process an OpenAI reasoning response with multipart prompts and write/append it to a markdown file.
    This function is tailored to the OpenAI response object structure.

    :param prompt_parts: dict, containing prompt components (query, rag_context, etc.)
    :param response: object, the OpenAI chat completion response object
    :param model: str, the model used (e.g. "o3-mini-2025-01-31")
    :param md_file_path: str, path to the markdown file
    :param datetime: str, a file-friendly datetime string
    :param heading_level: int, base heading level for the question
    :return: None
    """
    # Create heading markers based on the specified level
    q_level = '#' * heading_level
    sub_level = '#' * (heading_level + 1)
    
    # Get the first choice and its associated message and usage
    choice = response.choices[0]
    message = choice.message
    usage = response.usage

    # No reasoning content in OpenAI response - skip section

    cost_pennies_mycalc = get_call_cost_from_response(response, model, TOKEN_PRICE_DICT, verbose=False)
  
    markdown_content = f"""{q_level} {prompt_parts.get('query', 'No Query Provided')}
model: {model}
date: {datetime}

{sub_level} Answer
{message.content}

{sub_level} Response Fields
- ID: {response.id}
- Model: {response.model}
- Object: {response.object}
- Created: {response.created}
- Service Tier: {response.service_tier}
- System Fingerprint: {response.system_fingerprint}
- Cost Pennies Mycalc: {cost_pennies_mycalc}
Choice Details:
- Finish Reason: {choice.finish_reason}
- Index: {choice.index}
- Log Probs: {choice.logprobs}

Message Details:
- Role: {message.role}
- Refusal: {message.refusal}
- Audio: {message.audio}
- Function Call: {message.function_call}
- Tool Calls: {message.tool_calls}

Usage Statistics:
- Total Tokens: {usage.total_tokens}
- Completion Tokens: {usage.completion_tokens}
- Prompt Tokens: {usage.prompt_tokens}

Completion Tokens Details:
- Accepted Prediction Tokens: {usage.completion_tokens_details.accepted_prediction_tokens}
- Audio Tokens: {usage.completion_tokens_details.audio_tokens}
- Rejected Prediction Tokens: {usage.completion_tokens_details.rejected_prediction_tokens}
- Reasoning Tokens: {usage.completion_tokens_details.reasoning_tokens}

Prompt Tokens Details:
- Audio Tokens: {usage.prompt_tokens_details.audio_tokens}
- Cached Tokens: {usage.prompt_tokens_details.cached_tokens}

## Prompts
### Prompt Initial
{prompt_parts.get('prompt_initial', '').strip()}

### Query Context
{prompt_parts.get('query_context', '').strip()}

### RAG Context
{prompt_parts.get('rag_context', '').strip()}

### Large Context (FILE PATH ONLY)
from file: {prompt_parts.get('large_context_file_path', 'No file path provided')}"""

    # Prepend the new markdown content to the existing file (if any)
    existing_content = ""
    if os.path.exists(md_file_path):
        with open(md_file_path, 'r') as f:
            existing_content = f.read()
    
    with open(md_file_path, 'w') as f:
        f.write(markdown_content)
        if existing_content:
            f.write('\n\n\n' + existing_content)
    print(f"Reasoning response from openai saved to markdown file: {md_file_path}")
def reasoning_prompt_to_md_multipart(prompt_parts, model, md_file_path, heading_level=1, save_files=True):
    """
    Process a multipart reasoning prompt and write/append it to a markdown file.
    Only writes to the file if the response is successful.
    Returns the raw response from the model which can be saved or ignored.

    :param prompt_parts: dict, containing prompt components:
        - prompt_initial: str, initial prompt text
        - query: str, the main query
        - query_context: str, formatted query context
        - rag_context: str, RAG context to include in markdown
        - large_context: str, additional context (not included in markdown)
    :param md_file_path: str, path to the markdown file
    :param heading_level: int, base heading level for the question
    :return: None
    """
    # Combine all parts for the full prompt
    full_prompt = (
        prompt_parts.get('prompt_initial', '').strip() + '\n\n' +
        prompt_parts.get('query_context', '').strip() + '\n\n' +
        prompt_parts.get('rag_context', '').strip() + '\n\n' +
        prompt_parts.get('large_context', '').strip()
    ).strip()

    messages = [{"role": "user", "content": full_prompt}]
    if model.startswith("deepseek"):
        response = deepseek_chat_completion_request_sdk(messages=messages)
    elif model.startswith("o1") or model.startswith("o3"):
        response = openai_chat_completion_request_sdk(messages=messages, model=model)
    else:
        raise ValueError(f"Model '{model}' is not supported. Must start with 'deepseek' or 'o1' or 'o3'.")

    # print(colored("Full response object:", "green"))
    # print(response)

    # DEBUG START - load the response from a file ##########################
    # REMEMBER TO COMMENT OUT THE response = deepseek_chat_completion_request_sdk line above
    # response_json_file = f""  # have this here so can comment out the different DEBUG parts below
    # response = get_response_from_json_file(response_json_file)
    # print(f"Loaded response from file: {response_json_file}")
    # DEBUG END  #########################################################
    
    # Format the response
    datetime = get_current_datetime_filefriendly()

    # Save the response to a JSON file
    if save_files:
        save_llm_response_files(response, datetime, model, prompt_parts.get('query', '').strip())
    
    # Only proceed if response is successful (not an Exception)
    if isinstance(response, Exception):
        print(f"Error generating response: {str(response)}")
        return None

    if model.startswith("deepseek"):
        reasoning_response_to_md_multipart_deepseek(prompt_parts, response, model, md_file_path, datetime, heading_level=heading_level)
    elif model.startswith("o1") or model.startswith("o3"):
        reasoning_response_to_md_multipart_openai(prompt_parts, response, model, md_file_path, datetime, heading_level=heading_level)
    else:
        raise ValueError(f"Model '{model}' is not supported. Must start with 'deepseek' or 'o1' or 'o3'.")


### LLM PROCESSING
# TODO clean up 'prompt' terminology so system prompt is properly distinguished
def llm_process_block(block, prompt, provider="openai"):
    """
    Processes a single block of text with a given prompt using the OpenAI chat completion API.

    :param block: string of the text block to be processed.
    :param prompt: string of the prompt to use for the chat completion request.
    :param provider: string indicating the LLM provider (default is "openai").
    :return: string of the processed text block or None if no valid response is received.
    """
    if provider == "openai":
        messages = [{"role": "system", "content": prompt}, {"role": "user", "content": block}]
        print("OPENAI LLM = " + OPENAI_MODEL)
        chat_response = openai_chat_completion_request(messages)

        if chat_response.status_code == 200:
            response_json = chat_response.json()
            #print(f"DEBUG llm_process_block print full response_json:\n {response_json}")
            if 'choices' in response_json and len(response_json['choices']) > 0:
                return response_json['choices'][0]['message']['content']
            else:
                print("No 'choices' in response or 'choices' list is empty.")
                return None
        else:
            print(f"Request failed with status code {chat_response.status_code}: {chat_response.text}")
            return None
    else:
        raise ValueError(f"Provider '{provider}' is not set up yet.")
# TODO Figure out what the right metadata and content function does as suffix new is passed with an empty string. See chat history and test it
# TODO consider adding boolean to keep speaker lines
def llm_process_file_blocks(blocks_file_path, prompt, suffix_new, mode, provider="openai", retain_delimiters=False):
    """
    Processes blocks of text in a file using a specified prompt and operation mode, then writes the processed content back to the file.

    :param blocks_file_path: string of the path to the file containing text blocks
    :param prompt: string of the prompt to use for processing each text block
    :param suffix_new: string of the suffix to append to the file when saving the new content
    :param mode: string of the operation mode ('replace' or 'append') to handle the processed blocks
    :param provider: string indicating the LLM provider (default is "openai")
    :param retain_delimiters: boolean indicating whether to retain the original block delimiters in the new content
    :return: the path to the file with the updated content
    """
    from chalicelib.fileops import read_metadata_and_content, write_metadata_and_content
    
    if mode not in ['replace', 'append']:
        raise ValueError("mode must be 'replace' or 'append'.")

    metadata, content = read_metadata_and_content(blocks_file_path)
    content = content.lstrip("## content\n\n")
    blocks = content.split(BLOCK_DELIMITER)

    processed_blocks = []
    print(f"BLOCKS TO PROCESS WITH SIMPLE LLM CALL: {len(blocks)}\n")
    print(colored(f"Simple LLM Call Prompt: {prompt}\n", "red"))

    for i, block in enumerate(blocks):
        print(f"\n\nBlock number: {i+1}")
        llm_response = llm_process_block(block, prompt, provider)
        if llm_response:
            if mode == 'replace':
                processed_blocks.append(llm_response)
            elif mode == 'append':
                processed_blocks.append(block + "\n" + llm_response)
            print(colored("User Input:", "green"))
            print(colored(block, "green"))
            print(colored("LLM Response:", "blue"))
            print(colored(llm_response, "blue"))
        else:
            print("No response received for block.")
    print(colored(f"\nSingle LLM call prompt: {prompt}\n", "red"))
    
    new_content = '## content\n\n'
    new_content += '\n\n'.join(processed_blocks) if not retain_delimiters else BLOCK_DELIMITER.join(processed_blocks)
    return write_metadata_and_content(blocks_file_path, metadata, new_content, suffix_new, overwrite='no-sub')
def scall_replace(blocks_file_path, prompt, suffix_new='_scall-replace', provider="openai", retain_delimiters=False):
    """
    Processes a file's text blocks and replace the original text with LLM-processed content based on a given prompt.
    
    :param blocks_file_path: string of the path to the file containing text blocks
    :param prompt: string of the prompt to use for processing each text block
    :param suffix_new: string of the suffix to append to the file when saving the new content
    :param provider: string indicating the LLM provider (default is "openai")
    :param retain_delimiters: boolean indicating whether to retain the original block delimiters in the new content
    :return: string of the path to the file with the updated content
    """
    return llm_process_file_blocks(blocks_file_path, prompt, suffix_new, 'replace', provider=provider, retain_delimiters=retain_delimiters)
def scall_append(blocks_file_path, prompt, suffix_new='_scall-append', provider="openai", retain_delimiters=False):
    """
    Processes a file's text blocks to append LLM-processed content based on a given prompt after the original text.
    
    :param blocks_file_path: string of the path to the file containing text blocks
    :param prompt: string of the prompt to use for processing each text block
    :param suffix_new: string of the suffix to append to the file when saving the new content
    :param provider: string indicating the LLM provider (default is "openai")
    :param retain_delimiters: boolean indicating whether to retain the original block delimiters in the new content
    :return: string of the path to the file with the updated content
    """
    return llm_process_file_blocks(blocks_file_path, prompt, suffix_new, 'append', provider=provider, retain_delimiters=retain_delimiters)
def create_simple_llm_file(file_path, prompt, suffix_new, mode, split_file_function, provider="openai", *args, **kwargs):
    """
    Processes a file with a simple llm call to create a LLM-processed version using a specified block separation function and prompt.
    Substitutes the suffix_new for the original suffix of the file_path.

    :param file_path: string of the path to the file to be processed
    :param prompt: string of the prompt to use for processing each text block
    :param suffix_new: string of the new suffix that will be substituted for the original suffix
    :param mode: string indicating the operation mode ('replace' or 'append')
    :param split_file_function: function used to separate the file into blocks
    :param provider: string indicating the LLM provider (default is "openai")
    :param args: additional positional arguments passed to the block separation function
    :param kwargs: additional keyword arguments passed to the block separation function
    :return: string of the path to the file with the updated content
    """
    from chalicelib.fileops import delete_file

    # Call the block separation function without 'retain_delimiters'
    # Make a shallow copy of kwargs without 'retain_delimiters' for the separation function
    separation_kwargs = {key: value for key, value in kwargs.items() if key != 'retain_delimiters'}
    blocks_file_path = split_file_function(file_path, *args, **separation_kwargs)

    # Prepare kwargs for scall_replace or scall_append, including 'retain_delimiters'
    llm_kwargs = kwargs.copy()
    llm_kwargs['retain_delimiters'] = kwargs.get('retain_delimiters', False)

    if mode == "replace":
        llm_file_path = scall_replace(blocks_file_path, prompt, suffix_new=suffix_new, provider=provider, **llm_kwargs)
    elif mode == "append":
        llm_file_path = scall_append(blocks_file_path, prompt, suffix_new=suffix_new, provider=provider, **llm_kwargs)
    else:
        raise ValueError("mode must be 'replace' or 'append'.")
    delete_file(blocks_file_path)
    return llm_file_path


### LLM TRANSCRIPT PROCESSING
PROMPT_SUMMARIZE_3_KEYWORDS = """
Summarize the text after the speaker line as 3 keywords that best captures what is said.
Return the new key word line as the next line directly underneath the speaker line.
"""
PROMPT_QUOTATIONS = """
You are an expert at transcript processing, you are to evaluate the provided text according to specific quotation guidelines. Your task is to ensure that all instances of direct speech, internal monologue, specific terms, and imitations are correctly enclosed in single quotation marks. Additionally, you must identify and correct instances where quotations are missing or misused. Follow these guidelines:

1. Use single quotes ' ' for direct speech in anothers voice. Include a comma before the quote if it's preceded by a speech attribution (e.g., he said, she asked). Example correction: John said hello → John said, 'hello'.

2. Use single quotes for internal monologue presented as direct speech.

3. For specific terms, jargon, or phrases, use quotes, but do not add commas before the quotes. Place punctuation inside the single quotes.

4. Contextually decide if quotes are needed for ambiguous sentences.

In addition to those rules for quotations, please note the following things to keep in mind.

*  Do not add quotes for indirect speech. ie: they expressed their appreciation for them

*  For nested dialogue, use single quotes for the primary speech and double quotes for the nested part. 

*  Keep punctuation inside the single quotes for full sentences. For fragments, place punctuation outside.

*  For interrupted dialogue, continue the sentence within the same quotes after the tag or action.

*  Use single quotes for special cases like sarcasm or mimicry.

* Pay special attention to specific and related patterns that my preceed a quotation. These patterns include but are not limited to:
"they might say, "
"say well, "
"oh,"
"might ask"

Your primary tasks are to:
- Identify and fix instances where quotations are incorrectly applied.
- Locate and edit parts of the text where quotations are necessary but missing, according to these guidelines.

Please evaluate the text provided and make necessary corrections or suggest where quotations should be added or amended.
If an existing quotation is found your response should be the quote itself in curly braces, followed by a few word description of the problem with '**' at either end. if there is no problem with the existing quotation, just say 'CORRECT' for that description. If there is text that is not enclosed in quotes that shouldnt be, then DONT RETURN ANYTHING FOR IT. IGNORE IT. THE CURLY BRACES ARE AN IMPORTANT FLAG, USE THEM.
If there is a section that, according to the rules should have a quote, then return the section that should be quoted, with a few extra words from the text on either side. the quotes should be applied and flagged by curly braces and a description that uses the number of the rule that is being referenced to make the call.
If no changes at all are to be needed, please only respond with 'N/A'. Only use 'N/A' when there are no errors or quotes in the entire block."""
PROMPT_COPYEDIT = """
You are an expert in copyediting interview transcripts. Your task is to refine the transcript while preserving its verbatim nature. Follow these guidelines:
1. General Principles:
- Maintain verbatim transcription: Preserve the speaker's original words and speech patterns as much as possible.
- Aim for a polished and readable transcript while keeping the original meaning and style intact.
- Don't rephrase.
- Don't make drastic changes, don't make any changes that does not align with the given guidelines.
- Don't correct grammatical errors.
- Don't remove words if unnecessary or if it does not fall in any of the following guidelines mentioned.

2. Speaker Transitions and Segmentation based on context:
- Correct unsplit speaker segments based on context and conversation flow.

3. Proper Names and Terminology:
- Correct and standardize spelling of proper names, places, and specialized terms.
- Capitalize proper nouns appropriately.
- Capitalize also the positions and organizations (e.g., Town Manager, Town Council, Fire Marshal)
- Use unpunctuated acronyms, please don't add periods in between (e.g., ASCC instead of A.S.C.C.)

4. Transcription Error Correction:
- Identify and fix words that don't make sense given the surrounding context. (e.g., 'The cat jumped over the moon'  might be an error for 'The cat jumped over the broom.')
- Replace the informal word 'gonna' with 'going to' and 'wanna' with 'want to' 

5. Punctuations and Formatting:
- Use appropriate punctuation: commas, periods, question marks.
- Use double quotation marks ("") for quoted speech or phrase, meaning when the speaker is quoting someone else's words.
- Don't use exclamation marks (!) replace them with periods (.).
- If there are any forward slash (/) or backslash (\), replace them with dashes (-).
- Don't use semicolons (;) and colons (:), if needed then use commas (,) instead.
- Don't use hyphens (—) or dashes (-), if needed then use commas (,) instead.
- Don't use this format of ellipsis '…', use three periods (...) instead.

6. Disfluencies and Filler Words:
- Remove repetitions unless they add meaning (e.g., 'I I' change to 'I', 'this this' chang to 'this', 'he said that he said that' change to 'he said that').
- Remove 'uh' and 'um' unless they significantly impact meaning.
- Retain 'you know,' 'I mean,' 'like,' and 'yeah' if they add meaning to the statement.
- Only use commas for restarts, hesitations, and self-corrections (e.g., I want to, I mean, I need to fix, or rather, correct this issue.).
- Don't use hyphen (—) or dashes (-) for restarts, hesitations, and self-corrections.

7. Time and Dates:
- Change time format from 24-hour to 12-hour when appropriate (e.g., 14:00 to 2 o'clock).   
- Format dates consistently, as much as possible use the long format date (e.g., June 1st, June 4th).

8. Special Characters and Formatting:
- Spell out currency types (e.g., change $123 to 123 dollars).
- Use the special character '&' only if needed in the proper name (e.g., AT&T).
- Replace special characters with their standard English equivalents (e.g., Gödel to Godel).

9. Quotations and Specific Terms:
- Use double quotation marks if the speaker is quoting someone's words (e.g., Popper said, "Science must begin with myths, and with criticism of myths.").
- Follow the American style for quotations, place periods and commas inside quotation marks.

Here are examples with explanations of the kinds of edits I'm looking:
<example1>
Before: Dale Pfau (EPC Chair)  [9:14](https://youtu.be/hNFjjFll1EY&t=554)
When the new ones come out? We we will probably review them at least in September. We'll review full committing yet. Do you have any do you have any idea when that might happen?

After: Dale Pfau (EPC Chair)  [9:14](https://youtu.be/hNFjjFll1EY&t=554)
When the new ones come out? We will probably review them at least in subcommittee and may bring them to full committee. Yeah. Do you have any idea when that might happen?

Explanation:
- Removed repetition of "we".
- Corrected "full committing" to "full committee" based on context.
- Removed repetition of "do you have any".
- Added "Yeah." to separate the response to the previous question from the new question.
</example1>

<example2>
Before: Dale Pfau (EPC Chair)  [15:30](https://youtu.be/hNFjjFll1EY&t=930)
To add to that. I've had Starlink a little over a year now. I use it. I primarily got it as a backup to another Internet connection I have that goes out. StarLink never goes out. As long as you've got power, it's gonna be there. So even AT and T Fiber goes out occasionally when they lose power.

After: Dale Pfau (EPC Chair)  [15:30](https://youtu.be/hNFjjFll1EY&t=930)
To add to that, I've had Starlink a little over a year now. I use it. I primarily got it as a backup to another internet connection I have that goes out. Starlink never goes out. As long as you've got power, it's going to be there. So even AT&T Fiber goes out occasionally when they lose power.

Explanation:
- Added a comma after "To add to that".
- Changed "Internet" to lowercase "internet" as it's not a proper noun.
- Corrected the proper noun "StarLink" to "Starlink".
- Changed "gonna" to "going to" for formality.
- Corrected the proper noun "AT and T" to "AT&T".
</example2>

Please apply the necessary corrections to the transcript while maintaining the integrity of the spoken content. Remember that when in doubt and it's not specified in the given guidelines, prioritize preserving the original speech over making grammatical improvements. If you're unsure about a potential edit, flag it for human review, add *** in the beginning and end of the word or phrase that needs to be reviewed.

Before providing your final response, think through your edits step by step to ensure consistency and adherence to the provided guidelines.
"""
# TODO need to test - not tested after removing ffop code
def create_copyedit_file(file_path, split_file_function, prompt, *args, **kwargs):
    """
    Processes a file for copyediting by separating it into blocks, applying a prompt to each block, and appending the results to a new file with a '_copyedit' suffix.
    Uses an argument to pass in the separator function, in case you want different types of blocks

    :param file_path: string of the path to the file to be processed
    :param split_file_function: function used to separate the file into blocks
    :param prompt: string of the prompt to use for processing each text block
    :param args: additional positional arguments passed to the block separation function
    :param kwargs: additional keyword arguments passed to the block separation function
    :return: string of the path to the file with the updated content
    """
    from chalicelib.fileops import delete_file
    
    blocks_file_path = split_file_function(file_path, *args, **kwargs)
    copyedit_file_path = scall_replace(blocks_file_path, prompt, retain_delimiters=True, suffix_new='_llmce')
    delete_file(blocks_file_path)
    return copyedit_file_path
PROMPT_TRANSITIONS = """
    Your task is to analyze transcripts for speaker transition errors. 
    You will do this on a single speaker segment where the speaker segments are identified by a speaker name followed by a time stamp with a link. And then on the next line, the segment text, which is the dialogue of what that speaker
    The intended target segment is identified as the segment that follows the following text "TARGET SEGMENT TO ANALYZE FOR TRANSITIONS".
    The input text I'm providing contains the ending speaker text from the speaker segment above, and it also contains below the target segment the beginning text from below. And those adjacent text are provided for context so you can look to see if there are words from the previous segment that should be in the target segment, and likewise if there are words from the next segment that should, that start the next segment that should be at the end of the target segment.    
    For your analysis, ignore any text on the speaker line itself, which is the line that contains the speaker name and the timestamp. There could be additional words after that for other processing. Just ignore those, such as 'SKIPQA'
    
    To do the analysis To look for possible transition errors in the target segment, what you should do is look at the ending words of the text above, which is from the previous segment, and see if they both, see if that text both looks out of place at the end of that text, and then insert that text at the beginning of the speaker segment text for the target segment and see if that fits better as a speaker dialogue. And you can also analyze that target speaker segment text to see if it looks out of place without the added text.

    If your analysis concludes that there are no transition errors in the text for the target segment, then make your response only the text "No suspected transition errors."
    If your analysis concludes that there are transition errors, then state what those are with quoted text, but do not reproduce the entire text for the target segment. I will make the modifications manually.
    """
PROMPT_TRANSITIONS_2 = """
    Your task is to analyze transcripts for speaker transition errors. You will be given entiere speaker segments and you will return suggestions if needed. Follow these guidelines:
1. **Speaker Transitions (ST) - Identifying Missing Speaker Transitions**:
   - ALWAYS Flag and suggest changes when there is a possible interjection from another speaker such as these listed:
        - 'Yes, I agree.'
        - 'Okay.'
        - 'Right.'
    - Be creative and think deeply about any sentence that could be from a different speaker and flag it with curly braces if there is doubt that the entire block is from a single speaker.
    - If there is any text at all that could be interpreted as coming from a seperate speaker, than Flag it for review.
    - Heavily favor tagging possible errors in the middle of a speaker block, rather than at the beggining or end. Do not flag anything at the beginning or the end of a block. assume that whatever is there is correct.
3. **Evaluating Overlapping Talk**:
   a) If overlapping talk is short and doesn't affect meaning, suggest integrating it into the next speaker segment.
   b) If moving the overlap confuses the start of the next segment and the overlapping statement is short and insignificant, suggest deletion.
   c) If the overlapping statement is significant and moving it confuses the start of the next segment, suggest adding a new speaker segment.

Your response if a change is considered to be needed should be of the entire text given to you, but with the problematic section enclosed in curly braces, followed by a few word description of the problem with '**' at either end. THE CURLY BRACES ARE AN IMPORTANT FLAG, USE THEM.
If no changes at all are to be needed, please only respond with 'N/A'. Only use 'N/A' when there are no errors in the entire block. The parts that are without error before or after an error should still be returned.
    """
def mod_blocks_file_with_adjacent_words(blocks_file_path, num_adjacent_words):
    """
    Modifies the content of a file by adding a specified number of words from the previous and next blocks to each block.
    Also adds a Markdown heading and content at the beginning of the new content.
    :param blocks_file_path: string of the path to the file containing text blocks
    :param num_adjacent_words: integer indicating the number of words to add from adjacent blocks
    :return: None
    """
    from chalicelib.fileops import read_metadata_and_content, write_metadata_and_content

    metadata, content = read_metadata_and_content(blocks_file_path)
    content = content.lstrip("## content\n\n")
    blocks = content.split(BLOCK_DELIMITER)
    modified_blocks = []

    for i, block in enumerate(blocks):
        # Extract context from the preceding and following blocks
        prev_context = ' '.join(blocks[max(0, i-1)].split()[-num_adjacent_words:]) if i > 0 else ''
        # TODO modify this to use a yet-to-be-created is_speaker_line function (work w and without timestamps) to skip the speaker line if it's there, for now just add 3
        next_context = ' '.join(blocks[min(len(blocks)-1, i+1)].split()[:num_adjacent_words+3]) if i < len(blocks)-1 else ''
        
        # Concatenate the context with the current block, ensuring two new lines between contexts and the block
        augmented_block = f"{prev_context}\n\nTARGET SEGMENT\n{block}\n\n{next_context}".strip()
        modified_blocks.append(augmented_block)

    # Join modified blocks with delimiters
    new_content = "## content\n\n" + BLOCK_DELIMITER.join(modified_blocks)  

    # Overwrite the file with the modified content
    write_metadata_and_content(blocks_file_path, metadata, new_content, overwrite='yes')
    print(f"Modified block file with adjacent words for block file: {blocks_file_path}")
# TODO need to test - not tested after removing ffop code
def scall_replace_adjacent_words(blocks_file_path, prompt, adjacent_words, retain_delimiters=False, suffix_new='_scall-replace-adj'):
    """
    Replaces words adjacent to each block in a file with a language model processed version based on a given prompt.

    :param blocks_file_path: string of the path to the file containing text blocks
    :param prompt: string of the prompt to process each block with
    :param adjacent_words: integer indicating the number of words to add from adjacent blocks
    :param retain_delimiters: boolean indicating whether to retain original block delimiters
    :param suffix_new: string of the suffix to append to the new file name
    :return: string of the path to the modified file
    """
    mod_blocks_file_with_adjacent_words(blocks_file_path, adjacent_words)
    return llm_process_file_blocks(blocks_file_path, prompt, suffix_new, 'replace', retain_delimiters)
# TODO need to test - not tested after removing ffop code
def create_transitions_file(file_path, split_file_function, prompt, *args, **kwargs):
    """
    Creates a file with transitions between blocks processed by a language model based on a given prompt.

    :param file_path: string of the path to the original file
    :param split_file_function: function used to separate the original file into blocks
    :param prompt: string of the prompt to process each block with
    :return: string of the path to the transitions file
    """
    from chalicelib.fileops import delete_file
    adjacent_words = 10

    blocks_file_path = split_file_function(file_path, *args, **kwargs)
    transitions_file_path = scall_replace_adjacent_words(blocks_file_path, prompt, adjacent_words, retain_delimiters=True, suffix_new='_transitions')
    delete_file(blocks_file_path)
    return transitions_file_path


### QA GENERATION
FCALL_PROMPT_QA_DIALOGUE_STATEDQA = """
You are an expert text analyzer that is trained in identifying stated questions and answers in transcripts of dialogue. You will be given blocks of dialogue and your role is to return extracted question and answer pairs that faithfully capture the meaningful content in the dialogue, while removing filler words and minimally modifying the text for clarity and readability. You will use your tool to only return exact JSON in the format specified.
"""
FCALL_PROMPT_QA_DIALOGUE_ORIGQUERY = """
The question should capture the essence of the original query posed by the interviewer in a simplified, generic form. It should focus on the core topic or idea, removing extraneous contextual details. The modified question should have semantic alignment with {speaker}'s answer. The question should be rephrased for a third-person audience, ensuring it is generalized and does not include direct references to {speaker}. DO NOT mention the name {speaker} in the question.
""" 
FCALL_PROMPT_QA_DIALOGUE_FROMANSWER = """
You are an expert text analyzer that is trained in identifying questions or implied questions. You will be given dialogue and your role is to return a create a general, simple question from the provided answer of the speaker {speaker}. This created general question may or may not be related to the question actually asked in the dialogue preceding the answer. The created general question will be part of a question and answer set used for Retrieval Augmented Generation. The question must not mention any speaker names. You will use your tool to only return exact JSON in the format specified.
"""
CUSTOM_INSTRUCTIONS_DEUTSCH_GENERALQ = """
Analyze the following passage and create a general, simple question for which the answer will be the response. This will be part of a question and answer set such that new questions are compared against the questions, and answers retrieved. The question should not mention the author, or David Deutsch. The question should be written in such a way that it assumes that the answer provided is the best knowledge humanity has about this topic at present moment. Use the phrase 'multiverse quantum theory' rather than 'many-worlds interpretation of quantum'
"""
FCALL_PROMPT_QA_DEUTSCH = """
You are an expert text analyzer that is trained in identifying questions or implied questions. You will be given dialogue and your role is to return a create a general, simple question from the provided answer. This created general question may or may not be related to the question actually asked by the speaker in the dialogue preceding the answer. The created general question will be part of a question and answer set used for Retrieval Augmented Generation. The question must not mention the speaker name. The question should be written in such a way that it assumes that the answer provided is the best knowledge humanity has about this topic at present moment.  Some specific phrases to use include: 1) 'multiverse quantum theory' - rather than 'many-worlds interpretation of quantum'. You will use your tool to only return exact JSON in the format specified. 
"""
def tools_qa_speaker(speaker):
    """
    Generate a list of tools for question and answer extraction based on the speaker's response.

    :param speaker: string of the speaker's name whose responses are being analyzed
    :return: list of dictionaries containing tool configurations for QA extraction
    """
    return[
{
    "type": "function",
    "function": {
        "name": "get_qa",
        "description": "Extract and modify a question into a generic form and provide the exact verbatim answer from a transcript",
        "strict": True,  # Add for Stuctured Output
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description":f"""
                    You are an expert text analyzer that is trained in identifying questions or implied questions. You will be given dialogue and your role is to return a create a general, simple question from the provided answer of the speaker {speaker}. This created general question may or may not be related to the question actually asked in the dialogue preceding the answer. The created general question will be part of a question and answer set used for Retrieval Augmented Generation. The question must not mention any speaker names. You will use your tool to only return exact JSON in the format specified.
                    """ , 
                },
                "timestamp": {
                    "type": "string",
                    "description": f"""
                    The timestamp corresponding to the start of {speaker}'s response in the format H:MM:SS or MM:SS or M:SS (chose whichever is present in the input text). This timestamp is crucial for contextualizing the answer within the transcript and must be accurate to reflect the exact moment the response begins.
                    """, 
                },
            },
            "required": ["question","timestamp"],
            "additionalProperties": False  # Add for Stuctured Output
        },
    },
    },
    ]
def fcall_qa_speaker(block_file_path, speaker, fcall_prompt, suffix_new="_qa"):  # skip unittests because called below
    """ 
    Processes a transcript file already sectioned into blocks to generate new question and answer file.
    Answers are based on the speaker segments of the provided speaker.
    Uses OpenAI function calling.

    :param block_file_path: string of the path to the _blocks file to be processed.
    :param speaker: string of the speaker's name for the answers in QA.
    :param fcall_prompt: string of the prompt to be used for function calling.
    :param suffix_new: string of the suffix to be appended to the original filename for the new file. Defaults to "_qa".
    :return: string of the path to the newly created file with QA
    """
    print("***Running fcall_qa on file: " + block_file_path)
    
    metadata, block_content = read_metadata_and_content(block_file_path)
    # Corrected line: pass file_path instead of metadata
    metadata = set_metadata_field(metadata, "last updated", 'Created QA')

    blocks = block_content.split(BLOCK_DELIMITER)

    print(f"QA BLOCKS TO PROCESS: {len(blocks)}\n")
    print(colored(f"System Prompt: {fcall_prompt}\n", "red"))
    pretty_print_function_descriptions(tools_qa_speaker(speaker), "red")
    
    qa_content = "## content\n\n"
    for i, block in enumerate(blocks):
        print(f"\n\nQA BLOCK NUMBER: {i+1}")
        qa_response = openai_function_call(fcall_prompt, block, tools_qa_speaker(speaker)) # Finish function to return textual output 
        
        # Extract the 'arguments' field from the function call
        arguments_json = qa_response['tool_calls'][0]['function']['arguments']

        # Attempt to parse the JSON
        try:
            arguments = json.loads(arguments_json)
            question = arguments['question']
            timestamp = arguments['timestamp']
            answer = block[block.rfind(')') + 1:].strip()

        except json.decoder.JSONDecodeError as e:
            print("JSONDecodeError:", e)
        # Extract the question and answer

        qa_content += f"QUESTION: {question}\nTIMESTAMP: {timestamp}\nANSWER: {answer}\nEDITS: \nTOPICS: \nSTARS: \n\n"

    qa_file_path = write_metadata_and_content(block_file_path, metadata, qa_content, suffix_new)
    print("QA written to " + qa_file_path)
    add_timestamp_links(qa_file_path)
    print("Timestamp Links added.")
    print(colored(f"System Prompt: {fcall_prompt}\n", "red"))
    pretty_print_function_descriptions(tools_qa_speaker(speaker), "red")
    return qa_file_path
def create_qa_file_select_speaker(file_path, speaker, fcall_prompt):
    """
    Processes a _prepqa file to generate QA question and answer blocks using OpenAI LLM function calling.

    :param file_path: string of the path to the _prepqa transcript file to be processed.
    :param speaker: string of the speaker's name to be used in processing.
    :return: None.
    """    
    blocks_file_path = split_file_select_speaker(file_path, speaker)
    qa_file_path = fcall_qa_speaker(blocks_file_path, speaker, fcall_prompt)
    delete_file(blocks_file_path)
    return qa_file_path


### QA INCREMENTAL
FCALL_SYSTEM_PROMPT_QA_INCREMENTAL_TRANSCTIPRT_FDA_TOWNHALLS_1 = """
    You are an expert text analyzer trained in identifying questions and answers in transcripts of dialogue. 
    Your role is to extract and clarify the next question-answer pair from the given transcript chunk.
    The previous question-answer pair is provided in both the original text verbatim version and in a modified clarified version.

    Your task is identify the next important information that comes after the previous question-answer pair. This important information may comprise an explicit question asked by a speaker, or it may not and instead be a standalone statement.
    A requirement for qualification as important information of a next question-answer pair is that it is not included in the verbatim_answer property of the provided previous question answer pair.
     
    Identify the speakers for both questions and answers. Speakers are identified on separate lines of text that precede the speaker dialogue. The speaker lines end in either just a colon, or a timestamp which optionally be followed by a timestamp link. Speaker lines will start with the speaker name, or a surrogate string such as 'Moderator'. The speaker name may be followed by a role provided in parentheses. The role may comprise or contain text that specifies that speaker as an 'Authority Speaker'. See below for the text that specifies Authority Speakers.
    
    If important information is provided by a speaker identified as an Authority Speaker (see below), and that important information is not explicitly asked as a question, then you will generate a clarified question that is the best suitable question to be paired with that important information. The important information will be considered the answer. If a statement is made by a Non-Authority Speaker, and that statement is not phrased as a question, then it must be acknowledged by an Authority Speaker with an explicit affirmation response. See property descriptions below for values to use in this case where there is no explicit verbatim question.

    You will extract both the verbatim_answer from the transcript text, and then process the verbatim_answer to create the clarified_answer. The clarified_answer may be similar or perhaps even identical to the verbatim_answer from the transcript text. Typically the clarified answer wil be modified and therefore different at least to some extent from the verbatim_answer, however the clarified_answer must NEVER contradict the corresponding verbatim_answer and must ALWAYS have the same meaning. You will create the clarified versions of the question and answer by removing filler words to improve clarity and readability.

    This specific corpus comprises transcripts of the dialogue from virtual townhall meetings held by the United States Food and Drug Administration (FDA) to help answer technical questions about the development and validation of tests for the virus SARS-CoV2, and the updated policy on COVID-19 diagnostics policy for diagnostics test for coronavirus disease 2019 during the public health emergency caused by the COVID-19 global pandemic.

    Authority Speakers in this FDA Townhall Transcript Corpus are specified by the inclusion of the string 'FDA' in the role portion of the speaker line.

    The criteria for qualification for important information to be extracted as question-answer pairs is that the information be technical in nature, procedural, or legal. Information that should not be considered important and excluded from the question-answer extraction process is information related to the orchestration of the call such as which caller or speaker is being selected by the moderator. Information, whether questions by call-in speakers or answers by FDA staff, that is related to whether the FDA authorities can answer the question are considered to be legal and always to be included. These typical include answers from the FDA Authority Speakers similar to 'we are not able to respond to questions about specific submissions that might be under review'. If you are not sure whether information qualifies as important information, then includeit and set the review_flag property of the response to True.
    """
FCALL_SYSTEM_PROMPT_QA_INCREMENTAL_TRANSCRIPT_FDA_TOWNHALLS_2 = """
You are an expert text analyzer trained in identifying questions and answers in transcripts of dialogue, specifically for FDA Town Hall meetings on COVID-19 diagnostics. Your role is to extract and clarify the next question-answer pair from the given transcript chunk, while also precisely identifying its location within the text.

Your task:
1. Identify the next question or important information after the provided previous question-answer pair, even if there is overlap between the corresponding transcript text. The next question and answer may be related to but should be distinct from the previous question and answer.
2. Extract both verbatim and clarified versions of questions and answers, excluding speaker lines and newline characters.
3. Identify speakers and their roles for questions and answers separately.
4. Generate clarified questions for important statements from Authority Speakers if not explicitly asked as questions.
5. Focus on technical, procedural, or legal information.
6. Include information about FDA's ability to answer questions.
7. Exclude call orchestration details involving starting the meeting, openning for questions, connection problems, speaker order, and meeting feedback surveys.
8. Precisely identify the start and end positions of the verbatim text from the transcript that corresponds to the clairified question-answer pair.

Key points:
- Important information must not be included in the previous answer.
- Speakers are identified by lines ending with a colon or timestamp.
- Authority Speakers are indicated by 'FDA' in their role description.
- Clarified versions should improve readability without changing meaning.
- Non-Authority Speaker statements must be acknowledged by Authority Speakers to be included.
- If unsure about information importance, include it and set the review flag to True.
- Accurately report the relative character positions (start and end) of the input transcript text that the extracted question-answer pair correspond to.
- All extracted text (verbatim and clarified) should be on a single line without newline characters or speaker identifications.

The precise identification of question-answer pair positions is crucial for the incremental extraction process. It allows for:
- Accurate progression through the transcript without missing or duplicating content.
- Identification of the next chunk to be processed based on the end position of the current pair.
- Thorough extraction of all important question-answer pairs from the original transcript.

This incremental approach ensures comprehensive coverage of the transcript while maintaining context and continuity throughout the extraction process. Your accurate identification of text positions is essential for the seamless progression of this extraction method.

This process is crucial for organizing and clarifying important information from FDA Town Hall meetings on COVID-19 diagnostics, ensuring accurate and accessible information dissemination while maintaining the transcript's integrity and completeness.
"""
def tools_qa_incremental_2():
    return [{
        "type": "function",
        "function": {
            "name": "extract_qa",
            "description": "Extract and clarify the next question-answer pair from an FDA Town Hall transcript chunk",
            "strict": True,  # Add for Stuctured Output
            "parameters": {
                "type": "object",
                "properties": {
                    "clarified_question": {
                        "type": "string",
                        "description": "A clear, concise version of the next question given the context of the provided previous question and answer block, even if this next question overlaps with the previous answer. Remove filler words and improving readability of the question. If no explicit question is asked in the entirity of the transcrtipt text provided, analyze the text to determine if important information provided by an Authority Speaker. If so, then generate an appropriate question based on the important information. The entire text of this next question should be on a single line.",
                    },
                    "clarified_answer": {
                        "type": "string",
                        "description": "A clear, concise version of the answer to the next question, removing filler words and improving readability. Must maintain the same meaning as the verbatim answer but may rephrase for clarity. The entire text of this answer should be on a single line.",
                    },
                    "verbatim_question": {
                        "type": "string",
                        "description": "The exact text corresponding to the next question as it appears in the transcript, excluding the speaker line and any newline characters. If no explicit question is asked, use the string 'IMPLIED QUESTION'. The entire text should be on a single line.",
                    },
                    "verbatim_answer": {
                        "type": "string",
                        "description": "The exact answer as it appears in the transcript, including any filler words or hesitations, but excluding the speaker line and any newline characters. The entire text should be on a single line.",
                    },
                    "speaker_question": {
                        "type": "string",
                        "description": "The name or role of the person asking the question, as identified in the transcript by the text in the speaker line that precedes a colon or timestamp. Do not use a different name spelling that may appear in the speaker dialogue. If the question is implied from an Authority Speaker's statement, use 'NONE'.",
                    },
                    "speaker_answer": {
                        "type": "string",
                        "description": "The name and role of the person providing the answer, as identified in the transcript by the text in the speaker line that precedes a colon or timestamp. Do not use a different name spelling that may appear in the speaker dialogue.",
                    },
                    "relative_start_position": {
                        "type": "integer",
                        "description": "The character position in the transcript chunk where the verbatim_question begins, relative to the start of the chunk.",
                    },
                    "relative_end_position": {
                        "type": "integer",
                        "description": "The character position in the transcript chunk where the verbatim_answer ends, relative to the start of the chunk.",
                    },
                    "topics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "A list of 1-3 key topics addressed in the question-answer pair, focusing on technical, procedural, or legal aspects of COVID-19 diagnostics.",
                    },
                    "review_flag": {
                        "type": "boolean",
                        "description": "Set to True if there's any uncertainty about the importance or relevance of the extracted information, or if the content requires additional review. Otherwise, set to False.",
                    }
                },
                "required": ["clarified_question", "clarified_answer", "verbatim_question", "verbatim_answer", "speaker_question", "speaker_answer", "relative_start_position", "relative_end_position", "topics", "review_flag"],
                "additionalProperties": False  # Add for Stuctured Output
            }
        }
    }]
FCALL_SYSTEM_PROMPT_QA_INCREMENTAL_TRANSCRIPT_FDA_TOWNHALLS_F = """
You are an expert text analyzer trained in identifying questions and answers in transcripts of dialogue, specifically for FDA Town Hall meetings on COVID-19 diagnostics. Your role is to extract the **next** relevant question-answer pair from the given transcript chunk, while also identifying its location within the text with precision. This is an incremental process: each time you produce a QA pair, you must identify exactly which characters in the transcript it corresponds to, so that subsequent requests can continue from beyond that position without overlap or duplication.

Your **primary goals** when extracting each question-answer pair:
1. **Prevent Duplication**  
   - Each transcript chunk should yield at most one new or distinct Q&A if it involves the same question, the same speaker, or the same snippet previously captured.
   - If the text is essentially continuing or clarifying the same question-answer pair (same speaker, same context, no new question asked), do not produce a separate QA pair. Instead, merge it into the previous QA or skip it.
   - Skip or merge any "implied" question if it simply rehashes a previously extracted question or answer. Do not produce multiple QAs for repeated or partial references to the same question or the same speaker's statement.

2. **Identify & Label Speakers and Their Roles**  
   - For example, use "Tim Stenzel (FDA IVD Director):" or "Shannon Clark (UserWise Consulting):".  
   - If a speaker's question is truly separate, it should become a distinct QA pair. If it is a minor clarifying follow-up, merge it into the previous QA if possible.

3. **Capture Verbatim Text on a Single Line**  
   - Provide a "VERBATIM QUESTION" and "VERBATIM ANSWER" as continuous text without line breaks or extra speaker labels embedded inside. Eliminate "um," "uh," repeated words, or crosstalk noise only if they disrupt clarity; otherwise, keep the text as close to verbatim as possible.
   - Provide a "CLARIFIED QUESTION" and "CLARIFIED ANSWER" that rephrase or clean up the language for clarity, **but do not** change the meaning.
   - If the speaker never actually asks a question but is giving new, important regulatory or legal info not captured in a prior QA pair, you may label it as "IMPLIED QUESTION" / "IMPLIED ANSWER." However, do this only if it is clearly a separate, substantive piece of info that was not already covered. Do not produce multiple implied questions for partial or repeated quotes from the same speaker or the same text chunk.

4. **Location Reporting (Transcript Start/End Positions)**  
   - Precisely identify the start and end character positions in the provided transcript for each **verbatim** question and answer.  
   - Ensure these positions align exactly with the extracted text, so future incremental requests can skip ahead to the next chunk.

5. **Exclusions & Focus**  
   - **Exclude** housekeeping/orchestration and meeting management (e.g., "next steps in the meeting", "Moderator," "Coordinator" instructions about lines being muted, "press star-1," teleconference issues, or feedback survey reminders).  
   - **Exclude** repeated disclaimers that "FDA can't speak about specific submissions under review."  
   - **Focus** on technical, procedural, or legal content about COVID-19 diagnostics, test development, validation, labeling, and regulatory processes.

6. **One QA per Speaker Turn**
   - By default, a single speaker's turn (plus any immediate FDA response) should become one QA pair unless the speaker explicitly asks multiple distinct questions.
   - If the same speaker's turn includes meandering or repeated questions, condense them into one QA if they address the same overall topic.
   - Example: If a speaker says: "I have a question about in silico cross-reactivity. Also, do we need new data for interfering substances?" treat that entire turn as one question.

7. **Minor Clarifications or Follow-Ups**
   - If a speaker or the FDA official continues talking but does not pose a new distinct question, do not create a new QA pair.
   - If it's simply clarifying the same question (e.g., a short "Yes, exactly" or "That's correct"), merge it into the existing QA pair or skip if it adds no new regulatory content.

8. **Incremental Approach & Avoiding Over-Segmentation**  
   - After extracting one QA pair, you stop at the exact "TRANSCRIPT END POSITION." The next time a request is made, you begin looking for a new question or important statement from that end position forward.
   - Do not break out small or partial phrases from the same speaker answer or question into multiple QA pairs. If the question or answer is continuous (no separate speaker turn), it's a single QA.
   - If it was partially extracted previously, skip it unless the newly revealed text truly adds a completely new question or significant content.

9. **Minimize Implied Q&A**
   - If you already extracted a Q&A covering the same statement from an Authority Speaker, do not create a second "implied Q&A."
   - If the statement is basically repeating prior FDA guidance (e.g., "We are open to off-label use…" repeated), skip or merge it.

10. **Review Flag**  
    - If you are uncertain whether a piece of information is important enough to become a question-answer pair, include it, but set "REVIEW FLAG: True."

### **Output Format Example**

For each extraction, produce something like:
CLARIFIED QUESTION: <One-sentence, cleaned-up question>
CLARIFIED ANSWER: <One-sentence, cleaned-up answer or best summary of the official FDA stance>
VERBATIM QUESTION: <Exact single-line text from the transcript, no newlines>
VERBATIM ANSWER: <Exact single-line text from the transcript, no newlines>
SPEAKER QUESTION: <Name and role>
SPEAKER ANSWER: <Name and role>
TRANSCRIPT START POSITION: <integer index in transcript>
TRANSCRIPT END POSITION: <integer index in transcript>
TOPICS: <short list of relevant topics>
REVIEW FLAG: <True/False>

**Important:**  
- Keep the "VERBATIM QUESTION" and "VERBATIM ANSWER" truly on one line each, removing speaker tags or line breaks.  
- Do not repeat the same text chunk if it's already been extracted in a previous QA pair.  
- Use your judgment to maintain clarity but remain faithful to the transcript.

By following these updated guidelines, your extraction will avoid repetition, properly scope incremental location offsets, and keep the Q&A set tightly focused on the most critical technical and regulatory content from the FDA Town Hall. 

"""
def tools_qa_incremental_F():
    return [{
        "type": "function",
        "function": {
            "name": "extract_qa",
            "description": "Extract and clarify the next question-answer pair from an FDA Town Hall transcript chunk, ensuring no duplication from previously extracted content. Focus on single-line verbatim text for both question and answer, and only use 'IMPLIED QUESTION' if the speaker is an Authority Speaker providing important new information. Avoid re-extracting the same text used in previous QAs.",
            "strict": True,  # Add for Stuctured Output
            "parameters": {
                "type": "object",
                "properties": {
                    "clarified_question": {
                        "type": "string",
                        "description": "A clear, concise version of the next question given the context of the provided previous question and answer block, even if this next question overlaps with the previous answer. Remove filler words and improving readability of the question. If no explicit question is asked in the entirity of the transcrtipt text provided, analyze the text to determine if important information provided by an Authority Speaker. If so, then generate an appropriate question based on the important information. The entire text of this next question should be on a single line.",
                    },
                    "clarified_answer": {
                        "type": "string",
                        "description": "A clear, concise version of the answer to the next question, removing filler words and improving readability. Must maintain the same meaning as the verbatim answer but may rephrase for clarity. The entire text of this answer should be on a single line.",
                    },
                    "verbatim_question": {
                        "type": "string",
                        "description": "The exact text of the next question as it appears in the transcript, on a single line and excluding speaker labels or newline characters. If no explicit question is asked but there is new, important information from an Authority Speaker, use 'IMPLIED QUESTION'. Do not repeat or duplicate any text that was already extracted in a prior question.",
                    },
                    "verbatim_answer": {
                        "type": "string",
                        "description": "The exact text of the answer as it appears in the transcript, on a single line and excluding speaker labels or newline characters. Retain filler words only if they clarify meaning. Do not duplicate text previously extracted. Must match the same segment of transcript indicated by the start/end positions.",
                    },
                    "speaker_question": {
                        "type": "string",
                        "description": "The name or role of the person asking the question, as identified in the transcript by the text in the speaker line that precedes a colon or timestamp. Do not use a different name spelling that may appear in the speaker dialogue. If the question is implied from an Authority Speaker's statement, use 'NONE'.",
                    },
                    "speaker_answer": {
                        "type": "string",
                        "description": "The name and role of the person providing the answer, as identified in the transcript by the text in the speaker line that precedes a colon or timestamp. Do not use a different name spelling that may appear in the speaker dialogue.",
                    },
                    "relative_start_position": {
                        "type": "integer",
                        "description": "The character position in the transcript chunk where the verbatim_question begins, relative to the start of the chunk.",
                    },
                    "relative_end_position": {
                        "type": "integer",
                        "description": "The character position in the transcript chunk where the verbatim_answer ends, relative to the start of the chunk.",
                    },
                    "topics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "A list of 1-3 key topics addressed in the question-answer pair, focusing on technical, procedural, or legal aspects of COVID-19 diagnostics.",
                    },
                    "review_flag": {
                        "type": "boolean",
                        "description": "Set to True if there is any uncertainty about the importance or uniqueness of the extracted information (e.g., potential duplication, borderline relevance), or if it requires further review. Otherwise, set to False.",
                    }
                },
                "required": ["clarified_question", "clarified_answer", "verbatim_question", "verbatim_answer", "speaker_question", "speaker_answer", "relative_start_position", "relative_end_position", "topics", "review_flag"],
                "additionalProperties": False  # Add for Stuctured Output
            }
        }
    }]
FCALL_SYSTEM_PROMPT_QA_INCREMENTAL_TRANSCRIPT_FDA_TOWNHALLS_4 = """
You are an expert text analyzer trained in identifying questions and answers in transcripts of dialogue, specifically for FDA Town Hall meetings on COVID-19 diagnostics. Your role is to extract and clarify the next question-answer pair from the given transcript chunk.

Core Requirements:
1. DO NOT REPEAT ESSENTIALLY THE SAME QUESTION OR ANSWER from previous blocks
2. Focus only on technical, procedural, or legal information
3. Exclude meeting orchestration details (e.g., starting meeting, connection issues, speaker order)

Speaker Guidelines:
- Authority Speakers are indicated by 'FDA' in their role description
- Non-Authority Speaker statements require FDA acknowledgment
- Speakers are identified by lines ending with colon or timestamp

Position Tracking:
- Precisely identify start/end positions of extracted text in the transcript
- This enables accurate progression and prevents duplicating content
- Report positions relative to the start of the provided chunk

If unsure about information importance, include it but set review_flag to True.
"""
def tools_qa_incremental_4():
    return [{
        "type": "function",
        "function": {
            "name": "extract_qa",
            "description": "Extract and clarify the next question-answer pair from an FDA Town Hall transcript chunk",
            "strict": True,  # Add for Stuctured Output
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "A clear, single-line question using direct third-person phrasing (e.g., 'What is...' rather than 'Can you...'). For important statements from Authority Speakers without explicit questions, generate an appropriate question.",
                    },
                    "answer": {
                        "type": "string",
                        "description": "A clear, single-line, authoritative answer in FAQ document style. Must be direct, factual, unattributed to speakers, while maintaining the original meaning.",
                    },
                    "question_speaker": {
                        "type": "string",
                        "description": "Speaker name/role from the line preceding their dialogue. Use 'IMPLIED' for Authority Speaker statements without explicit questions.",
                    },
                    "answer_speaker": {
                        "type": "string",
                        "description": "Speaker name/role from the line preceding their answer.",
                    },
                    "relative_start_position": {
                        "type": "integer",
                        "description": "Character position where the question begins, relative to chunk start.",
                    },
                    "relative_end_position": {
                        "type": "integer",
                        "description": "Character position where the answer ends, relative to chunk start.",
                    },
                    "topics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "1-3 key topics about technical, procedural, or legal aspects of COVID-19 diagnostics.",
                    },
                    "review_flag": {
                        "type": "boolean",
                        "description": "True if uncertain about importance/relevance; False otherwise.",
                    }
                },
                "required": ["question", "answer", "question_speaker", "answer_speaker", "relative_start_position", "relative_end_position", "topics", "review_flag"],
                "additionalProperties": False
            }
        }
    }]
FCALL_SYSTEM_PROMPT_QA_INCREMENTAL_TRANSCRIPT_FDA_TOWNHALLS_5 = """
You are an expert text analyzer trained in identifying questions and answers in transcripts of dialogue, specifically for FDA Town Hall meetings on COVID-19 diagnostics. Your role is to extract and clarify the next question-answer pair from the given transcript chunk and previous questions.

Core Requirement:
DO NOT REPEAT ESSENTIALLY THE SAME QUESTION given the list of previous questions

Speaker Guidelines:
- Authority Speakers are indicated by 'FDA' in their role description
- Non-Authority Speaker statements require FDA acknowledgment
- Speakers are identified by lines ending with colon or timestamp
- Treat a single speaker's turn plus FDA response as one QA pair unless multiple distinct questions
- Merge minor clarifications or follow-ups into existing QA rather than creating new pairs

Position Tracking:
- Precisely identify start/end positions of extracted text in the transcript
- This enables accurate progression and prevents duplicating content
- Report positions relative to the start of the provided chunk

Content Guidelines:
- Focus on technical, procedural, or legal aspects of COVID-19 diagnostics, test development, validation, labeling
- Minimize implied questions - only use for important new regulatory content not previously captured
- Exclude meeting orchestration details (e.g., starting meeting, connection issues, speaker order)
- Exclude repeated disclaimers about FDA not discussing specific submissions

If unsure about information importance, include it but set review_flag to True.
"""
def tools_qa_incremental_5():
    return [{
        "type": "function",
        "function": {
            "name": "extract_qa",
            "description": "Extract and clarify the next question-answer pair from an FDA Town Hall transcript chunk",
            "strict": True,  # Add for Stuctured Output
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "A clear, single-line question using direct third-person phrasing (e.g., 'What is...' rather than 'Can you...'). For important statements from Authority Speakers without explicit questions, generate an appropriate question.",
                    },
                    "answer": {
                        "type": "string",
                        "description": "A clear, single-line, authoritative answer in FAQ document style. Must be direct, factual, unattributed to speakers, while maintaining the original meaning.",
                    },
                    "question_speaker": {
                        "type": "string",
                        "description": "Speaker name/role from the line preceding their dialogue. Use 'IMPLIED' for Authority Speaker statements without explicit questions.",
                    },
                    "answer_speaker": {
                        "type": "string",
                        "description": "Speaker name/role from the line preceding their answer.",
                    },
                    "relative_start_position": {
                        "type": "integer",
                        "description": "Character position where the question begins, relative to chunk start.",
                    },
                    "relative_end_position": {
                        "type": "integer",
                        "description": "Character position where the answer ends, relative to chunk start.",
                    },
                    "topics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "1-3 key topics about technical, procedural, or legal aspects of COVID-19 diagnostics.",
                    },
                    "review_flag": {
                        "type": "boolean",
                        "description": "True if uncertain about importance/relevance; False otherwise.",
                    }
                },
                "required": ["question", "answer", "question_speaker", "answer_speaker", "relative_start_position", "relative_end_position", "topics", "review_flag"],
                "additionalProperties": False
            }
        }
    }]
FCALL_SYSTEM_PROMPT_QA_INCREMENTAL_TRANSCRIPT_FDA_TOWNHALLS_6RT = """
You are an expert text analyzer trained in identifying questions and answers in transcripts of dialogue, specifically for FDA Town Hall meetings on COVID-19 diagnostics. Your role is to extract and clarify the next question-answer pair from the given transcript chunk and previous questions.

Core Requirements:
1. Identify the next question or important information from the provided transcript chunk
2. Must come after the provided previous question-answer pair
3. 



NEVER EXTRACT A QUESTION THAT COVERS THE SAME CORE TOPIC AND INFORMATION AS ANY PREVIOUS QUESTION
2. If a new question seems too similar to previous ones, SKIP AHEAD in the transcript to find the next truly distinct topic
3. When multiple questions discuss the same general topic only extract the FIRST comprehensive question-answer pair
4. For follow-up questions or clarifications, merge them into the original answer rather than creating new QA pairs
5. If no novel questions remain in the current chunk, set review_flag to True and move to the next chunk

Question Diversity Guidelines:
- Each question must introduce a completely new topic or regulatory aspect
- Reject questions that merely rephrase or slightly extend previous questions
- For multi-part discussions, combine related points into a single comprehensive QA pair
- When in doubt about similarity, err on the side of skipping the question

Speaker Guidelines:
- Authority Speakers are indicated by 'FDA' in their role description
- Non-Authority Speaker statements require FDA acknowledgment
- Speakers are identified by lines ending with colon or timestamp
- Treat a single speaker's turn plus FDA response as one QA pair unless multiple distinct questions
- Merge minor clarifications or follow-ups into existing QA rather than creating new pairs

Position Tracking:
- Precisely identify start/end positions of extracted text in the transcript
- This enables accurate progression and prevents duplicating content
- Report positions relative to the start of the provided chunk

Content Guidelines:
- Focus on technical, procedural, or legal aspects of COVID-19 diagnostics, test development, validation, labeling
- Minimize implied questions - only use for important new regulatory content not previously captured
- Exclude meeting orchestration details (e.g., starting meeting, connection issues, speaker order)
- Exclude repeated disclaimers about FDA not discussing specific submissions

If unsure about information importance, include it but set review_flag to True.
"""
FCALL_SYSTEM_PROMPT_QA_INCREMENTAL_TRANSCRIPT_FDA_TOWNHALLS_6 = """
You are an expert text analyzer trained in identifying questions and answers in transcripts of dialogue, specifically for FDA Town Hall meetings on COVID-19 diagnostics.

Your Role:
- Determine whether there is important content that should be extracted as an additional question-answer (QA) block, with the provided context of a list of the last several previous questions and the complete previous QA block.
- If additional important content is present, extract and clarify the next question-answer pair from the provided transcript chunk.
- If no additional important content is present, respond with "NO NEW QA" for the clarified_question field and leave the other fields blank (empty strings) or zero.
- Extract only new, distinct question-answer content that appears after the text already covered by the previous QA block. Do not duplicate an already-extracted Q&A from the same text segment. However, if there is new or distinct content within a previously introduced speaker response that was never captured, you may extract it now.
- Provide both verbatim and clarified versions of the question and answer to ensure thorough coverage and readability.

Coverage & Percentage Guidance:
- Aim to capture the majority of important FDA information while minimizing redundant or overlapping Q&A blocks.
- Strive for high coverage of significant technical, procedural, or legal information. If a transcript chunk introduces new, important content not already captured, create a new QA block.
- However, do not generate duplicate or near-duplicate QA pairs.
- Regulatory updates, new test authorizations, or statements of priority from FDA speakers count as important content. If not obviously phrased as a question, treat them as implied questions and produce a new QA.
- Any significant statement of FDA updates, newly authorized tests, or top priorities from FDA staff should be captured as an implied question and answer if not already extracted.
- If an FDA speaker (or other speaker) shares new or significant updates, always create an implied question if not covered previously.

Core Requirements:
1. DO NOT REPEAT QUESTIONS THAT COVER THE SAME CORE TOPIC AND INFORMATION as any question in the provided list of previous questions.
2. If a potential question is too similar to previous ones, skip ahead in the transcript or mark "NO NEW QA" for this segment.
3. For multi-part discussions of the same topic, merge clarifications into one comprehensive QA pair.
4. If you determine there is no distinct new content for a given chunk, return "NO NEW QA" (see instructions below).

Speaker Guidelines:
- Speakers are identified by lines ending with a colon, timestamp, or by a direct statement of their role (e.g., "Dr. Smith (FDA):").
- Authority Speakers are indicated by 'FDA' in their role description.
- Non-Authority Speaker statements must be included in the clarified_answer field if they contain important details or are directly addressed by the FDA. If uncertain, set review_flag = True.

Position Tracking:
- Precisely identify start/end positions of extracted text (verbatim) within the chunk.
- Use these positions to prevent duplication and ensure incremental coverage.

Content Guidelines:
- Focus on technical, procedural, or legal aspects of COVID-19 diagnostics (test development, validation, labeling, etc.).
- Exclude trivial or orchestration details like meeting start-up or speaker order.
- If important FDA information is present but no explicit question is asked, generate an “implied” question.
- Whenever uncertain, set review_flag to True.

Verbatim vs. Clarified Output:
- Provide both verbatim_question and verbatim_answer, exactly as they appear in the transcript (minus speaker labels and newlines).
- Provide clarified_question and clarified_answer for conciseness, improved clarity, and readability.

Option to Return “No New QA”:
- If no new question is found, set "clarified_question" to the exact string "NO NEW QA" and leave the other fields blank (empty strings) or zero. 
- Set "review_flag" to True if there is significant uncertainty in whether new QA content is present, or False if there is clearly no remaining new content given the provided context in the form of the previous list of several questions and previous entire QA block.
- If the previously extracted QA block is empty or nonexistent, parse all important content in the chunk as new Q&A, since there is no older QA to conflict with.

Your output must strictly follow the schema. All fields are required, so if there is no new QA, fill them with the agreed-upon placeholders or zeros.

The transcript will be processed in a progressive manner with the response being one in a sequence.
"""
def tools_qa_incremental_6():
    return [{
        "type": "function",
        "function": {
            "name": "extract_qa",
            "description": "Extract and clarify the next question-answer pair (both verbatim and clarified) from an FDA Town Hall transcript chunk. If no new QA is found, fill all required fields with placeholders/zeros as instructed in the system prompt.",
            "strict": True,  # For Structured Output
            "parameters": {
                "type": "object",
                "properties": {
                    "clarified_question": {
                        "type": "string",
                        "description": (
                            "A concise, edited version of the question. If no new QA is found, set this to 'NO NEW QA'. The entire text should be on one line."
                        )
                    },
                    "clarified_answer": {
                        "type": "string",
                        "description": (
                            "A concise, edited version of the answer. If no new QA is found, leave this field blank (e.g., ''). The entire text of this answer should be on a single line."
                        )
                    },
                    "verbatim_question": {
                        "type": "string",
                        "description": (
                            "The exact text of the question, minus speaker labels/newlines. If no new QA is found, use ''. If no explicit question is asked, use the string 'IMPLIED QUESTION'. The entire text should be on a single line."
                        )
                    },
                    "verbatim_answer": {
                        "type": "string",
                        "description": (
                            "The exact text of the answer, minus speaker labels/newlines. If no new QA is found, use ''. The entire text should be on a single line."
                        )
                    },
                    "speaker_question": {
                        "type": "string",
                        "description": (
                            "Name/role of question speaker. Use '' if no new QA is found. The name must be as identified in the transcript by the text in the speaker line that precedes a colon or timestamp. Do not use a different name spelling that may appear in the speaker dialogue. If the question is implied from an Authority Speaker's statement, use 'IMPLIED'."
                        )
                    },
                    "speaker_answer": {
                        "type": "string",
                        "description": (
                            "Name/role of answer speaker. Use '' if no new QA is found. The name must be as identified in the transcript by the text in the speaker line that precedes a colon or timestamp. Do not use a different name spelling that may appear in the speaker dialogue. If the question is implied from an Authority Speaker's statement, use 'IMPLIED'."
                        )
                    },
                    "relative_start_position": {
                        "type": "integer",
                        "description": (
                            "The character position in the transcript chunk where the verbatim_question begins, relative to the start of the chunk.If no new QA, set to 0."
                        )
                    },
                    "relative_end_position": {
                        "type": "integer",
                        "description": (
                            "The character position in the transcript chunk where the verbatim_answer ends, relative to the start of the chunk. If no new QA, set to 0."
                        )
                    },
                    "topics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "A list of 1-3 key topics addressed in the question-answer pair. If no new QA, return an empty list []."
                        )
                    },
                    "review_flag": {
                        "type": "boolean",
                        "description": (
                            "Set True if significant uncertainty in the response. Otherwise False."
                        )
                    }
                },
                "required": [
                    "clarified_question", "clarified_answer",
                    "verbatim_question", "verbatim_answer",
                    "speaker_question", "speaker_answer",
                    "relative_start_position", "relative_end_position",
                    "topics", "review_flag"
                ],
                "additionalProperties": False
            }
        }
    }]
FCALL_SYSTEM_PROMPT_QA_INCREMENTAL_TRANSCRIPT_FDA_TOWNHALLS_6B = """
You are an expert text analyzer trained in identifying questions and answers in transcripts of dialogue, specifically for FDA Town Hall meetings on COVID-19 diagnostics.

Your Role:
- Determine whether there is important content that should be extracted as one or more question-answer (QA) blocks, given a list of previous questions and the previous QA block.
- If additional important content is present, extract and clarify one or more new Q&A pairs from the provided transcript chunk.
- If no additional important content is present, respond with "NO NEW QA" for the clarified_question field and leave the other fields blank (empty strings) or zero.
- Extract only new, distinct question-answer content that appears after the text already covered by the previous QA block. 
  - Do not duplicate a Q&A already extracted from the same text segment. 
  - However, if a single answer covers multiple topics (and those topics are not yet captured in any previous question), you should create multiple QA pairs—one for each distinct point.
- Provide both verbatim and clarified versions of each question and answer to ensure thorough coverage and readability.

Coverage & Percentage Guidance:
- **Aim for comprehensive coverage** of the FDA’s important regulatory and technical information. 
- If a transcript chunk introduces new or significant material not previously extracted, **create a new QA block.** 
- **Avoid overlap**: if a question has essentially the same meaning as a previous question, skip it.
- **Include high-level updates**: Regulatory updates, newly authorized tests, or statements of FDA priority should be treated as “implied questions” if they are not explicitly phrased as questions.
- **Allow multiple questions** from a single turn or answer if there are clearly separate topics or points worth indexing.

Core Requirements:
1. DO NOT REPEAT QUESTIONS THAT COVER THE SAME CORE TOPIC AND INFORMATION as any in the provided previous-questions list.
2. If a potential question is too similar to previous ones, skip it or return “NO NEW QA” for that segment.
3. For multi-part discussions of the same topic, merge clarifications into one comprehensive QA pair. However, if an answer covers multiple unrelated points, **split** them into multiple QA pairs for clarity.
4. If you determine there is no distinct new content for a given chunk, return "NO NEW QA" (instructions below).

Speaker Guidelines:
- Speakers are identified by lines ending with a colon, timestamp, or by a direct statement of their role (e.g., "Dr. Smith (FDA):").
- Authority Speakers are indicated by 'FDA' in their role description.
- Non-Authority Speaker statements must be included in the clarified_answer field if they contain important details or are directly addressed by the FDA. If uncertain, set review_flag = True.

Position Tracking:
- Precisely identify start/end positions of extracted text (verbatim) within the chunk.
- Use these positions to prevent duplication and ensure incremental coverage.

Content Guidelines:
- Focus on **technical, procedural, or legal** aspects of COVID-19 diagnostics (test development, validation, labeling, etc.).
- Exclude trivial meeting details (startup, speaker order).
- If important FDA information is present but no explicit question is asked, generate an “implied” question.
- Whenever uncertain, set review_flag to True.

Verbatim vs. Clarified Output:
- Provide both verbatim_question and verbatim_answer, exactly as they appear (minus speaker labels and newlines).
- Provide clarified_question and clarified_answer for readability, combining or splitting content *only* to improve clarity and coverage without contradicting the original meaning.

Option to Return “NO NEW QA”:
- If no new question is found, set "clarified_question" to the exact string "NO NEW QA" and leave other fields blank (empty strings) or zero.
- Set "review_flag" to True if uncertain whether new QA content is present, or False if obviously none remains.
- If the previously extracted QA block is empty or nonexistent, parse all important content in the chunk as new Q&A.

Remember, **the user’s application will index only the questions** for semantic search, so your clarified_question fields must capture all key points that a user might search for in the future. Avoid discarding or merging clearly separate topics into one question.

Your output must strictly follow the schema. All fields are required, so if there is no new QA, fill them with the agreed-upon placeholders or zeros. The transcript will be processed in a progressive manner, each output forming part of a larger incremental extraction.
"""
FCALL_SYSTEM_PROMPT_QA_INCREMENTAL_TRANSCRIPT_FDA_TOWNHALLS_6C = """
You are an expert text analyzer trained in identifying questions and answers in transcripts of dialogue, specifically for FDA Town Hall meetings on COVID-19 diagnostics.

Your Role:
- Determine whether there is content in a provided a transcript chunk of text that should be extracted as an additional question, given a list of previous questions that have previously been extracted.
- If additional important content is present, extract and clarify one or more new questions from the provided transcript chunk and create all associated fields in the question-answer (QA) block.
- If no additional important content is present, respond with "NO NEW QA" for the clarified_question field and leave the other fields blank (empty strings) or zero.

Important Note on Use Case:
- Only the clarified_question field will be indexed and used for semantic search. Therefore, the coverage of each new topic or keyword must appear in the question, ensuring users can find it later by searching. If an answer covers multiple distinct topics, you should form multiple questions—even if they overlap in the answer text—so that each topic appears in its own question for better searchability.
- In other words, the question text itself must include key terms, phrases, or concepts from the answer. This way, anyone searching for those terms will retrieve the relevant QA pair. Redundant or nearly duplicated questions should be avoided, but it’s acceptable for multiple different questions to reference the same or partially overlapping answer segments if each question addresses a unique aspect that users might search for.

Coverage & Percentage Guidance:
- **Aim for comprehensive coverage** of the FDA’s important regulatory and technical information. 
- If a transcript chunk introduces new or significant material not in the previous questions, **extract a new question.** 
- **Include high-level updates**: Regulatory updates, newly authorized tests, or statements of FDA priority should be treated as “implied questions” if they are not explicitly phrased as questions.
- **Allow multiple questions** from a single turn or answer if there are clearly separate topics or points worth extracting.
- If you determine there is no distinct new question to be extracted for a given chunk, return "NO NEW QA" (instructions below).

Speaker Guidelines:
- Speakers are identified by lines ending with a colon, timestamp, or by a direct statement of their role (e.g., "Dr. Smith (FDA):").
- Authority Speakers are indicated by 'FDA' in their role description.
- Non-Authority Speaker statements must be included in the clarified_answer field if they contain important details or are directly addressed by the FDA. If uncertain, set review_flag = True.

Position Tracking:
- Precisely identify start/end positions of extracted text (verbatim) within the chunk.
- Use these positions to prevent duplication and ensure incremental coverage.

Content Guidelines:
- Focus on **technical, procedural, or legal** aspects of COVID-19 diagnostics (test development, validation, labeling, etc.).
- Exclude trivial meeting details (startup, speaker order).
- If important FDA information is present but no explicit question is asked, generate an “implied” question.
- Whenever uncertain, set review_flag to True.

Verbatim vs. Clarified Output:
- Provide both verbatim_question and verbatim_answer, exactly as they appear (minus speaker labels and newlines).
- Provide clarified_question and clarified_answer for readability, combining or splitting content *only* to improve clarity and coverage without contradicting the original meaning.

Option to Return “NO NEW QA”:
- If no new question is found, set "clarified_question" to the exact string "NO NEW QA" and leave other fields blank (empty strings) or zero.
- Set "review_flag" to True if uncertain whether new QA content is present, or False if obviously none remains.
- If the previously extracted QA block is empty or nonexistent, parse all important content in the chunk as new Q&A.

Remember, **the user’s application will index only the questions** for semantic search, so your clarified_question fields must capture all key points that a user might search for in the future. Avoid discarding or merging clearly separate topics into one question.

Your output must strictly follow the schema. All fields are required, so if there is no new QA, fill them with the agreed-upon placeholders or zeros. The transcript will be processed in a progressive manner, each output forming part of a larger incremental extraction.
"""

def get_next_chunk(transcript, start_position, next_tokens):
    """
    Get the next chunk of transcript to process, based on the algorithm specification.
    
    :param transcript: Complete transcript text.
    :param start_position: Starting character position in the transcript.
    :param next_tokens: Number of tokens to look ahead.
    :return: Tuple of (chunk_text, end_position).
    """
    chars_per_token = 4
    look_ahead_chars = next_tokens * chars_per_token
    
    end_position = min(start_position + look_ahead_chars, len(transcript))
    
    # Go to the end of the line
    while end_position < len(transcript) and transcript[end_position] != '\n':
        end_position += 1
    
    chunk_text = transcript[start_position:end_position]
    return chunk_text, end_position
def get_last_qa_block_start_position(qa_file_path):
    """
    Read the last processed start position from the existing QA file.
    
    :param qa_file_path: String of the path to the QA file.
    :return: Integer of the transcript start position, or 0 if not found.
    """
    try:
        with open(qa_file_path, 'r') as f:
            content = f.read()
            field_identifier = "TRANSCRIPT START POSITION: "
            last_transcript_start_position = content.rfind(field_identifier)
            if last_transcript_start_position != -1:
                end_of_line = content.find("\n", last_transcript_start_position)
                position_str = content[last_transcript_start_position + len(field_identifier):end_of_line].strip()
                return int(position_str.replace(',', ''))
    except FileNotFoundError:
        pass
    return 0
def fcall_qa_incremental(transcript, next_tokens, fcall_prompt, start_position, debug=True):
    """
    Processes a transcript string incrementally to extract the next question-answer pair using OpenAI function calling.
    This function yields each QA block along with the current position in the transcript, allowing for incremental processing and resumption from the last processed position.  

    :param transcript: string of the transcript content.
    :param next_tokens: integer of the number of tokens to look ahead.
    :param fcall_prompt: string of the prompt to be used for function calling.
    :param start_position: integer of the starting position in the transcript.
    :yield: tuple of (qa_block, current_position) or (None, current_position) if an error occurred.
    """
    HISTORY_SIZE = 6  # Number of previous questions and chunk end positions to maintain
    previous_questions = []  # List to store previous questions
    previous_block = None  # Store the most recent QA block
    current_position = start_position
    total_chars_transcript = len(transcript)
    block_counter = 1  # Counter for QA blocks
    
    # Add tracking for detecting stuck positions
    chunk_end_history = []  # Track chunk end positions
    
    def is_no_new_qa(arguments):
        """Helper function to check if response indicates no new QA"""
        return (arguments['clarified_question'].upper() == 'NO NEW QA' or 
                not arguments['clarified_answer'].strip())
    
    while current_position < len(transcript):
        chunk, next_position = get_next_chunk(transcript, current_position, next_tokens)
        print(f"chunk transcript positions: {current_position:,} to {next_position:,} of total: {total_chars_transcript:,} | Percent done: {round(current_position / total_chars_transcript * 100)}%")
        
        # Track chunk end positions - maintain rolling history
        chunk_end_history.append(next_position)
        if len(chunk_end_history) > HISTORY_SIZE:
            chunk_end_history.pop(0)
        
        verbose_print(debug, f"DEBUG: Current chunk_end_history: {chunk_end_history}")
            
        # Check for stuck processing - modified condition
        if (len(chunk_end_history) >= HISTORY_SIZE and 
            len(set(chunk_end_history)) == 1 and 
            next_position < len(transcript)):
            print(colored(f"__Detected stuck processing - chunks repeatedly ending at position {next_position:,}__", "red"))
            print(f"Forcing skip to next chunk starting at: {next_position:,}")
            current_position = next_position
            continue

        # Remove early exit for end of transcript - we still need to process the final chunk
        # Instead, just note that we're processing the final chunk
        if next_position >= len(transcript):
            print("Processing final transcript chunk")

        # Create context with previous questions and previous block
        prev_questions_context = "Previous questions (from most recent to oldest):\n"
        for i, q in enumerate(previous_questions, 1):
            prev_questions_context += f"{i}. {q}\n"
        
        if not previous_block:
            prev_block_context = ("Please identify the first question-answer pair in the following transcript chunk:")
        else:
            prev_block_context = (f"Previous Question-Answer Block:\n{previous_block}\nPlease identify the next question-answer pair after this one in the following transcript chunk:")
        
        full_prompt = (
            f"{fcall_prompt}\n\n"
            f"{prev_questions_context}\n"
            f"{prev_block_context}\n\n"
            f"{chunk}"
        )
        
        try:
            qa_response = openai_function_call(full_prompt, chunk, tools_qa_incremental_6())
            arguments = json.loads(qa_response['tool_calls'][0]['function']['arguments'])
            
            # If no new QA found and we're at the end of transcript, signal completion
            if is_no_new_qa(arguments):
                print(colored(f"No new QA found at position {current_position:,}\n", "green"))
                if next_position >= len(transcript):
                    print("Completed processing final chunk - ending extraction")
                    yield None, -1
                    return
                current_position = next_position
                continue
            
            # Update previous questions list
            previous_questions.insert(0, arguments['clarified_question'])  # Add new question at the beginning
            if len(previous_questions) > HISTORY_SIZE:
                previous_questions.pop()  # Remove oldest question if exceeding HISTORY_SIZE

            qa_block = f"QA Block {block_counter}:\n"
            qa_block += f"CLARIFIED QUESTION: {arguments['clarified_question']}\n"
            qa_block += f"CLARIFIED ANSWER: {arguments['clarified_answer']}\n"
            qa_block += f"VERBATIM QUESTION: {arguments['verbatim_question']}\n"
            qa_block += f"VERBATIM ANSWER: {arguments['verbatim_answer']}\n"
            qa_block += f"SPEAKER QUESTION: {arguments['speaker_question']}\n"
            qa_block += f"SPEAKER ANSWER: {arguments['speaker_answer']}\n"
            abs_transcript_start_pos = current_position + arguments['relative_start_position']
            abs_transcript_end_pos = current_position + arguments['relative_end_position']
            qa_block += f"TRANSCRIPT START POSITION: {abs_transcript_start_pos:,}\n"
            qa_block += f"TRANSCRIPT END POSITION: {abs_transcript_end_pos:,}\n"
            qa_block += f"TOPICS: {', '.join(arguments['topics'])}\n"
            qa_block += f"REVIEW FLAG: {arguments['review_flag']}\n\n"

            block_counter += 1  # Increment block counter after successful processing
            previous_block = qa_block  # Store the current block as previous block
            
            print(f"qa response transcript position: {abs_transcript_start_pos:,} to {abs_transcript_end_pos:,}")
            
            yield qa_block, abs_transcript_start_pos
            
        except Exception as e:
            print(f"Error in qa extraction: {str(e)}")
            if next_position >= len(transcript):
                print("Error in final chunk - ending extraction")
                yield None, -1
                return
            current_position += next_tokens
            yield None, current_position
def create_qa_file_from_transcript_incremental(file_path, fcall_prompt):
    """
    Manages the incremental extraction of question-answer pairs from a transcript file.
    This function handles the overall process, including reading the transcript, determining the next chunk to process, and appending the extracted QA blocks to a new file.

    :param file_path: string of the path to the transcript file to be processed
    :param fcall_prompt: string of the prompt to be used for function calling
    :return qa_file_path: string of the path to the newly created QA file
    """
    from chalicelib.structured import count_blocks

    metadata, content = read_metadata_and_content(file_path)
    metadata = set_metadata_field(metadata, "last updated", 'Created QA Incremental')
    metadata = set_metadata_field(metadata, "source file", file_path)
    
    print("OPENAI_MODEL = " + OPENAI_MODEL)
    segment_tokens = count_segment_tokens(file_path)
    max_segment_tokens = max(segment_tokens)
    transcript = get_heading(file_path, "### transcript")
    transcript = transcript.lstrip('### transcript').rstrip('\n').lstrip('\n*')
    print(f"Number of characters in transcript: {len(transcript):,}\n")

    initial_content = "## content\n\n### qa\n"
    qa_file_path = write_metadata_and_content(file_path, metadata, initial_content, overwrite='no-sub', suffix_new='_qa-inc')
    
    current_position = 0
    max_retries = 5

    while current_position < len(transcript):
        existing_blocks = count_blocks(qa_file_path)
        block_number = existing_blocks + 1
        
        for qa_block, abs_transcript_start_pos in fcall_qa_incremental(transcript, max_segment_tokens, fcall_prompt, start_position=current_position):
            if abs_transcript_start_pos == -1:  # Check for end-of-transcript signal
                print("QA extraction completed due to end of transcript.")
                return qa_file_path
                
            retry_count = 0
            while retry_count < max_retries:
                try:
                    if qa_block is None:
                        raise Exception(f"Error occurred on block {block_number}.")
                    
                    qa_lines = qa_block.splitlines()[:2]
                    print()
                    print(qa_lines[0])
                    print(colored(qa_lines[1], "yellow"))
                    with open(qa_file_path, 'a') as f:
                        f.write(qa_block)
                    
                    current_position = abs_transcript_start_pos
                    block_number += 1
                    break  # Successfully processed the block, exit retry loop
                
                except Exception as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        print(f"\n********** K2 retries ({max_retries}) reached for block {block_number}. Skipping this block.")
                        current_position += max_segment_tokens  # Move to next position
                    else:
                        print(f"\n********** Error encountered: {str(e)}")
                        print(f"Retry attempt {retry_count} of {max_retries}")
                        print("Retrying the same block.")
            
            if retry_count == 0:
                print("Block processed successfully.")
            elif retry_count < max_retries:
                print("Block processed after retries.")
            else:
                print("Block skipped due to repeated errors.")

    print("QA extraction completed.")
    print("QA written to " + qa_file_path)
    
    return qa_file_path

def fcall_qa_incremental_OLD(transcript, next_tokens, fcall_prompt, start_position, debug=False):
    """
    Processes a transcript string incrementally to extract the next question-answer pair using OpenAI function calling.
    This function yields each QA block along with the current position in the transcript, allowing for incremental processing and resumption from the last processed position.  

    :param transcript: string of the transcript content.
    :param next_tokens: integer of the number of tokens to look ahead.
    :param fcall_prompt: string of the prompt to be used for function calling.
    :param start_position: integer of the starting position in the transcript.
    :yield: tuple of (qa_block, current_position) or (None, current_position) if an error occurred.
    """
    current_position = start_position
    previous_block = None
    total_chars_transcript = len(transcript)
    
    # Add tracking for detecting stuck positions
    position_history = []
    stuck_threshold = 3  # Number of times to try processing same area before forcing skip
    min_position_advance = next_tokens # Minimum characters to skip if stuck

    while current_position < len(transcript):
        chunk, next_position = get_next_chunk(transcript, current_position, next_tokens)
        print(f"chunk transcript positions: {current_position:,} to {next_position:,} of total: {total_chars_transcript:,} | Percent done: {round(current_position / total_chars_transcript * 100)}%")
        
        # Track positions to detect if we're stuck
        position_history.append(current_position)
        if len(position_history) > stuck_threshold:
            position_history.pop(0)
            
            # If we've processed the same area multiple times
            if max(position_history) - min(position_history) < min_position_advance:
                print(f"Detected stuck processing - forcing skip forward by {min_position_advance} characters")
                current_position += min_position_advance
                position_history.clear()  # Reset history after skip
                continue

        prev_block_prompt = "Please identify the first question-answer pair in the following transcript chunk:" if not previous_block else f"""
        Previous Question-Answer Block:
        {previous_block}
        Please identify the next question-answer pair after this one in the following transcript chunk:
        """

        full_prompt = fcall_prompt + "\n" + prev_block_prompt + "\n\n" + chunk
        
        try:
            verbose_print(debug, f"DEBUG\nfull_prompt: {full_prompt}\nchunk: {chunk}\n")
            qa_response = openai_function_call(full_prompt, chunk, tools_qa_incremental_4())
            verbose_print(debug, f"qa_response: {qa_response}\n")
            
            # Extract the 'arguments' field from the function call
            arguments_json = qa_response['tool_calls'][0]['function']['arguments']

            # Attempt to parse the JSON
            try:
                arguments = json.loads(arguments_json)
                
                qa_block = f"CLARIFIED QUESTION: {arguments['clarified_question']}\n"
                qa_block += f"CLARIFIED ANSWER: {arguments['clarified_answer']}\n"
                qa_block += f"VERBATIM QUESTION: {arguments['verbatim_question']}\n"
                qa_block += f"VERBATIM ANSWER: {arguments['verbatim_answer']}\n"
                qa_block += f"SPEAKER QUESTION: {arguments['speaker_question']}\n"
                qa_block += f"SPEAKER ANSWER: {arguments['speaker_answer']}\n"
                abs_transcript_start_pos = current_position + arguments['relative_start_position']
                abs_transcript_end_pos = current_position + arguments['relative_end_position']
                qa_block += f"TRANSCRIPT START POSITION: {abs_transcript_start_pos:,}\n"
                qa_block += f"TRANSCRIPT END POSITION: {abs_transcript_end_pos:,}\n"
                qa_block += f"TOPICS: {', '.join(arguments['topics'])}\n"
                qa_block += f"REVIEW FLAG: {arguments['review_flag']}\n\n"

            except json.decoder.JSONDecodeError as e:
                print("JSONDecodeError:", e)
                current_position += min_position_advance  # Force advance on error
                yield None, current_position
                continue
            
            print(f"qa response transcript position: {abs_transcript_start_pos:,} to {abs_transcript_end_pos:,}")
            # Update previous_block for the next iteration
            previous_block = qa_block
            
            # Update position based on LLM response
            current_position = abs_transcript_start_pos
            
            # If we successfully processed a block, clear the position history
            position_history.clear()
            
            yield qa_block, abs_transcript_start_pos
        except Exception as e:
            print(f"Error in qa extraction: {str(e)}")
            current_position += min_position_advance  # Force advance on error
            yield None, current_position


### QA BY SECTIONS - FULL BLOCKS
FCALL_SYSTEM_PROMPT_QA_SECTIONS_TRANSCRIPT_FDA_TOWNHALLS_1A = """
You are an expert text analyzer trained in identifying questions and answers in transcript sections of dialogue, specifically for FDA Town Hall meetings on COVID-19 diagnostics.

Your Role:
- Determine whether there is important content that should be extracted as an additional question-answer (QA) block, with the provided context of a list of the last several previous questions and the complete previous QA block.
- If additional important content is present, extract and clarify the next question-answer block from the provided transcript chunk.
- If no additional important content is present, respond with "NO NEW QUESTION" for the clarified_question field and leave the other fields blank (empty strings) or zero.
- Extract only new, distinct question-answer content that appears after the text already covered by the previous QA block. Do not duplicate an already-extracted Q&A from the same text segment. However, if there is new or distinct content within a previously introduced speaker response that was never captured, you may extract it now.
- Provide both verbatim and clarified versions of the question and answer to ensure thorough coverage and readability.

Important Note on Use Case:
- Only the clarified_question field will be indexed and used for semantic search. Therefore, the coverage of each new topic or keyword must appear in the question, ensuring users can find it later by searching. If an answer covers multiple distinct topics, you should form multiple questions, even if they overlap in the answer text, so that each topic appears in its own question for better searchability.
- In other words, the question text itself must include key terms, phrases, or concepts from the answer. This way, anyone searching for those terms will retrieve the relevant QA block. Redundant or nearly duplicated questions should be avoided, but it’s acceptable for multiple different questions to reference the same or partially overlapping answer segments if each question addresses a unique aspect that users might search for.

Coverage & Percentage Guidance:
- **Aim for comprehensive coverage** of the FDA’s important regulatory and technical information. 
- If a transcript chunk introduces new or significant material not in the previous questions, **extract a new question.** 
- **Include high-level updates**: Regulatory updates, newly authorized tests, or statements of FDA priority should be treated as “implied questions” if they are not explicitly phrased as questions.
- **Allow multiple questions** from a single turn or answer if there are clearly separate topics or points worth extracting.
- If you determine there is no distinct new question to be extracted for a given chunk, return "NO NEW QUESTION" (instructions below).

Coverage & Percentage Guidance:
- **Aim for comprehensive coverage** of the FDA’s important regulatory and technical information. 
- If a transcript chunk introduces new or significant material not in the previous questions, **extract a new question.** 
- **Include high-level updates**: Regulatory updates, newly authorized tests, or statements of FDA priority should be treated as “implied questions” if they are not explicitly phrased as questions.
- **Allow multiple questions** from the same transcript section if there are clearly separate topics or points worth extracting.
- If you determine there is no distinct new question to be extracted for a given transcript section, return "NO NEW QUESTION" (instructions below).

Speaker Guidelines:
- Speakers are identified by lines ending with a colon, timestamp, or by a direct statement of their role (e.g., "Dr. Smith (FDA):").
- Authority Speakers are indicated by 'FDA' in their role description.
- Non-Authority Speaker statements must be included in the clarified_answer field if they contain important details or are directly addressed by the FDA. If uncertain, set review_flag = True.

Content Guidelines:
- Focus on technical, procedural, or legal aspects of COVID-19 diagnostics (test development, validation, labeling, etc.).
- Exclude trivial or orchestration details like meeting start-up or speaker order.
- If important FDA information is present but no explicit question is asked, generate an “implied” question.
- Whenever uncertain, set review_flag to True.

Verbatim vs. Clarified Output:
- Provide both verbatim_question and verbatim_answer, exactly as they appear in the transcript (minus speaker labels and newlines).
- Provide clarified_question and clarified_answer for conciseness, improved clarity, and readability.

Option to Return “NO NEW QUESTION”:
- If no new question is found, set "clarified_question" to the exact string "NO NEW QUESTION" and leave the other fields blank (empty strings) or zero. 
- Set "review_flag" to True if there is significant uncertainty in whether new QA content is present, or False if there is clearly no remaining new content given the provided context in the form of the previous list of several questions and previous entire QA block.
- If the previously extracted QA block is empty or nonexistent, extract the earliest important content as the new Q&A, since there are no previous questions to consider.
- You **must extract at least one question-answer block** from each transcript section.

Remember, the user’s application will index only the questions for semantic search, so your clarified_question fields must capture all key points that a user might search for in the future. Avoid discarding or merging clearly separate topics into one question.
Your output must strictly follow the schema. All fields are required, so if there is no new QA, fill them with the agreed-upon placeholders or zeros.

The transcript will be processed in a progressive manner with the response being one in a sequence.
"""
FCALL_SYSTEM_PROMPT_QA_SECTIONS_TRANSCRIPT_FDA_TOWNHALLS_1B = """
You are an expert text analyzer trained in identifying questions and answers in transcript sections of dialogue, specifically for FDA Town Hall meetings on COVID-19 diagnostics.

Your Role:
- Determine whether there is important content that should be extracted as an additional question-answer (QA) block, with the provided context of a list of the last several previous questions and the complete previous QA block.
- If additional important content is present, extract and clarify the next question-answer block from the provided transcript chunk.
- If no additional important content is present, respond with "NO NEW QUESTION" for the clarified_question field and leave the other fields blank (empty strings) or zero.
- Extract only new, distinct question-answer content that appears after the text already covered by the previous QA block. Do not duplicate an already-extracted Q&A from the same text segment. However, if there is new or distinct content within a previously introduced speaker response that was never captured, you may extract it now.
- Provide both verbatim and clarified versions of the question and answer to ensure thorough coverage and readability.

Important Note on Use Case:
- Only the clarified_question field will be indexed and used for semantic search. Therefore, the coverage of each new topic or keyword must appear in the question, ensuring users can find it later by searching. If an answer covers multiple distinct topics, you should form multiple questions, even if they overlap in the answer text, so that each topic appears in its own question for better searchability.
- In other words, the question text itself must include key terms, phrases, or concepts from the answer. This way, anyone searching for those terms will retrieve the relevant QA block. Redundant or nearly duplicated questions should be avoided, but it’s acceptable for multiple different questions to reference the same or partially overlapping answer segments if each question addresses a unique aspect that users might search for.

Coverage & Redundancy Guidelines:
- **Focus on distinct, significant content**: Extract only genuinely new information or materially different perspectives on a topic.
- **Avoid splitting related points**: If multiple statements support the same core concept, combine them into a single comprehensive Q&A rather than creating separate blocks.
- **Prioritize unique regulatory guidance**: Focus especially on FDA directives, policy changes, and official clarifications.
- **Consolidate similar topics**: When multiple speakers discuss the same topic, combine their key points into a single thorough Q&A unless they present contradictory or significantly different information.
- **Distinguish truly new content**: Before creating a new QA block, verify that the information isn't effectively covered by previous blocks in the section, even if phrased differently.

Redundancy Prevention:
- Before extracting a new QA block, carefully review the previous questions and answers in this section.
- Do not create a new block if the core information is already captured, even if expressed differently.
- When in doubt about whether content is sufficiently distinct, prefer consolidating into existing QA blocks over creating new ones.
- Multiple perspectives on the same topic should be combined unless they present materially different information or contradictory guidance.

Speaker Guidelines:
- Speakers are identified by lines ending with a colon, timestamp, or by a direct statement of their role (e.g., "Dr. Smith (FDA):").
- Authority Speakers are indicated by 'FDA' in their role description.
- Non-Authority Speaker statements must be included in the clarified_answer field if they contain important details or are directly addressed by the FDA. If uncertain, set review_flag = True.

Content Guidelines:
- Focus on technical, procedural, or legal aspects of COVID-19 diagnostics (test development, validation, labeling, etc.).
- Exclude trivial or orchestration details like meeting start-up or speaker order.
- If important FDA information is present but no explicit question is asked, generate an “implied” question.
- Whenever uncertain, set review_flag to True.
- Combine related points into comprehensive QA blocks rather than creating multiple overlapping blocks.
- Focus on extracting genuinely new information rather than different phrasings of the same guidance.

Verbatim vs. Clarified Output:
- Provide both verbatim_question and verbatim_answer, exactly as they appear in the transcript (minus speaker labels and newlines).
- Provide clarified_question and clarified_answer for conciseness, improved clarity, and readability.

Option to Return “NO NEW QUESTION”:
- If no new question is found, set "clarified_question" to the exact string "NO NEW QUESTION" and leave the other fields blank (empty strings) or zero. 
- Set "review_flag" to True if there is significant uncertainty in whether new QA content is present, or False if there is clearly no remaining new content given the provided context in the form of the previous list of several questions and previous entire QA block.
- If the previously extracted QA block is empty or nonexistent, extract the earliest important content as the new Q&A, since there are no previous questions to consider.
- You **must extract at least one question-answer block** from each transcript section.

Remember, the user’s application will index only the questions for semantic search, so your clarified_question fields must capture all key points that a user might search for in the future. Avoid discarding or merging clearly separate topics into one question.
Your output must strictly follow the schema. All fields are required, so if there is no new QA, fill them with the agreed-upon placeholders or zeros.

The transcript will be processed in a progressive manner with the response being one in a sequence.
"""
def tools_qa_sections_1():
    return [{
        "type": "function",
        "function": {
            "name": "extract_qa",
            "description": "Extract and clarify the next question-answer block (both verbatim and clarified fields) from an FDA Town Hall transcript section. If no new question is found, fill all required fields with placeholders/zeros as instructed in the system prompt.",
            "strict": True,  # For Structured Output
            "parameters": {
                "type": "object",
                "properties": {
                    "clarified_question": {
                        "type": "string",
                        "description": (
                            "A concise, edited version of the question. If no new question is found, set this to 'NO NEW QUESTION'. The entire text should be on one line. Do not mention any specific speaker names."
                        )
                    },
                    "clarified_answer": {
                        "type": "string",
                        "description": (
                            "A concise, edited version of the answer. If no new question is found, leave this field blank (e.g., ''). The entire text of this answer should be on a single line. Do not mention any specific speaker names, instead use 'FDA' where appropriate."
                        )
                    },
                    "verbatim_question": {
                        "type": "string",
                        "description": (
                            "The exact text of the question, minus speaker labels/newlines. If no new question is found, use ''. If no explicit question is asked, use the string 'IMPLIED QUESTION'. The entire text should be on a single line. Do not start the text with the speaker name from the preceding speaker line."
                        )
                    },
                    "verbatim_answer": {
                        "type": "string",
                        "description": (
                            "The exact text of the answer, minus speaker labels/newlines. If no new question is found, use ''. The entire text should be on a single line. Do not start the text with the speaker name from the preceding speaker line."
                        )
                    },
                    "speaker_question": {
                        "type": "string",
                        "description": (
                            "Name/role of question speaker. Use '' if no new question is found. The name must be as identified in the transcript by the text in the speaker line that precedes a colon or timestamp. Do not use a different name spelling that may appear in the speaker dialogue. If the question is implied from an Authority Speaker's statement, use 'IMPLIED'."
                        )
                    },
                    "speaker_answer": {
                        "type": "string",
                        "description": (
                            "Name/role of answer speaker. Use '' if no new question is found. The name must be as identified in the transcript by the text in the speaker line that precedes a colon or timestamp. Do not use a different name spelling that may appear in the speaker dialogue. If the question is implied from an Authority Speaker's statement, use 'IMPLIED'."
                        )
                    },
                    "topics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "A list of 1-3 key topics addressed in the question-answer block. If no new question is found, return an empty list []."
                        )
                    },
                    "review_flag": {
                        "type": "boolean",
                        "description": (
                            "Set True if significant uncertainty in the response. Otherwise False."
                        )
                    }
                },
                "required": [
                    "clarified_question", "clarified_answer","verbatim_question", "verbatim_answer",
                    "speaker_question", "speaker_answer", "topics", "review_flag"
                ],
                "additionalProperties": False
            }
        }
    }]
def fcall_qa_section(transcript_section, fcall_prompt, provider="openai", debug=False):
    """
    Process a single transcript section to extract one or more question-answer blocks.
    Must extract at least one question-answer block from each section.
    
    :param transcript_section: string containing a section of the transcript to process
    :param fcall_prompt: string containing the prompt for function calling
    :param provider: string indicating which provider to use ("openai" or "anthropic")
    :param debug: boolean to enable debug printing
    :yield: tuple of (qa_block, None) for each QA block found in the section, or (None, None) if error
    """
    HISTORY_SIZE = 10  # Number of previous questions to maintain
    previous_questions = []  # List to store previous questions
    previous_block = None  # Store the most recent QA block
    qa_blocks_found = 0  # Track number of QA blocks found in this section
    max_retries = 3  # Maximum attempts to get at least one QA block
    
    def is_no_new_question(arguments):
        """Helper function to check if response indicates no new question"""
        return (arguments['clarified_question'].upper() == 'NO NEW QUESTION' or 
                not arguments['clarified_answer'].strip())
    
    # Get appropriate tools format for the provider
    tools = tools_qa_sections_1()
    if provider == "anthropic":
        tools = convert_tools_to_anthropic_format(tools)
    
    # Process the section until no more QA blocks are found
    while True:
        # Check if we've reached the maximum questions per section
        if len(previous_questions) >= HISTORY_SIZE:
            max_msg = f"__Reached maximum number of questions to extract per section ({HISTORY_SIZE})__"
            yield None, max_msg  # Change the second element of tuple from None to the message
            return
            
        # Create context with previous questions and previous block (from most recent to oldest)
        prev_questions_context = "Previous questions - **DO NOT extract near identicalnew questions**:\n"
        for i, q in enumerate(previous_questions, 1):
            prev_questions_context += f"{i}. {q}\n"
        
        if not previous_block:
            prev_block_context = "Please identify the first question-answer block in this transcript section. Every section must have at least one QA block extracted:"
        else:
            prev_block_context = (f"Previous Question-Answer Block:\n{previous_block}\n"
                                f"Please identify the next question-answer block in this transcript section:")
        
        full_prompt = (
            f"{fcall_prompt}\n\n"
            f"{prev_questions_context}\n"
            f"{prev_block_context}\n\n"
            f"{transcript_section}"
        )
        verbose_print(debug, f"full_prompt: {full_prompt}")

        try:
            # Make the appropriate function call based on provider
            if provider == "openai":
                qa_response = openai_function_call(full_prompt, transcript_section, tools)
            elif provider == "anthropic":  # anthropic
                qa_response = anthropic_function_call(full_prompt, transcript_section, tools)
            else:
                raise ValueError("Provider must be either 'openai' or 'anthropic'")
            
            # Parse the response using the common parser
            arguments = parse_function_call_response(qa_response, provider)
            
            if not arguments:
                raise Exception("Failed to parse function call response")
            
            # If no new QA found
            if is_no_new_question(arguments):
                # If we haven't found any QA blocks yet, retry
                if qa_blocks_found == 0 and max_retries > 0:
                    max_retries -= 1
                    print(colored(f"**No QA found but section requires at least one. Retrying... ({max_retries} attempts remaining)**", "red"))
                    continue
                # If we've found at least one QA block, we can end
                elif qa_blocks_found > 0:
                    return
                # If we've exhausted retries and still haven't found a QA block
                else:
                    print(colored("**Failed to extract any QA blocks after multiple attempts. This section may need review.**", "red"))
                    yield None, None
                    return
            
            # Successfully found a QA block
            qa_blocks_found += 1
            
            # Update previous questions list
            previous_questions.insert(0, arguments['clarified_question'])
            if len(previous_questions) > HISTORY_SIZE:
                previous_questions.pop()

            # Create QA block without numbering
            qa_block = ""
            qa_block += f"CLARIFIED QUESTION: {arguments['clarified_question']}\n"
            qa_block += f"CLARIFIED ANSWER: {arguments['clarified_answer']}\n"
            qa_block += f"VERBATIM QUESTION: {arguments['verbatim_question']}\n"
            qa_block += f"VERBATIM ANSWER: {arguments['verbatim_answer']}\n"
            qa_block += f"SPEAKER QUESTION: {arguments['speaker_question']}\n"
            qa_block += f"SPEAKER ANSWER: {arguments['speaker_answer']}\n"
            qa_block += f"TOPICS: {', '.join(arguments['topics'])}\n"
            qa_block += f"REVIEW FLAG: {arguments['review_flag']}\n\n"

            previous_block = qa_block
            yield qa_block, None
            
        except Exception as e:
            print(colored(f"**Error in qa extraction: {str(e)}**", "red"))
            if qa_blocks_found == 0 and max_retries > 0:
                max_retries -= 1
                print(colored(f"**Error occurred but section requires at least one QA. Retrying... ({max_retries} attempts remaining)**", "red"))
                continue
            yield None, None
            return
def create_qa_file_from_transcript_sections(file_path, fcall_prompt, provider="openai", heading="### transcript", delimiter='---'):
    """
    Extract QA blocks from a transcript file by processing sections delimited by a separator.
    
    :param file_path: string path to the transcript file
    :param fcall_prompt: string prompt for function calling
    :param provider: string indicating which provider to use ("openai" or "anthropic")
    :param delimiter: string used to separate transcript sections
    :return qa_file_path: string path to the created QA file
    """
    # Setup file and get transcript
    start_time = time.time()  # used to calculate elapsed time at the end of the function
    datetime = get_current_datetime_humanfriendly()
    date = datetime.split(' ')[0]
    metadata, content = read_metadata_and_content(file_path)
    metadata = set_metadata_field(metadata, "last updated", f"{date} Created QA Sections")
    metadata = set_metadata_field(metadata, "source file", file_path)
    
    # Set model based on provider
    if provider == "openai":
        model = OPENAI_MODEL
    elif provider == "anthropic":
        model = ANTHROPIC_MODEL
    else:
        raise ValueError("Provider must be either 'openai' or 'anthropic'")
    
    # Initialize log lines for extract log
    log_lines = []
    log_lines.append("### extract log")
    log_lines.append(f"datetime: {datetime}")
    log_lines.append("function: primary.llm.create_qa_file_from_transcript_sections")
    # Find the global variable name that matches the prompt content
    prompt_name = next((var_name for var_name, var_value in globals().items() 
                       if var_value is fcall_prompt), "UNKNOWN_PROMPT")
    log_lines.append(f"prompt: {prompt_name}")
    log_lines.append("tools: tools_qa_sections_1")
    log_lines.append("prep: primary.llm.add_transcript_section_delimiters for non-FDA speakers")
    log_lines.append(f"provider: {provider}")
    log_lines.append(f"model: {model}")
    
    transcript = get_heading(file_path, "### transcript")
    transcript = transcript.lstrip('### transcript').rstrip('\n').lstrip('\n*')
    log_lines.append(f"number of characters in transcript: {len(transcript):,}")
    print("\n".join(log_lines))  # Print header information

    # Create output file
    initial_content = "## content\n\n### qa\n"
    qa_file_path = write_metadata_and_content(file_path, metadata, initial_content, overwrite='no-sub', suffix_new='_qa-created')
    
    # Split transcript into sections
    sections = transcript.split(delimiter)
    total_sections = len(sections)
    block_counter = 1
    max_retries = 5

    # Process each section
    for section_num, section in enumerate(sections, 1):
        section_header = f"\n#### Processing section {section_num} of {total_sections}"
        print(section_header)
        log_lines.append(section_header)
        
        section = section.strip()
        if not section:  # Skip empty sections
            continue
            
        try:
            # Process all QA blocks in this section
            for qa_block, msg in fcall_qa_section(section, fcall_prompt, provider=provider):
                if qa_block is None:
                    if msg:  # If there's a message about max questions
                        print(colored(msg, "yellow"))  # Print once in yellow
                        while log_lines and not log_lines[-1].strip():  # Strip only trailing blank lines
                            log_lines.pop()
                        log_lines.append(msg)  # Keep any trailing newlines in message
                    break  # Move to next section
                
                # Add block number and write to file
                numbered_block = f"QA Block {block_counter}\n{qa_block}"
                qa_lines = numbered_block.splitlines()[:2]
                question_line = qa_lines[1].replace("CLARIFIED QUESTION: ", "")
                print(f"{qa_lines[0]}:  {question_line}")
                log_lines.append(f"{qa_lines[0]}:  {question_line}")
                
                with open(qa_file_path, 'a') as f:
                    f.write(numbered_block)
                
                block_counter += 1
                
        except Exception as e:
            error_msg = f"\n********** Error encountered in section {section_num}: {str(e)}"
            print(colored(error_msg, "red"))
            log_lines.append(error_msg)
            continue  # Move to next section

    # Append extract log to the QA file
    with open(qa_file_path, 'a') as f:
        f.write("\n\n" + "\n".join(log_lines))

    print(f"\nQA extraction completed in {(time.time() - start_time) / 60:.1f} minutes.")
    print("QA written to " + qa_file_path)
    return qa_file_path

#CUR_SOURCE_FILE_PATH = "data/floodlamp/reg/fda-townhalls/f5_fixnames/2020-12-09_Virtual Town Hall 36_fixnames.md"

### Q SIMILARITY
def get_questions_from_qa_file(qa_file_path, heading):
    """
    Gets questions and their section numbers from a QA file, handling different heading formats.
    For custom headings (not "### qa"), this function will find any line containing a colon
    under the specified heading and treat everything after the colon (and any following whitespace)
    as a question, ignoring any prefixes or numbering schemes before the colon.

    :param qa_file_path: string, path to the QA file to parse.
    :param heading: string, heading format to determine parsing method.
    :return questions: list, tuples of (section number, question text).
    """
    from chalicelib.structured import get_blocks_from_file, get_field_value
    from chalicelib.fileops import get_heading, get_heading_level
    
    if heading == "### qa":
        # Get all blocks from the file
        blocks = get_blocks_from_file(qa_file_path)
        
        # Process each block to extract questions and section numbers
        questions = []
        for block in blocks:
            # Extract section number from block header (e.g., "QA Block 6-8")
            block_lines = block.split('\n')
            if block_lines and block_lines[0].startswith('QA Block '):
                try:
                    section_num = int(block_lines[0].split('-')[0].replace('QA Block ', ''))
                except (IndexError, ValueError):
                    continue
                
                # Get question from CLARIFIED QUESTION field
                question = get_field_value(block, "CLARIFIED QUESTION")
                if question:
                    questions.append((section_num, question))
                
        return questions
    elif heading.startswith("##### "):
        # Read the file content
        with open(qa_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Split into sections for processing
        sections = content.split('\n')
        questions = []
        
        # Get the heading level to find parent sections
        heading_level = get_heading_level(heading)
        parent_level = heading_level - 1
        
        # Process each line
        current_section = None
        for i, line in enumerate(sections):
            # If we find our target heading
            if line.strip() == heading:
                # Look backwards for the parent section heading
                parent_pattern = f"^{'#' * parent_level} Section (\\d+)"
                
                for prev_line in reversed(sections[:i]):
                    match = re.match(parent_pattern, prev_line)
                    if match:
                        current_section = int(match.group(1))
                        break
                continue
            
            # Stop if we hit another heading of same level or a heading with fewer hashtags
            if line.startswith('#'):
                line_level = len(re.match('^#+', line).group())
                if line_level <= heading_level:
                    current_section = None
                    continue
                
            # If we're under a heading and find a line with a colon
            if current_section is not None and ':' in line:
                # Split on first colon and take everything after it, stripped of whitespace
                question_text = line.split(':', 1)[1].strip()
                if question_text:  # Only add if there's actual text after the colon
                    questions.append((current_section, question_text))
        
        return questions
    else:
        raise ValueError(f"Invalid heading format: {heading}")
def get_questions_from_extract_log(qa_file_path, heading_level=5, verbose=False):
    """
    Gets all questions from a QA file by finding unique headings at the specified level
    and extracting questions from each heading section.

    :param qa_file_path: string, path to the QA file to parse
    :param heading_level: integer, markdown heading level to search for (e.g., 5 for #####)
    :param verbose: boolean, whether to print heading counts
    :return: list of tuples (section_number, question_text) sorted by section number
    """
    from chalicelib.fileops import get_heading_level
    
    # Read the file content
    with open(qa_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all headings at the specified level
    heading_prefix = '#' * heading_level + ' '
    headings = []
    for line in content.split('\n'):
        if line.startswith(heading_prefix):
            heading = line.strip()
            if heading not in headings:  # Only add unique headings
                headings.append(heading)
    
    if not headings:
        print(f"No headings found at level {heading_level} (#{'#' * heading_level})")
        return []
    
    # Get questions from each heading
    all_questions = []
    total_questions = 0
    verbose_print(verbose, f"{qa_file_path}")
    for heading in headings:
        questions = get_questions_from_qa_file(qa_file_path, heading)
        if questions:  # Only extend if we got questions back
            all_questions.extend(questions)
            total_questions += len(questions)
            verbose_print(verbose, f"Questions in {heading}: {len(questions)}")
    
    # Sort questions by section number while preserving order within sections
    all_questions.sort(key=lambda x: x[0])
    
    verbose_print(verbose, f"Total questions in extract log: {total_questions}")
    
    return all_questions
def compare_question_tuple_lists(list1, list2, list1_name="List 1", list2_name="List 2"):
    """
    Compares two lists of question tuples and identifies differences between them.
    
    :param list1: list of tuples (section_number, question_text)
    :param list2: list of tuples (section_number, question_text)
    :param list1_name: string name for first list in output
    :param list2_name: string name for second list in output
    :return: boolean True if lists are identical, False otherwise
    """
    # Convert tuples to lists to preserve order
    questions1 = [q[1] for q in list1]
    questions2 = [q[1] for q in list2]

    print(f"Number of questions in {list1_name}: {len(questions1)}")
    print(f"Number of questions in {list2_name}: {len(questions2)}")
    
    # Compare questions at each position
    min_len = min(len(questions1), len(questions2))
    questions_identical = True
    align_width = 15  # Width for aligning output
    
    for i in range(min_len):
        if questions1[i] != questions2[i]:
            if questions_identical:
                print(colored("***** Differences between Extract log and QA Blocks Questions Listsfound *****", "red"))
                questions_identical = False
            print(f"Found difference at position {i+1}:")
            print(f"{list1_name}:".ljust(align_width) + questions1[i])
            print(f"{list2_name}:".ljust(align_width) + questions2[i])
    
    # Check for any remaining questions in the longer list
    if len(questions1) > len(questions2):
        for i in range(min_len, len(questions1)):
            if questions_identical:
                print(colored("***** Differences between Extract log and QA Blocks Questions Listsfound *****", "red"))
                questions_identical = False
            print(f"Found difference at position {i+1}:")
            print(f"{list1_name}:".ljust(align_width) + questions1[i])
            print(f"{list2_name}:".ljust(align_width) + "<missing>")
    elif len(questions2) > len(questions1):
        for i in range(min_len, len(questions2)):
            if questions_identical:
                print(colored("***** Differences between Extract log and QA Blocks Questions Listsfound *****", "red"))
                questions_identical = False
            print(f"Found difference at position {i+1}:")
            print(f"{list1_name}:".ljust(align_width) + "<missing>")
            print(f"{list2_name}:".ljust(align_width) + questions2[i])
    
    if questions_identical:
        print(colored("Extract log and QA Blocks Questions Lists are identical.", "green"))
    
    # Return sets of unique questions for backward compatibility
    # return set(questions1) - set(questions2), set(questions2) - set(questions1)
    return questions_identical
def mrun_get_questions_from_qa_file():
    pass
#if __name__ == "__main__":
    #qa_file_path = "data/floodlamp/reg/fda-townhalls/f5_fixnames/2020-12-09_Virtual Town Hall 36_qa-qonly_found.md"
    qa_file_path = sub_suffix_in_str(CUR_SOURCE_FILE_PATH, '_qa-qonly')
    # cur_heading = "##### Implicit Questions Extraction"
    # questions = get_questions_from_qa_file(cur_file_path, cur_heading)
    # print(f"Number of questions in {cur_heading}: {len(questions)}")

    questions_extract_log = get_questions_from_extract_log(qa_file_path, verbose=True)
    print(f"Number of questions in extract log: {len(questions_extract_log)}")
    questions_qa_blocks = get_questions_from_qa_file(qa_file_path, heading="### qa")
    print(f"Number of questions in qa blocks: {len(questions_qa_blocks)}")
    compare_question_tuple_lists(questions_extract_log, questions_qa_blocks, "Extract log", "QA blocks")

    # for question in questions:
    #     print(question)

def generate_and_save_question_embeddings(qa_file_path, questions, verbose=True):
    """
    Generates embeddings for questions and saves them to a file.

    :param qa_file_path: string, path to the QA file to parse.
    :param questions: list, questions to generate embeddings for.
    :param verbose: bool, whether to print progress messages.
    :return: string, path to the saved embeddings file.
    """
    import numpy as np
    from chalicelib.vectordb import generate_embedding
    
    # Create output filename
    embeddings_file = qa_file_path.replace(".md", "_q-vectors.npz")
    
    # Check if file already exists
    if os.path.exists(embeddings_file):
        response = input(f"\nEmbeddings file already exists at: {embeddings_file}\nHit ctrl-c to check file, 's' to run and overwrite, any other key to skip and use current file: ")
        if response.lower() != 's':
            print(f"Skipping embedding generation and using existing file.")
            return embeddings_file
    
    # Generate embeddings
    embeddings_data = {
        'questions': [],
        'section_numbers': [],
        'embeddings': []
    }
    
    # Process each question
    for i, (section_num, question) in enumerate(questions, 1):
        verbose_print(verbose, f"Generating embedding {i} of {len(questions)}: {question[:100]}...")
        embedding = generate_embedding(question)
        embeddings_data['questions'].append(question)
        embeddings_data['section_numbers'].append(section_num)
        embeddings_data['embeddings'].append(embedding)
        
    # Save to compressed numpy format
    np.savez_compressed(
        embeddings_file,
        questions=embeddings_data['questions'],
        section_numbers=embeddings_data['section_numbers'],
        embeddings=embeddings_data['embeddings']
    )
    
    verbose_print(verbose, f"Saved embeddings to: {embeddings_file}")
    return embeddings_file
def mrun_generate_and_save_question_embeddings():
    pass
#if __name__ == "__main__":
    qa_file_path = sub_suffix_in_str(CUR_SOURCE_FILE_PATH, '_qa-qonly')
    questions = get_questions_from_extract_log(qa_file_path)
    embeddings_file = generate_and_save_question_embeddings(qa_file_path, questions)
    print(f"Embeddings file saved to: {embeddings_file}")
def calc_question_list_similarities(embeddings_file, similarity_threshold=0.781):
    """
    Calculates pairwise similarities between questions within the same section.

    :param embeddings_file: string, path to the saved embeddings file.
    :param similarity_threshold: float, threshold for similarity score to remove questions
    :return: tuple of (similarities dict, list of questions to remove, output string)
        - similarities: dict containing grouped questions and their similarity matrices by section
        - questions_to_remove: list of strings in format "section-question" for shorter questions in similar pairs
        - output_str: string containing the formatted output of similar questions and removal decisions
    """
    import numpy as np
    from scipy.spatial.distance import cdist
    from collections import defaultdict
    
    output_lines = [
        "### deduplication log",
        f"Showing question pairs above similarity threshold: {similarity_threshold}"]

    # Load the saved embeddings
    data = np.load(embeddings_file, allow_pickle=True)
    questions = data['questions']
    section_numbers = data['section_numbers']
    embeddings = data['embeddings']
    
    # Group by section
    sections = defaultdict(list)
    for i, (section, question, embedding) in enumerate(zip(section_numbers, questions, embeddings)):
        sections[section].append({
            'question': question,
            'embedding': embedding,
            'index': i
        })
    
    # Calculate similarities within each section
    section_similarities = {}
    questions_to_remove = []
    
    for section_num, items in sections.items():
        if len(items) > 1:
            section_embeddings = np.array([item['embedding'] for item in items])
            similarity_matrix = 1 - cdist(section_embeddings, section_embeddings, metric='cosine')
            
            max_sim = np.max(similarity_matrix - np.eye(len(items)))
            found_similar = False
            if max_sim > similarity_threshold:
                output_lines.append(f"\n#### Section {section_num} similar questions (similarity > {similarity_threshold}):")
                n = len(items)
                for i in range(n):
                    for j in range(i+1, n):
                        sim = similarity_matrix[i][j]
                        if sim >= similarity_threshold:
                            if not found_similar:
                                found_similar = True
                            
                            # Determine which question to remove (the shorter one)
                            q1_len = len(items[i]['question'])
                            q2_len = len(items[j]['question'])
                            
                            # Format the questions, marking the shorter one
                            q1_text = items[i]['question']
                            q2_text = items[j]['question']
                            
                            output_lines.append(f"Q{i+1} & Q{j+1} (similarity: {sim:.3f}):")
                            if q1_len <= q2_len:
                                output_lines.append(f"__X Q{i+1}: {q1_text}__")
                                output_lines.append(f"    Q{j+1}: {q2_text}\n")
                                questions_to_remove.append(f"{section_num}-{i+1}")
                            else:
                                output_lines.append(f"    Q{i+1}: {q1_text}")
                                output_lines.append(f"__X Q{j+1}: {q2_text}__\n")
                                questions_to_remove.append(f"{section_num}-{j+1}")
            
            section_similarities[section_num] = {
                'matrix': similarity_matrix,
                'questions': [item['question'] for item in items],
                'indices': [item['index'] for item in items]
            }

    # Add final summary lines
    output_lines.append(f"Embeddings file: {embeddings_file}")
    output_lines.append(f"Similarity threshold: {similarity_threshold}")
    output_lines.append(f"Questions to remove {len(questions_to_remove)}: {questions_to_remove}")
    
    # Print the output as before
    print("\n".join(output_lines))
    output_text = "\n".join(output_lines)
    
    return section_similarities, questions_to_remove, output_text
def mrun_calc_question_list_similarities():
    pass
#if __name__ == "__main__":
    qa_file_path = sub_suffix_in_str(CUR_SOURCE_FILE_PATH, '_qa-qonly')
    embeddings_file_path = qa_file_path.replace(".md", "_q-vectors.npz")
    similarities, questions_to_remove, output_text = calc_question_list_similarities(embeddings_file_path)
    print(f"\n\noutput_text:\n{output_text}")
def visualize_question_similarities_1(vectors_file_path, min_similarity=0.7):  # uses seaborn which cannot do tooltips
    """
    Creates separate heatmaps for questions within each section, showing only the lower triangular portion.
    Takes a vectors file path as input, calculates similarities, and saves visualization.

    :param vectors_file_path: string, path to the NPZ file containing question vectors
    :param min_similarity: float, minimum similarity threshold to report
    :return: string, path to the saved visualization file
    """
    import seaborn as sns
    import matplotlib.pyplot as plt
    import numpy as np
    
    # Calculate similarities from the vectors file
    similarities = calc_question_list_similarities(vectors_file_path)
    
    # Calculate number of sections and setup subplot grid
    n_sections = len(similarities)
    if n_sections == 0:
        print("No sections with multiple questions found.")
        return
        
    # Calculate grid dimensions - aim for roughly square layout
    n_cols = min(5, n_sections)  # K2 5 columns
    n_rows = (n_sections + n_cols - 1) // n_cols
    
    # Scale figure size to fit laptop screen (roughly 1200x800 pixels)
    # Using 100 DPI as typical screen resolution
    max_width = 14  # inches (≈1200 pixels)
    max_height = 10  # inches (≈800 pixels)
    
    # Calculate size per subplot
    width_per_plot = max_width / n_cols
    height_per_plot = max_height / n_rows
    
    # Create figure with adjusted size
    fig = plt.figure(figsize=(width_per_plot * n_cols, height_per_plot * n_rows))
    
    # Create heatmaps for each section
    for idx, (section_num, section_data) in enumerate(similarities.items()):
        plt.subplot(n_rows, n_cols, idx + 1)
        
        # Create mask for upper triangle (excluding diagonal)
        mask = np.triu(np.ones_like(section_data['matrix']), k=1)
        
        # Create heatmap with mask
        sns.heatmap(
            section_data['matrix'],
            xticklabels=range(1, len(section_data['questions']) + 1),
            yticklabels=range(1, len(section_data['questions']) + 1),
            cmap='YlOrRd',
            vmin=0,
            vmax=1,
            mask=mask,
            square=True  # Make cells square
        )
        plt.title(f'Section {section_num}')
        plt.xlabel('Question Number')
        plt.ylabel('Question Number')
        
        # Print similar pairs for this section
        print(f"\n\n#### Section {section_num} similar questions (similarity > {min_similarity}):")
        n = len(section_data['questions'])
        
        # Track if we found any similar pairs and find max similarity
        found_similar = False
        max_sim = 0
        max_i = 0 
        max_j = 0
        
        for i in range(n):
            for j in range(i+1, n):  # Only upper triangle to avoid duplicates
                sim = section_data['matrix'][i][j]
                if sim >= min_similarity:
                    print(f"\nQ{i+1} & Q{j+1} (similarity: {sim:.3f}):")
                    print(f"Q{i+1}: {section_data['questions'][i]}")
                    print(f"Q{j+1}: {section_data['questions'][j]}")
                    found_similar = True
                if sim > max_sim:
                    max_sim = sim
                    max_i = i
                    max_j = j
                    
        if not found_similar:
            print(f"None with similarity greater than {min_similarity}")
            # print(f"\nHighest similarity pair (similarity: {max_sim:.3f}):")
            # print(f"Q{max_i+1}: {section_data['questions'][max_i]}")
            # print(f"Q{max_j+1}: {section_data['questions'][max_j]}")
    
    plt.tight_layout()
    
    # Adjust the layout to prevent overlap
    plt.subplots_adjust(hspace=0.5)
    
    # Create output filename based on vectors file
    viz_file = vectors_file_path.replace("_q-vectors.npz", "_q-similarities.png")
    
    # Save high-resolution version
    plt.savefig(viz_file, bbox_inches='tight', dpi=300)
    
    # Show the plot (need to close it manually to free memory and have terminal return)
    plt.show()
    
    # Close the figure to free memory
    #plt.close(fig)
    
    return viz_file
def visualize_question_similarities(vectors_file_path, min_similarity=0.7, fixed_colorscale=True):
    """
    Creates interactive heatmaps for questions within each section using Plotly.
    Shows similarity scores and questions in tooltips when hovering.

    :param vectors_file_path: string, path to the NPZ file containing question vectors
    :param min_similarity: float, minimum similarity threshold to report
    :param fixed_colorscale: bool, if True keeps color scale fixed while thresholding, if False rescales colors
    :return: string, path to the saved visualization file
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import numpy as np
    
    # Calculate similarities from the vectors file
    similarities = calc_question_list_similarities(vectors_file_path)
    
    # Calculate grid dimensions
    n_sections = len(similarities)
    if n_sections == 0:
        print("No sections with multiple questions found.")
        return
        
    n_cols = min(4, n_sections)  # DO NOT CHANGE THIS - K2 4 columns for better readability
    n_rows = (n_sections + n_cols - 1) // n_cols
    
    # Create subplot figure with additional vertical space for slider
    fig = make_subplots(
        rows=n_rows, 
        cols=n_cols,
        subplot_titles=[f'Section {section_num}' for section_num in similarities.keys()],
        vertical_spacing=0.1  # Add some space for the slider
    )
    
    # Store all heatmaps to update them with slider
    heatmaps = []
    
    # Create heatmaps for each section
    for idx, (section_num, section_data) in enumerate(similarities.items()):
        row = (idx // n_cols) + 1
        col = (idx % n_cols) + 1
        
        # Create mask for lower triangle (changed from upper to lower)
        mask = np.tril(np.ones_like(section_data['matrix']), k=0)  # Changed from triu to tril, k=0 includes diagonal
        masked_matrix = np.ma.masked_array(section_data['matrix'], mask)
        masked_matrix[mask == 1] = None  # Explicitly set masked values to None for Plotly
        
        # Create hover text matrix - modified to match new masking
        hover_text = []
        for i in range(len(section_data['questions'])):
            hover_row = []
            for j in range(len(section_data['questions'])):
                if i < j:  # Changed from i >= j to i < j for upper triangle
                    hover_row.append(
                        f"Similarity: {section_data['matrix'][i][j]:.3f}<br>" +
                        f"Q{i+1}: {section_data['questions'][i]}<br>" +
                        f"Q{j+1}: {section_data['questions'][j]}"
                    )
                else:
                    hover_row.append("")
            hover_text.append(hover_row)
        
        # Create base heatmap with modified colorbar settings
        heatmap = go.Heatmap(
            z=masked_matrix,
            text=hover_text,
            hoverongaps=False,
            hoverinfo='text',
            colorscale='YlOrRd',
            zmin=0,
            zmax=1,
            showscale=(idx == 0),
            colorbar=dict(
                len=0.3,
                thickness=12,
                x=1.05, # Colorbar horizontal position
                y=0.95, # Colorbar vertical position
                yanchor='top',
                xanchor='left',
                ticks='outside',
                ticklen=4,
                tickwidth=1,
                tickfont=dict(size=12),
                title=dict(
                    text='Similarity',
                    font=dict(size=14)
                )
            ),
            # Add these properties to maintain colorbar
            visible=True,
            showlegend=False,
        )
        
        fig.add_trace(heatmap, row=row, col=col)
        heatmaps.append(heatmap)
        
        # Update axes labels with more spacing for colorbar
        fig.update_xaxes(
            title_text='Question Number',
            ticktext=list(range(1, len(section_data['questions']) + 1)),
            tickvals=list(range(len(section_data['questions']))),
            row=row, col=col
        )
        fig.update_yaxes(
            title_text='Question Number',
            ticktext=list(range(1, len(section_data['questions']) + 1)),
            tickvals=list(range(len(section_data['questions']))),
            side='right',
            row=row, col=col
        )
    
    # Add slider with behavior based on fixed_colorscale
    if fixed_colorscale:
        slider_steps = [dict(
            method="update",
            args=[{
                "z": [[np.where(m >= val/20, m, None) if m is not None else None 
                      for m in hmap.z] for hmap in heatmaps]
            }, {
                "showscale": [True if i == 0 else False for i in range(len(heatmaps))],
                "colorbar.visible": True  # Force colorbar visibility in layout
            }],
            label=f"{val/20:.2f}"
        ) for val in range(0, 21)]
    else:
        slider_steps = [dict(
            method="update",
            args=[{
                "zmin": val/20
            }, {
                "showscale": [True if i == 0 else False for i in range(len(heatmaps))],
                "colorbar.visible": True  # Force colorbar visibility in layout
            }],
            label=f"{val/20:.2f}"
        ) for val in range(0, 21)]
    
    # Add slider with adjusted position
    fig.update_layout(
        sliders=[dict(
            active=0,
            currentvalue=dict(
                prefix="Threshold: ",
                font=dict(size=14),
                xanchor="right"
            ),
            pad=dict(t=50),
            len=0.3,
            x=1.05, # Slider horizontal position
            y=0.6,  # Slider vertical position
            steps=slider_steps
        )],
        margin=dict(r=150),
        height=300 * n_rows + 50,
        title_text="Question Similarities by Section",
        showlegend=False,
        width=400 * n_cols,
        grid=dict(columns=n_cols, rows=n_rows, pattern='independent')  # Ensure independent subplots
    )
    
    # Add callback to update heatmaps based on slider
    fig.update_traces(
        customdata=[0],  # Initial threshold
        selector=dict(type='heatmap')
    )
    
    # Save as HTML file for interactivity
    html_file = vectors_file_path.replace("_q-vectors.npz", "_q-similarities.html")
    fig.write_html(html_file)
    
    # Also save static PNG version
    png_file = vectors_file_path.replace("_q-vectors.npz", "_q-similarities.png")
    fig.write_image(png_file)
    
    # Show the plot in browser or notebook
    fig.show()
    
    return html_file, png_file
def mrun_visualize_question_similarities():
    pass
#if __name__ == "__main__":
    #qa_file_path = "data/floodlamp/reg/fda-townhalls/f5_fixnames/2020-12-09_Virtual Town Hall 36_qa-qonly.md"
    qa_file_path = sub_suffix_in_str(CUR_SOURCE_FILE_PATH, '_qa-qonly')
    vectors_file_path = qa_file_path.replace(".md", "_q-vectors.npz")
    html_viz_file, png_viz_file = visualize_question_similarities(vectors_file_path, min_similarity=0.7)
    print(f"\n\nVisualization HTML saved to: {html_viz_file}")
    print(f"Visualization PNG saved to: {png_viz_file}")

### ************************** START OF REFACTORED CODE **************************
### QA BY SECTIONS - Q ONLY
def create_extract_log_header(fcall_prompt, provider, model, round_num, round_name):
    """
    Create the extract log header information for a specific round.

    :param fcall_prompt: string prompt for function calling
    :param provider: string indicating which provider to use
    :param model: string indicating which model is being used
    :param round_num: integer indicating which round this is
    :param round_name: string name of the extraction round
    :return: list of log lines
    """
    datetime = get_current_datetime_humanfriendly()
    
    log_lines = []
    
    # Only add header lines for round 1
    if round_num == 1:
        log_lines.append("### extract log")
        log_lines.append("#### extract log header")
        log_lines.append(f"datetime: {datetime}")
        #log_lines.append("source file prep: primary.llm.add_transcript_section_delimiters for non-FDA speakers")
        log_lines.append(f"source file prep: sections before all sub chapters md level 3")
    
    log_lines.append(f"ROUND {round_num} NAME: {round_name}")
    prompt_name = next((var_name for var_name, var_value in globals().items() 
                       if var_value is fcall_prompt), "UNKNOWN_PROMPT")
    log_lines.append(f"- prompt: {prompt_name}")
    log_lines.append(f"- tools: tools_qa_qonly_explicit_1")
    log_lines.append(f"- provider: {provider}")
    log_lines.append(f"- model: {model}")
    log_lines.append("")
    
    return log_lines
def get_file_metadata_and_sections(file_path, heading='### transcript', delimiter='---', auto_detect_section_titles=True):
    """
    Read metadata and content from a file, splitting sections by delimiter or next-level headings.

    :param file_path: string, path to the file to read
    :param heading: string, heading to extract content from, or None to use full content
    :param delimiter: string, delimiter used to split content into sections, or None to skip delimiter check
    :param auto_detect_section_titles: bool, if True and no delimiters found, split by next heading level
    :return metadata: dict, metadata from the file
    :return sections: list, sections split by delimiter or headings
    :return total_sections: int, number of sections found
    """
    metadata, full_content = read_metadata_and_content(file_path)

    # if heading is present, extract that portion
    # otherwise, you can skip or use the entire file
    if heading:
        text = get_heading(file_path, heading, strip_heading_line=True)
    else:
        # fallback if user set heading=None
        text = full_content

    # First try splitting by delimiter if it's provided and exists in text
    if delimiter and delimiter in text:
        sections = text.split(delimiter)
    # If no delimiter found or delimiter is None, try auto-detecting sections by headings
    elif auto_detect_section_titles and heading:
        # Get the heading level of the main heading
        heading_level = get_heading_level(heading)
        # Look for headings one level deeper
        next_level_pattern = r'^#{' + str(heading_level + 1) + r'}\s.*$'
        
        # Split the text at these headings
        sections = []
        current_section = []
        
        for line in text.splitlines():
            if re.match(next_level_pattern, line):
                if current_section:
                    sections.append('\n'.join(current_section))
                current_section = [line]
            else:
                current_section.append(line)
                
        if current_section:
            sections.append('\n'.join(current_section))
    else:
        # If no splitting method works, treat the entire text as one section
        sections = [text]

    total_sections = len(sections)
    return metadata, sections, total_sections
def mtest_get_file_metadata_and_sections():
    pass
#if __name__ == "__main__":
    cur_source_file_path = "data/misc_books/Sovereign Child/The Sovereign Child_sections.md"
    metadata, sections, total_sections = get_file_metadata_and_sections(cur_source_file_path, heading='CONTENT', delimiter='---', auto_detect_section_titles=True)
    print(f"Total Sections: {total_sections} for file: {cur_source_file_path}")
    cur_source_file_path = "data/misc_books/Sovereign Child/2025-01-17_Tim Ferriss Show - Naval and Aaron Stupple on Sovereign Child_section-titles.md"
    metadata, sections, total_sections = get_file_metadata_and_sections(cur_source_file_path, heading='### transcript', delimiter='---', auto_detect_section_titles=True)
    print(f"Total Sections: {total_sections} for file: {cur_source_file_path}")
def log_section_items(log_lines, section_num, items, round_name, prefix):
    """
    Add items to the log under the appropriate section heading,
    ensuring that all sections from 1..section_num include the round heading
    (even if no items are provided for earlier sections).
    
    :param log_lines: list of existing log lines
    :param section_num: current section number
    :param items: list of items (questions) to add
    :param round_name: name of the current round (e.g. "Explicit Questions Extraction")
    :param prefix: prefix for item numbering (e.g., "QE" or "QI")
    :return: updated log lines
    """
    def is_blank(line):
        return not line.strip()

    for sn in range(1, section_num + 1):
        # 1) Find the "#### Section sn of"
        section_pattern = f"#### Section {sn} of"
        try:
            sect_start = next(i for i, line in enumerate(log_lines) if section_pattern in line)
        except StopIteration:
            raise ValueError(f"Could not find section {sn} in log lines.")

        # 2) Find the next section heading or end
        try:
            sect_end = next(i for i, line in enumerate(log_lines[sect_start + 1:], sect_start + 1)
                            if line.startswith("#### Section"))
        except StopIteration:
            sect_end = len(log_lines)

        # Extract lines for this section
        original_section_lines = log_lines[sect_start:sect_end]

        # Split out the first line (the main "#### Section X of Y" heading) 
        # vs. the rest (the body).
        new_section_lines = [original_section_lines[0]]
        existing_body = original_section_lines[1:]

        # --  A) Remove all-blank lines if the section body is totally empty  --
        if all(is_blank(x) for x in existing_body):
            existing_body = []

        # Check if our round heading already exists
        heading_found = any(line.strip() == f"##### {round_name}"
                            for line in existing_body)

        # --  B) Keep existing body lines exactly as they are  --
        new_section_lines.extend(existing_body)

        # --  C) If heading missing, add it to the bottom of this section  --
        if not heading_found:
            # If there's *some* content, and the last line is non-blank,
            # we insert a blank line before our heading.
            if existing_body and not is_blank(new_section_lines[-1]):
                new_section_lines.append("")
            new_section_lines.append(f"##### {round_name}")

        # --  D) If this is the final requested section (sn == section_num) and we have items, append them --
        if sn == section_num and items:
            # If the last line is not blank and not the heading, add a blank line
            if not is_blank(new_section_lines[-1]) and not new_section_lines[-1].startswith("#####"):
                new_section_lines.append("")
            for i, question in enumerate(items, 1):
                new_section_lines.append(f"{prefix} {sn}-{i}: {question}")

        # --  E) Ensure exactly one blank line if there's another section after it --
        if sect_end < len(log_lines):
            if not is_blank(new_section_lines[-1]):
                new_section_lines.append("")

        # Replace in the master log
        log_lines[sect_start:sect_end] = new_section_lines

    return log_lines
def mtest_log_section_items():
    pass
#if __name__ == "__main__":
    # Test Case 1: Starting from blank -> Adding Explicit Questions
    initial_log_text_1 = """### extract log
#### extract log header
datetime: 2024

#### Section 1 of 2

#### Section 2 of 2"""

    expected_output_1 = """### extract log
#### extract log header
datetime: 2024

#### Section 1 of 2
##### Explicit Questions Extraction

#### Section 2 of 2
##### Explicit Questions Extraction
QE 2-1: What is the process for LAMP testing validation?"""

    # Test Case 2: Starting with Explicit -> Adding Implicit Questions
    initial_log_text_2 = expected_output_1

    expected_output_2 = """### extract log
#### extract log header
datetime: 2024

#### Section 1 of 2
##### Explicit Questions Extraction

##### Implicit Questions Extraction
QI 1-1: What are the FDA's requirements for pooling tests?

#### Section 2 of 2
##### Explicit Questions Extraction
QE 2-1: What is the process for LAMP testing validation?

##### Implicit Questions Extraction
QI 2-1: What validation is needed for test modifications?"""

    # Test Case 1: Adding Explicit Questions
    log_lines_1 = initial_log_text_1.split('\n')
    result_1 = log_section_items(log_lines_1, 1, 
                              [],
                              "Explicit Questions Extraction", "QE")
    result_1 = log_section_items(result_1, 2, 
                              ["What is the process for LAMP testing validation?"],
                              "Explicit Questions Extraction", "QE")
    
    # Test Case 2: Adding Implicit Questions
    log_lines_2 = initial_log_text_2.split('\n')
    result_2 = log_section_items(log_lines_2, 1,
                              ["What are the FDA's requirements for pooling tests?"],
                              "Implicit Questions Extraction", "QI")
    result_2 = log_section_items(result_2, 2,
                              ["What validation is needed for test modifications?"],
                              "Implicit Questions Extraction", "QI")

    # Compare results for test case 1
    test1_result = '\n'.join(result_1)
    test1_passed = test1_result == expected_output_1
    if test1_passed:
        print("\n\n\n********** Test Case 1 - Adding Explicit Questions: PASS")
    else:
        print("\n\n\n********** Test Case 1 - Adding Explicit Questions: FAIL")
        print("\n=========== Initial:")
        print(initial_log_text_1)
        print("\n=========== Result:")
        print(test1_result)
        print("\n=========== Expected:")
        print(expected_output_1)

    # Compare results for test case 2  
    test2_result = '\n'.join(result_2)
    test2_passed = test2_result == expected_output_2
    if test2_passed:
        print("\n\n\n********** Test Case 2 - Adding Implicit Questions: PASS")
    else:
        print("\n\n\n********** Test Case 2 - Adding Implicit Questions: FAIL")
        print("\n=========== Initial:")
        print(initial_log_text_2) 
        print("\n=========== Result:")
        print(test2_result)
        print("\n=========== Expected:")
        print(expected_output_2)
        
    print(f"\ntestcase1-{'pass' if test1_passed else 'fail'}")
    print(f"testcase2-{'pass' if test2_passed else 'fail'}")
def mrun_log_section_items():
    pass
#if __name__ == "__main__":
    cur_qa_file_path = "data/floodlamp/reg/fda-townhalls/dev-qa-extract/VTH 36 just2_qa-qonly-REF QE.md"
    log_text = get_heading(cur_qa_file_path, "### extract log")
    log_lines = log_text.split('\n')
    print("log_lines before:")
    print("\n".join(log_lines))
    print("\n\nlog_lines after:")
    new_log_lines = log_section_items(log_lines, 2, ["First fake implicit question?", "Second implicit question?"], "Implicit Questions Extraction", prefix="QI")
    print("\n".join(new_log_lines))

FCALL_SYSTEM_PROMPT_QA_QONLY_EXPLICIT_FDA_1D = """
You are an expert text analyzer trained to extract explicitly asked questions from FDA Town Hall transcripts on COVID-19 diagnostics. 

Your Task (Round 1 - Explicit Questions Only):
1. Identify every explicitly stated question. 
   - A question is explicit if it appears with a question mark or contains phrases indicating a direct inquiry 
     (e.g., 'I'd like to ask...', 'Could you clarify...', 'My question is...').

2. For each explicit question, create a concise, edited version ('clarified question'):
   - Remove speaker names and extraneous filler phrases.
   - **If one speaker's turn contains multiple sub-questions (even within one sentence), split them into separate clarified questions.** 
     - This applies even if they revolve around a similar topic or share partial overlap.

3. Apply these guidelines to each question:
   - **Distinct Content**: Avoid including duplicates or near-duplicates. 
   - **Relevance**: Focus on technical, procedural, or legal aspects related to COVID-19 test development, validation, labeling, etc.
   - **No Speaker Names**: Do not include speaker identifiers (e.g. 'Dr. Smith', 'Audience Member').
   - **Coverage**: If a transcript chunk has multiple explicit questions, include them all as separate entries in the list.
   - **Redundancy Prevention**: If the same question appears in slightly different wording within the same chunk, consolidate into one clarified question (unless there is a clear difference in content or context).
   - **Standalone Clarity**: If the original text uses pronouns or ambiguous references (e.g., 'If it's just an empty tube...'), rewrite the clarified question so that it explicitly names the subject (e.g., 'If a saliva collection tube is just an empty tube...') rather than relying on prior context or pronouns.

4. Return the clarified questions as a JSON array of strings. Each entry in the array corresponds to one distinct clarified explicit question.

5. If no explicit questions are found, return an empty array (i.e., []).

Remember:
- No implied questions in this round (explicit only).
- If a speaker lumps multiple sub-questions into one statement, **always** separate them into distinct questions when feasible.
- Do not include any speaker labels or personal identifiers in the clarified questions.
- Ensure each question is clearly standalone in wording.
"""
def tools_qa_qonly_explicit():
    return [{
        "type": "function",
        "function": {
            "name": "extract_explicit_questions",
            "description": "Extract and clarify all explicitly asked questions from the text, breaking multi-part questions into separate entries",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "questions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of clarified, explicitly asked questions. Each should be concise and clear, without speaker names."
                    }
                },
                "required": ["questions"],
                "additionalProperties": False
            }
        }
    }]
def deepseek_qa_output_schema():
    return {
        "questions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of clarified questions. Each should be concise and clear, without speaker names."
        }
    }
def fcall_qa_qonly_explicit(section_text, fcall_prompt, provider="openai", debug=False):
    """
    Process a single section of text to extract explicit questions.
    
    :param section_text: string containing a section of the text to process
    :param fcall_prompt: string containing the prompt for function calling
    :param provider: string indicating which provider to use ("openai" or "anthropic")
    :param debug: boolean to enable debug printing
    :return: list of clarified explicit questions found in the section, or None if error
    """
    max_retries = 2  # Maximum attempts to get questions from a section
    
    # Add debug print for initial inputs
    verbose_print(debug, f"\nProcessing section of length: {len(section_text)} chars")
    
    # Get appropriate tools format for the provider
    tools = tools_qa_qonly_explicit()
    if provider == "anthropic":
        tools = convert_tools_to_anthropic_format(tools)
    
    while max_retries > 0:
        try:
            verbose_print(debug, f"Attempting function call with {provider}")
            # Make the appropriate function call based on provider
            if provider == "openai":
                response = openai_function_call(fcall_prompt, section_text, tools)
            elif provider == "anthropic":
                response = anthropic_function_call(fcall_prompt, section_text, tools)
            elif provider == "deepseek":
                response = deepseek_structured_output(fcall_prompt, section_text, 
                                        deepseek_qa_output_schema())
                return response.get('questions', []) if response else None
            else:
                raise ValueError("Provider must be either 'openai' or 'anthropic'")
            
            verbose_print(debug, f"Got response: {response}")
            
            # Parse the response
            arguments = parse_function_call_response(response, provider)
            verbose_print(debug, f"Parsed arguments: {arguments}")
            
            if not arguments:
                raise Exception("Failed to parse function call response")
            
            questions = arguments.get('questions', [])
            verbose_print(debug, f"Extracted questions: {questions}")
                
            return questions  # Can be empty list if no questions found
            
        except Exception as e:
            print(colored(f"Error in question extraction: {str(e)}", "red"))
            verbose_print(debug, f"Full error details: {str(e)}")
            if max_retries > 1:
                max_retries -= 1
                print(colored(f"Error occurred. Retrying... ({max_retries} attempts remaining)", "red"))
                continue
            return None
    
    return None
def do_qonly_round_1_explicit(source_file_path, fcall_prompt, provider="openai", heading="### transcript", delimiter='---', suffix_new='_qa-qonly'):
    """
    Extract explicit questions from a text file by processing sections delimited by a separator.
    Creates a new file with extraction log but no QA blocks yet.

    :param ile_path: string path to the file
    :param fcall_prompt: string prompt for function calling
    :param provider: string indicating which provider to use ("openai" or "anthropic")
    :param delimiter: string used to separate sections
    :param suffix_new: string suffix for the new file name
    :return qa_file_path: string path to the created file
    """
    round_num = 1
    round_name = "Explicit Questions Extraction"
    start_time = time.time()

    # Set model based on provider
    if provider == "openai":
        model = OPENAI_MODEL
    elif provider == "anthropic":
        model = ANTHROPIC_MODEL
    else:
        raise ValueError("Provider must be either 'openai' or 'anthropic'")
    
    # Initialize log lines
    log_lines = create_extract_log_header(fcall_prompt, provider, model, round_num, round_name)
    print("\n".join(log_lines))  # Print header information

    # Get transcript sections and metadata
    metadata, sections, total_sections = get_file_metadata_and_sections(source_file_path, heading=heading, delimiter=delimiter)

    # Get current datetime string to update metadata for new qa file
    current_datetime = get_current_datetime_humanfriendly()
    date = current_datetime.split(' ')[0]
    metadata = set_metadata_field(metadata, "last updated", f"{date} Created QA Sections")
    metadata = set_metadata_field(metadata, "source file", source_file_path)

    # Create output file with initial content
    initial_content = "## content\n"  # Note: ### qa section will be added later
    qa_file_path = write_metadata_and_content(source_file_path, metadata, initial_content, overwrite='no-sub', suffix_new=suffix_new)

    # First pass: Create section heading lines
    for section_num, section in enumerate(sections, 1):
        section_header = f"#### Section {section_num} of {total_sections}"
        log_lines.append(section_header)
        log_lines.append("")

    log_text = "\n".join(log_lines)
    #print(f"DEBUG ===***===*** log_text after first pass: {log_text}")  
     
    # Second pass: Process each section
    for section_num, section in enumerate(sections, 1):
        section = section.strip()
        if not section:
            raise ValueError(f"Empty section found at position {section_num}. All sections should exist in qa file extract log section.")
        try:
            print(f"\n\nProcessing Round {round_num} {round_name} - section {section_num} of {total_sections}")
            # Process this section (keeping fcall in main loop)
            questions = fcall_qa_qonly_explicit(section, fcall_prompt, provider=provider)
            
            # Get formatted log lines and append them
            log_lines = log_section_items(log_lines, section_num, questions, round_name, prefix="QE")
                    
        except Exception as e:
            error_msg = f"\n********** Error encountered in section {section_num}: {str(e)}"
            print(colored(error_msg, "red"))
            log_lines.append(error_msg)
            continue

    # Append extract log to the file
    with open(qa_file_path, 'a') as f:
        f.write("\n\n" + "\n".join(log_lines))

    print(f"\n{round_name} completed in {(time.time() - start_time) / 60:.1f} minutes.")
    print("Extract log written to " + qa_file_path)
    return qa_file_path
def mrun_do_qonly_round_1_explicit():
    pass
#if __name__ == "__main__":
    #cur_file_path = "data/floodlamp/reg/fda-townhalls/dev-qa-extract/VTH 36_cemanual-sections.md"
    cur_file_path = CUR_SOURCE_FILE_PATH
    #cur_file_path = "data/floodlamp/reg/fda-townhalls/dev-qa-extract/VTH 36 just2_trans.md"
    qa_file_path = do_qonly_round_1_explicit(cur_file_path, FCALL_SYSTEM_PROMPT_QA_QONLY_EXPLICIT_1D)
    print(f"QA file created at: {qa_file_path}")   
FCALL_SYSTEM_PROMPT_QA_QONLY_IMPLICIT_FDA_1A = """
You are an expert text analyzer trained to identify implied (unspoken) questions from FDA Town Hall transcripts on COVID-19 diagnostics. 

Context:
- The target audience is COVID-19 diagnostic test developers.
- Below is a list of explicit questions previously identified. You must NOT repeat or rephrase these explicit questions.
- Extract only additional questions that are implied or indirectly addressed by the FDA or other speakers, focusing on:
  - Regulatory updates or technical details that are not framed as explicit questions but could be questions from the perspective of a COVID-19 test developer.
  - Clarifications the FDA provides that respond to an unasked question.
  - Any statements that convey new requirements, guidelines, or instructions, which a developer might ask about even if it wasn't explicitly asked.

Requirements:
1. **No Duplicates**: Exclude any question that matches or closely overlaps with a previously extracted explicit question.
2. **Standalone Clarity**: If the original text uses ambiguous references or pronouns, rewrite them so each implied question is clear on its own (e.g., 'What are the validation requirements for saliva collection tubes?' instead of 'What about these tubes?').
3. **Multiple Sub-Questions**: If a speaker covers multiple implied questions in one statement, split them into separate clarified questions.
4. **Relevance**: Focus on regulatory, technical, or procedural aspects of COVID-19 diagnostics. Skip trivial or off-topic points.
5. **Concise Format**: Return the implied questions as a JSON array under the key 'implicit_questions'. Each entry in the array is one distinct question in plain text (no speaker names).

Input to the Model:
- A transcript section
- A list of previously extracted explicit questions (explicit_questions_list)

Output Format:
- A valid JSON object with a single key "implicit_questions" mapping to a list of strings.
- Example:
{
  "implicit_questions": [
    "How does the FDA recommend interpreting borderline positive results?",
    "Are there special controls for home-based collection devices?"
  ]
}

If no implied questions exist, return an empty array: "implicit_questions": []

Remember:
- Do NOT restate or slightly rephrase any explicit questions already extracted.
- Ensure each implied question is relevant, standalone, and helpful for COVID-19 test developers.
- Keep it concise and avoid speaker labels or personal identifiers.
"""
def tools_qa_qonly_implicit():
    """
    This function schema returns a JSON object with a single key: 'implicit_questions',
    which is a list of newly identified implied questions (strings).
    """
    return [{
        "type": "function",
        "function": {
            "name": "extract_implicit_questions",
            "description": (
                "Extract and clarify any implied questions from the transcript, excluding any questions that match or "
                "overlap with a given list of explicit questions."
            ),
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "implicit_questions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "A list of distinct implied questions relevant to FDA regulations, diagnostics, disease testing, COVID-19, the pandemic, the public health response, and any other important or relevant topics."
                            "No duplicates of previously identified explicit questions."
                        )
                    }
                },
                "required": ["implicit_questions"],
                "additionalProperties": False
            }
        }
    }]
def fcall_qa_qonly_implicit(section_text, fcall_prompt, prev_questions, provider="openai", debug=False, abort_on_error=True):
    """
    Process a single section of text to extract implicit questions.
    
    :param section_text: string containing a section of text to process
    :param fcall_prompt: string containing the prompt for function calling
    :param prev_questions: list of previously extracted explicit questions
    :param provider: string indicating which provider to use ("openai" or "anthropic")
    :param debug: boolean to enable debug printing
    :param abort_on_error: boolean to control whether to raise exceptions on error
    :return: list of clarified implicit questions found in the section, or None if error
    """
    max_retries = 2  # Maximum attempts to get questions from a section
    
    # Add debug print for initial inputs
    verbose_print(debug, f"\nProcessing section with {len(prev_questions)} previous questions")
    
    # Get appropriate tools format for the provider
    tools = tools_qa_qonly_implicit()
    if provider == "anthropic":
        tools = convert_tools_to_anthropic_format(tools)
    verbose_print(debug, f"Using provider: {provider}")
    
    # Create context with previous questions list
    prev_questions_context = "Previously extracted explicit questions - **DO NOT extract similar or overlapping questions**:\n"
    for i, q in enumerate(prev_questions, 1):
        prev_questions_context += f"{i}. {q}\n"
    verbose_print(debug, f"Previous questions context:\n{prev_questions_context}")
    
    # Create full prompt with context
    full_prompt = (
        f"{fcall_prompt}\n\n"
        f"{prev_questions_context}\n\n"
        f"Please identify any implied questions in the following transcript section:\n\n"
        f"{section_text}"
    )
    verbose_print(debug, f"Full prompt:\n{full_prompt}")
    
    while max_retries > 0:
        try:
            verbose_print(debug, f"Attempting function call with {provider}")
            # Make the appropriate function call based on provider
            if provider == "openai":
                response = openai_function_call(full_prompt, section_text, tools)
            elif provider == "anthropic":
                response = anthropic_function_call(full_prompt, section_text, tools)
            else:
                raise ValueError("Provider must be either 'openai' or 'anthropic'")
            
            verbose_print(debug, f"Got response: {response}")
            
            # Parse the response
            arguments = parse_function_call_response(response, provider)
            verbose_print(debug, f"Parsed arguments: {arguments}")
            
            if not arguments:
                if abort_on_error:
                    raise Exception("Failed to parse function call response")
                return None
            
            questions = arguments.get('implicit_questions', [])
            verbose_print(debug, f"Extracted questions: {questions}")
            
            # No need to retry if we got a valid response (even if empty questions list)
            return questions
            
        except Exception as e:
            error_msg = str(e)
            if error_msg:  # Only print error if there's an actual message
                print(colored(f"Error in implicit question extraction: {error_msg}", "red"))
                verbose_print(debug, f"Full error details: {error_msg}")
                if abort_on_error:
                    raise  # Re-raise the exception to abort processing
            if max_retries > 1:
                max_retries -= 1
                print(colored(f"Error occurred. Retrying... ({max_retries} attempts remaining)", "red"))
                continue
            return None
    
    return None
def do_qonly_round_2_implicit(source_file_path, fcall_prompt, provider="openai", heading="### transcript", delimiter='---', suffix_new='_qa-qonly'):
    """
    Extract implicit questions from a source file by processing sections delimited by a separator.
    Modifies an existing QA file by appending implicit questions to the extract log.

    :param source_file_path: string, path to the source file
    :param fcall_prompt: string, prompt for function calling
    :param provider: string, indicating which provider to use ("openai" or "anthropic")
    :param delimiter: string, used to separate sections
    :param suffix_new: string, suffix for the existing QA file
    :return qa_file_path: string, path to the modified file
    """
    round_num = 2
    round_name = "Implicit Questions Extraction"
    start_time = time.time()

    # Verify QA file exists
    qa_file_path = sub_suffix_in_str(source_file_path, suffix_new)
    if not os.path.exists(qa_file_path):
        raise ValueError(f"QA file not found: {qa_file_path}")

    # Get existing explicit questions
    prev_questions_all = get_questions_from_qa_file(qa_file_path, heading="##### Explicit Questions Extraction")

    # Set model based on provider
    if provider == "openai":
        model = OPENAI_MODEL
    elif provider == "anthropic":
        model = ANTHROPIC_MODEL
    else:
        raise ValueError("Provider must be either 'openai' or 'anthropic'")
    
    # Get the existing extract log for log_lines
    log_text = get_heading(qa_file_path, "### extract log")
    log_lines = log_text.split('\n')
    #print("\n".join(log_lines))  # Print header information

    # Get transcript sections and metadata
    _, sections, total_sections = get_file_metadata_and_sections(source_file_path, heading=heading, delimiter=delimiter)

    # Process each section
    for section_num, section in enumerate(sections, 1):
        section = section.strip()
        if not section:
            raise ValueError(f"Empty section found at position {section_num}. All sections should exist in qa file extract log section.")
        try:
            print(f"\n\nProcessing Round {round_num} {round_name} - section {section_num} of {total_sections}")
            # Process this section with implicit question extraction
            prev_questions_section = [q[1] for q in prev_questions_all if q[0] == section_num]  # Filter questions for this section
            #print(f"prev_questions_section: {prev_questions_section}")
            questions = fcall_qa_qonly_implicit(section, fcall_prompt, prev_questions_section, provider=provider)
            
            # Get formatted log lines and append them
            log_lines = log_section_items(log_lines, section_num, questions, round_name, prefix="QI")
                    
        except Exception as e:
            error_msg = str(e)
            if error_msg:  # Only log actual errors
                error_msg = f"\n********** Error encountered in section {section_num}: {error_msg}"
                print(colored(error_msg, "red"))
                log_lines.append(error_msg)
            raise  # Re-raise to abort processing

    updated_extract_log = f"\n".join(log_lines)
    
    set_heading(qa_file_path, updated_extract_log, "### extract log")
    print(f"\n{round_name} completed in {(time.time() - start_time) / 60:.1f} minutes.")
    print("Extract log updated in " + qa_file_path)
    return qa_file_path
def mrun_do_qonly_round_2_implicit():
    pass
#if __name__ == "__main__":
    #cur_source_file_path = "data/floodlamp/reg/fda-townhalls/dev-qa-extract/VTH 36_cemanual-sections.md"
    cur_source_file_path = CUR_SOURCE_FILE_PATH
    #cur_source_file_path = "data/floodlamp/reg/fda-townhalls/dev-qa-extract/VTH 36 just2_trans.md"

    # ONLY USE THIS AFTER copying the _qa-qonly file as a different name
    # qa_file_path = CUR_FILE_PATH
    # qa_file_path = sub_suffix_in_str(qa_file_path, '_qa-qonly')
    # delete_all_heading_instances(qa_file_path, "##### Implicit Questions Extraction")

    qa_file_path = do_qonly_round_2_implicit(cur_source_file_path, FCALL_SYSTEM_PROMPT_QA_QONLY_IMPLICIT_1A)
    print(f"Implicit Round 2 - QA file updated: {qa_file_path}")
    get_questions_from_extract_log(qa_file_path, verbose=True)
def single_section_qonly_round_2_implicit(source_file_path, fcall_prompt, section_num, provider="openai", heading="### transcript", delimiter='---', suffix_new='_qa-qonly'):
    # Verify QA file exists
    qa_file_path = sub_suffix_in_str(source_file_path, suffix_new)
    if not os.path.exists(qa_file_path):
        raise ValueError(f"QA file not found: {qa_file_path}")

    # Get existing explicit questions
    prev_questions_all = get_questions_from_qa_file(qa_file_path, heading="##### Explicit Questions Extraction")

    # Set model based on provider
    if provider == "openai":
        model = OPENAI_MODEL
    elif provider == "anthropic":
        model = ANTHROPIC_MODEL
    else:
        raise ValueError("Provider must be either 'openai' or 'anthropic'")

    # Get transcript sections and metadata
    _, sections, total_sections = get_file_metadata_and_sections(source_file_path, heading='### transcript', delimiter=delimiter)

    # Process only the requested section
    section = sections[section_num - 1].strip()
    if not section:
        raise ValueError(f"Empty section found at position {section_num}. All sections should exist in qa file extract log section.")
    try:
        print(f"\n\nProcessing section {section_num} of {total_sections}")
        # Process this section with implicit question extraction
        prev_questions_section = [q[1] for q in prev_questions_all if q[0] == section_num]  # Filter questions for this section
        print(f"prev_questions_section: {prev_questions_section}")
        questions = fcall_qa_qonly_implicit(section, fcall_prompt, prev_questions_section, provider=provider)    
                
    except Exception as e:
        error_msg = str(e)
        if error_msg:  # Only log actual errors
            error_msg = f"\n********** Error encountered in section {section_num}: {error_msg}"
            print(colored(error_msg, "red"))
        raise  # Re-raise to abort processing

    prefix="QI"
    # Prepend prefix and section number to each question
    questions = [f"{prefix} {section_num}-{i+1}: {q}" for i, q in enumerate(questions)]
    return questions
def mrun_single_section_qonly_round_2_implicit():
    pass
#if __name__ == "__main__":
    cur_file_path = CUR_SOURCE_FILE_PATH
    section_num = 1
    questions = single_section_qonly_round_2_implicit(cur_file_path, FCALL_SYSTEM_PROMPT_QA_QONLY_IMPLICIT_1A, section_num)
    print("Implicit Questions:")
    for question in questions:
        print(question)
FCALL_SYSTEM_PROMPT_QA_QONLY_BLOCKS_FDA_1A = """
You are an expert text analyzer trained in extracting full Q&A blocks for FDA Town Hall transcripts on COVID-19 diagnostics.

Your Role:
- A single, *already clarified* question will be provided to you as input along with an section of transcript text.
- Your task is to generate exactly one Q&A block following the schema:

1. 'verbatim_question': 
   - Using the provided question, find the exact text from the transcript section that corresponds to it.
   - If the question is implied, set this to 'IMPLICIT' because the verbatim_answer field will contain the relevant text from the trancript.
2. 'verbatim_answer': 
   - Provide the exact text of the answer from the transcript excerpt (minus speaker labels/newlines).
   - Find the best answer possible from the transcript excerpt.
   - This verbatim_answer field must be found and extracted from the transcript section text.
3. 'clarified_answer': 
   - Provide a concise, edited restatement of the answer. Use 'FDA' where appropriate; do not include personal names.
4. 'speaker_question': 
   - Name/role exactly as it appears in the transcript (preceding a colon or timestamp). 
   - If the question is implied from an authority speaker, set 'NOT APPLICABLE'.
5. 'speaker_answer': 
   - Name/role exactly as it appears in the transcript for the speaker who provides the answer. 
   - If the question is implicit, use the speaker’s name who implied it.
6. 'topics': 
   - List 1–3 brief topics addressed; if none, return an empty list [].
7. 'review_flag': 
   - True if uncertain or incomplete; else False.

Return only a single JSON object, nothing else.
"""
def tools_qa_qonly_blocks():
    """
    This function schema returns a single QA block that addresses the final question from the transcript excerpt.
    The 'clarified_question' field is removed, because the question is already provided and does not need clarification.
    """
    return [{
        "type": "function",
        "function": {
            "name": "extract_final_qa_block",
            "description": (
                "Given a final question (verbatim) and an excerpt of transcript text, extract the best possible answer."
                " Return only ONE QA block containing the relevant data fields. If no answer is found, set verbatim_answer "
                "to 'NO RELEVANT ANSWER IN TRANSCRIPT' and clarified_answer to an empty string or minimal note."
            ),
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "verbatim_question": {
                        "type": "string",
                        "description": (
                            "The exact text from the transcript section text that corresponds to the provided question, minus speaker labels/newlines. The entire text should be on a single line. Do not start the text with the speaker name from the preceding speaker line. If the question is implicit, use the string 'IMPLICIT'."
                        )
                    },
                    "verbatim_answer": {
                        "type": "string",
                        "description": (
                            "The exact text of the answer as it appears in the transcript section text, minus speaker labels/newlines. Do not start the text with the speaker name from the preceding speaker line."
                        )
                    },
                    "clarified_answer": {
                        "type": "string",
                        "description": (
                            "A concise, edited version of the answer. The entire text of this answer should be on a single line. Do not mention any specific speaker names, instead use 'FDA' where appropriate."
                        )
                    },
                    "speaker_question": {
                        "type": "string",
                        "description": (
                            "Name/role of question speaker. The name must be as identified in the transcript by the text in the speaker line that precedes a colon or timestamp. Do not use a different name spelling that may appear in the speaker dialogue. If the question is implied from an Authority Speaker's statement, use 'NOT APPLICABLE'."
                        )
                    },
                    "speaker_answer": {
                        "type": "string",
                        "description": (
                            "Name/role of answer speaker. The name must be as identified in the transcript by the text in the speaker line that precedes a colon or timestamp. Do not use a different name spelling that may appear in the speaker dialogue. If the question is implicit, use the speaker name of the statement that implied the question."
                        )
                    },
                    "topics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "A list of 1-3 key topics addressed in the question-answer block. If no new question is found, return an empty list []."
                        )
                    },
                    "review_flag": {
                        "type": "boolean",
                        "description": (
                            "Set True if significant uncertainty in the response. Otherwise False."
                        )
                    }
                },
                "required": [
                    "verbatim_question", "verbatim_answer", "clarified_answer",
                    "speaker_question", "speaker_answer", "topics", "review_flag"
                ],
                "additionalProperties": False
            }
        }
    }]
def fcall_qa_qonly_block(section_text, fcall_prompt, question, provider="openai", debug=False):
    """
    Process a single section of text to extract a QA block for a given question.
    
    :param section_text: string containing a section of text to process
    :param fcall_prompt: string containing the prompt for function calling
    :param question: string containing the already clarified question
    :param provider: string indicating which provider to use ("openai" or "anthropic")
    :param debug: boolean to enable debug printing
    :return: tuple of (qa_block, None) for successful extraction, or (None, error_msg) if error
    """
    max_retries = 1  # Maximum attempts to get a QA block
    
    # Get appropriate tools format for the provider
    tools = tools_qa_qonly_blocks()
    if provider == "anthropic":
        tools = convert_tools_to_anthropic_format(tools)
    
    # Create full prompt with question context
    full_prompt = (
        f"{fcall_prompt}\n\n"
        f"<PROVIDED QUESTION>\n{question}\n</PROVIDED QUESTION>\n\n"    
        f"<TRANSCRIPT SECTION>\n{section_text}\n</TRANSCRIPT SECTION>\n\n"
        f"Return only a single JSON object, nothing else."
    )
    verbose_print(debug, f"full_prompt: {full_prompt}")

    while max_retries > 0:
        try:
            # Make the appropriate function call based on provider
            if provider == "openai":
                qa_response = openai_function_call(full_prompt, section_text, tools)
            elif provider == "anthropic":
                qa_response = anthropic_function_call(full_prompt, section_text, tools)
            else:
                raise ValueError("Provider must be either 'openai' or 'anthropic'")
            
            # Parse the response using the common parser
            arguments = parse_function_call_response(qa_response, provider)
            
            if not arguments:
                raise Exception("Failed to parse function call response")
            
            # Create QA block
            qa_block = ""
            qa_block += f"CLARIFIED QUESTION: {question}\n"  # Use the provided question
            qa_block += f"CLARIFIED ANSWER: {arguments['clarified_answer']}\n"
            qa_block += f"VERBATIM QUESTION: {arguments['verbatim_question']}\n"
            qa_block += f"VERBATIM ANSWER: {arguments['verbatim_answer']}\n"
            qa_block += f"SPEAKER QUESTION: {arguments['speaker_question']}\n"
            qa_block += f"SPEAKER ANSWER: {arguments['speaker_answer']}\n"
            qa_block += f"TOPICS: {', '.join(arguments['topics'])}\n"
            qa_block += f"REVIEW FLAG: {arguments['review_flag']}\n"

            return qa_block, None
            
        except Exception as e:
            error_msg = str(e)
            if error_msg:  # Only print error if there's an actual message
                print(colored(f"Error in QA block extraction: {error_msg}", "red"))
            if max_retries > 1:
                max_retries -= 1
                print(colored(f"Error occurred. Retrying... ({max_retries} attempts remaining)", "red"))
                continue
            return None, error_msg
    
    return None, "K2 retries exceeded"
def get_last_qa_block_identifier(qa_file_path):
    """
    Get the section and question numbers from the last QA block in the file.

    :param qa_file_path: string path to the QA file
    :return: tuple of (section_num, question_num) or None if no QA blocks found
    """
    # Get QA section content
    qa_content = get_heading(qa_file_path, "### qa")
    if not qa_content:
        return None
        
    # Split into blocks and get the last non-empty block
    blocks = [block.strip() for block in qa_content.split('\n\n') if block.strip()]
    if not blocks:
        return None
        
    # Get the first line of the last block which should contain "QA Block X-Y"
    last_block_first_line = blocks[-1].split('\n')[0]
    
    # Parse the section and question numbers using regex
    match = re.match(r'QA Block (\d+)-(\d+)', last_block_first_line)
    if not match:
        return None
        
    # Convert to integers and return as tuple
    section_num = int(match.group(1))
    question_num = int(match.group(2))
    return (section_num, question_num)
def mtest_get_last_qa_block_identifier():
    pass
#if __name__ == "__main__":
    qa_file_path = "data/floodlamp/reg/fda-townhalls/f5_fixnames/run_auto/2021-12-15_Virtual Town Hall 75_qa-qonly.md"
    section_num, question_num = get_last_qa_block_identifier(qa_file_path)
    print(f"Last QA Block: Section {section_num}, Question {question_num}")
def do_qonly_round_3_blocks(file_path, fcall_prompt, provider="openai", heading="### transcript", delimiter='---', suffix_new='_qa-qonly'):
    """
    Extract QA blocks for previously identified questions from a textfile.
    Can resume processing from the last completed QA block in a partially processed file.
    
    :param file_path: string path to the text file
    :param fcall_prompt: string prompt for function calling
    :param provider: string indicating which provider to use ("openai" or "anthropic")
    :param delimiter: string used to separate transcript sections
    :param suffix_new: string suffix for the QA file
    :return qa_file_path: string path to the modified file
    """
    round_num = 3
    round_name = "QA Blocks Extraction"
    start_time = time.time()

    # Verify QA file exists
    qa_file_path = sub_suffix_in_str(file_path, suffix_new)
    if not os.path.exists(qa_file_path):
        raise ValueError(f"QA file not found: {qa_file_path}")

    # Get all questions (both explicit and implicit)
    questions_all = get_questions_from_extract_log(qa_file_path)

    # Set model based on provider
    if provider == "openai":
        model = OPENAI_MODEL
    elif provider == "anthropic":
        model = ANTHROPIC_MODEL
    else:
        raise ValueError("Provider must be either 'openai' or 'anthropic'")
    
    # Get transcript sections and metadata
    _, sections, total_sections = get_file_metadata_and_sections(file_path, heading=heading, delimiter=delimiter)

    # Get the last processed block (if any)
    last_block = get_last_qa_block_identifier(qa_file_path)
    if last_block:
        last_section, last_question = last_block
        print(f"Resuming from after section {last_section}, question {last_question}")
    else:
        last_section = last_question = 0
        # Add a new heading at the end of the file for the QA section
        with open(qa_file_path, 'r+') as f:
            content = f.read().rstrip()  # Remove trailing whitespace/newlines
            f.seek(0)
            f.write(content + "\n\n\n### qa\n\n")  # 3 newlines before, 2 after
            f.truncate()

    # Process each section
    for section_num, section in enumerate(sections, 1):
        section = section.strip()
        if not section:
            raise ValueError(f"Empty section found at position {section_num}")
            
        # Skip sections we've already processed
        if section_num < last_section:
            continue
            
        try:
            print(f"\n========== Round {round_num} {round_name} - Section {section_num} of {total_sections} ==========")
            
            # Get questions for this section
            section_questions = [q[1] for q in questions_all if q[0] == section_num]
            
            # Process each question in this section
            for i, question in enumerate(section_questions, 1):
                # Skip questions we've already processed in the last section
                if section_num == last_section and i <= last_question:
                    continue
                    
                print(f"  Processing question {i} of {len(section_questions)}")
                qa_block, error = fcall_qa_qonly_block(section, fcall_prompt, question, provider=provider)
                if qa_block:
                    # Add QA block identifier at the top
                    qa_block = f"QA Block {section_num}-{i}\n{qa_block}"
                    with open(qa_file_path, 'a') as f:
                        f.write(qa_block + "\n")
                elif error:
                    print(colored(f"Error processing question: {error}", "red"))
                    
        except Exception as e:
            error_msg = str(e)
            if error_msg:  # Only log actual errors
                error_msg = f"\n********** Error encountered in section {section_num}: {error_msg}"
                print(colored(error_msg, "red"))
            raise  # Re-raise to abort processing

    time_now = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
    print(f"\n{round_name} completed in {(time.time() - start_time) / 60:.1f} minutes at {time_now}.")
    print(f"{round_name} - QA blocks written to {qa_file_path}")
    return qa_file_path
def mrun_do_qonly_round_3_blocks():
    pass
#if __name__ == "__main__":
    #cur_source_file_path = "data/floodlamp/reg/fda-townhalls/f5_fixnames/2020-08-05_Virtual Town Hall 20_fixnames.md"
    cur_source_file_path = CUR_SOURCE_FILE_PATH
    qa_file_path = do_qonly_round_3_blocks(cur_source_file_path, FCALL_SYSTEM_PROMPT_QA_QONLY_BLOCKS_FDA_1A)
    
    print(f"Implicit Round 3 - QA file updated: {qa_file_path}")
def move_removed_qa_blocks(qa_file_path, block_ids_to_remove, new_section_name="### removed qa blocks"):
    """
    Moves specified QA blocks from the qa section to a new section.

    :param qa_file_path: string, path to the QA file.
    :param block_ids_to_remove: list, block identifiers to move (e.g., ['16-4', '16-5']).
    :param new_section_name: string, name of the section to move blocks to.
    :return: None
    """
    # Get all QA blocks text
    all_blocks_text = get_heading(qa_file_path, "### qa")
    if not all_blocks_text:
        return
    
    # Split into individual blocks (split on double newline)
    all_blocks = [block.strip() for block in all_blocks_text.split('\n\n') if block.strip()]
    
    # Separate blocks into removed and remaining
    removed_blocks = []
    remaining_blocks = []
    
    for block in all_blocks:
        # Check if block matches any of the block IDs to remove
        is_removed = False
        for block_id in block_ids_to_remove:
            if block.startswith(f"QA Block {block_id}"):
                removed_blocks.append(block)
                is_removed = True
                break
        
        if not is_removed:
            remaining_blocks.append(block)
    
    # Create text content for both sections
    removed_blocks_text = '\n\n'.join(removed_blocks) + '\n\n\n'
    remaining_blocks_text = '\n\n'.join(remaining_blocks) + '\n\n\n'
    
    # Update the file: delete qa section, add removed blocks, then add remaining blocks
    delete_heading(qa_file_path, "### qa")
    set_heading(qa_file_path, removed_blocks_text, new_section_name)
    set_heading(qa_file_path, remaining_blocks_text, "### qa")
def mrun_move_removed_qa_blocks():
    pass
#if __name__ == "__main__":
    qa_file_path = sub_suffix_in_str(CUR_SOURCE_FILE_PATH, '_qa-qonly')
    removed_questions = ['16-4', '16-5']
    move_removed_qa_blocks(qa_file_path, removed_questions)
def rerun_qa_block_fcall(source_file_path, fcall_prompt, first_2_qa_block_lines, provider="openai", heading="### transcript", delimiter='---', suffix_new='_qa-qonly'):
    # Verify QA file exists
    qa_file_path = sub_suffix_in_str(source_file_path, suffix_new)
    if not os.path.exists(qa_file_path):
        raise ValueError(f"QA file not found: {qa_file_path}")

    # Set model based on provider
    if provider == "openai":
        model = OPENAI_MODEL
    elif provider == "anthropic":
        model = ANTHROPIC_MODEL
    else:
        raise ValueError("Provider must be either 'openai' or 'anthropic'")
    
    # Parse section number and question from input lines
    lines = first_2_qa_block_lines.strip().split('\n')
    if len(lines) < 2:
        raise ValueError("Input must contain at least 2 lines")
    
    # Parse section number from "QA Block X-Y" format
    section_match = re.match(r'QA Block (\d+)-', lines[0])
    if not section_match:
        raise ValueError("First line must be in format 'QA Block X-Y'")
    section_num = int(section_match.group(1))
    
    # Parse question from "CLARIFIED QUESTION: X" format
    question_match = re.match(r'CLARIFIED QUESTION: (.*)', lines[1])
    if not question_match:
        raise ValueError("Second line must start with 'CLARIFIED QUESTION:'")
    question = question_match.group(1)

    # Get transcript sections
    _, sections, _ = get_file_metadata_and_sections(source_file_path, heading='### transcript', delimiter=delimiter)
    
    # Verify section number is valid
    if section_num < 1 or section_num > len(sections):
        raise ValueError(f"Invalid section number: {section_num}")
    
    # Get the specific section we want to process
    section = sections[section_num - 1].strip()
    if not section:
        raise ValueError(f"Empty section found at position {section_num}")

    # Process the single question
    print(f"\nProcessing section {section_num}, question: {question}")
    qa_block, error = fcall_qa_qonly_block(section, fcall_prompt, question, provider=provider)
    
    if qa_block:
        # Add QA block identifier at the top
        qa_block = f"QA Block {section_num}-1\n{qa_block}"
        print("\nGenerated QA Block:")
        print(qa_block)
        return qa_block
    elif error:
        print(colored(f"Error processing question: {error}", "red"))
        return None    
    else:
        print(colored("No QA block generated", "yellow"))
        return None
def mrun_rerun_qa_block_fcall():
    pass
#if __name__ == "__main__":
    source_file_path = CUR_SOURCE_FILE_PATH
    first_2_qa_block_lines = """
QA Block 4-1
CLARIFIED QUESTION: How high should the CT values be for low positives in retrospective studies of a rapid antigen test?"""
    rerun_qa_block_fcall(source_file_path, FCALL_SYSTEM_PROMPT_QA_QONLY_BLOCKS_FDA_1A, first_2_qa_block_lines)
# NOTE Can also manually search for 'ANSWER: NO'
def search_for_no_answers_in_qa_blocks(qa_file_path, verbose=False):
    """
    Search for patterns indicating missing or no answers in QA sections.

    :param qa_file_path: str, path to the QA file to analyze.
    :param verbose: bool, whether to print detailed match information.
    :return block_ids: list, block identifiers (e.g. ['28-3', '28-5']) for blocks with no answers.
    """
    from chalicelib.structured import get_blocks_from_file
    
    # Search patterns that indicate missing/no answers, ordered from most specific to most general
    NO_ANSWER_PATTERNS = [
        r"^VERBATIM ANSWER:\s*NO\s+(?:RELEVANT\s+)?ANSWER(?:\s+IN\s+TRANSCRIPT)?$",  # Matches exact "NO ANSWER" phrases
        r"^VERBATIM ANSWER:\s*[A-Z\s]+$"  # Matches VERBATIM ANSWER: followed by all caps text
    ]
    
    # Get QA section content
    qa_content = get_heading(qa_file_path, heading="### qa")
    if not qa_content:
        return []
    
    # Store matches with full blocks and block IDs
    matches = []
    block_ids = []
    
    # Split content into QA blocks
    qa_blocks = get_blocks_from_file(qa_file_path, heading="### qa")
    
    # Search through blocks
    for block in qa_blocks:
        block_lines = block.split('\n')
        block_matched = False
        
        # Extract block ID if block starts with "QA Block X-Y"
        qa_block_match = re.match(r"QA Block (\d+-\d+)", block_lines[0].strip())
        if not qa_block_match:
            continue
        block_id = qa_block_match.group(1)
        
        for pattern in NO_ANSWER_PATTERNS:
            if block_matched:
                break
            for line in block_lines:
                if re.search(pattern, line):
                    matches.append({
                        'pattern': pattern,
                        'line': line.strip(),
                        'block': block.strip(),
                        'block_id': block_id
                    })
                    block_ids.append(block_id)
                    block_matched = True
                    break
    
    # Print results if verbose
    if verbose:
        if not matches:
            print(colored("***** No 'NO ANSWER' matches found *****", "green"))
        else:
            print(colored("***** Found 'NO ANSWER' matches *****", "red"))
            for match in matches:
                print(f"Pattern: {match['pattern']}")
                print(colored(f"Matching line: {match['line']}", "yellow"))
                print(f"Block ID: {match['block_id']}")
                print(f"{match['block']}")
                print()  # Blank line between matches
            print(f"Total 'NO ANSWER' matches found: {len(matches)}")
            print(colored("*****************************************", "red"))
    
    return block_ids
def mrun_search_for_no_answers_in_qa_blocks():
    pass
#if __name__ == "__main__":
    qa_file_path = "data/misc_books/Sovereign Child/2025-01-17_Tim Ferriss Show - Naval and Aaron Stupple on Sovereign Child_qa-qonly.md"
    #qa_file_path = "data/misc_books/Sovereign Child/The Sovereign Child_qa-qonly.md"
    block_ids = search_for_no_answers_in_qa_blocks(qa_file_path)
    print(f"Number of blocks with no answers: {len(block_ids)}")
    print(f"block_ids: {block_ids}")
def mrun_search_and_move_no_answers():
    pass
#if __name__ == "__main__":
    qa_file_path = "data/misc_books/Sovereign Child/2025-01-17_Tim Ferriss Show - Naval and Aaron Stupple on Sovereign Child_qa-qonly.md"
    block_ids = search_for_no_answers_in_qa_blocks(qa_file_path)
    print(f"Number of blocks with no answers: {len(block_ids)}")
    print(f"block_ids: {block_ids}")
    move_removed_qa_blocks(qa_file_path, block_ids)
def auto_process_qa_qonly(source_file_path, heading):
    qa_file_path = sub_suffix_in_str(source_file_path, '_qa-qonly')  # can remove this
    
    # Check if QA file exists and has QA section
    qa_content = None
    if os.path.exists(qa_file_path):
        qa_content = get_heading(qa_file_path, "### qa")
        
    # Run all rounds if no QA file or no QA content
    if not os.path.exists(qa_file_path) or not qa_content:
        qa_file_path = do_qonly_round_1_explicit(source_file_path, FCALL_SYSTEM_PROMPT_QA_QONLY_EXPLICIT_FDA_1D, heading=heading)
        qa_file_path = do_qonly_round_2_implicit(source_file_path, FCALL_SYSTEM_PROMPT_QA_QONLY_IMPLICIT_FDA_1A, heading=heading)
        qa_file_path = do_qonly_round_3_blocks(source_file_path, FCALL_SYSTEM_PROMPT_QA_QONLY_BLOCKS_FDA_1A, heading=heading)
    else:
        # Skip first two rounds if QA section exists
        print("QA section found - skipping rounds 1 and 2") 
        qa_file_path = do_qonly_round_3_blocks(source_file_path, FCALL_SYSTEM_PROMPT_QA_QONLY_BLOCKS_FDA_1A, heading=heading)

    matches = search_for_no_answers_in_qa_blocks(qa_file_path)

    questions_extract_log = get_questions_from_extract_log(qa_file_path, verbose=True)
    print(f"Number of questions in extract log: {len(questions_extract_log)}")
    questions_qa_blocks = get_questions_from_qa_file(qa_file_path, heading="### qa")
    print(f"Number of questions in qa blocks: {len(questions_qa_blocks)}")
    compare_question_tuple_lists(questions_extract_log, questions_qa_blocks, "Extract log", "QA blocks")

    questions_qa_blocks = get_questions_from_qa_file(qa_file_path, heading="### qa")
    embeddings_file_path = generate_and_save_question_embeddings(qa_file_path, questions_qa_blocks)
    _, questions_to_remove, output_text = calc_question_list_similarities(embeddings_file_path)
    print(f"\n\n***** Questions to Remove ***** output_text:\n{output_text}")
    move_removed_qa_blocks(qa_file_path, questions_to_remove)
def mrun_auto_process_qa_qonly():
    pass
#if __name__ == "__main__":
    # cur_source_file_path = "data/floodlamp/reg/fda-townhalls/dev-qa-extract/test_transcript_just2/VTH 36 just2_trans.md"
    # cur_heading = "### transcript"
    cur_source_file_path = "data/misc_books/Sovereign Child/The Sovereign Child_sectionsJUST2.md"
    cur_heading = "CONTENT"
    auto_process_qa_qonly(cur_source_file_path, heading=cur_heading)
def mrun_auto_process_qa_qonly_folder():
    pass
#if __name__ == "__main__":
    cur_folder_path = "data/floodlamp/reg/fda-townhalls/f5_fixnames/run_auto"
    files_to_run = get_files_in_folder(cur_folder_path, suffixpat_include='_fixnames')
    total_start_time = time.time()
    
    for i, file_path in enumerate(files_to_run, 1):
        print(colored(f"\nAuto Processing file {i}/{len(files_to_run)}: {file_path}", "blue"))
        file_start_time = time.time()
        auto_process_qa_qonly(file_path)
        file_end_time = time.time()
        print(colored(f"Auto Process Time taken for file: {(file_end_time - file_start_time)/60:.1f} minutes", "blue"))
    
    total_end_time = time.time()
    print(f"\nAuto Processed {len(files_to_run)} files in {(total_end_time - total_start_time)/60:.1f} minutes")
def mrun_auto_check_qa_qonly_folder():
    pass
#if __name__ == "__main__":
    cur_folder_path = "data/floodlamp/reg/fda-townhalls/f5_fixnames/done_auto"
    qa_files_to_run = get_files_in_folder(cur_folder_path, suffixpat_include='_qa-qonly')
    
    for i, qa_file_path in enumerate(qa_files_to_run, 1):
        print(colored(f"\n{qa_file_path}", "blue"))
        search_for_no_answers_in_qa_blocks(qa_file_path)
### ************************** END OF REFACTORED CODE **************************


### QA QONLY REFACTOR
FCALL_SYSTEM_PROMPT_QA_QONLY_QUESTIONS_1A = """
You are an expert text analyzer trained in extracting and clarifying questions from any type of text content.

Your Role:
- Analyze the provided text to identify key questions that would help a reader understand the main points and concepts.
- Extract both explicit questions (directly stated) and implicit questions (derived from statements or concepts).
- Break down complex topics into clear, focused questions.
- Ensure questions are comprehensive but non-redundant.

Guidelines:
1. Create clear, concise questions that capture the essential information.
2. Break multi-part questions into separate, focused questions.
3. Avoid overly broad or vague questions.
4. Remove any speaker names or unnecessary context from questions.
5. Maintain the original meaning while making questions more direct and clear.
6. Include questions about key concepts, definitions, examples, and relationships.

Return only the structured output following the schema, nothing else.
"""
FCALL_SYSTEM_PROMPT_QA_QONLY_QUESTIONS_1B = """
You are an expert text analyzer trained in extracting and clarifying questions from any type of text content.

Your Role:
- Analyze the provided text to identify key questions that would help a reader understand the main points and concepts.
- Extract both explicit questions (directly stated) and implicit questions (derived from statements or concepts).
- Break down complex topics into clear, focused questions.
- Ensure questions are comprehensive but non-redundant.

Guidelines:
1. Treat the text as an authoritative source:
   - Phrase questions to address concepts directly (e.g., "Why is X considered incorrect?" not "Why does the author say X is incorrect?")
   - Only use "author" for personal experiences, encounters, or individual perspectives
   - Frame factual claims and arguments as standalone statements (e.g., "What historical examples illustrate Y?" not "What examples does the author use to show Y?")

2. Question Structure:
   - Create clear, concise questions that capture the essential information
   - Break multi-part questions into separate, focused questions
   - Avoid overly broad or vague questions
   - Remove unnecessary context from questions
   - Maintain the original meaning while making questions direct and clear

3. Content Coverage:
   - Include questions about key concepts, definitions, examples, and relationships
   - Cover both explicit statements and implicit ideas
   - Ensure comprehensive coverage without redundancy

Return only the structured output following the schema, nothing else.
"""
FCALL_SYSTEM_PROMPT_QA_QONLY_BLOCKS_1A = """
You are an expert text analyzer trained in extracting precise question-answer pairs from text content.

Your Role:
- A single question will be provided to you as input along with a section of text.
- Your task is to find the best possible answer to that question within the text.
- Generate exactly one Q&A block following the schema.

Guidelines for Answer Extraction:
1. 'verbatim_answer':
   - Find and extract the exact text that best answers the question.
   - The text must be a direct quote from the source, not a paraphrase.
   - Remove speaker labels and collapse multi-line text to a single line.
   - If no relevant answer exists, use 'NO RELEVANT ANSWER IN TRANSCRIPT'.

2. 'clarified_answer':
   - Provide a concise, clear restatement of the answer.
   - Edit for clarity while maintaining accuracy.
   - Keep the entire answer on a single line.

3. 'topics':
   - List 1-3 key topics addressed in the answer.
   - Use brief, descriptive terms.
   - If no answer is found, return an empty list [].

4. 'review_flag':
   - Set True if there is significant uncertainty about the answer's accuracy or completeness.
   - Otherwise set False.

Return only a single JSON object following the schema, nothing else.
"""
TOOLS_QA_QONLY_QUESTIONS = [{
    "type": "function",
    "function": {
        "name": "extract_questions_generic",
        "description": "Extract and clarify questions from the text.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of clarified questions that comprehensively cover the content of the text. Each should be concise and clear, without speaker names."
                }
            },
            "required": ["questions"],
            "additionalProperties": False
        }
    }
}]
TOOLS_QA_QONLY_BLOCKS= [{
    "type": "function",
    "function": {
        "name": "extract_final_qa_block",
        "description": (
                "Given a provided question and a section of text, extract the best possible answer."
                "Return only ONE QA block containing the relevant data fields. If no answer is found, set verbatim_answer to 'NO RELEVANT ANSWER IN TRANSCRIPT' and clarified_answer to an empty string."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "verbatim_answer": {
                    "type": "string",
                    "description": (
                        "The exact text of the answer as it appears in the text. This must be a direct quote from the text, not a paraphrase or summary."
                        "This should be on a single line, so if the answer is multi-line, it should be collapsed to a single line."
                    )
                },
                "clarified_answer": {
                    "type": "string",
                    "description": (
                        "A concise, edited version of the answer. This should be on a single line."
                    )
                },
                "topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "A list of 1-3 key topics addressed in the question-answer block. If no new question is found, return an empty list []."
                    )
                },
                "review_flag": {
                    "type": "boolean",
                    "description": (
                        "Set True if significant uncertainty in the response. Otherwise False."
                    )
                }
            },
            "required": [
                "verbatim_answer", "clarified_answer", "topics", "review_flag"
            ],
            "additionalProperties": False
        }
    }
}]
QA_EXTRACT_CONFIG_CONTENT = {
    "config_name": "QA_EXTRACT_CONFIG_CONTENT", 
    "suffix_new": "_qa-qonly",
    "heading": "CONTENT",
    "delimiter": "---",
    "q_rounds": [
        {
            "q_round_num": 1,
            "q_round_name": "Questions Extraction",
            "prefix": "Q",
            "prompt": FCALL_SYSTEM_PROMPT_QA_QONLY_QUESTIONS_1B,
            "tools": TOOLS_QA_QONLY_QUESTIONS,
            "provider": "openai",
            "model": "gpt-4o-2024-11-20",
            "max_retries": 2
        }
    ],
    "qa_block_extraction": {
        "prompt": FCALL_SYSTEM_PROMPT_QA_QONLY_BLOCKS_1A,
        "tools": TOOLS_QA_QONLY_BLOCKS,
        "provider": "openai", 
        "model": "gpt-4o-2024-11-20",
        "max_retries": 1
    }
}

FCALL_SYSTEM_PROMPT_QA_QONLY_EXPLICIT_1A = """
You are an expert text analyzer trained to extract explicitly asked questions from transcript content.

Your Task (Round 1 - Explicit Questions Only):
1. Identify every explicitly stated question:
   - A question is explicit if it appears with a question mark or contains phrases indicating a direct inquiry 
     (e.g., 'I'd like to ask...', 'Could you clarify...', 'My question is...', 'Can you explain...').
   - Include rhetorical questions that address key concepts or points.

2. For each explicit question, create a concise, edited version ('clarified question'):
   - Remove speaker names and extraneous filler phrases.
   - **If one speaker's turn contains multiple sub-questions (even within one sentence), split them into separate clarified questions.**
     - This applies even if they revolve around a similar topic or share partial overlap.

3. Apply these guidelines to each question:
   - **Distinct Content**: Avoid including duplicates or near-duplicates.
   - **Relevance**: Focus on substantive questions that address key concepts, definitions, examples, and relationships.
   - **No Speaker Names**: Do not include speaker identifiers in the questions.
   - **Coverage**: If a transcript chunk has multiple explicit questions, include them all as separate entries.
   - **Redundancy Prevention**: If the same question appears in slightly different wording, consolidate into one clarified question (unless there is a clear difference in content or context).
   - **Standalone Clarity**: Rewrite questions to be self-contained without relying on pronouns or context (e.g., 'What are the implications of this approach?' becomes 'What are the implications of using machine learning for text analysis?').

4. Question Treatment:
   - Treat the content as authoritative - phrase questions to address concepts directly.
   - Only reference speakers/authors for personal experiences or individual perspectives.
   - Frame factual claims and arguments as standalone questions.

5. Return the clarified questions as a JSON array of strings. Each entry corresponds to one distinct clarified explicit question.

6. If no explicit questions are found, return an empty array (i.e., []).

Remember:
- No implied questions in this round (explicit only).
- Always separate multi-part questions into distinct entries when feasible.
- Remove speaker labels and personal identifiers.
- Ensure each question is clearly standalone in wording. Do not use referential words (like "this" or "these") unless they refer to something explicitly defined within the question itself.
"""
FCALL_SYSTEM_PROMPT_QA_QONLY_IMPLICIT_1A = """
You are an expert text analyzer trained to identify implied (unspoken) questions from transcript content.

Context:
- Below is a list of explicit questions previously identified. You must NOT repeat or rephrase these explicit questions.
- Extract additional questions that are implied or indirectly addressed by speakers, focusing on:
  - Key concepts, definitions, and relationships discussed without explicit questions
  - Explanations that respond to unasked questions
  - Important statements that naturally raise questions
  - Complex ideas that benefit from being reframed as questions

Requirements:
1. **No Duplicates**: Exclude any question that matches or closely overlaps with a previously extracted explicit question.
2. **Standalone Clarity**: Write each question to be fully self-contained, explicitly naming all relevant concepts, processes, or entities rather than using referential language.
3. **Multiple Sub-Questions**: If a speaker covers multiple implied questions in one statement, split them into separate clarified questions.
4. **Relevance**: Focus on substantive topics that help readers understand key concepts and relationships. Skip trivial or tangential points.
5. **Question Treatment**:
   - Treat content as authoritative - phrase questions to address concepts directly
   - Only reference speakers/authors for personal experiences or perspectives
   - Frame factual claims and arguments as standalone questions
6. **Precise Language**:
   - Never use referential words (like "this" or "these") unless they refer to something explicitly defined within the question itself
   - Include all necessary context within each question
   - Be specific about processes, concepts, and relationships

Input to the Model:
- A transcript section
- A list of previously extracted explicit questions (explicit_questions_list)

Output Format:
- A valid JSON object with a single key "implicit_questions" mapping to a list of strings.
- Example:
{
  "implicit_questions": [
    "What factors influence machine learning model selection for natural language processing tasks?",
    "How do gradient descent optimization techniques apply to neural network training?"
  ]
}

If no implied questions exist, return an empty array: "implicit_questions": []

Remember:
- Do NOT restate or slightly rephrase any explicit questions already extracted.
- Ensure each implied question is relevant, standalone, and adds value to understanding the content.
- Keep questions concise and avoid speaker labels or personal identifiers.
- Break down complex topics into clear, focused questions.
- Never use referential words (like "this" or "these") unless they refer to something explicitly defined within the question itself.
"""
# 01-pro
FCALL_SYSTEM_PROMPT_QA_QONLY_EXPLICIT_2A = """
You are an expert text analyzer trained in extracting and clarifying explicitly stated questions from any type of text or transcript.

Your Task (Round 1 - Explicit Questions Only):
1. Identify every explicitly stated question in the provided text:
   - A question is explicit if it appears with a question mark or includes phrases/structure that indicate a direct inquiry.
   - Ignore any rhetorical questions or statements that merely hint at an inquiry without being stated explicitly.

2. For each explicit question, create a concise “clarified question”:
   - Remove speaker names, filler phrases, and extraneous context.
   - If one speaker’s turn contains multiple sub-questions (even if nested in a single sentence), split them into separate clarified questions.
   - Ensure each clarified question can stand on its own without relying on prior text references or pronouns.

3. Avoid Redundancy:
   - If the same explicit question appears multiple times with only minor wording differences, consolidate into one clarified question unless there is a significant difference in content.

4. Adhere to These Guidelines:
   - Treat the text as an authoritative source:
     - Frame questions directly (e.g., “Why is X considered significant?” rather than “Why does the author say X is significant?”).
     - Use “author” only for personal experiences or perspectives unique to the original text.
   - Question Structure:
     - Keep questions focused and clear; break multi-part inquiries into separate questions.
     - Remove unnecessary context to maintain directness and clarity.
   - Content Coverage:
     - Include explicit questions about key concepts, definitions, examples, and relationships within the text.
     - Ensure comprehensive coverage without duplicating nearly identical questions.
   - Standalone Clarity:
     - Replace ambiguous pronouns or references (e.g., “this” or “that”) with concrete terms so each question is self-contained.

5. Return Format:
   - Provide the final clarified questions as a JSON array of strings (no additional keys).
   - For example: [ "Clarified Question 1", "Clarified Question 2", ... ]

6. No Explicit Questions Found?
   - Return an empty array: []

Remember: 
- No implied questions in this round. 
- Keep each question succinct and self-contained.
"""
FCALL_SYSTEM_PROMPT_QA_QONLY_IMPLICIT_2A = """
You are an expert text analyzer trained in identifying and articulating implied (unspoken) questions from any type of text or transcript.

Your Task (Round 2 - Implied Questions Only):
1. You have already extracted explicit questions in a previous step; do NOT repeat or rephrase them here.
2. Identify additional questions that are implied by the text but not explicitly asked:
   - Questions a reader might naturally ask based on explanations, instructions, or statements within the text.
   - Clarifications implied by the text’s content or context, even if never directly posed as a question.

3. Avoid Duplicates:
   - Do not duplicate or closely overlap with any previously extracted explicit questions.

4. Multiple Implied Sub-Questions:
   - If a single statement suggests multiple distinct implied questions, split them accordingly.

5. Relevance:
   - Focus on clarifications, technical details, or key points that someone reading the text would be curious about or need to understand more deeply.
   - Omit trivial or tangential questions.

6. Adhere to These Guidelines:
   - Treat the text as an authoritative source:
     - Phrase implied questions directly (e.g., “What factors contribute to X?” instead of “What might the author mean by X?”).
   - Question Structure:
     - Keep questions direct and clear, ensuring each is self-contained.
     - Remove ambiguous references or pronouns, replacing them with clear terms.
   - Content Coverage:
     - Cover any unasked yet relevant questions about main ideas, definitions, examples, or relationships.
     - Ensure there is no redundancy with explicit questions.

7. Return Format:
   - Output must be a valid JSON object with the key "implicit_questions" mapping to a JSON array of question strings.
   - Example:
   {
     "implicit_questions": [
       "How can concept A be applied in practical scenarios?",
       "Why might factor B limit the effectiveness of this approach?"
     ]
   }
   - If no implied questions are found, return "implicit_questions": [].

Remember:
- Do NOT restate or overlap with explicit questions already identified.
- Each implied question should be concise, relevant, and self-explanatory.
"""
TOOLS_QA_QONLY_EXPLICIT = [{
    "type": "function",
    "function": {
        "name": "extract_explicit_questions",
        "description": "Extract and clarify all explicitly asked questions from the text, breaking multi-part questions into separate entries",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of clarified, explicitly asked questions. Each should be concise and clear, without speaker names."
                }
            },
            "required": ["questions"],
            "additionalProperties": False
        }
    }
}]
TOOLS_QA_QONLY_IMPLICIT = [{
    "type": "function",
    "function": {
        "name": "extract_implicit_questions",
        "description": (
            "Extract and clarify any implied questions from the transcript, excluding any questions that match or overlap with a given list of explicit questions."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "implicit_questions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "A list of distinct implied questions in the text."
                        "No duplicates of previously identified questions."
                    )
                }
            },
            "required": ["implicit_questions"],
            "additionalProperties": False
        }
    }
}]
QA_EXTRACT_CONFIG_TRANSCRIPT = {
    "config_name": "QA_EXTRACT_CONFIG_TRANSCRIPT",
    "suffix_new": "_qa-qonly",
    "heading": "### transcript",
    "delimiter": "---",
    "q_rounds": [
        {
            "q_round_num": 1,
            "q_round_name": "Explicit Questions Extraction",
            "prefix": "QE",
            "prompt": FCALL_SYSTEM_PROMPT_QA_QONLY_EXPLICIT_2A,
            "tools": TOOLS_QA_QONLY_EXPLICIT,
            "provider": "openai",
            "model": "gpt-4o-2024-11-20",
            "max_retries": 2
        },
        {
            "q_round_num": 2,
            "q_round_name": "Implicit Questions Extraction",
            "prefix": "QI",
            "prompt": FCALL_SYSTEM_PROMPT_QA_QONLY_IMPLICIT_2A,
            "tools": TOOLS_QA_QONLY_IMPLICIT,
            "provider": "openai",
            "model": "gpt-4o-2024-11-20",
            "max_retries": 2
        }
    ],
    "qa_block_extraction": {
        "prompt": FCALL_SYSTEM_PROMPT_QA_QONLY_BLOCKS_1A,
        "tools": TOOLS_QA_QONLY_BLOCKS,
        "provider": "openai",
        "model": "gpt-4o-2024-11-20",
        "max_retries": 1
    }
}

TOOLS_QA_QONLY_IMPLICIT_FDA = [{
    "type": "function",
    "function": {
        "name": "extract_implicit_questions",
        "description": (
            "Extract and clarify any implied questions from the transcript, excluding any questions that match or overlap with a given list of explicit questions."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "implicit_questions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "A list of distinct implied questions relevant to FDA regulations, diagnostics, disease testing, COVID-19, the pandemic, the public health response, and any other important or relevant topics."
                        "No duplicates of previously identified explicit questions."
                    )
                }
            },
            "required": ["implicit_questions"],
            "additionalProperties": False
        }
    }
}]
TOOLS_QA_QONLY_BLOCKS_FDA = [{
    "type": "function",
    "function": {
        "name": "extract_final_qa_block",
        "description": (
                "Given a final question (verbatim) and an excerpt of transcript text, extract the best possible answer."
                " Return only ONE QA block containing the relevant data fields. If no answer is found, set verbatim_answer "
                "to 'NO RELEVANT ANSWER IN TRANSCRIPT' and clarified_answer to an empty string or minimal note."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "verbatim_question": {
                    "type": "string",
                    "description": (
                        "The exact text from the transcript section text that corresponds to the provided question, minus speaker labels/newlines. The entire text should be on a single line. Do not start the text with the speaker name from the preceding speaker line. If the question is implicit, use the string 'IMPLICIT'."
                    )
                },
                "verbatim_answer": {
                    "type": "string",
                    "description": (
                        "The exact text of the answer as it appears in the transcript section text, minus speaker labels/newlines. Do not start the text with the speaker name from the preceding speaker line."
                    )
                },
                "clarified_answer": {
                    "type": "string",
                    "description": (
                        "A concise, edited version of the answer. The entire text of this answer should be on a single line. Do not mention any specific speaker names, instead use 'FDA' where appropriate."
                    )
                },
                "speaker_question": {
                    "type": "string",
                    "description": (
                        "Name/role of question speaker. The name must be as identified in the transcript by the text in the speaker line that precedes a colon or timestamp. Do not use a different name spelling that may appear in the speaker dialogue. If the question is implied from an Authority Speaker's statement, use 'NOT APPLICABLE'."
                    )
                },
                "speaker_answer": {
                    "type": "string",
                    "description": (
                        "Name/role of answer speaker. The name must be as identified in the transcript by the text in the speaker line that precedes a colon or timestamp. Do not use a different name spelling that may appear in the speaker dialogue. If the question is implicit, use the speaker name of the statement that implied the question."
                    )
                },
                "topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "A list of 1-3 key topics addressed in the question-answer block. If no new question is found, return an empty list []."
                    )
                },
                "review_flag": {
                    "type": "boolean",
                    "description": (
                        "Set True if significant uncertainty in the response. Otherwise False."
                    )
                }
            },
            "required": [
                "verbatim_question", "verbatim_answer", "clarified_answer",
                "speaker_question", "speaker_answer", "topics", "review_flag"
            ],
            "additionalProperties": False
        }
    }
}]
QA_EXTRACT_CONFIG_FDA_C19_VTH = {
    "config_name": "QA_EXTRACT_CONFIG_FDA_C19_VTH",
    "suffix_new": "_qa-qonly",
    "heading": "### transcript",
    "delimiter": "---",
    "q_rounds": [
        {
            "q_round_num": 1,
            "q_round_name": "Explicit Questions Extraction",
            "prefix": "QE",
            "prompt": FCALL_SYSTEM_PROMPT_QA_QONLY_EXPLICIT_FDA_1D,
            "tools": TOOLS_QA_QONLY_EXPLICIT,  # or None if you'd do a simple call
            "provider": "openai",
            "model": "gpt-4o-2024-11-20",
            "max_retries": 2
        },
        {
            "q_round_num": 2,
            "q_round_name": "Implicit Questions Extraction",
            "prefix": "QI",
            "prompt": FCALL_SYSTEM_PROMPT_QA_QONLY_IMPLICIT_FDA_1A,
            "tools": TOOLS_QA_QONLY_IMPLICIT_FDA,     # or None for simple call
            "provider": "openai",
            "model": "gpt-4o-2024-11-20",
            "max_retries": 2
        }
    ],
    "qa_block_extraction": {
        "prompt": FCALL_SYSTEM_PROMPT_QA_QONLY_BLOCKS_FDA_1A,
        "tools": TOOLS_QA_QONLY_BLOCKS_FDA,  # or None
        "provider": "openai",
        "model": "gpt-4o-2024-11-20",
        "max_retries": 1
    }
}


def create_extract_log_header_config(config):
    """
    Create the header for the extract log with config information.
    Shows the config exactly as it appears in the global variable definition.

    :param config: dict, the configuration dictionary
    :return: list of header lines
    """
    current_datetime = get_current_datetime_humanfriendly()
    
    # Create header lines
    header_lines = [
        "#### extract log header",
        f"datetime: {current_datetime}",
        "source file prep: sections before all sub chapters md level 3",
    ]
    
    # Get the config name from the config itself
    config_name = config.get('config_name', 'UNNAMED_CONFIG')
    
    # Find the variable name in globals that matches our config object
    config_var_name = None
    for var_name, var_value in globals().items():
        if var_value is config:
            config_var_name = var_name
            break
            
    if not config_var_name:
        raise ValueError("Could not find config in global variables")
        
    # Get the source code of this file
    with open(__file__, 'r') as f:
        source_lines = f.readlines()
    
    # Find the config definition
    config_def = ""
    in_config = False
    brace_count = 0
    
    for line in source_lines:
        if f"{config_var_name} = {{" in line:
            in_config = True
            brace_count = 1
            config_def = line
        elif in_config:
            config_def += line
            brace_count += line.count("{")
            brace_count -= line.count("}")
            if brace_count == 0:
                break
    
    header_lines.append(f"config: {config_def.strip()}\n")
    return header_lines
def mtest_create_extract_log_header_config():
    pass
#if __name__ == "__main__":
    header_lines = create_extract_log_header_config(QA_EXTRACT_CONFIG_FDA_C19_VTH)
    for line in header_lines:
        print(line)
def extract_questions_single_round(section_text, prompt, tools=None, prev_questions=None, provider="openai", max_retries=2, debug=False, abort_on_error=True):
    """
    Extract questions from a single section of text, either by function calling or 
    simple call, depending on provider/tools.

    :param section_text: str, the content of the section
    :param prompt: str, the LLM prompt to use (could be specialized for function calling or not)
    :param tools: list or None, if present -> function-calling approach; if None -> simple call
    :param prev_questions: list of str, previously extracted questions (optional)
    :param provider: str, e.g. "openai", "anthropic", "deepseek", or others
    :param debug: bool, for debug prints
    :param abort_on_error: bool, raise exceptions if True
    :param max_retries: int, how many times to retry in case of errors
    :return: list of extracted question strings, or None if error
    """
    # Add debug print for initial inputs
    verbose_print(debug, f"\nStarting extract_questions_single_round with section of length: {len(section_text)} chars")
    if prev_questions:
        verbose_print(debug, f"  Processing section with {len(prev_questions)} previous questions")
    
    # Create full prompt with context if we have previous questions
    if prev_questions:
        prev_questions_context = "Previously extracted questions - **DO NOT extract similar or overlapping questions**:\n"
        for i, q in enumerate(prev_questions, 1):
            prev_questions_context += f"{i}. {q}\n"
        verbose_print(debug, f"Previous questions context:\n{prev_questions_context}")
        
        full_prompt = (
            f"<system_prompt>{prompt}</system_prompt>\n\n"
            f"<context>{prev_questions_context}</context>\n\n"
            f"<instruction>Please identify questions in the following transcript section:</instruction>\n\n"
            f"<content>{section_text}</content>"
        )
    else:
        full_prompt = prompt + "\n\n" + section_text
    verbose_print(debug, f"Full prompt:\n{full_prompt}")
    
    attempts_left = max_retries
    while attempts_left > 0:
        try:
            verbose_print(debug, f"Attempting function call with {provider}")
            
            # TODO: Remove this check when adding simple non-function call capability
            if tools is None:
                raise ValueError("Tools must be provided - simple non-function call capability not yet implemented")
                
            # Make the appropriate function call based on provider
            if provider == "openai":
                response = openai_function_call(full_prompt, section_text, tools)
            elif provider == "anthropic":
                # Convert tools format for anthropic if needed
                if tools:
                    tools = convert_tools_to_anthropic_format(tools)
                response = anthropic_function_call(full_prompt, section_text, tools)
            elif provider == "deepseek":
                response = deepseek_structured_output(full_prompt, section_text, deepseek_qa_output_schema())
                return response.get('questions', []) if response else None
            else:
                raise ValueError(f"Provider must be either 'openai', 'anthropic', or 'deepseek' - {provider} is not supported")
            
            verbose_print(debug, f"Got response: {response}")
            
            # Parse the response
            arguments = parse_function_call_response(response, provider)
            verbose_print(debug, f"Parsed arguments: {arguments}")
            
            if not arguments:
                if abort_on_error:
                    raise Exception("Failed to parse function call response")
                return None
            
            # Get questions from the first available key in the response
            for key in ['questions', 'implicit_questions']:
                if key in arguments:
                    questions = arguments[key]
                    break
            else:
                questions = []
                
            verbose_print(debug, f"Extracted questions: {questions}")
            return questions  # Can be empty list if no questions found

        except Exception as e:
            error_msg = str(e)
            if error_msg:  # Only print error if there's an actual message
                print(colored(f"Error in question extraction: {error_msg}", "red"))
                verbose_print(debug, f"Full error details: {error_msg}")
                if abort_on_error:
                    if attempts_left <= 1:
                        raise  # Re-raise the exception to abort processing
                    else:
                        print(colored(f"Error occurred. Retrying... {attempts_left - 1} attempts remaining", "red"))
            attempts_left -= 1

    # If we exhaust all retries without success:
    print(colored("All retries exhausted; returning None from extract_questions_single_round", "red"))
    return None
def process_qa_extraction_rounds(source_file_path, config, do_blocks=True,debug=False):
    """
    Process one or more rounds of question extraction from a source file,
    optionally followed by QA-block extraction if 'qa_block_extraction' is in config.
    
    Merges aspects of both your run_q_extraction_by_sections() and Sonnet's process_qa_extraction_rounds().

    :param source_file_path: str, path to the source file
    :param config: dict, configuration for extraction rounds and optionally QA block generation
    :param debug: bool, enable debug output
    :return: str, path to the created/modified QA file
    """
    start_time = time.time()
    suffix_new = config.get('suffix_new', '_qa-qonly')
    heading = config.get('heading', '### transcript')
    delimiter = config.get('delimiter', '---')
    q_rounds = config.get('q_rounds', [])
    
    # If no rounds are defined, do nothing
    if not q_rounds:
        print("No Q Rounds defined in config; returning.")
        return None
    
    # Prepare or find the QA file
    qa_file_path = sub_suffix_in_str(source_file_path, suffix_new)
    
    # Read transcript
    metadata, sections, total_sections = get_file_metadata_and_sections(
        source_file_path, heading=heading, delimiter=delimiter
    )

    # Check if QA file exists, if not => create and initialize it
    qa_file_exists = os.path.exists(qa_file_path)
    if not qa_file_exists:
        # We'll use the FIRST round in q_rounds to build a "header"
        first_round = q_rounds[0]
        first_round_num = first_round.get("q_round_num", 1)
        first_round_name = first_round.get("q_round_name", "Q Extraction")
        first_prompt = first_round.get("prompt", "")
        first_provider = first_round.get("provider", "openai")
        first_model = first_round.get("model", "gpt-4")

        # A) Create an extract log header
        log_header_lines = create_extract_log_header_config(config=config)
        
        # B) Add placeholders for each section
        for section_num in range(1, total_sections + 1):
            log_header_lines.append(f"#### Section {section_num} of {total_sections}")
            log_header_lines.append("")

        # Prepare metadata
        current_datetime = get_current_datetime_humanfriendly()
        date = current_datetime.split(' ')[0]
        metadata = set_metadata_field(metadata, "last updated", f"{date} Created QA Sections")
        metadata = set_metadata_field(metadata, "source file", source_file_path)

        # Create the QA file with an initial "## content" heading
        initial_content = "## content\n"
        qa_file_path = write_metadata_and_content(
            source_file_path,
            metadata,
            initial_content,
            overwrite='no-sub',
            suffix_new=suffix_new
        )
        # Append the entire log header
        with open(qa_file_path, 'a') as f:
            f.write("\n### extract log\n\n" + "\n".join(log_header_lines) + "\n")

        print(f"Created new QA file: {qa_file_path}")
    else:
        print(f"QA file already exists, will update: {qa_file_path}")
    
    # For storing questions from previous rounds so we can skip duplicates
    # or pass them to subsequent rounds. We'll store them as (section_num, question_text).
    prev_questions_all = []

    # -----------
    # Perform each round in q_rounds
    # -----------
    total_q_rounds = len(q_rounds)
    for idx, round_cfg in enumerate(q_rounds, start=1):
        round_num = round_cfg.get('q_round_num', idx)
        round_name = round_cfg.get('q_round_name', f"Q Round {round_num}")
        prompt = round_cfg.get('prompt')
        tools = round_cfg.get('tools')
        provider = round_cfg.get('provider', 'openai')
        max_retries = round_cfg.get('max_retries', 2)
        prefix = round_cfg.get('prefix', f"Q{round_num}")

        print(f"\n===== Starting Q Round {round_num} of {total_q_rounds}: {round_name} =====")
        round_start_time = time.time()

        # Get the existing extract log for editing
        if idx == 1:  # First round - use the header lines we just created
            log_lines = log_header_lines
        else:  # Subsequent rounds - read from file
            extract_log_text = get_heading(qa_file_path, "### extract log")
            if not extract_log_text:
                extract_log_text = "### extract log\n"
            log_lines = extract_log_text.split('\n')

        # Iterate over each section
        for section_num, section_text in enumerate(sections, 1):
            section_text = section_text.strip()
            if not section_text:
                print(f"Empty section at position {section_num}; skipping.")
                continue
            
            print(f"Processing Round {round_num} {round_name} - section {section_num}/{total_sections}")

            # Gather prior questions for this section (if desired)
            # We are storing them in prev_questions_all
            prev_questions_section = [
                q[1] for q in prev_questions_all if q[0] == section_num
            ] if prev_questions_all else None

            # Extract new questions
            new_questions = extract_questions_single_round(
                section_text=section_text,
                prompt=prompt,
                tools=tools,
                prev_questions=prev_questions_section,
                provider=provider,
                max_retries=max_retries,
                debug=debug,
                abort_on_error=True
            )
            if new_questions is None:
                new_questions = []  # indicates an error or no output

            # Update the log for this section
            log_lines = log_section_items(
                log_lines=log_lines,
                section_num=section_num,
                items=new_questions,
                round_name=round_name,
                prefix=prefix
            )

            # Extend our global store of questions so we can skip duplicates or pass them on
            if new_questions:
                for q_text in new_questions:
                    prev_questions_all.append((section_num, q_text))

        # Write updated log lines back to the QA file
        updated_log_text = "\n".join(log_lines)
        set_heading(qa_file_path, updated_log_text, "### extract log")

        round_end_time = time.time()
        print(f"{round_name} completed in {(round_end_time - round_start_time)/60:.1f} minutes.")
        print(f"Extract log updated in {qa_file_path}")

    # -----------
    # Optionally perform QA-block extraction
    # -----------
    if do_blocks and 'qa_block_extraction' in config:
        qa_block_cfg = config['qa_block_extraction']
        print("\nDetected QA block extraction config. Performing do_qonly_round_3_blocks now.")
        do_qonly_round_3_blocks(
            file_path=source_file_path,
            fcall_prompt=qa_block_cfg['prompt'],
            provider=qa_block_cfg.get('provider', 'openai'),
            heading=heading,
            delimiter=delimiter,
            suffix_new=suffix_new
        )

    total_time = time.time() - start_time
    time_now = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
    print(f"\nAll question extraction rounds completed in {total_time/60:.1f} minutes at {time_now}.")
    return qa_file_path
def mrun_process_qa_extraction_rounds():
    pass
#if __name__ == "__main__":
    # cur_source_file_path = "data/floodlamp/reg/fda-townhalls/dev-qa-extract/test_transcript_just2/VTH 36 just2_trans.md"
    # process_qa_extraction_rounds(cur_source_file_path, QA_EXTRACT_CONFIG_FDA_C19_VTH)
    # cur_source_file_path = "data/misc_books/Sovereign Child/The Sovereign Child_sections.md"
    # process_qa_extraction_rounds(cur_source_file_path, QA_EXTRACT_CONFIG_CONTENT)
    cur_source_file_path = "data/misc_books/Sovereign Child/2025-01-17_Tim Ferriss Show - Naval and Aaron Stupple on Sovereign Child_section-titles.md"
    process_qa_extraction_rounds(cur_source_file_path, QA_EXTRACT_CONFIG_TRANSCRIPT, do_blocks=False)

### ADD SECTIONS
def get_section_lines_by_speakers(file_path, remove_speakers, remove_duplicates=False, verbose=False):
    """
    Get speaker lines and their line numbers from a transcript file.
    
    :param file_path: string of the path to the file to process
    :param remove_speakers: list of strings, any speaker containing these strings will be removed
    :param remove_duplicates: boolean, if True removes consecutive duplicate speakers
    :return: list of tuples containing (speaker_full, line_number) where line_number is absolute to file start
    """
    # Get the heading text and find the starting line number
    transcript = get_heading(file_path, "### transcript")
    if transcript is None:
        print(f"No transcript found in {file_path}")
        return []
    
    # Count lines until we find the heading to get the correct line number
    heading_line_start = find_line_number_in_file(file_path, "### transcript")
    
    speaker_lines = []
    lines = transcript.split('\n')
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:  # Skip empty lines
            continue
            
        # Handle lines ending with colon
        if line.endswith(':'):
            speaker_full = line.rstrip(' :')  # Remove colon and whitespace
            absolute_line_num = heading_line_start + i
            speaker_lines.append((speaker_full, absolute_line_num))
            
        # Handle lines with timestamp following speaker name
        else:
            timestamp, index = get_timestamp(line)
            if index is not None:
                speaker_full = line[:index].strip()
                absolute_line_num = heading_line_start + i
                speaker_lines.append((speaker_full, absolute_line_num))
    
    # Remove specified speakers
    if remove_speakers:
        speaker_lines = [
            (speaker, line_num) 
            for speaker, line_num in speaker_lines 
            if not any(rm_speaker.lower() in speaker.lower() for rm_speaker in remove_speakers)
        ]
    
    # Remove consecutive duplicates if requested
    if remove_duplicates and speaker_lines:
        filtered_lines = [speaker_lines[0]]  # Keep first entry
        for current in speaker_lines[1:]:
            if current[0] != filtered_lines[-1][0]:  # Compare speaker_full strings
                filtered_lines.append(current)
        speaker_lines = filtered_lines
    
    if verbose:
        for speaker, line_num in speaker_lines:
            print(f"({speaker}, {line_num})")
    return speaker_lines
def mtest_get_section_lines_by_speakers():
    pass
#if __name__ == "__main__":
    cur_file_path = "data/floodlamp/reg/fda-townhalls/dev-qa-extract/VTH 36_cemanual.md"
    speaker_lines = get_section_lines_by_speakers(cur_file_path, remove_speakers=["FDA"], remove_duplicates=True, verbose=True)
def get_section_lines_by_perfect_segments(eval_seg_csv_path, ref_transcript_path):
    pass
def get_section_lines_by_markdown(md_file_path, heading_level):
    """
    Get line numbers for blank lines before markdown headings of specified level or lower.
    Raises ValueError if any heading doesn't have a blank line before it.

    :param md_file_path: string, path to the markdown file to process
    :param heading_level_: int, maximum heading level to consider (e.g., 3 means look for ###, ##, and #)
    :return: list of integers, line numbers of blank lines before headings (1-based)
    """
    # Read file lines
    with open(md_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Create list to store line numbers
    section_lines = []
    
    # Create pattern to match headings of specified level or lower
    heading_pattern = r'^#{1,' + str(heading_level) + r'}\s'
    
    # Iterate through lines to find headings
    for i in range(len(lines)):
        line = lines[i].strip()
        if re.match(heading_pattern, line):
            # Check if there's a previous line and it's blank
            if i > 0 and not lines[i-1].strip():
                section_lines.append(i)  # 1-based line number
            else:
                raise ValueError(f"No blank line before heading at line {i+1}: '{line}'")
    
    return section_lines
def add_section_delimiters(file_path, line_numbers, delimiter="---"):
    """
    Add delimiter strings at specified line numbers in a file.
    
    :param file_path: string, path to the file to modify
    :param line_numbers: list of integers, line numbers where delimiters should be added (1-based)
    :param delimiter: string, delimiter to add at specified lines (default: "---")
    :return: None
    """
    # Read all lines from file
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Convert line numbers from 1-based to 0-based indexing
    zero_based_lines = [line_num - 1 for line_num in line_numbers]
    
    # Check if any line numbers are out of bounds
    if any(line_num >= len(lines) for line_num in zero_based_lines):
        raise ValueError(f"Line numbers {[ln + 1 for ln in zero_based_lines if ln >= len(lines)]} are out of bounds. File has {len(lines)} lines.")
    
    # Check if specified lines are blank (allowing whitespace)
    non_blank_lines = []
    for line_num in zero_based_lines:
        if lines[line_num].strip():  # Use strip() to remove all whitespace before checking
            print(f"Line {line_num + 1} content: '{lines[line_num]}'")  # Debug print
            non_blank_lines.append(line_num + 1)
    
    if non_blank_lines:
        raise ValueError(f"The following line numbers are not blank: {non_blank_lines}\nFor file: {file_path}")
    
    # Add delimiters
    for line_num in zero_based_lines:
        lines[line_num] = delimiter + '\n'  # Replace entire line, including any whitespace
    
    # Write modified content back to file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"Added {len(line_numbers)} section delimiters to file: {file_path}")
def mrun_add_section_delimiters():
    pass
#if __name__ == "__main__":
    cur_file_path = "data/floodlamp/reg/fda-townhalls/f5_fixnames/2020-05-20_Virtual Town Hall 9_fixnames.md"
    speaker_tuples = get_section_lines_by_speakers(cur_file_path, remove_speakers=["FDA"], remove_duplicates=True)
    
    # Extract line numbers and subtract 1 from each
    prev_line_numbers = [line_num - 1 for _, line_num in speaker_tuples]
    print(f"prev_line_numbers: {prev_line_numbers}")
    add_section_delimiters(cur_file_path, prev_line_numbers)
def mrun_add_section_delimiters_folder():
    pass
#if __name__ == "__main__":
    cur_folder_path = "data/floodlamp/reg/fda-townhalls/f5_fixnames/run_delimiter"
    files_to_run = get_files_in_folder(cur_folder_path, suffixpat_include='_fixnames')
    total_start_time = time.time()
    
    for i, file_path in enumerate(files_to_run, 1):
        speaker_tuples = get_section_lines_by_speakers(file_path, remove_speakers=["FDA"], remove_duplicates=True)
        # Extract line numbers and subtract 1 from each
        prev_line_numbers = [line_num - 1 for _, line_num in speaker_tuples]
        print(f"prev_line_numbers: {prev_line_numbers}")
        add_section_delimiters(file_path, prev_line_numbers)  
def mrun_add_markdown_section_delimiters():
    pass
#if __name__ == "__main__":
    cur_file_path = "data/misc_books/Sovereign Child/The Sovereign Child_sections.md"
    section_lines = get_section_lines_by_markdown(cur_file_path, heading_level=3)
    print(f"num section lines: {len(section_lines)}")
    print(f"section_lines: {section_lines}")
    add_section_delimiters(cur_file_path, section_lines)
def propagate_section_titles_to_qa(source_file_path, section_heading='####', suffix_new='_qa-qonly'):
    """
    Propagates section titles from text file to corresponding QA file.

    :param source_file_path: string, path to the source file containing section titles
    :param section_heading: string, heading format to look for in source file
    :param suffix_new: string, suffix to identify QA file
    :return qa_file_path: string, path to the modified QA file
    """
    # Verify QA file exists
    qa_file_path = sub_suffix_in_str(source_file_path, suffix_new)
    if not os.path.exists(qa_file_path):
        raise ValueError(f"QA file not found: {qa_file_path}")

    # Get transcript lines from the transcript section
    transcript_text = get_heading(source_file_path, "### transcript")
    transcript_lines = transcript_text.splitlines()

    # Extract section titles with their numbers
    section_titles = {}
    for line in transcript_lines:
        if line.strip().startswith(section_heading):
            # Extract section number and title
            match = re.match(rf"{section_heading}\s+(\d+)\.\s+(.+)", line.strip())
            if match:
                section_num = int(match.group(1))
                section_title = line.strip()  # Keep full heading line
                section_titles[section_num] = section_title

    # Get QA lines
    qa_text = get_heading(qa_file_path, "### qa")
    qa_lines = qa_text.splitlines()

    # Process QA lines and insert section titles
    new_qa_lines = []
    current_section = None
    
    for line in qa_lines:
        # Check for QA block header
        match = re.match(r'QA Block (\d+)-', line.strip())
        if match:
            section_num = int(match.group(1))
            # If this is a new section and we have a title for it
            if section_num != current_section and section_num in section_titles:
                if new_qa_lines:  # Add extra newline if not at the start
                    new_qa_lines.append('')
                new_qa_lines.append(section_titles[section_num])
                new_qa_lines.append('')  # Add blank line after title
                current_section = section_num
        new_qa_lines.append(line)

    # Join the lines and ensure proper spacing
    new_qa_text = '\n'.join(new_qa_lines).strip() + '\n\n'
    
    # Write the updated text back using set_heading
    set_heading(qa_file_path, new_qa_text, "### qa")

    print(f"Section titles propagated to QA file: {qa_file_path}")
    return qa_file_path
def mrun_propagate_section_titles_to_qa():
    pass
#if __name__ == "__main__":
    cur_file_path = "data/misc_books/Sovereign Child/2025-01-17_Tim Ferriss Show - Naval and Aaron Stupple on Sovereign Child_section-titles.md"
    propagate_section_titles_to_qa(cur_file_path)
def mrun_section_titles():
    pass
#if __name__ == "__main__":
    # cur_file_path = "tests/test_data_files/fileops/document.md"
    # write_section_titles(cur_file_path, SCALL_PROMPT_SECTION_TITLE)
    cur_folder_path = "data/floodlamp/reg/fda-townhalls/f5_fixnames/done_auto"
    #files_to_run = get_files_in_folder(cur_folder_path, suffixpat_include='_fixnames')
    files_to_run = get_files_in_folder(cur_folder_path, suffixpat_include='_section-titles')

    for i, file_path in enumerate(files_to_run, 1):
        #write_section_titles(file_path, SCALL_PROMPT_SECTION_TITLE)
        propagate_section_titles_to_qa(file_path)
#NOT USED
SCALL_PROMPT_SECTION_TITLE = """
You will receive a single section of text. From that text, generate one section title that is no more than ten words. Aim for six words if possible. The title should capture the main idea, question, or topic in a condensed format.
Important Requirements:
No additional text beyond the section title.
No preamble, explanations, or quotes around the title—only the title itself.
The title must be one line and stand on its own.
INSTRUCTIONS:
Identify the core theme or question in the text.
Craft a concise heading of up to ten words, ideally six.
Do not include any other text, formatting, or commentary.
When you are finished, your entire response should contain only that single section title, with no quotation marks, extra text, or spacing before or after it.
"""
def write_section_titles(source_file_path, scall_prompt, provider="openai", heading="### transcript", delimiter='---', prepend="\n\n#### ", suffix_new='_section-titles'):
    """
    Generate section titles and replace delimiters with these titles.

    :param source_file_path: string, path to the source file
    :param scall_prompt: string, prompt for section title generation
    :param provider: string, which provider to use ("openai" or "anthropic")
    :param delimiter: string, used to separate sections
    :param suffix_new: string, suffix for the new file name
    :return new_file_path: string, path to the created file
    """
    start_time = time.time()

    # Set model based on provider
    if provider == "openai":
        model = OPENAI_MODEL
    elif provider == "anthropic":
        model = ANTHROPIC_MODEL
    else:
        raise ValueError("Provider must be either 'openai' or 'anthropic'")

    # Get transcript sections and metadata
    metadata, sections, total_sections = get_file_metadata_and_sections(source_file_path, heading='### transcript', delimiter=delimiter)

    # Update metadata
    current_datetime = get_current_datetime_humanfriendly()
    date = current_datetime.split(' ')[0]
    metadata = set_metadata_field(metadata, "last updated", f"{date} Added Section Titles")
    metadata = set_metadata_field(metadata, "source file", source_file_path)

    # Process sections and generate titles
    processed_content = []
    for section_num, section in enumerate(sections, 1):
        section = section.strip()
        if not section:
            continue

        print(f"\nProcessing section {section_num} of {total_sections}")
        try:
            # Generate section title based on provider
            if provider == "openai":
                title = simple_openai_chat_completion_request(scall_prompt + "\n\n" + section, model)
            elif provider == "anthropic":
                title = simple_anthropic_chat_completion_request(scall_prompt + "\n\n" + section, model)
            else:
                raise ValueError("Provider must be either 'openai' or 'anthropic'")
            
            # Add section with title
            processed_content.append(f"{prepend} {section_num}. {title.strip()}\n")  # Title with heading format
            processed_content.append(section)
            print(colored(title.strip(), "blue"))
            
        except Exception as e:
            error_msg = f"\n********** Error generating title for section {section_num}: {str(e)}"
            print(colored(error_msg, "red"))
            processed_content.append(section)  # Include original section without title
            continue

    # Create output file with processed content
    initial_content = "## content\n\n### transcript"
    new_content = initial_content + "\n".join(processed_content)
    new_file_path = write_metadata_and_content(
        source_file_path, 
        metadata, 
        new_content, 
        overwrite='no-sub', 
        suffix_new=suffix_new
    )

    time_now = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
    print(f"\nSection titles generation completed in {(time.time() - start_time) / 60:.1f} minutes at {time_now}.")
    print(colored("New file written to " + new_file_path, "green"))
    return new_file_path

### MULTI QUESTIONS
FCALL_PROMPT_QA_MULTI = """
You are an expert text analyzer, trained in identifying multiple relevant questions or implied questions from a given answer that adequately cover the content of the answer.
Your job:
  - Take the provided answer and generate several clear, consise questions covering the major topics of the answer.
  - The questions must not mention speaker names or personal details.
  - The questions should treat the answer as authoritative knowledge.
  - Always return EXACT JSON, matching the specified schema, where the property 'questions' is an array of question strings.

You are an expert text analyzer, trained in identifying multiple relevant questions or implied questions from a given answer that adequately cover the content of the answer.
Your job:
  - Take the provided answer and generate several clear, concise questions covering the major topics of the answer.
  - The questions must not mention speaker names or personal details.
  - The questions should treat the answer as authoritative knowledge.
  - Use full names for people instead of just last names, such as "Alan Turing" and "Karl Popper". Do this for every question not just the first one.
  - Use "AGI (artificial general intelligence)" instead of just "AGI".
  - Use double quotes instead of single quotes for quoted text in the questions.
  - Always return EXACT JSON, matching the specified schema, where the property 'questions' is an array of question strings.

DO NOT Do the following:
  - DO NOT create questions that are too similar to existing questions
  - DO NOT generate questions that are overly specific about minor details
  - DO NOT create questions that require knowledge not contained in the answer
  - DO NOT include questions that are too broad or vague
  - DO NOT include examples or scenarios that are not essential to the main ideas of the question
  - DO NOT generate questions that misrepresent the content of the answer
  - DO NOT create questions that use jargon not explained in the answer
  - DO NOT include questions that make assumptions beyond what's stated in the answer
  - DO NOT generate questions that are leading or contain implicit assumptions
  - DO NOT include phrases like "in the text," "according to the speaker/answer," "in this passage," etc.
  - DO NOT reference the answer or quote the speaker in any way
  - DO NOT create questions that aren't standalone (questions must make sense without seeing the answer)
  - DO NOT use meta-references like "How does the author describe..." or "What does the passage say about..."

Use terminology and concepts that are provided in the answer.
"""
TOOLS_QA_MULTI = [
    {
        "type": "function",
        "function": {
            "name": "get_multi_qa", 
            "description": "Extract or create multiple new questions from the provided answer text.",
            "strict": True,  # For structured (JSON) output
            "parameters": {
                "type": "object",
                "properties": {
                    "questions": {
                        "type": "array",
                        "description": "A list of new questions derived from the answer text. Do not duplicate questions - these questions should be sufficiently different from the provided current question or questions. Do not mention speaker names. Avoid overly specific questions about minor details. Questions must be answerable using only the information in the answer. Do not create questions that are too broad, vague, or that misrepresent the content. Never include phrases like 'in the text,' 'according to the speaker,' 'in this passage,' etc. Questions must be completely standalone without referencing the answer or quoting the speaker. Avoid meta-references like 'How does the author describe...' or 'What does the passage say about...'",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": ["questions"],
                "additionalProperties": False
            },
        },
    }
]
def get_existing_questions(block_text):
    """
    Extract all questions from a block of text by finding fields that contain 'QUESTION' in their name.

    :param block_text: string, the text block to parse for questions
    :return: list, list of question strings found in the block
    """
    from structured import get_all_fields_dict
    fields_dict = get_all_fields_dict(block_text)
    questions = []
    
    # Find all fields that contain 'QUESTION' in their name
    for field_name, field_value in fields_dict.items():
        if 'QUESTION' in field_name and field_value:
            questions.append(field_value)
            
    return questions
def generate_new_questions(existing_questions, answer_text, fcall_prompt=FCALL_PROMPT_QA_MULTI, fcall_tools=TOOLS_QA_MULTI, model='o3-mini', provider="openai"):
    """
    Generate new questions based on existing questions and answer text.

    :param existing_questions: list, list of existing questions
    :param answer_text: string, the answer text to generate new questions from
    :param fcall_prompt: string, the prompt to use for function calling
    :param fcall_tools: list, the tools to use for function calling
    :param model: string, the model to use for function calling
    :param provider: string, the provider to use ("openai" or "anthropic")
    :return: list, list of new questions
    """
    fcall_content = "<CURRENT EXISTING QUESTIONS>\n" + "\n".join(existing_questions) + "\n</CURRENT EXISTING QUESTIONS>\n"
    fcall_content += "<ANSWER>\n" + answer_text + "\n</ANSWER>\n"
    
    # Make the appropriate function call based on provider
    if provider == "openai":
        fcall_response = openai_function_call(fcall_prompt, fcall_content, fcall_tools, model=model)
    elif provider == "anthropic":
        fcall_response = anthropic_function_call(fcall_prompt, fcall_content, fcall_tools, model=model)
    else:
        raise ValueError("Provider must be either 'openai' or 'anthropic'")
    
    # Parse the response using the common parser
    arguments = parse_function_call_response(fcall_response, provider)
    
    if not arguments:
        raise Exception("Failed to parse function call response")
    
    new_questions = arguments['questions']
    return new_questions
def create_qa_multi_file_from_qa(qa_file_path, fcall_prompt=FCALL_PROMPT_QA_MULTI, fcall_tools=TOOLS_QA_MULTI, model='o3-mini', provider="openai", suffix_new="_qa-multi", verbose=False, max_workers=50):
    """
    Processes an existing QA file to generate multiple numbered questions per block 
    via multi-question extraction. Uses parallel processing for faster execution.

    :param qa_file_path: string, path to the existing QA file
    :param suffix_new: string, suffix to add to the output file name
    :param verbose: boolean, whether to print verbose output
    :param max_workers: int, maximum number of parallel workers
    :return: string, path to the generated QA multi file
    """
    import concurrent.futures
    from structured import get_blocks_from_file, get_all_fields_dict
    print("Running create_qa_multi_file_from_qa on file: " + qa_file_path)

    blocks = get_blocks_from_file(qa_file_path, heading="### qa")
    print(f"Found {len(blocks)} blocks to process")
    
    # Define a function to process a single block
    def process_block(block_data):
        index, block = block_data
        verbose_print(verbose, f"  Starting processing for QA block number: {index+1}/{len(blocks)}")
        
        # Use get_all_fields_dict to extract all fields from the block
        fields_dict = get_all_fields_dict(block)
        
        # Extract answer from fields_dict
        answer_text = fields_dict.get("ANSWER", "")
        
        if not answer_text:
            verbose_print(verbose, f"  No answer text found for block {index+1}. Keeping as is.")
            return index, block
            
        # Get existing questions from the block
        existing_questions = get_existing_questions(block)
        
        try:
            # Generate new questions from the answer using default parameters
            new_questions = generate_new_questions(existing_questions, answer_text, fcall_prompt, fcall_tools, model, provider)
            
            # Combine existing + new questions
            combined_questions = existing_questions + new_questions
            
            # Create new dictionary starting with numbered questions
            new_fields_dict = {}
            
            # Add numbered questions first
            for q_idx, question in enumerate(combined_questions, 1):
                new_fields_dict[f"QUESTION {q_idx}"] = question
                
            # Add remaining fields that don't have 'QUESTION' in the name
            for k, v in fields_dict.items():
                if 'QUESTION' not in k:
                    # Handle TOPICS field properly whether it's a list or string
                    if k == 'TOPICS':
                        if isinstance(v, list):
                            # If it's already a list, join it directly
                            new_fields_dict[k] = ', '.join(v) if v else ''
                        elif isinstance(v, str):
                            # If it's a string representation of a list like "['item1', 'item2']"
                            if v.startswith('[') and v.endswith(']') and "'" in v:
                                try:
                                    # Try to convert string representation to actual list
                                    items = v[1:-1].replace("'", "").split(', ')
                                    new_fields_dict[k] = ', '.join(items)
                                except:
                                    # If conversion fails, keep as is
                                    new_fields_dict[k] = v
                            else:
                                # Regular string, keep as is
                                new_fields_dict[k] = v
                        else:
                            # For any other type, convert to string
                            new_fields_dict[k] = str(v)
                    else:
                        # For all other fields, keep as is
                        new_fields_dict[k] = v
                    
            # Create block lines from updated dictionary
            new_block_lines = [f"{field}: {value}" for field, value in new_fields_dict.items()]
            
            # Join the lines to form the new block
            new_block = "\n".join(new_block_lines)
            verbose_print(verbose, f"  Completed processing for QA block number: {index+1}/{len(blocks)}")
            return index, new_block
            
        except Exception as e:
            print(colored(f"Error processing block {index+1}: {str(e)}", "red"))
            # Return the original block if there's an error
            return index, block

    # Process blocks in parallel
    processed_blocks_dict = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all blocks for processing
        future_to_block = {
            executor.submit(process_block, (i, block)): i 
            for i, block in enumerate(blocks)
        }
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_block):
            block_idx = future_to_block[future]
            try:
                idx, processed_block = future.result()
                processed_blocks_dict[idx] = processed_block
                verbose_print(verbose, f"  ***** Block {idx+1}/{len(blocks)} completed *****")
            except Exception as exc:
                verbose_print(verbose, f"  ***** Block {block_idx+1} generated an exception: {exc} *****")
                # Keep the original block in case of error
                processed_blocks_dict[block_idx] = blocks[block_idx]
    
    # Reassemble blocks in the original order
    processed_blocks = [processed_blocks_dict[i] for i in range(len(blocks))]
    
    # Join all processed blocks with a blank line between them
    qa_multi_content = "## content\n\n" + "\n\n".join(processed_blocks)

    # Write out to new file
    metadata, _ = read_metadata_and_content(qa_file_path)
    metadata = set_metadata_field(metadata, "model qa-multi", model)
    qa_multi_file_path = write_metadata_and_content(qa_file_path, metadata, qa_multi_content, suffix_new, overwrite='no-sub')
    set_last_updated(qa_multi_file_path, "Created multi-QA")
    print("Multi-QA written to " + qa_multi_file_path)

    return qa_multi_file_path
def create_qa_multi_file_from_qa_sequential(qa_file_path, suffix_new="_qa-multi", verbose=False):
    """
    Processes an existing QA file to generate multiple numbered questions per block 
    via multi-question extraction.

    :param qa_file_path: string, path to the existing QA file
    :param suffix_new: string, suffix to add to the output file name
    :return: string, path to the generated QA multi file
    """
    from structured import get_blocks_from_file, get_all_fields_dict
    print("Running create_qa_multi_file_from_qa on file: " + qa_file_path)

    blocks = get_blocks_from_file(qa_file_path, heading="### qa")
    
    # Accumulate all the processed blocks here
    processed_blocks = []

    for i, block in enumerate(blocks):
        verbose_print(verbose, f"  Processing QA block number: {i+1}/{len(blocks)}")
        
        # Use get_all_fields_dict to extract all fields from the block
        fields_dict = get_all_fields_dict(block)
        
        # Extract answer from fields_dict
        answer_text = fields_dict.get("ANSWER", "")
        
        if not answer_text:
            print("No answer text found for this block. Keeping as is.")
            processed_blocks.append(block)
            continue
            
        # Get existing questions from the block
        existing_questions = get_existing_questions(block)
        
        # Generate new questions from the answer
        new_questions = generate_new_questions(existing_questions, answer_text)
        
        # Combine existing + new questions
        combined_questions = existing_questions + new_questions
        
        # Create new dictionary starting with numbered questions
        new_fields_dict = {}
        
        # Add numbered questions first
        for idx, question in enumerate(combined_questions, 1):
            new_fields_dict[f"QUESTION {idx}"] = question
            
        # Add remaining fields that don't have 'QUESTION' in the name
        for k,v in fields_dict.items():
            if 'QUESTION' not in k:
                new_fields_dict[k] = v
                
        fields_dict = new_fields_dict
            
        # Create block lines from updated dictionary
        new_block_lines = [f"{field}: {value}" for field, value in fields_dict.items()]
        
        # Join the lines to form the new block
        new_block = "\n".join(new_block_lines)
        processed_blocks.append(new_block)

    # Join all processed blocks with a blank line between them
    qa_multi_content = "## content\n\n" + "\n\n".join(processed_blocks)

    # Write out to new file
    metadata, _ = read_metadata_and_content(qa_file_path)
    qa_multi_file_path = write_metadata_and_content(qa_file_path, metadata, qa_multi_content, suffix_new, overwrite='no-sub')
    set_last_updated(qa_multi_file_path, "Created multi-QA")
    print("Multi-QA written to " + qa_multi_file_path)

    return qa_multi_file_path

### OLD PROMPTS
def tools_qonly_explicit_list():  # not tried - think this is incorrect format
    return [{
        "type": "function",
        "function": {
            "name": "extract_explicit_questions",
            "description": "Return a list of clarified questions extracted from the transcript. Each question is explicitly asked in the text.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "clarified_questions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "An array of clarified question strings, each representing a distinct explicit question."
                    }
                },
                "required": ["clarified_questions"],
                "additionalProperties": False
            }
        }
    }]
FCALL_SYSTEM_PROMPT_QA_QONLY_EXPLICIT_1A = """
You are an expert at identifying and clarifying explicitly asked questions in meeting transcripts.

Your Role:
- Extract and clarify all explicitly asked questions from the provided text
- Only process questions marked by:
  * Question marks
  * Clear question phrases ("Could you explain", "I'd like to ask", etc.)
- Break multi-part questions into separate, individual questions
- Create clear, concise versions of each question that preserve technical accuracy

Content Guidelines:
- Focus on technical, procedural, or legal questions about COVID-19 diagnostics
- Exclude trivial questions (e.g., "Can you hear me?", "Who's next?")
- Do not include implied questions or statements that could be questions
- Do not mention specific speaker names in the questions
- Remove unnecessary context while preserving key technical terms

Question Clarification Rules:
- Make questions concise and direct
- Break compound questions into separate individual questions
- Preserve all technical terms and regulatory references
- Standardize terminology while maintaining accuracy
- Remove conversational elements ("you know", "I was wondering", etc.)

Redundancy Prevention:
- Avoid duplicate questions even if asked by different speakers
- If similar questions are asked with slightly different focus, preserve each distinct aspect
- Combine closely related questions that seek the same information
- When questions build on each other, maintain the logical distinction between them
"""
FCALL_SYSTEM_PROMPT_QA_QONLY_EXPLICIT_1B_o1pro = """
You are an expert text analyzer trained to extract explicitly asked questions from FDA Town Hall transcripts on COVID-19 diagnostics. 

Your Task (Round 1 - Explicit Questions Only):
1. Identify every explicitly stated question. 
   - A question is explicit if it appears with a question mark or contains phrases indicating a direct inquiry 
     (e.g., "I'd like to ask...", "Could you clarify...", "My question is...").
2. For each explicit question, create a concise, edited version ("clarified question"):
   - Remove speaker names and extraneous filler phrases.
   - If a single speaker asks multiple related questions in one turn, separate them into distinct clarified questions 
     whenever they address different topics.
3. Apply these guidelines to each question:
   - **Distinct Content**: Avoid including duplicates or near-duplicates. 
   - **Relevance**: Focus on technical, procedural, or legal aspects related to COVID-19 test development, validation, labeling, etc.
   - **No Speaker Names**: The clarified questions should not include any speaker identifiers (e.g. "Dr. Smith", "Audience Member").
   - **Coverage**: If a transcript chunk has multiple explicit questions, include them all as separate entries in the list.
   - **Redundancy Prevention**: If the same question appears in slightly different wording within the same chunk, consolidate into one clarified question (unless there is a clear difference in content or context).

4. Return the clarified questions as a JSON array of strings. Each entry in the array corresponds to one distinct clarified explicit question.

5. If no explicit questions are found, return an empty array (i.e., []).

Remember:
- No implied questions in this round (explicit only).
- If a speaker lumps multiple sub-questions into one statement, separate them if they are truly different queries.
- Do not include any speaker labels or personal identifiers in the clarified questions.
"""
FCALL_SYSTEM_PROMPT_QA_QONLY_EXPLICIT_1C = """
You are an expert text analyzer trained to extract explicitly asked questions from FDA Town Hall transcripts on COVID-19 diagnostics. 

Your Task (Round 1 - Explicit Questions Only):
1. Identify every explicitly stated question. 
   - A question is explicit if it appears with a question mark or contains phrases indicating a direct inquiry 
     (e.g., "I'd like to ask...", "Could you clarify...", "My question is...").
2. For each explicit question, create a concise, edited version ("clarified question"):
   - Remove speaker names and extraneous filler phrases.
   - If a single speaker asks multiple related questions in one turn, separate them into distinct clarified questions 
     whenever they address different topics.
3. Apply these guidelines to each question:
   - **Distinct Content**: Avoid including duplicates or near-duplicates. 
   - **Relevance**: Focus on technical, procedural, or legal aspects related to COVID-19 test development, validation, labeling, etc.
   - **No Speaker Names**: The clarified questions should not include any speaker identifiers (e.g. "Dr. Smith", "Audience Member").
   - **Coverage**: If a transcript chunk has multiple explicit questions, include them all as separate entries in the list.
   - **Redundancy Prevention**: If the same question appears in slightly different wording within the same chunk, consolidate into one clarified question (unless there is a clear difference in content or context).
   - **Standalone Clarity**: If the original text uses pronouns or ambiguous references (e.g., 'If it's just an empty tube...'), rewrite the clarified question so that it explicitly names the subject (e.g., 'If a saliva collection tube is just an empty tube...') rather than relying on prior context or pronouns.

4. Return the clarified questions as a JSON array of strings. Each entry in the array corresponds to one distinct clarified explicit question.

5. If no explicit questions are found, return an empty array (i.e., []).

Remember:
- No implied questions in this round (explicit only).
- If a speaker lumps multiple sub-questions into one statement, separate them if they are truly different queries.
- Do not include any speaker labels or personal identifiers in the clarified questions.
- Ensure each question is clearly standalone in wording.
"""

### NOT USED - LLM SECTIONS
PROMPT_MEETING_SECTIONS_1 = """
Please analyze the following transcript of a meeting and identify the line numbers where a delimiter ('---') should be applied to break the text into sections for structured question and answer extraction.

<< INSTRUCTIONS >>
- Break the text into sections so that dialogue that should go together stays together.
- Apply a delimiter when transitioning to a new question or a new audience member asking a question.
- Provide a list of line numbers where the delimiter should be applied.
- Make your response only the line numbers separated by commas and surrounded by the square brackets.
- DO NOT include any other text in your response.

<< OUTPUT EXAMPLE >>
"[28, 37, 42, 55, 64, 79, 96, 108, 132, 141, 154, 192, 205, 214, 223, 238, 246, 252, 261, 300]"

<< TRANSCRIPT >>

"""
def scall_meeting_sections(file_path, system_prompt, heading="### transcript"):
    # Get the heading text and find the starting line number
    heading_text = get_heading(file_path, heading)
    
    # Count lines until we find the heading to get the correct line number
    heading_line_start = find_line_number_in_file(file_path, heading)
    #print(f"heading line start: {heading_line_start}")
    
    # Get the response from OpenAI
    prompt = system_prompt + heading_text
    response = simple_openai_chat_completion_request(prompt, model=OPENAI_MODEL)
    print(f"response: {response}")
    
    # Convert string response to Python list
    # Remove brackets and split by commas
    numbers_str = response.strip('[]').split(',')
    # Convert strings to integers and add heading_line_start to each
    line_numbers = [int(num.strip()) + heading_line_start for num in numbers_str]
    
    return line_numbers
PROMPT_MEETING_SECTIONS_2 = """
You are a precise transcript analyzer. Your task is to identify natural section breaks ('---') in FDA town hall transcripts based on conversation flow and speaker transitions.

<< COUNTING RULES >>
1. Count lines sequentially from the start of the transcript:
   - Each new line (marked by a line break) counts as one line
   - Speaker names like "Coordinator:" or "Tim Stenzel (FDA IVD Director):" count as their own line
   - Each paragraph of speech counts as its own line
   - Blank lines count as their own line number
   - The delimiter ('---') will replace an existing blank line

2. Example of a natural section break:
   "Tim Stenzel (FDA IVD Director):"
   "That's a good question. [answer content]"
   "Thank you for your question."
   "" (blank line) <-- This is where a delimiter should go
   "Coordinator: Our next question comes from..."

<< SECTION BREAK RULES >>
1. Add ONE delimiter at a blank line when these logical conditions are met:
   - A complete Q&A exchange has concluded (question asked and fully answered)
   - The conversation is transitioning to a new participant or topic
   - There's a natural pause in the dialogue

2. Key transition indicators:
   - After the opening remarks/introduction section ends
   - When the Coordinator introduces a new questioner
   - After a complete answer, before a new topic begins
   - When switching between distinct discussion topics
   - Before "Coordinator: Our next question comes from..."
   - After concluding remarks on one topic, before starting another

3. Do NOT add breaks:
   - Between back-and-forth clarifications within the same Q&A exchange
   - During ongoing discussion between the same participants
   - At every blank line (only at genuine topic transitions)
   - In pairs or groups (one break per transition)

Output format: Return the line numbers corresponding to natural section breaks: "[24, 33, 42, 51, ...]"

Remember: Focus on the natural flow of conversation and logical completion of topics. Each section should contain one complete thought or exchange.
"""
TOOLS_MEETING_SECTIONS_2 = [{
    "type": "function",
    "function": {
        "name": "analyze_meeting_sections",
        "description": "Analyze FDA town hall transcript to identify natural section breaks at topic transitions",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "line_numbers": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": """
                    List of line numbers where section breaks ('---') should be placed. Each number MUST:
                    1. Correspond to an existing blank line in the transcript
                    2. Mark a natural transition point between complete Q&A exchanges
                    3. Represent the end of one complete topic/discussion and the start of another
                    4. Follow the natural flow of conversation
                    
                    Only include breaks at genuine topic transitions and completed exchanges.
                    Each break should mark a clear shift in speaker or subject matter.
                    """
                }
            },
            "required": ["line_numbers"],
            "additionalProperties": False
        }
    }
}]
PROMPT_MEETING_SECTIONS_sonnet_rules = """
You are a precise transcript analyzer for FDA town hall meetings. Your task is to identify the exact line numbers where natural section breaks ('---') should be inserted in the transcript.

<< LINE COUNTING RULES >>
1. Count each line sequentially from the start of the transcript:
   - Every line break starts a new line number
   - Speaker identifications (e.g., "Coordinator:", "Tim Stenzel (FDA IVD Director):") count as their own line
   - Each paragraph of speech is its own line
   - All blank lines count in the line numbering
   - Delimiters will only be placed on existing blank lines

<< SECTION BREAK IDENTIFICATION RULES >>
1. Primary Break Points - Insert ONE delimiter when ALL these conditions are met:
   - A question has been completely answered by FDA representatives
   - The Coordinator is about to introduce the next speaker
   - There is a blank line available between these exchanges
   
2. Complete Q&A Exchange Structure:
   - Starts with Coordinator introducing a speaker
   - Contains the speaker's question
   - Includes FDA representative's complete response
   - May include brief clarifying exchanges
   - Ends before the next speaker introduction

3. Follow-up Question Handling:
   - Keep follow-up questions from the same speaker in the same section
   - Only add a break after the FDA representative has fully addressed all follow-ups
   - The entire exchange should stay together until the topic is complete

4. Special Cases:
   - Place a break after the opening remarks section concludes
   - Place a break after any lengthy FDA announcements or updates
   - Place a break when there's a clear shift to a new major topic
   - Place a break before the closing remarks begin

<< DO NOT ADD BREAKS >>
1. During active back-and-forth clarifications
2. Between a speaker's initial question and their follow-up
3. When the FDA representative is expanding on their previous answer
4. At random blank lines that don't represent true topic transitions
5. Between procedural exchanges (like asking for speaker affiliations)

<< OUTPUT REQUIREMENTS >>
- Return ONLY the line numbers where breaks should be inserted
- Each number MUST correspond to an existing blank line
- Numbers should be in ascending order
- Format: [24, 33, 42, 51, ...]

Remember: The goal is to create logical, complete sections that preserve the natural flow of conversation while making the transcript more readable and organized.
"""
TOOLS_MEETING_SECTIONS_sonnet_rules = [{
    "type": "function",
    "function": {
        "name": "analyze_meeting_sections",
        "description": "Analyze FDA town hall transcript to identify natural section breaks at complete Q&A transitions",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "line_numbers": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": """
                    List of line numbers for section breaks ('---'). Each number MUST:
                    1. Correspond to an existing blank line in the transcript
                    2. Come after a complete Q&A exchange (including any follow-ups)
                    3. Precede a new speaker introduction by the Coordinator
                    4. Represent a natural conversation break point
                    
                    Key placement criteria:
                    - After FDA representatives complete their response
                    - Before "Coordinator: Our next question comes from..."
                    - When one complete topic/discussion concludes
                    - Where there's a clear transition in subject matter
                    
                    The goal is to create logical, self-contained sections that each represent
                    a complete exchange while maintaining the natural flow of the conversation.
                    """
                }
            },
            "required": ["line_numbers"],
            "additionalProperties": False
        }
    }
}]
PROMPT_MEETING_SECTIONS = """
You are a precise transcript analyzer. Your task is to identify natural section breaks ('---') in FDA town hall transcripts based on conversation flow and speaker transitions.

<< COUNTING RULES >>
1. Count lines sequentially from the start of the transcript:
   - Each new line (marked by a line break) counts as one line
   - Speaker names like "Coordinator:" or "Tim Stenzel (FDA IVD Director):" count as their own line
   - Each paragraph of speech counts as its own line
   - Blank lines count as their own line number
   - The delimiter ('---') will replace an existing blank line

2. Example of a natural section break:
   "Tim Stenzel (FDA IVD Director):"
   "That's a good question. [answer content]"
   "Thank you for your question."
   "" (blank line) <-- This is where a delimiter should go
   "Coordinator: Our next question comes from..."

<< SECTION BREAK RULES >>
1. Add ONE delimiter at a blank line when these logical conditions are met:
   - A complete Q&A exchange has concluded (question asked and fully answered)
   - The conversation is transitioning to a new participant or topic
   - There's a natural pause in the dialogue

2. Key transition indicators:
   - After the opening remarks/introduction section ends
   - When the Coordinator introduces a new questioner
   - After a complete answer, before a new topic begins
   - When switching between distinct discussion topics
   - Before "Coordinator: Our next question comes from..."
   - After concluding remarks on one topic, before starting another

3. Do NOT add breaks:
   - Between back-and-forth clarifications within the same Q&A exchange
   - During ongoing discussion between the same participants
   - At every blank line (only at genuine topic transitions)
   - In pairs or groups (one break per transition)

4. Focus on the natural flow of conversation and logical completion of topics within the transcript.
   Each section should contain one complete thought or exchange.

Output format: Return the line numbers corresponding to natural section breaks in the form: "[24, 33, 42, 51, ...]"
"""
TOOLS_MEETING_SECTIONS = [{
    "type": "function",
    "function": {
        "name": "analyze_meeting_sections",
        "description": "Analyze a transcript to identify natural section breaks at topic transitions",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "line_numbers": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": """
                    List of line numbers where section breaks ('---') should be placed. Each number MUST:
                    1. Correspond to an existing blank line in the transcript
                    2. Mark a natural transition point between complete Q&A exchanges
                    3. Represent the end of one complete topic/discussion and the start of another
                    4. Follow the natural flow of conversation
                    
                    Only include breaks at genuine topic transitions and completed exchanges.
                    Each break should mark a clear shift in speaker or subject matter.
                    """
                }
            },
            "required": ["line_numbers"],
            "additionalProperties": False
        }
    }
}]
def fcall_meeting_sections(file_path, system_prompt=PROMPT_MEETING_SECTIONS, heading="### transcript"):
    """
    Analyze a transcript file using function calling to identify section break line numbers.

    :param file_path: string of the path to the file to analyze
    :param model: string specifying the OpenAI model to use
    :param system_prompt: string containing the system prompt for analysis
    :param heading: string specifying the heading to look for in the file
    :return: list of integers representing line numbers where section breaks should be placed
    """
    # Get the heading text and find the starting line number
    heading_text = get_heading(file_path, heading)
    heading_line_start = find_line_number_in_file(file_path, heading)
    
    # Get the response from OpenAI using function calling
    response = openai_function_call(system_prompt, heading_text, TOOLS_MEETING_SECTIONS)
    
    if response and "tool_calls" in response:
        try:
            # Extract and parse the function arguments
            arguments_json = response['tool_calls'][0]['function']['arguments']
            arguments = json.loads(arguments_json)
            
            # Get the line numbers and adjust them by the heading start line
            line_numbers = [num + heading_line_start for num in arguments['line_numbers']]
            return line_numbers
            
        except (KeyError, json.JSONDecodeError) as e:
            print(f"Error processing function call response: {str(e)}")
            return []
    
    print("No valid response received from function call")
    return []
def get_delimiter_line_numbers(file_path, heading="### transcript", delimiter="---"):
    # Get the heading text and find the starting line number
    transcript = get_heading(file_path, heading)
    
    # Count lines until we find the heading to get the correct line number
    heading_line_start = find_line_number_in_file(file_path, heading)
    #print(f"heading line start: {heading_line_start}")
    
    # Get line numbers relative to heading and add heading_line_start
    delimiter_line_numbers = [i + heading_line_start for i, line in enumerate(transcript.splitlines()) if delimiter in line]
    return delimiter_line_numbers


### QA EVAL
def validate_qa_transcript_positions(transcript, qa_dict):
    """
    Validate the extracted QA block against the original transcript based on reported positions.
    
    :param transcript: String of the full transcript text.
    :param qa_dict: Dictionary containing the extracted QA information.
    :return: Tuple of (bool, str) indicating pass/fail and a mismatch description if applicable.
    """
    start_pos = int(qa_dict['TRANSCRIPT START POSITION'].replace(',', ''))
    end_pos = int(qa_dict['TRANSCRIPT END POSITION'].replace(',', ''))
    
    original_text = transcript[start_pos:end_pos].strip()
    extracted_text = (qa_dict['VERBATIM QUESTION'] + ' ' + qa_dict['VERBATIM ANSWER']).strip()
    
    # Remove any newlines and extra spaces for comparison
    original_text = ' '.join(original_text.split())
    extracted_text = ' '.join(extracted_text.split())
    
    if original_text == extracted_text:
        return True, ""
    else:
        return False, f"Mismatch between original and extracted text.\n    ORIGINAL TRANSCRIPT: '{original_text}'\n    EXTRACTED VERBATIM: '{extracted_text}'"
def evaluate_qa_extraction(transcript, qa_file_path):
    """
    Evaluate the QA extraction process using LLM-based checks and position validation.
    
    :param transcript: String of the full transcript text.
    :param qa_file_path: String path to the file containing extracted QA blocks.
    :return: List of dictionaries containing evaluation results for each QA block.
    """
    from chalicelib.structured import get_all_fields_dict, count_blocks
    _, qa_content = read_metadata_and_content(qa_file_path)
    
    # Split the QA content into blocks, excluding empty blocks and those starting with '#'
    qa_blocks = [block for block in qa_content.split('\n\n') if block.strip() and not block.strip().startswith('#')]
    evaluation_results = []

    num_blocks = count_blocks(qa_file_path)
    
    for i, block in enumerate(qa_blocks, start=1):
        # if i == 4:  # Debug: Process only the first two blocks
        #     break
        qa_dict = get_all_fields_dict(block)
        
        # Perform position validation
        #print(f"DEBUG\n{qa_dict}")
        position_valid, mismatch_description = validate_qa_transcript_positions(transcript, qa_dict)
        
        # Prepare input for LLM evaluation
        eval_prompt = f"""
        Evaluate the following question-answer pair extracted from an FDA Town Hall transcript:
        
        Verbatim Question: {qa_dict['VERBATIM QUESTION']}
        Verbatim Answer: {qa_dict['VERBATIM ANSWER']}
        Clarified Question: {qa_dict['CLARIFIED QUESTION']}
        Clarified Answer: {qa_dict['CLARIFIED ANSWER']}
        
        Please evaluate based on the following criteria:
        1. Accuracy (0-5 scale): How well does the extracted information match the content and intent of the original transcript?
        2. Formatting (Pass/Fail): Are all texts on a single line without newline characters or speaker identifications?
        3. Topic Relevance (Pass/Fail): Do the extracted topics align with the content of the Q&A pair?
        
        Provide your evaluation in JSON format with the following structure:
        {{
            "accuracy_score": int,
            "formatting": "Pass" or "Fail",
            "topic_relevance": "Pass" or "Fail",
            "comments": "Any additional comments or explanations"
        }}
        """
        
        # Make LLM call for evaluation using openai_chat_completion_request
        messages = [
            {"role": "system", "content": "You are an expert evaluator of text extraction quality."},
            {"role": "user", "content": eval_prompt}
        ]
        response = openai_chat_completion_request(messages, model=OPENAI_MODEL)
        
        if isinstance(response, Exception):
            print(f"Error in LLM call: {response}")
            continue
        
        try:
            llm_evaluation = json.loads(response.json()['choices'][0]['message']['content'])
        except json.JSONDecodeError:
            print("Error: Unable to parse JSON from LLM response")
            continue
        except KeyError:
            print("Error: Unexpected response structure from LLM")
            continue
        
        # Combine all evaluation results
        evaluation_result = {
            "accuracy_score": llm_evaluation["accuracy_score"],
            "formatting": llm_evaluation["formatting"],
            "topic_relevance": llm_evaluation["topic_relevance"],
            "position_validation": "Pass" if position_valid else "Fail",
            "mismatch_description": mismatch_description,
            "llm_comments": llm_evaluation["comments"]
        }
        
        print(f"\nAuto Evaluation of block {i} of {num_blocks}")
        print(f"CLARIFIED QUESTION: {qa_dict['CLARIFIED QUESTION']}")
        print(evaluation_result)
        evaluation_results.append(evaluation_result)
    
    return evaluation_results
def generate_evaluation_report(evaluation_results, output_file):
    """
    Generate a readable report from the evaluation results.
    
    :param evaluation_results: List of dictionaries containing evaluation results.
    :param output_file: String path to write the report.
    """
    with open(output_file, 'w') as f:
        f.write("# QA Extraction Auto Evaluation Report\n\n\n")
        
        # Calculate and write summary statistics
        avg_accuracy = sum(r['accuracy_score'] for r in evaluation_results) / len(evaluation_results)
        formatting_pass = sum(1 for r in evaluation_results if r['formatting'] == "Pass")
        topic_relevance_pass = sum(1 for r in evaluation_results if r['topic_relevance'] == "Pass")
        position_validation_pass = sum(1 for r in evaluation_results if r['position_validation'] == "Pass")
        
        f.write("## Summary Statistics:\n")
        f.write(f"Average Accuracy Score: {avg_accuracy:.2f}/5\n")
        f.write(f"Formatting Pass Rate: {formatting_pass}/{len(evaluation_results)}\n")
        f.write(f"Topic Relevance Pass Rate: {topic_relevance_pass}/{len(evaluation_results)}\n")
        f.write(f"Position Validation Pass Rate: {position_validation_pass}/{len(evaluation_results)}\n\n\n")
        
        for i, result in enumerate(evaluation_results, 1):
            f.write(f"## QA Block {i}:\n")
            f.write(f"Accuracy Score: {result['accuracy_score']}/5\n")
            f.write(f"Formatting: {result['formatting']}\n")
            f.write(f"Topic Relevance: {result['topic_relevance']}\n")
            f.write(f"Position Validation: {result['position_validation']}\n")
            if result['mismatch_description']:
                f.write(f"Mismatch Description: {result['mismatch_description']}\n")
            f.write(f"LLM Comments: {result['llm_comments']}\n\n")
def run_automated_evaluation(transcript_file, qa_file):
    """
    Run the automated evaluation process.
    
    :param transcript_file: String path to the original transcript file.
    :param qa_file: String path to the file containing extracted QA blocks.
    """
    transcript = get_heading(transcript_file, "### transcript")
    transcript = transcript.lstrip('### transcript').rstrip('\n').lstrip('\n*')
    
    evaluation_results = evaluate_qa_extraction(transcript, qa_file)
    
    output_file = manage_file_overwrite(qa_file, "_autoeval", overwrite="no")
    generate_evaluation_report(evaluation_results, output_file)
    
    print(f"Evaluation completed. Report written to {output_file}")

PROMPT_QUESTION_ERRORS = """
Analyze the questions from interview transcripts which are in a question and answer format. Identify any questions ('questions' are the ones in 'QUESTIONS:' field, not in 'ANSWERS:', not in 'ORIGINAL QUESTION:', and not in 'NOTES') that exhibit one or more of the following problems:
1. Mentions 'David Deutsch' explicitly.
- Only flag questions that explicitly mention "David Deutsch".
2. Written in first-person.
- flag questions that use "I".
- some first-person questions may be acceptable if they are autobiographical and difficult to generalize without losing meaning.
3. Contains special characters.
- flag questions containing colons (:) or semicolons (;).
- do not flag if it does not contain any special characters at all.

Output format:
QUESTION: [Full text of the question]
PROBLEM TYPE(S): [List of applicable problem numbers]

Example Output:
QUESTION: How did David Deutsch feel about the New York Times book review on The Beginning of Infinity?
PROBLEM TYPE(S): Problem 1 (mentions 'David Deutsch' explicitly)

QUESTION: What would happen if I am unable to create new knowledge?
PROBLEM TYPE(S): Problem 2 (written in first-person)

If a question does not exhibit any of the specified problems, do not include it in the output. Only flag questions that genuinely need generalization.
Analyze all questions in the provided transcript and only output those that are problematic according to these criteria. Do not hallucinate. Do not include questions that don't even exist in the provided transcript.
"""
def create_question_errors_file(file_path, split_file_function, prompt, *args, **kwargs):
    """
    Creates a file containing corrected question-answer pairs from a QA fixed file.

    :param file_path: string of the path to the original file
    :param split_file_function: function used to separate the original file into blocks
    :param prompt: string of the prompt to process each block with
    :param args: additional positional arguments passed to the block separation function
    :param kwargs: additional keyword arguments passed to the block separation function
    :return: string of the path to the file with corrected question-answer pairs
    """
    blocks_file_path = split_file_function(file_path, *args, **kwargs)
    errors_file_path = scall_replace(blocks_file_path, prompt, retain_delimiters=True, suffix_new='_errors')
    delete_file(blocks_file_path)
    return errors_file_path

# ===== END OF FILE primary/llm.py =====
