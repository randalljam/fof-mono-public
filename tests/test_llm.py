# Run tests with python -m unittest discover -s tests

import os
import shutil
import sys
import tempfile
# Add the parent directory to the Python path so we can import the 'core' module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import unittest
from unittest.mock import patch, Mock, mock_open, MagicMock, call
from termcolor import colored

from core.fileops import *
from core.llm import *

from dotenv import load_dotenv
load_dotenv(override=True)  # Load environment variables from .env file

from dotenv import load_dotenv
load_dotenv(override=True)  # Load environment variables from .env file
OPENAI_API_KEY = os.environ["OPENAI_API_KEY_LOCAL"]

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "test_data_files")

### PRINT AND TOKENS
class TestPrettyPrintFunction(unittest.TestCase):
    def setUp(self):
        # Example setup for messages and tools
        self.messages = [
            {
                "role": "system",
                "content": "\nYou are an expert text analyzer that is trained in identifying questions or implied questions. You will be given dialogue and your role is to return a question that would make sense to ask, or was asked that is best answered by the final text block in the dialogue. You will use your tool to only return exact JSON in the format specified.\n"
            },
            {
                "role": "user",
                "content": "David Deutsch [4:12](https://www.youtube.com/watch?v=SDZ454K_lBY&t=252)\nThe multiverse theory comes about as an explanation of the predictions of our best theory of physics, which is quantum mechanics. Quantum mechanics makes very accurate predictions, the most accurate predictions that any theory of physics has ever made. But if you want to explain why these predictions are so, how these physical events come about, there's no alternative but to postulate that what we see around us is not the whole of reality, that reality is much more varied and has a great multiplicity. This is what we call multiple universes."
            },
            {
                "role": "assistant",
                "content": {
                    "tool_calls": [
                        {
                            "type": "function",
                            "function": {
                                "name": "get_qa",
                                "arguments": '{"question":"What is the basis for the existence of multiple universes according to quantum mechanics?","timestamp":"4:12"}'
                            }
                        }
                    ]
                }
            }
        ]
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "TestFunction",
                    "description": "This is a test function.",
                    "parameters": {
                        "properties": {
                            "param1": {
                                "description": "This is the first parameter."
                            },
                            "param2": {
                                "description": "This is the second parameter."
                            }
                        }
                    }
                }
            }
        ]

    def test_pretty_print_function_with_prompts(self):
        output = pretty_print_function(self.messages, self.tools, print_prompts=True, print_input=True)
        # print(f"DEBUG output[0] = {output[0]}")
        # print(f"DEBUG output[1] = {output[1]}")
        # print(f"DEBUG output[2] = {output[2]}")
        self.assertIn("System Prompt:", output[0])
        self.assertIn("User Input:", output[1])
        self.assertIn("Function Parameters Responses:", output[2])

    def test_pretty_print_function_without_prompts(self):
        output = pretty_print_function(self.messages, self.tools, print_prompts=False, print_input=True)
        self.assertEqual("", output[0])  # No system prompts
        self.assertIn("User Input:", output[1])
        self.assertIn("Function Parameters Responses:", output[2])
    
class TestPrettyPrintFunctionDescriptions(unittest.TestCase):
    def test_pretty_print_function_descriptions(self):
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "TestFunction",
                    "description": "This is a test function.",
                    "parameters": {
                        "properties": {
                            "param1": {
                                "description": "This is the first parameter."
                            },
                            "param2": {
                                "description": "This is the second parameter."
                            }
                        }
                    }
                }
            }
        ]
        print_color = "blue"  # Example color

        # Expected output generation
        expected_output = ""
        for tool in tools:
            if tool["type"] == "function":
                function_name = f"Function Name: {tool['function']['name']}\n"
                function_description = f"Function Description: {tool['function']['description']}\n"
                expected_output += function_name + function_description
                expected_output += "Function Parameter Descriptions:\n\n"
                properties = tool['function']['parameters']['properties']
                for prop, details in properties.items():
                    prop_description = f"  {prop}: {details['description'].strip()}\n"
                    expected_output += prop_description
                #expected_output += '\n'  # Ensure there is a newline after each property description

        # Call the function to test
        output_str = pretty_print_function_descriptions(tools, print_color)
        # print(f"\nDEBUG returned: {repr(output_str)}")
        # print(f"\nDEBUG expected: {repr(expected_output)}")
        
        # Compare the function output with the expected output
        self.assertEqual(output_str.strip(), expected_output.strip())


### SPLIT FILES
class TestGetLineNumbersWithMatch(unittest.TestCase):
    def setUp(self):
        # Setup method to create a temporary test file
        self.test_filename = 'test_file.md'
        self.test_content = """Start
---
This is a test file.
---
It contains multiple lines.
---
Some of which match a given string.
---
"""
        with open(self.test_filename, 'w') as f:
            f.write(self.test_content)

    def tearDown(self):
        # Teardown method to remove the temporary test file
        os.remove(self.test_filename)

    def test_get_line_numbers_with_match__match_found(self):
        # Test case where the match string is found in the file
        match_str = '---'
        expected_line_numbers = [2, 4, 6, 8]
        self.assertEqual(get_line_numbers_with_match(self.test_filename, match_str), expected_line_numbers)

    def test_get_line_numbers_with_match__no_match(self):
        # Test case where the match string is not found in the file
        match_str = 'not found'
        self.assertEqual(get_line_numbers_with_match(self.test_filename, match_str), [])

    def test_get_line_numbers_with_match__file_does_not_exist(self):
        # Test case where the file does not exist
        with self.assertRaises(ValueError):
            get_line_numbers_with_match('nonexistent_file.md', '---')

class TestGetSpeakerSegments(unittest.TestCase):
    def setUp(self):
        # Setup method to create a temporary test file before each test
        self.test_file_name = 'test_speaker_segments.md'
        self.test_header = """## metadata
last updated: 11-19-2023

## content

### transcript

"""
        self.test_segskip = """Charles Bédard  [0:00](https://www.youtube.com/watch?v=CluVy2jICgs&t=0)  SKIPQA
So welcome everyone"""
        self.test_seg0 = """David Deutsch  [1:14](https://www.youtube.com/watch?v=CluVy2jICgs&t=74)
Well, it's no."""
        self.test_seg1 = """Charles Bédard  [1:18](https://www.youtube.com/watch?v=CluVy2jICgs&t=78)
Yeah, yeah, yeah"""
        self.test_seg2 = """David Deutsch  [14:42](https://www.youtube.com/watch?v=CluVy2jICgs&t=882)
Well, I think"""
        self.test_text = self.test_header + self.test_segskip + '\n\n' + self.test_seg0 + '\n\n' + self.test_seg1 + '\n\n' + self.test_seg2 + '\n\n'
        # print(f"DEBUG test text: {self.test_text}")
        with open(self.test_file_name, 'w') as f:
            f.write(self.test_text)

    def tearDown(self):
        # Teardown method to remove the temporary test file after each test
        os.remove(self.test_file_name)

    def test_get_speaker_segments__default_skip_string(self):
        # Test retrieving segments without the skip string
        segments = get_speaker_segments(self.test_file_name)
        expected_segments = [self.test_seg0, self.test_seg1, self.test_seg2]
        self.assertEqual(segments, expected_segments)

    def test_get_speaker_segments__with_different_skip_string(self):
        # Test retrieving segments with a different skip string that is not present
        segments = get_speaker_segments(self.test_file_name, 'NOSUCHSTRING')
        expected_segments = [self.test_segskip, self.test_seg0, self.test_seg1, self.test_seg2]
        self.assertEqual(segments, expected_segments)

class TestGroupSegmentsSelectSpeaker(unittest.TestCase):
    def setUp(self):
        # Setup test segments
        self.segments = [
            "Charles Bédard  [1:00](https://www.youtube.com/watch?v=CluVy2jICgs&t=0)\nI have questions.",
            "David Deutsch  [1:14](https://www.youtube.com/watch?v=CluVy2jICgs&t=74)\nWell, it's no.",
            "Charles Bédard  [1:18](https://www.youtube.com/watch?v=CluVy2jICgs&t=78)\nYeah, yeah, yeah",
            "Extra Dude  [1:34](https://www.youtube.com/watch?v=CluVy2jICgs&t=78)\nHi mom",
            "David Deutsch  [14:42](https://www.youtube.com/watch?v=CluVy2jICgs&t=882)\nWell, I think"
        ]

    def test_group_segments_select_speaker__for_deutsch(self):
        # Test filtering segments for David Deutsch
        returned_segments = group_segments_select_speaker(self.segments, 'David Deutsch')
        expected_segments = [
            "Charles Bédard  [1:00](https://www.youtube.com/watch?v=CluVy2jICgs&t=0)\nI have questions.\n\nDavid Deutsch  [1:14](https://www.youtube.com/watch?v=CluVy2jICgs&t=74)\nWell, it's no.",
            "Charles Bédard  [1:18](https://www.youtube.com/watch?v=CluVy2jICgs&t=78)\nYeah, yeah, yeah\n\nExtra Dude  [1:34](https://www.youtube.com/watch?v=CluVy2jICgs&t=78)\nHi mom\n\nDavid Deutsch  [14:42](https://www.youtube.com/watch?v=CluVy2jICgs&t=882)\nWell, I think"
        ]
        self.assertEqual(returned_segments, expected_segments)

    def test_group_segments_select_speaker__for_bedard(self):
        # Test filtering segments for Charles Bédard
        returned_segments = group_segments_select_speaker(self.segments, 'Charles Bédard')
        expected_segments = [
            "Charles Bédard  [1:00](https://www.youtube.com/watch?v=CluVy2jICgs&t=0)\nI have questions.",
            "David Deutsch  [1:14](https://www.youtube.com/watch?v=CluVy2jICgs&t=74)\nWell, it's no.\n\nCharles Bédard  [1:18](https://www.youtube.com/watch?v=CluVy2jICgs&t=78)\nYeah, yeah, yeah"
        ]
        # print(f"\nDEBUG returned_segments: {repr(returned_segments)}")
        # print(f"\nDEBUG expected_segments: {repr(expected_segments)}")
        self.assertEqual(returned_segments, expected_segments)

class TestGroupSegmentsTokenCap(unittest.TestCase):
    def setUp(self):
        self.segments = [
            "Charles Bédard  [1:00](https://www.youtube.com/watch?v=CluVy2jICgs&t=0)\nThis is a short segment.",  # Assume 5 words = 3.75 tokens
            "David Deutsch  [1:14](https://www.youtube.com/watch?v=CluVy2jICgs&t=74)\nThis segment is a bit longer than the previous one, but still not too long.",  # Assume 14 words = 10.5 tokens
            "Charles Bédard  [1:18](https://www.youtube.com/watch?v=CluVy2jICgs&t=78)\nThis is another short segment.",  # Assume 5 words = 3.75 tokens
            "Extra Dude  [1:34](https://www.youtube.com/watch?v=CluVy2jICgs&t=78)\nThis segment is extremely long and definitely exceeds the token cap on its own by having a huge amount of words that no other segment has.",  # Assume 28 words = 21 tokens
            "David Deutsch  [14:42](https://www.youtube.com/watch?v=CluVy2jICgs&t=882)\nFinal short segment to test grouping."  # Assume 7 words = 5.25 tokens
        ]

    def test_group_segments_token_cap__above_all_cap(self):
        # Test grouping segments without any single segment exceeding the token cap
        token_cap = 1000  # above all combined
        returned_segments = group_segments_token_cap(self.segments, token_cap)
        expected_segments = [
            "Charles Bédard  [1:00](https://www.youtube.com/watch?v=CluVy2jICgs&t=0)\nThis is a short segment.\n\nDavid Deutsch  [1:14](https://www.youtube.com/watch?v=CluVy2jICgs&t=74)\nThis segment is a bit longer than the previous one, but still not too long.\n\nCharles Bédard  [1:18](https://www.youtube.com/watch?v=CluVy2jICgs&t=78)\nThis is another short segment.\n\nExtra Dude  [1:34](https://www.youtube.com/watch?v=CluVy2jICgs&t=78)\nThis segment is extremely long and definitely exceeds the token cap on its own by having a huge amount of words that no other segment has.\n\nDavid Deutsch  [14:42](https://www.youtube.com/watch?v=CluVy2jICgs&t=882)\nFinal short segment to test grouping."
        ]
        # print(f"\nDEBUG returned_segments: {repr(returned_segments)}")
        # print(f"\nDEBUG expected_segments: {repr(expected_segments)}")
        # self.assertEqual(returned_segments, expected_segments)

    def test_group_segments_token_cap__intermediate_cap(self):
        # Test grouping segments without any single segment exceeding the token cap
        token_cap = 50  # above all combined
        returned_segments = group_segments_token_cap(self.segments, token_cap)
        expected_segments = [
            "Charles Bédard  [1:00](https://www.youtube.com/watch?v=CluVy2jICgs&t=0)\nThis is a short segment.\n\nDavid Deutsch  [1:14](https://www.youtube.com/watch?v=CluVy2jICgs&t=74)\nThis segment is a bit longer than the previous one, but still not too long.\n\nCharles Bédard  [1:18](https://www.youtube.com/watch?v=CluVy2jICgs&t=78)\nThis is another short segment.\n\nExtra Dude  [1:34](https://www.youtube.com/watch?v=CluVy2jICgs&t=78)\nThis segment is extremely long and definitely exceeds the token cap on its own by having a huge amount of words that no other segment has.",
            "David Deutsch  [14:42](https://www.youtube.com/watch?v=CluVy2jICgs&t=882)\nFinal short segment to test grouping."
        ]
        # print(f"\nDEBUG returned_segments: {repr(returned_segments)}")
        # print(f"\nDEBUG expected_segments: {repr(expected_segments)}")
        # self.assertEqual(returned_segments, expected_segments)

    def test_group_segments_token_cap__low_cap(self):
        # Test grouping segments without any single segment exceeding the token cap
        token_cap = 20  # above all combined
        returned_segments = group_segments_token_cap(self.segments, token_cap)
        expected_segments = [
            "Charles Bédard  [1:00](https://www.youtube.com/watch?v=CluVy2jICgs&t=0)\nThis is a short segment.\n\nDavid Deutsch  [1:14](https://www.youtube.com/watch?v=CluVy2jICgs&t=74)\nThis segment is a bit longer than the previous one, but still not too long.",
            "Charles Bédard  [1:18](https://www.youtube.com/watch?v=CluVy2jICgs&t=78)\nThis is another short segment.", 
            "Extra Dude  [1:34](https://www.youtube.com/watch?v=CluVy2jICgs&t=78)\nThis segment is extremely long and definitely exceeds the token cap on its own by having a huge amount of words that no other segment has.",
            "David Deutsch  [14:42](https://www.youtube.com/watch?v=CluVy2jICgs&t=882)\nFinal short segment to test grouping."
        ]
        # print(f"\nDEBUG returned_segments: {repr(returned_segments)}")
        # print(f"\nDEBUG expected_segments: {repr(expected_segments)}")
        # self.assertEqual(returned_segments, expected_segments)

    def test_group_segments_token_cap__empty_segments(self):
        # Test handling of empty segments list
        grouped_segments = group_segments_token_cap([], 100)
        self.assertEqual(grouped_segments, [])

class TestSeparateBlocksSelectSpeaker(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_filepath = os.path.join(self.temp_dir.name, "dialogue.md")
        shutil.copyfile(
            os.path.join(TEST_DATA_DIR, "llm", "dialogue.md"),
            self.test_filepath,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_split_file_select_speaker(self):
        # Test adding block delimiters after a specific speaker
        speaker = "Test Expert"
        new_file_path = split_file_select_speaker(self.test_filepath, speaker)
        expected_line_numbers = [10, 16]
        self.assertEqual(get_line_numbers_with_match(new_file_path, '---'), expected_line_numbers)

class TestSeparateBlocksEverySpeaker(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_filepath = os.path.join(self.temp_dir.name, "dialogue.md")
        shutil.copyfile(
            os.path.join(TEST_DATA_DIR, "llm", "dialogue.md"),
            self.test_filepath,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_split_file_every_speaker(self):
        # Test adding block delimiters after a specific speaker
        new_file_path = split_file_every_speaker(self.test_filepath)
        expected_line_numbers = [10, 13, 16, 19, 22]
        self.assertEqual(get_line_numbers_with_match(new_file_path, '---'), expected_line_numbers)

class TestSeparateBlocksTokenCap(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_filepath = os.path.join(self.temp_dir.name, "dialogue.md")
        shutil.copyfile(
            os.path.join(TEST_DATA_DIR, "llm", "dialogue.md"),
            self.test_filepath,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_split_file_token_cap(self):
        # Test adding block delimiters after a specific speaker
        new_file_path = split_file_token_cap(self.test_filepath, token_cap=20)
        expected_line_numbers = [13, 16]
        self.assertEqual(get_line_numbers_with_match(new_file_path, '---'), expected_line_numbers)


### LLM SIMPLE
class TestAPIMOCKOpenAIChatCompletionRequest(unittest.TestCase):
    def setUp(self):
        # Mock data for the tests
        self.messages = [{"role": "user", "content": "Hello, world!"}]
        self.tools = ["tool1", "tool2"]
        self.tool_choice = "tool1"
        self.model = OPENAI_MODEL
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + OPENAI_API_KEY,
        }
        self.json_data = {
            "model": self.model,
            "messages": self.messages,
            "tools": self.tools,
            "tool_choice": self.tool_choice,
        }

    @patch('requests.post')
    def test_openai_chat_completion_request__success(self, mock_post):
        # Mock the requests.post to simulate a successful API call
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        # Call the function
        response = openai_chat_completion_request(self.messages, self.tools, self.tool_choice, self.model)
        # Assertions to ensure the function behaved as expected
        mock_post.assert_called_once_with(
            "https://api.openai.com/v1/chat/completions",
            headers=self.headers,
            json=self.json_data
        )
        self.assertEqual(response, mock_response)

    @patch('requests.post')
    def test_openai_chat_completion_request__failure(self, mock_post):
        # Mock the requests.post to simulate an exception
        mock_post.side_effect = Exception("API request failed")
        # Execute the function under test
        response = openai_chat_completion_request(self.messages, self.tools, self.tool_choice, self.model)
        # Assertions to check how the function handles the exception
        self.assertIsInstance(response, Exception)
        self.assertEqual(str(response), "API request failed")

class TestAPIMOCKTestOpenAIChat(unittest.TestCase):
    def setUp(self):
        # Mock data used for testing
        self.model = OPENAI_MODEL

    @patch('core.llm.openai_chat_completion_request')
    @patch('builtins.print')
    def test_openai_chat__success(self, mock_print, mock_chat_request):
        # Set up a mock response object
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{
                'message': {'content': "Knock knock! Who's there? Science joke."}
            }]
        }
        mock_chat_request.return_value = mock_response
        # Execute the function
        test_openai_chat(model=self.model)
        # Assertions to ensure that print was called correctly with the response
        mock_print.assert_called_with("API chat response:", "Knock knock! Who's there? Science joke.")
        # Ensure the API request was called correctly
        mock_chat_request.assert_called_once_with([{"role": "user", "content": "Tell me a knock knock joke about science."}], model=self.model)

    @patch('core.llm.openai_chat_completion_request')
    @patch('builtins.print')
    def test_openai_chat__invalid_response(self, mock_print, mock_chat_request):
        # Set up a mock response object with an invalid status code
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_chat_request.return_value = mock_response
        # Execute the function
        test_openai_chat(model=self.model)
        # Assertions to check that the correct error message is printed
        mock_print.assert_called_with("Failed to get a valid response from the API")

    @patch('core.llm.openai_chat_completion_request')
    @patch('builtins.print')
    def test_openai_chat__error(self, mock_print, mock_chat_request):
        # Configure the mock to raise an exception when called
        mock_chat_request.side_effect = Exception("Network error")
        # Execute the function
        test_openai_chat(model=self.model)
        # Assertions to check that the exception handling prints the correct error message
        mock_print.assert_called_with("An error occurred: Network error")

class TestLLMProcessBlock(unittest.TestCase):
    @patch('core.llm.openai_chat_completion_request')
    def test_llm_process_block__successful_response(self, mock_chat_completion):
        # Simulate a successful API response
        mock_chat_completion.return_value.json.return_value = {
            "choices": [{"message": {"content": "Processed text block"}}]
        }
        mock_chat_completion.return_value.status_code = 200

        block = "Original text block"
        prompt = "Please summarize this text."
        expected_response = "Processed text block"
        response = llm_process_block(block, prompt)

        self.assertEqual(response, expected_response)

    @patch('core.llm.openai_chat_completion_request')
    def test_llm_process_block__no_choices(self, mock_chat_completion):
        # Simulate a response with no 'choices'
        mock_chat_completion.return_value.json.return_value = {}
        mock_chat_completion.return_value.status_code = 200

        block = "Original text block"
        prompt = "Please summarize this text."
        response = llm_process_block(block, prompt)

        self.assertIsNone(response)

    @patch('core.llm.openai_chat_completion_request')
    def test_llm_process_block__failed_request(self, mock_chat_completion):
        # Simulate a failed request
        mock_chat_completion.return_value.status_code = 400
        mock_chat_completion.return_value.text = "Bad Request"

        block = "Original text block"
        prompt = "Please summarize this text."
        response = llm_process_block(block, prompt)

        self.assertIsNone(response)

class TestLLMProcessFileBlocks(unittest.TestCase):
    test_file_path = 'test_file_blocks.md'

    @classmethod
    def setUpClass(cls):
        # Prepare a test file
        with open(cls.test_file_path, 'w') as f:
            f.write("## metadata\nlast updated: \n\n\n## content\n\nBlock 1 text\n---\nBlock 2 text")

    @classmethod
    def tearDownClass(cls):
        # Cleanup test file
        os.remove(cls.test_file_path)

    @patch('core.llm.llm_process_block', return_value="Summarized text")
    @patch('core.fileops.write_metadata_and_content', return_value='path/to/updated_file_summarized.md')
    def test_llm_process_file_blocks__replace_mode_no_delimiters(self, mock_write, mock_process):
        updated_file_path = llm_process_file_blocks(self.test_file_path, "Please summarize this block.", '_summarized', 'replace', provider="openai", retain_delimiters=False)
        mock_write.assert_called_once()
        self.assertIn('_summarized', updated_file_path)
        args, _ = mock_write.call_args
        expected_content = "## content\n\nSummarized text\n\nSummarized text"
        actual_content = args[2]
        self.assertIn(expected_content, actual_content)
        mock_process.assert_any_call("Block 1 text", "Please summarize this block.", "openai")
        mock_process.assert_any_call("Block 2 text", "Please summarize this block.", "openai")

    @patch('core.llm.llm_process_block', return_value="Summarized text")
    @patch('core.fileops.write_metadata_and_content', return_value='path/to/updated_file_summarized_delimiters.md')
    def test_llm_process_file_blocks__replace_mode_with_delimiters(self, mock_write, mock_process):
        updated_file_path = llm_process_file_blocks(self.test_file_path, "Please summarize this block.", '_summarized_delimiters', 'replace', provider="openai", retain_delimiters=True)
        mock_write.assert_called_once()
        self.assertIn('_summarized_delimiters', updated_file_path)
        args, _ = mock_write.call_args
        expected_content = "## content\n\nSummarized text\n---\nSummarized text"
        actual_content = args[2]
        self.assertIn(expected_content, actual_content)
        mock_process.assert_any_call("Block 1 text", "Please summarize this block.", "openai")
        mock_process.assert_any_call("Block 2 text", "Please summarize this block.", "openai")

    @patch('core.llm.llm_process_block', side_effect=lambda block, prompt, provider: f"Analyzed {block}")
    @patch('core.fileops.write_metadata_and_content', return_value='path/to/updated_file_appended.md')
    def test_llm_process_file_blocks__append_mode_no_delimiters(self, mock_write, mock_process):
        new_file_path = llm_process_file_blocks(self.test_file_path, "Please analyze this block.", '_analyzed', 'append', provider="openai", retain_delimiters=False)
        args, _ = mock_write.call_args
        self.assertTrue(mock_write.called)
        expected_file_path = 'path/to/updated_file_appended.md'
        self.assertEqual(new_file_path, expected_file_path)
        mock_process.assert_called()
        expected_content = "## content\n\nBlock 1 text\nAnalyzed Block 1 text\n\nBlock 2 text\nAnalyzed Block 2 text"
        actual_content = args[2]
        self.assertIn(expected_content, actual_content)
        mock_process.assert_any_call("Block 1 text", "Please analyze this block.", "openai")
        mock_process.assert_any_call("Block 2 text", "Please analyze this block.", "openai")

    @patch('core.llm.llm_process_block', side_effect=lambda block, prompt, provider: f"Analyzed {block}")
    @patch('core.fileops.write_metadata_and_content', return_value='path/to/updated_file_appended_delimiters.md')
    def test_llm_process_file_blocks__append_mode_with_delimiters(self, mock_write, mock_process):
        new_file_path = llm_process_file_blocks(self.test_file_path, "Please analyze this block.", '_analyzed_delimiters', 'append', provider="openai", retain_delimiters=True)
        args, _ = mock_write.call_args
        self.assertTrue(mock_write.called)
        expected_file_path = 'path/to/updated_file_appended_delimiters.md'
        self.assertEqual(new_file_path, expected_file_path)
        mock_process.assert_called()
        expected_content = "## content\n\nBlock 1 text\nAnalyzed Block 1 text\n---\nBlock 2 text\nAnalyzed Block 2 text"
        actual_content = args[2]
        self.assertIn(expected_content, actual_content)
        mock_process.assert_any_call("Block 1 text", "Please analyze this block.", "openai")
        mock_process.assert_any_call("Block 2 text", "Please analyze this block.", "openai")

    @patch('core.llm.llm_process_block', return_value="Processed text")
    @patch('core.fileops.write_metadata_and_content', return_value='path/to/updated_file_custom_provider.md')
    def test_llm_process_file_blocks__custom_provider(self, mock_write, mock_process):
        updated_file_path = llm_process_file_blocks(self.test_file_path, "Please process this block.", '_custom_provider', 'replace', provider="custom_provider", retain_delimiters=False)
        mock_write.assert_called_once()
        self.assertIn('_custom_provider', updated_file_path)
        args, _ = mock_write.call_args
        expected_content = "## content\n\nProcessed text\n\nProcessed text"
        actual_content = args[2]
        self.assertIn(expected_content, actual_content)
        mock_process.assert_any_call("Block 1 text", "Please process this block.", "custom_provider")
        mock_process.assert_any_call("Block 2 text", "Please process this block.", "custom_provider")

class TestScallReplace(unittest.TestCase):
    test_file_path = 'test_file_blocks_replace.md'

    @classmethod
    def setUpClass(cls):
        # Prepare a test file
        with open(cls.test_file_path, 'w') as f:
            f.write("## metadata\nlast updated: \n\n\n## content\n\nBlock 1 content\n---\nBlock 2 content")

    @classmethod
    def tearDownClass(cls):
        # Cleanup test file
        os.remove(cls.test_file_path)

    @patch('core.llm.llm_process_block', side_effect=lambda block, prompt, provider: f"Processed {block}")
    @patch('core.fileops.write_metadata_and_content', return_value='path/to/updated_file_scall-replace.md')
    def test_scall_replace__retain_delimiters_false(self, mock_write, mock_process):
        new_file_path = scall_replace(self.test_file_path, "REPLACE - retain_delimiters=False Please summarize this block.", '_scall-replace', provider="openai", retain_delimiters=False)
        args, _ = mock_write.call_args
        self.assertTrue(mock_write.called)
        expected_file_path = 'path/to/updated_file_scall-replace.md'
        self.assertEqual(new_file_path, expected_file_path)
        mock_process.assert_called()
        expected_content = "## content\n\nProcessed Block 1 content\n\nProcessed Block 2 content"
        actual_content = args[2]
        self.assertIn(expected_content, actual_content)
        mock_process.assert_any_call("Block 1 content", "REPLACE - retain_delimiters=False Please summarize this block.", "openai")
        mock_process.assert_any_call("Block 2 content", "REPLACE - retain_delimiters=False Please summarize this block.", "openai")

    @patch('core.llm.llm_process_block', side_effect=lambda block, prompt, provider: f"Processed {block}")
    @patch('core.fileops.write_metadata_and_content', return_value='path/to/updated_file_scall-replace-delimiters.md')
    def test_scall_replace__retain_delimiters_true(self, mock_write, mock_process):
        new_file_path = scall_replace(self.test_file_path, "REPLACE - retain_delimiters=True Please summarize this block.", '_scall-replace-delimiters', provider="openai", retain_delimiters=True)
        args, _ = mock_write.call_args
        self.assertTrue(mock_write.called)
        expected_file_path = 'path/to/updated_file_scall-replace-delimiters.md'
        self.assertEqual(new_file_path, expected_file_path)
        mock_process.assert_called()
        expected_content = "## content\n\nProcessed Block 1 content\n---\nProcessed Block 2 content"
        actual_content = args[2]
        self.assertIn(expected_content, actual_content)
        mock_process.assert_any_call("Block 1 content", "REPLACE - retain_delimiters=True Please summarize this block.", "openai")
        mock_process.assert_any_call("Block 2 content", "REPLACE - retain_delimiters=True Please summarize this block.", "openai")

class TestScallAppend(unittest.TestCase):
    test_file_path = 'test_file_blocks_append.md'

    @classmethod
    def setUpClass(cls):
        # Prepare a test file
        with open(cls.test_file_path, 'w') as f:
            f.write("## metadata\nlast updated: \n\n\n## content\n\nBlock 1 content\n---\nBlock 2 content")

    @classmethod
    def tearDownClass(cls):
        # Cleanup test file
        os.remove(cls.test_file_path)

    @patch('core.llm.llm_process_block', side_effect=lambda block, prompt, provider: f"Analyzed {block}")
    @patch('core.fileops.write_metadata_and_content', return_value='path/to/updated_file_scall-append.md')
    def test_scall_append__retain_delimiters_false(self, mock_write, mock_process):
        new_file_path = scall_append(self.test_file_path, "APPEND - retain_delimiters=False Please summarize this block.", '_scall-append', provider="openai", retain_delimiters=False)
        args, _ = mock_write.call_args
        self.assertTrue(mock_write.called)
        expected_file_path = 'path/to/updated_file_scall-append.md'
        self.assertEqual(new_file_path, expected_file_path)
        mock_process.assert_called()
        expected_content = "## content\n\nBlock 1 content\nAnalyzed Block 1 content\n\nBlock 2 content\nAnalyzed Block 2 content"
        actual_content = args[2]
        self.assertIn(expected_content, actual_content)
        mock_process.assert_any_call("Block 1 content", "APPEND - retain_delimiters=False Please summarize this block.", "openai")
        mock_process.assert_any_call("Block 2 content", "APPEND - retain_delimiters=False Please summarize this block.", "openai")

    @patch('core.llm.llm_process_block', side_effect=lambda block, prompt, provider: f"Analyzed {block}")
    @patch('core.fileops.write_metadata_and_content', return_value='path/to/updated_file_scall-append-delimiters.md')
    def test_scall_append__retain_delimiters_true(self, mock_write, mock_process):
        new_file_path = scall_append(self.test_file_path, "APPEND - retain_delimiters=True Please summarize this block.", '_scall-append-delimiters', provider="openai", retain_delimiters=True)
        args, _ = mock_write.call_args
        self.assertTrue(mock_write.called)
        expected_file_path = 'path/to/updated_file_scall-append-delimiters.md'
        self.assertEqual(new_file_path, expected_file_path)
        mock_process.assert_called()
        expected_content = "## content\n\nBlock 1 content\nAnalyzed Block 1 content\n---\nBlock 2 content\nAnalyzed Block 2 content"
        actual_content = args[2]
        self.assertIn(expected_content, actual_content)
        mock_process.assert_any_call("Block 1 content", "APPEND - retain_delimiters=True Please summarize this block.", "openai")
        mock_process.assert_any_call("Block 2 content", "APPEND - retain_delimiters=True Please summarize this block.", "openai")

class TestCreateSimpleLLMFile(unittest.TestCase):
    def setUp(self):
        self.file_path = "test_file.md"
        self.prompt = "Test prompt"
        self.suffix_new = "_test"
        self.operation_mode = "replace"
        self.split_file_function = MagicMock()
        self.kwargs = {"retain_delimiters": False}

    @patch('core.llm.scall_replace')
    @patch('core.fileops.delete_file')
    def test_create_simple_llm_file__replace_mode(self, mock_delete_file, mock_scall_replace):
        self.split_file_function.return_value = "blocks_file.md"
        mock_scall_replace.return_value = "processed_file.md"

        result = create_simple_llm_file(
            self.file_path, self.prompt, self.suffix_new, 
            self.operation_mode, self.split_file_function, provider="openai", **self.kwargs
        )

        self.split_file_function.assert_called_once_with(self.file_path)
        mock_scall_replace.assert_called_once_with(
            "blocks_file.md", self.prompt, 
            suffix_new=self.suffix_new, provider="openai", retain_delimiters=False
        )
        mock_delete_file.assert_called_once_with("blocks_file.md")
        self.assertEqual(result, "processed_file.md")

    @patch('core.llm.scall_append')
    @patch('core.fileops.delete_file')
    def test_create_simple_llm_file__append_mode(self, mock_delete_file, mock_scall_append):
        self.split_file_function.return_value = "blocks_file.md"
        mock_scall_append.return_value = "processed_file.md"
        self.operation_mode = "append"

        result = create_simple_llm_file(
            self.file_path, self.prompt, self.suffix_new, 
            self.operation_mode, self.split_file_function, provider="openai", **self.kwargs
        )

        self.split_file_function.assert_called_once_with(self.file_path)
        mock_scall_append.assert_called_once_with(
            "blocks_file.md", self.prompt, 
            suffix_new=self.suffix_new, provider="openai", retain_delimiters=False
        )
        mock_delete_file.assert_called_once_with("blocks_file.md")
        self.assertEqual(result, "processed_file.md")

    def test_create_simple_llm_file__invalid_mode(self):
        self.operation_mode = "invalid"

        with self.assertRaises(ValueError) as context:
            create_simple_llm_file(
                self.file_path, self.prompt, self.suffix_new, 
                self.operation_mode, self.split_file_function, provider="openai", **self.kwargs
            )

        self.assertEqual(str(context.exception), "mode must be 'replace' or 'append'.")

            
### LLM FUNCTION CALLING
class TestAPIMOCKOpenAiFunctionCall(unittest.TestCase):
    def setUp(self):
        self.prompt_system = "System prompt message"
        self.content = "User content message"
        # Update tools to match the structure of TOOLS_FCALL_TEST_RHYME
        self.tools = [{
            "type": "function",
            "function": {
                "name": "test_fcall_rhyme",
                "description": "Extract the timestamp and generate a two sentence rhyme",
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "rhyme": {
                            "type": "string",
                            "description": "Create a two-line rhyming poem based on the content",
                        },
                        "timestamp": {
                            "type": "string",
                            "description": "The timestamp from the text",
                        },
                    },
                    "required": ["rhyme", "timestamp"],
                    "additionalProperties": False
                },
            },
        }]
        self.model = "gpt-4o-mini"
        self.verbose = True

    @patch('builtins.print')
    @patch('core.llm.openai_chat_completion_request')
    def test_openai_function_call__success(self, mock_chat_request, mock_print):
        # Create mock response with function call structure
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_ihxJCRj8L75tI8rup6dbeCiH",
                        "type": "function",
                        "function": {
                            "name": "test_fcall_rhyme",
                            "arguments": '{"rhyme": "Hello, world!\\nThis message has been told!", "timestamp": "0:00"}'
                        }
                    }],
                    "refusal": None
                }
            }]
        }
        mock_chat_request.return_value = mock_response

        # Call the function
        assistant_message = openai_function_call(
            self.prompt_system,
            self.content,
            self.tools,
            model=self.model,
            verbose=self.verbose
        )

        # Verify the mock was called with correct arguments
        mock_chat_request.assert_called_once()
        args, kwargs = mock_chat_request.call_args
        
        # Check the arguments match what we expect
        expected_messages = [
            {"role": "system", "content": self.prompt_system},
            {"role": "user", "content": self.content}
        ]
        self.assertEqual(kwargs['messages'], expected_messages)
        self.assertEqual(kwargs['tools'], self.tools)
        self.assertEqual(kwargs['model'], self.model)
        
        # Check the returned message contains the function call response
        self.assertEqual(assistant_message["role"], "assistant")
        self.assertIsNone(assistant_message["content"])
        self.assertIsNone(assistant_message["refusal"])
        self.assertEqual(len(assistant_message["tool_calls"]), 1)
        tool_call = assistant_message["tool_calls"][0]
        self.assertEqual(tool_call["type"], "function")
        self.assertEqual(tool_call["function"]["name"], "test_fcall_rhyme")
        self.assertIn("rhyme", json.loads(tool_call["function"]["arguments"]))
        self.assertIn("timestamp", json.loads(tool_call["function"]["arguments"]))

        # Verify print wasn't called (unless verbose was True)
        if not self.verbose:
            mock_print.assert_not_called()


    @patch('core.llm.pretty_print_function')
    @patch('core.llm.openai_chat_completion_request')
    def test_openai_function_call__exception_processing_response(self, mock_openai_chat_completion_request, mock_pretty_print):
        # Setup the mock response from openai_chat_completion_request
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Make the json() method raise a JSON parsing exception
        mock_response.json.side_effect = Exception("Failed to parse JSON")
        mock_openai_chat_completion_request.return_value = mock_response
        # Execute the function under test with updated parameters
        assistant_message = openai_function_call(self.prompt_system, self.content, self.tools, model=self.model)
        # Assert no message is returned because an exception was raised during json parsing
        self.assertIsNone(assistant_message)
        # Ensure pretty_print_function was not called since an exception occurs before it in the call flow
        mock_pretty_print.assert_not_called()


### QA EXTRACTION
class TestAPIMOCKCreateQaFileSelectSpeaker(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_filepath = os.path.join(self.temp_dir.name, "qa_input.md")
        shutil.copyfile(
            os.path.join(TEST_DATA_DIR, "llm", "qa_input.md"),
            self.test_filepath,
        )
        self.ref_filepath = os.path.join(TEST_DATA_DIR, "llm", "qa_reference.md")

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch('core.llm.openai_function_call')
    def test_create_qa_file_select_speaker__main(self, mock_openai_function_call):
        # Mock the openai_function_call to return a predefined response
        mock_openai_function_call.return_value = {
            'tool_calls': [{
                'function': {
                    'arguments': json.dumps({
                        'question': 'Mocked question',
                        'timestamp': '[00:00](https://www.youtube.com/watch?v=VIDEO_ID&t=0)'
                    })
                }
            }]
        }

        # Test creating QA from the markdown file
        qa_filepath = create_qa_file_select_speaker(self.test_filepath, "Test Expert", FCALL_PROMPT_QA_DIALOGUE_FROMANSWER)
        self.assertTrue(os.path.exists(qa_filepath))

        with open(qa_filepath, 'r') as qa_file, open(self.ref_filepath, 'r') as ref_file:
            qa_content = qa_file.read()
            ref_content = ref_file.read()

            # Check if the main structure is correct
            self.assertIn("## metadata", qa_content)
            self.assertIn("## content", qa_content)

            # Check if the QA format is correct
            self.assertIn("QUESTION: ", qa_content)
            self.assertIn("TIMESTAMP: ", qa_content)
            self.assertIn("ANSWER: ", qa_content)
            self.assertIn("EDITS: ", qa_content)
            self.assertIn("TOPICS: ", qa_content)
            self.assertIn("STARS: ", qa_content)

            # Compare the content excluding the dynamic parts
            qa_lines = qa_content.split('\n')
            ref_lines = ref_content.split('\n')
            for qa_line, ref_line in zip(qa_lines, ref_lines):
                if not (qa_line.startswith('last updated: ') or 
                        qa_line.startswith('QUESTION: ') or 
                        qa_line.startswith('TIMESTAMP: ')):
                    self.assertEqual(qa_line.rstrip(), ref_line.rstrip())

        # Verify that the mock was called
        mock_openai_function_call.assert_called()


# AssertionError: 'Returned' != 'Expected'

if __name__ == '__main__':
    unittest.main()
