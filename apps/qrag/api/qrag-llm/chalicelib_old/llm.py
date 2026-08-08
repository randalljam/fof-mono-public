import sys
import os
import json
import glob
import shutil
import warnings
import tiktoken
from termcolor import colored
from chalicelib.config import OPENAI_API_KEY_CONFIG_LLM, ANTHROPIC_API_KEY_CONFIG_LLM
import requests
from tenacity import retry, wait_random_exponential, stop_after_attempt
from chalicelib.fileops import *


warnings.formatwarning = custom_formatwarning
# USAGE: warnings.warn(f"Insert warning message here")

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir) # Add the parent directory to sys.path

os.environ["OPENAI_API_KEY_CONFIG_LLM"] = OPENAI_API_KEY_CONFIG_LLM  # updated 7-20-24 RT as new Project Key (User Keys have been replace by OpenAI for Project Keys but our old User Keys still work)
os.environ['ANTHROPIC_API_KEY'] = ANTHROPIC_API_KEY_CONFIG_LLM

# OpenAI model name - comment one out
#OPENAI_MODEL = "gpt-4o-mini"  # cost $0.15/$0.60, use instead of gpt3.5
OPENAI_MODEL = "gpt-4o" # cost $5/$15, use for all gpt4
ANTHROPIC_MODEL = "claude-3-5-sonnet-20240620"
# NOT IMPLEMENTED YET   ANT_LLM = "claude-3-5-sonnet"  # cost $3/$15 60% less gpt4o, not sure if works without -20240620

TOKEN_COST_DICT = {
    'gpt-4o':{'input_token_cost':5, 'output_token_cost':15}, # costs in $/million tokens
    'gpt-4-turbo':{'input_token_cost':10, 'output_token_cost':15},
    'gpt-3.5-turbo':{'input_token_cost':0.5, 'output_token_cost':1.5}
    }
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
def cost_llm_on_file(file_path, prompt, model, token_cost_dict, verbose=False, chunking_function=None, chunking_function_args=(), output_tokens_ratio=1, output_tokens_fixed=0):  # no unittests
    """
    Calculates the cost of processing a file using a language model, based on the number of input and output tokens.

    :param file_path: string of the path to the file to be processed.
    :param prompt: string of the prompt to be used for the language model.
    :param model: string of the name of the language model to be used.
    :param token_cost_dict: dictionary containing the cost per token for the input and output of the model.
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
    input_token_cost = token_cost_dict[model]['input_token_cost']
    output_token_cost = token_cost_dict[model]['output_token_cost']
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

    total_input_cost = (total_input_tokens / 1000000) * input_token_cost
    total_output_cost = (total_output_tokens / 1000000) * output_token_cost
    total_cost = total_input_cost + total_output_cost

    if verbose:
        print(file_path)
        print(f"File input tokens: {total_input_tokens:,} (Cost: ${input_token_cost:.4f}/1M tokens, Input token cost: ${total_input_cost:.2f})")
        print(f"File output tokens: {total_output_tokens:,} (Cost: ${output_token_cost:.4f}/1M tokens, Output token cost: ${total_output_cost:.2f})")
        print(f"File cost: ${total_cost:.2f}\n\n")

    return total_input_cost, total_output_cost, total_cost, total_input_tokens
def cost_llm_on_corpus(corpus_path, prompt, model, token_cost_dict, verbose=False, suffix_include=None, suffix_exclude=None, include_subfolders=False, chunking_function=None, chunking_function_args=(), output_tokens_ratio=1, output_tokens_fixed=0):
    """
    Calculates the cost of processing a corpus using a language model, based on the number of input and output tokens.

    :param corpus_path: string of the path to the corpus to be processed.
    :param prompt: string of the prompt to be used for the language model.
    :param model: string of the name of the language model to be used.
    :param token_cost_dict: dictionary containing the cost per token for the input and output of the model.
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
    
    file_paths = get_files_in_folder(corpus_path, suffix_include=suffix_include, suffix_exclude=suffix_exclude, include_subfolders=include_subfolders)
    
    for file_path in file_paths:
        file_input_cost, file_output_cost, file_cost, input_tokens = cost_llm_on_file(file_path, prompt, model, token_cost_dict, verbose, chunking_function, chunking_function_args, output_tokens_ratio, output_tokens_fixed)
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
    return f"Total tokens: {total_tokens:,}\n\n{result}"


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
    from primary.fileops import get_timestamp

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
def group_segments_token_cap(segments, token_cap=2000):
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
    from primary.fileops import read_metadata_and_content, write_metadata_and_content

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
    from primary.fileops import read_metadata_and_content, write_metadata_and_content

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
    from primary.fileops import read_metadata_and_content, write_metadata_and_content

    metadata, _ = read_metadata_and_content(file_path)
    segments = get_speaker_segments(file_path, skip_string)
    #print(f"\nDEBUG separate segments: {segments}")
    grouped_segments = group_segments_token_cap(segments, token_cap)
    new_content = "## content\n\n" + BLOCK_DELIMITER.join(grouped_segments)  # Using the global variable BLOCK_DELIMITER  
    return write_metadata_and_content(file_path, metadata, new_content, suffix_new, overwrite='no')


### OPENAI LLM
def test_openai_chat(model=OPENAI_MODEL):# DS, cat 5, unittests 2 APIMOCK
    """
    Sends a predefined message to the OpenAI chat API and prints the response.

    :param model: string of the model name to be used for the chat completion request
    :return: None
    """
    try:
        messages = [{"role": "user", "content": "Tell me a knock knock joke about science."}]
        response = openai_chat_completion_request(messages, model=model)
        if response:
            print("API chat response:", response.text)
    except Exception as e:
        print(f"Failed to access the OpenAI API: {e}")
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
        "Authorization": "Bearer " + OPENAI_API_KEY_CONFIG_LLM,  # Use the imported API key instead of this way "openai.api_key,"
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
# TODO: refactor so calls openai_chat_completion_request, rename
def simple_openai_chat_completion_request(prompt, model):  # no unittests
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + OPENAI_API_KEY_CONFIG_LLM,  # Use the imported API key instead of this way "openai.api_key,"
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
def openai_function_call(fcall_prompt, content, tools, verbose=False):  # APIMOCK unittests 3
    """
    Sends a prompt and content to the OpenAI LLM and returns the assistant's message.

    :param prompt_system: string of the system's prompt to initiate the conversation
    :param content: string of the user's content to process
    :param tools: list of dictionaries containing tool configurations
    :param verbose: boolean indicating whether to print detailed response text
    :return: string of the assistant's message from the LLM response
    """
    messages = [{"role": "system", "content": fcall_prompt}, {"role": "user", "content": content}]
    verbose_print(verbose, "OPENAI_MODEL = " + OPENAI_MODEL)
    chat_response = openai_chat_completion_request(messages, tools=tools)

    verbose_print(verbose, "Response Status Code:", chat_response.status_code)
    verbose_print(verbose, "Response Text:", chat_response.text)

    assistant_message = None  # Initialize to None or a sensible default
    try:
        assistant_message = chat_response.json()["choices"][0]["message"]
        messages.append({"role": "assistant", "content": assistant_message})
        if verbose:
            pretty_print_function(messages, tools)
        # print(f"DEBUG openai_function_call print full messages:\n {messages}")
    except Exception as e:
        print("Error parsing response:", e)
    return(assistant_message)


### ANTHROPIC LLM
def anthropic_chat_completion_request(messages, model=ANTHROPIC_MODEL, system=None, max_tokens=4096, temperature=0.7):
    """
    Make a chat completion request to Anthropic's API.

    :param messages: List of message objects representing the conversation
    :param model: The model to use for the completion
    :param system: System message to set the behavior of the assistant
    :param max_tokens: Maximum number of tokens to generate (default: 4096)
    :param temperature: Controls randomness in the output (0 to 1, default: 0.7)
    :return: The generated message content or None if an error occurs
    """
    # Initialize the client
    client = anthropic.Anthropic()

    # Prepare the request parameters
    request_params = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    # Add system message if provided
    if system:
        request_params["system"] = system

    # Add messages if provided, otherwise raise an exception
    if messages:
        request_params["messages"] = messages
    else:
        raise ValueError("No messages were provided for Anthropic chat completion request.")

    try:
        # Make the API call
        message = client.messages.create(**request_params)

        # Return the content of the message
        return message.content[0].text
    except anthropic.APIError as e:
        print(f"Anthropic API error: {str(e)}")
    except anthropic.APIConnectionError as e:
        print(f"Error connecting to Anthropic API: {str(e)}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
    
    return None
def simple_anthropic_chat_completion_request(prompt, model=ANTHROPIC_MODEL):
    """
    Make a simple chat completion request to Anthropic's API.

    :param prompt: String containing the user's prompt or message
    :param model: String specifying the Anthropic model to use (default: "claude-3-opus-20240229")
    :return: String containing the generated message content, or an error message if the request fails
    """
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": os.environ['ANTHROPIC_API_KEY'],
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
    from primary.fileops import read_metadata_and_content, write_metadata_and_content
    
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
    from primary.fileops import delete_file

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


PROMPT_SUMMARIZE = """
summaize the text after the speaker line as 3 keywords that best captures what is said, returned as a single line with commas between the words. retain the speaker line exactly as it is and put the new key word line as the next line directly underneath"""
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

### COPYEDIT
PROMPT_COPYEDIT = """
copyedit the text WIP"""
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
    from primary.fileops import delete_file
    
    blocks_file_path = split_file_function(file_path, *args, **kwargs)
    copyedit_file_path = scall_append(blocks_file_path, prompt, retain_delimiters=True, suffix_new='_copyedit')
    delete_file(blocks_file_path)
    return copyedit_file_path

### SPEAKER SEGMENT TRANSITIONS
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
    from primary.fileops import read_metadata_and_content, write_metadata_and_content

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
    from primary.fileops import delete_file
    adjacent_words = 10

    blocks_file_path = split_file_function(file_path, *args, **kwargs)
    transitions_file_path = scall_replace_adjacent_words(blocks_file_path, prompt, adjacent_words, retain_delimiters=True, suffix_new='_transitions')
    delete_file(blocks_file_path)
    return transitions_file_path

### QA EXTRACTION
FCALL_PROMPT_QA_DIALOGUE_STATEDQA = """
You are an expert text analyzer that is trained in identifying stated questions and answers in transcripts of dialogue. You will be given blocks of dialogue and your role is to return extracted question and answer pairs that faithfully capture the meaningful content in the dialogue, while removing filler words and minimally modifying the text for clarity and readability. You will use your tool to only return exact JSON in the format specified.
"""
FCALL_PROMPT_QA_DIALOGUE_FROMANSWER = """
You are an expert text analyzer that is trained in identifying questions or implied questions. You will be given dialogue and your role is to return a create a general, simple question from the provided answer. This created general question may or may not be related to the question actually asked by the speaker in the dialogue preceding the answer. The created general question will be part of a question and answer set used for Retrieval Augmented Generation. The question must not mention the speaker name. You will use your tool to only return exact JSON in the format specified.
"""
CUSTOM_INSTRUCTIONS_DEUTSCH_GENERALQ = """
Analyze the following passage and create a general, simple question for which the answer will be the response. This will be part of a question and answer set such that new questions are compared against the questions, and answers retrieved. The question should not mention the author, or David Deutsch. The question should be written in such a way that it assumes that the answer provided is the best knowledge humanity has about this topic at present moment. Some specific phrases to use include:

'multiverse quantum theory' - rather than 'many-worlds interpretation of quantum'"""
# TODO modify to use the FCALL_PROMPT_QA_DIALOGUE_FROMANSWER above
def tools_qa_speaker(speaker):  # no unittests
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
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description":f"""
                    The question should capture the essence of the original query posed by the interviewer in a simplified, generic form. It should focus on the core topic or idea, removing extraneous contextual details. The modified question should have semantic alignment with {speaker}'s answer. The question should be rephrased for a third-person audience, ensuring it is generalized and does not include direct references to {speaker}. DO NOT mention the name {speaker} in the question. The question should be written in such a way that it assumes that the answer provided is the best knowledge humanity has about this topic at present moment.  Some specific phrases to use include: 1) 'multiverse quantum theory' - rather than 'many-worlds interpretation of quantum'.
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
    from primary.fileops import read_metadata_and_content, add_timestamp_links
    from primary.fileops import sub_suffix_in_str, set_last_updated, write_metadata_and_content

    print("***Running fcall_qa on file: " + block_file_path)
    
    metadata, block_content = read_metadata_and_content(block_file_path)
    metadata = set_last_updated(metadata, 'Created QA')

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

FCALL_SYSTEM_PROMPT_QA_INCREMENTAL_TRANSCTIPRT_FDA_TOWNHALLS_1ST_DRAFT = """
    You are an expert text analyzer trained in identifying questions and answers in transcripts of dialogue. 
    Your role is to extract and clarify the next question-answer pair from the given transcript chunk.
    The previous question-answer pair is provided in both the original text verbatim version and in a modified clarified version.

    Your task is identify the next important information that comes after the previous question-answer pair. This important information may comprise an explicit question asked by a speaker, or it may not and instead be a standalone statement.
    A requirement for qualification as important information of a next question-answer pair is that it is not included in the verbatim_answer property of the provided previous question answer pair.
     
    Identify the speakers for both questions and answers. Speakers are identified on separate lines of text that precede the speaker dialogue. The speaker lines end in either just a colon, or a timestamp which optionally be followed by a timestamp link. Speaker lines will start with the speaker name, or a surrogate string such as 'Moderator'. The speaker name may be followed by a role provided in parentheses. The role may comprise or contain text that specifies that speaker as an 'Authority Speaker'. See below for the text that specifies Authority Speakers.
    
    If important information is provided by a speaker identified as an Authority Speaker (see below), and that important information is not explicitly asked as a question, then you will generate a clarified question that is the best suitable question to be paired with that important information. The important information will be considered the answer. If a statement is made by a Non-Authority Speaker, and that statement is not phrased as a question, then it must be acknowledged by an Authority Speaker with an explicit affirmation response. See property descriptions below for values to use in this case where there is no explicit verbatim question.

    You will extract both the verbatim_answer from the transcript text, and then process the verbatim_answer to create the clarified_answer. The clarified_answer may be similar or perhaps even identical to the verbatim_answer from the transcript text. Typically the clarified answer wil be modified and therefore different at least to some extent from the verbatim_answer, however the clarified_answer must NEVER contradict the corresponding verbatim_answer and must ALWAYS have the same meaning. You will create the clarified versions of the question and answer by removing filler words to improve clarity and readability.

    This specific corpus comprises transcripts of the dialogue from virtual townhall meetings held by the United States Food and Drug Administration (FDA) to help answer technical questions about the development and validation of tests for the virus SARS-CoV2, and the updated policy on COVID-19 diagnostics policy for diagnostics test for coronavirus disease 2019 during the public health emergency caused by the COVID-19 global pandemic.

    Authority Speakers in this FDA Townhall Transcript Corpus are specified by the inclusion of the string ‘FDA’ in the role portion of the speaker line.

    The criteria for qualification for important information to be extracted as question-answer pairs is that the information be technical in nature, procedural, or legal. Information that should not be considered important and excluded from the question-answer extraction process is information related to the orchestration of the call such as which caller or speaker is being selected by the moderator. Information, whether questions by call-in speakers or answers by FDA staff, that is related to whether the FDA authorities can answer the question are considered to be legal and always to be included. These typical include answers from the FDA Authority Speakers similar to ‘we are not able to respond to questions about specific submissions that might be under review’. If you are not sure whether information qualifies as important information, then includeit and set the review_flag property of the response to True.
    """

FCALL_SYSTEM_PROMPT_QA_INCREMENTAL_TRANSCTIPRT_FDA_TOWNHALLS = """
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

def tools_qa_incremental():
    return [{
        "type": "function",
        "function": {
            "name": "extract_qa",
            "description": "Extract and clarify the next question-answer pair from an FDA Town Hall transcript chunk",
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
                "required": ["clarified_question", "clarified_answer", "verbatim_question", "verbatim_answer", "speaker_question", "speaker_answer", "relative_end_position", "topics", "review_flag"]
            }
        }
    }]

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

def fcall_qa_incremental(transcript, next_tokens, fcall_prompt, start_position):
    """
    Processes a transcript string incrementally to extract the next question-answer pair using OpenAI function calling.
    This function yields each QA block along with the current position in the transcript, allowing for incremental processing and resumption from the last processed position.  

    :param transcript: String of the transcript content.
    :param next_tokens: Integer of the number of tokens to look ahead.
    :param fcall_prompt: String of the prompt to be used for function calling.
    :param start_position: Integer of the starting position in the transcript.
    :yield: Tuple of (qa_block, current_position) or (None, current_position) if an error occurred.
    """
    current_position = start_position
    previous_block = None
    total_chars_transcript = len(transcript)

    while current_position < len(transcript):
        chunk, next_position = get_next_chunk(transcript, current_position, next_tokens)
        print(f"chunk transcript positions:        {current_position:,} to {next_position:,} of total: {total_chars_transcript:,} | Percent done: {round(current_position / total_chars_transcript * 100)}%")
        
        prev_block_prompt = "Please identify the first question-answer pair in the following transcript chunk:" if not previous_block else f"""
        Previous Question-Answer Block:
        {previous_block}
        Please identify the next question-answer pair after this one in the following transcript chunk:
        """

        full_prompt = fcall_prompt + "\n" + prev_block_prompt + "\n\n" + chunk
        
        try:
            qa_response = openai_function_call(full_prompt, chunk, tools_qa_incremental())
            arguments = json.loads(qa_response['tool_calls'][0]['function']['arguments'])
            
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
            
            print(f"qa response transcript position: {abs_transcript_start_pos:,} to {abs_transcript_end_pos:,}")
            # Update previous_block for the next iteration
            previous_block = qa_block
            
            yield qa_block, abs_transcript_start_pos
        except Exception as e:
            print(f"Error in qa extraction: {str(e)}")
            yield None, current_position
        
        current_position = abs_transcript_start_pos

def create_qa_file_from_transcript_incremental(file_path, fcall_prompt):
    """
    Manages the incremental extraction of question-answer pairs from a transcript file.
    This function handles the overall process, including reading the transcript, determining the next chunk to process, and appending the extracted QA blocks to a new file.

    :param file_path: String of the path to the transcript file to be processed.
    :param fcall_prompt: String of the prompt to be used for function calling.
    :return: String of the path to the newly created QA file.
    """
    from primary.structured import count_blocks

    metadata, content = read_metadata_and_content(file_path)
    metadata = set_last_updated(metadata, 'Created QA Incremental')
    metadata = set_metadata_field(metadata, "source file", file_path)
    
    print("OPENAI_MODEL = " + OPENAI_MODEL)
    segment_tokens = count_segment_tokens(file_path)
    max_segment_tokens = max(segment_tokens)
    transcript = get_heading(file_path, "### transcript")
    transcript = transcript.lstrip('### transcript').rstrip('\n').lstrip('\n*')
    print(f"Number of characters in transcript: {len(transcript):,}\n")

    initial_content = "## content\n\n### qa\n"
    qa_file_path = write_metadata_and_content(file_path, metadata, initial_content, overwrite='no-sub', suffix_new='_qa-incremental')
    
    current_position = 0
    max_retries = 5

    while current_position < len(transcript):
        existing_blocks = count_blocks(qa_file_path)
        block_number = existing_blocks + 1
        
        for qa_block, abs_transcript_start_pos in fcall_qa_incremental(transcript, max_segment_tokens, fcall_prompt, start_position=current_position):
            retry_count = 0
            while retry_count < max_retries:
                try:
                    if qa_block is None:
                        raise Exception(f"Error occurred on block {block_number}.")
                    
                    print(f"writing block number {block_number}\n")
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
    from primary.structured import get_all_fields_dict
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
