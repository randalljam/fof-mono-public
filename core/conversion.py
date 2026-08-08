# ===== START OF FILE core/conversion.py =====
# Library of functions and execution code to do conversion tasks    

import os
import re
import logging
import pypandoc
from llama_parse import LlamaParse  # pip install llama-index llama-parse
from llama_index.core import SummaryIndex
from llama_index.readers.google import GoogleDocsReader  # pip install llama-index llama-index-readers-google
from markitdown import MarkItDown
from openai import OpenAI
from nltk.corpus import words
from collections import defaultdict
import xml.etree.ElementTree as ET
import html
from bs4 import BeautifulSoup
from markdownify import markdownify
import requests
from urllib.parse import urlparse
import datetime
import tempfile

# from IPython.display import Markdown, display

from core.fileops import *

# ---API KEYS AND SECRETS---
from dotenv import load_dotenv
load_dotenv(override=True)  # Load environment variables from .env file
LLAMA_CLOUD_API_KEY = os.environ["LLAMA_CLOUD_API_KEY"]
# INSERT in chalice/config.json "LLAMA_CLOUD_API_KEY": "LLAMA_CLOUD_API_KEY"
OPENAI_API_KEY = os.environ["OPENAI_API_KEY_ORIG"]

# ---START OF SYNCED CODE--- only code below will be synchronized with chalicelib.

### LLAMAINDEX
def convert_llamaparse_pdf_to_md(file_path):
    suffix_append = "_llamaparse"
    documents = LlamaParse(api_key=LLAMA_CLOUD_API_KEY, result_type="markdown",verbose=True).load_data(file_path)
    #print(documents[0].text[0:1000])
    md_file_path = file_path.rsplit('.', 1)[0] + suffix_append + '.md'  # Replace the file extension with .md
    with open(md_file_path, 'w', encoding='utf-8') as md_file:
        md_file.write(documents[0].text)
    print("Completed LlamaParse pdf to md conversion and appended suffix: " + suffix_append + " on input file_path: " + file_path)
    return md_file_path
def mrun_convert_llamaparse_pdf_to_md():
    pass
#if __name__ == "__main__":
    file_path = 'data/misc_books/The Sovereign Child.pdf'
    print(convert_llamaparse_pdf_to_md(file_path))

# TODO WIP - not working because needs different gcloud auth than service account
def convert_llamaindex_gdocs_to_md(gdoc_id_list):
    """
    Converts Google Docs to Markdown using Llama Index.

    :param gdoc_id_list: list of Google Docs document IDs.
    :return: Markdown representation of the Google Docs.
    """
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logging.getLogger().addHandler(logging.StreamHandler())

    # Hardcoded full path to the credentials file
    credentials_file = 'credentials_new.json'

    # Get the directory and original filename of the credentials file
    credentials_dir, original_filename = os.path.split(credentials_file)

    # # Save the current working directory
    # cwd = os.getcwd()

    # # Change the working directory to the one containing the credentials file
    # os.chdir(credentials_dir)

    # Temporarily rename the credentials file to credentials.json
    os.rename(original_filename, 'credentials.json')

    # Load the Google Docs data
    documents = GoogleDocsReader().load_data(gdoc_id_list=gdoc_id_list)

    # Rename the credentials file back to its original name
    os.rename('credentials.json', original_filename)

    # # Change the working directory back to the original one
    # os.chdir(cwd)

    # Create a summary index from the documents
    index = SummaryIndex.from_documents(documents)

    # # Convert each document to Markdown and display it
    # for doc in index.documents:
    #     display(Markdown(doc.text))
def mtest_convert_llamaindex_gdocs_to_md(gdoc_id_list):
    pass
#if __name__ == "__main__": 
    cur_gdoc_id_list = ['19yTV3UUkOQrfbqOPcL5hhBw9eJyc_5ra5Uz_tKQcs24']
    convert_llamaindex_gdocs_to_md(cur_gdoc_id_list)

### PANDOC
''' To confirm installation, run: pandoc --version
Should see:
pandoc 3.2
Features: +server +lua
Scripting engine: Lua 5.4
'''

def convert_file_to_md_pandoc(file_path, suffix_new="_pandoc"):
    """
    Converts any pandoc supported file format to a markdown file using pypandoc.
    Including but not limited to: doc, docx, html, latex, epub, odt, rtf, ascii doc.
    pdf has limitations.

    :param file_path: string of the path to the file to be converted.
    """
    output_markdown_file_path = os.path.splitext(file_path)[0] + suffix_new + '.md'
    extra_args = [
        '--wrap=none',
        '--to=markdown_strict+pipe_tables',
        '--extract-media=./media'  # Extract media to a 'media' directory relative to the markdown file
    ]
    output = pypandoc.convert_file(file_path, 'markdown', outputfile=output_markdown_file_path, extra_args=extra_args)
    assert output == ""  # ensures that the conversion process did not return any content directly, which implies that the conversion output was successfully written to the file

    print(f"Successful file conversion to markdown using pypandoc for file: {file_path}")
    return output_markdown_file_path
def mtest_convert_file_to_md_pandoc():
    pass
#if __name__ == "__main__": 
    #cur_file_path = 'tests/test_data_files/fileops/document.md'
    cur_file_path = 'data/floodlamp_fda/subs/2021-05-18_Pre-EUA Sub - FloodLAMP Proposed Pooling and Asymptomatic Screening Study.docx'
    print(convert_file_to_md_pandoc(cur_file_path))
def convert_md_file_to_epub(md_file_path, title=None):
    """
    Converts a markdown file to an epub file using pypandoc with error handling.

    :param md_file_path: string, path to the markdown file to convert
    :param title: string, optional title for the epub metadata
    :return: string, path to the output epub file
    """
    output_epub_file_path = os.path.splitext(md_file_path)[0] + '.epub'
    
    # If no title provided, use the filename without extension
    if not title:
        title = os.path.splitext(os.path.basename(md_file_path))[0]
    
    # Build extra arguments with required metadata
    extra_args = [
        '--standalone',
        '--wrap=none',
        '-f', 'markdown-raw_html-native_divs-native_spans',  # More permissive markdown parsing
        '--epub-chapter-level=2',
        # Required metadata
        '--metadata', f'title={title}',
        '--metadata', 'lang=en-US',
        '--metadata', 'creator=Unknown',  # Required for some EPUB readers
        '--metadata', 'date=' + datetime.now().strftime('%Y-%m-%d')  # Add current date
    ]
    
    try:
        pypandoc.convert_file(
            md_file_path,
            'epub',
            outputfile=output_epub_file_path,
            extra_args=extra_args,
            encoding='utf-8'  # Explicitly set encoding
        )
        print(f"Successfully converted {md_file_path} to EPUB with title: {title}")
        return output_epub_file_path
    except Exception as e:
        print(f"Error converting file: {str(e)}")
        raise  # Re-raise the exception to see the full error trace
def mrun_convert_md_file_to_epub():
    pass
#if __name__ == "__main__": 
    cur_md_file_path = 'data/misc_books/Sovereign Child/The Sovereign Child_sectionsJUST2.md'
    title = "The Sovereign Child"
    print(convert_md_file_to_epub(cur_md_file_path, title))

### MEGAPARSE
def convert_megaparse_pdf_to_md(file_path, use_llama_parse=False, use_vision=False):
    """
    Converts PDF to markdown using LlamaParse, MegaParse with GPT-4 Vision, or UnstructuredParser.
    
    :param file_path: string path to the PDF file
    :param use_llama_parse: bool, whether to use LlamaParse (True) or other parsers (False)
    :param use_vision: bool, whether to use GPT-4 Vision (True) or UnstructuredParser (False)
    :return: string path to the output markdown file
    """
    from megaparse import MegaParse
    
    if use_llama_parse:  # not working - see several github issues about this
        suffix_append = "_megaparse-lp"
        # from megaparse.parser.llama_parse import LlamaParser
        # parser = LlamaParser(api_key=os.getenv("LLAMA_CLOUD_API_KEY"))
    elif use_vision:
        suffix_append = "_megaparse-v" 
        from megaparse.parser.megaparse_vision import MegaParseVision
        from langchain_openai import ChatOpenAI
        model = ChatOpenAI(model="gpt-4-vision-preview", api_key=OPENAI_API_KEY)
        parser = MegaParseVision(model=model)
    else:
        suffix_append = "_megaparse-u"
        from megaparse.parser.unstructured_parser import UnstructuredParser
        parser = UnstructuredParser()
    
    # Initialize MegaParse with selected parser
    megaparse = MegaParse(parser)
    
    # Process the document
    response = megaparse.load(file_path)
    
    # Create output path
    md_file_path = file_path.rsplit('.', 1)[0] + suffix_append + '.md'
    
    # Save to markdown
    megaparse.save(md_file_path)
    
    parser_type = "with LlamaParse" if use_llama_parse else "without LlamaParse"
    print(f"Completed MegaParse with {parser_type} for pdf to md conversion.")
    return md_file_path
def mrun_convert_megaparse_pdf_to_md():
    pass
#if __name__ == "__main__":
    file_path = 'data/misc_books/The Sovereign Child.pdf'
    print(convert_megaparse_pdf_to_md(file_path))
# audiblez book.epub -l en-gb -v af_nicole -s 1.5
# audiblez "data/misc_books/Sovereign Child/The Sovereign Child_sectionsJUST2.epub" -l en-gb -v af_sky -s 1.5

### MS MARKITDOWN
def convert_file_to_md_msmid(file_path, new_suffix="_msmid"):
    """
    Converts a file to markdown using Microsoft's MarkItDown library and saves the output.

    :param file_path: string, path to the input file
    :param new_suffix: string, suffix to append to the output filename
    :return: string, path to the output markdown file
    """
    md = MarkItDown()
    result = md.convert(file_path)
    
    # Create output path with new suffix
    md_file_path = file_path.rsplit('.', 1)[0] + new_suffix + '.md'
    
    # Save the markdown content to file
    with open(md_file_path, 'w', encoding='utf-8') as md_file:
        md_file.write(result.text_content)
    
    print(f"Completed Microsoft MarkItDown conversion and appended suffix: {new_suffix} on input file_path: {file_path}")
    return md_file_path
def mrun_convert_file_to_md_msmid():
    pass
#if __name__ == "__main__":
    file_path = 'data/misc_books/The Sovereign Child.pdf'
    print(convert_file_to_md_msmid(file_path))

# TODO not tested - from readme at https://github.com/microsoft/markitdown/blob/main/README.md
def get_image_description_msmid(image_file_path, verbose=True):
    # To use Large Language Models for image descriptions, provide llm_client and llm_model:
    client = OpenAI()
    md = MarkItDown(llm_client=client, llm_model="gpt-4o")
    result = md.convert(image_file_path)
    description = result.text_content   
    verbose_print(verbose, description)
    return description

### TEXT
_word_set = None  # Declare the global variable
def initialize_nltk(silent=True):
    """
    Initialize NLTK resources if not already downloaded and report their status.
    Also initializes the word set used for word joining.
    """
    import nltk.data
    global _word_set
    
    resources = [
        ('corpora/words', 'words'),
        ('tokenizers/punkt', 'punkt'),
        ('tokenizers/punkt_tab', 'punkt_tab'),
        ('taggers/averaged_perceptron_tagger_eng', 'averaged_perceptron_tagger_eng'),
        ('corpora/stopwords', 'stopwords'),
        ('chunkers/maxent_ne_chunker_tab', 'maxent_ne_chunker_tab')
    ]
    
    for resource_path, resource_name in resources:
        try:
            nltk.data.find(resource_path)
            print(f"Resource '{resource_name}' is already available.")
        except LookupError:
            print(f"Resource '{resource_name}' not found. Downloading...")
            if silent:
                import warnings
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore")
                    nltk.download(resource_name, quiet=True)
            else:
                nltk.download(resource_name)
            print(f"Resource '{resource_name}' downloaded successfully.")
    
    # Initialize word set after ensuring resources are available
    _word_set = set(w.lower() for w in words.words())
    _word_set.update({
        'curiosity', 'priorities',
        # Add more as needed
    })
def mrun_initialize_nltk():
    pass
#if __name__ == "__main__":
    initialize_nltk(silent=False)
# TODO 7-18 RT - consider whether this is OK to be in function, think it was not previously and getting Problems
def load_custom_dictionary(file_path):
    """ Load a custom dictionary from a file. """
    try:
        with open(file_path, 'r') as file:
            return set(word.strip() for word in file)
    except FileNotFoundError:
        print("Custom dictionary file not found.")
        return set()
def lines_alphabetize_and_remove_duplicates(file_path):
    """
    Alphabetizes and removes duplicates from a list.
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    # Strip newline characters and sort the unique lines
    unique_lines = sorted(set(line.strip() for line in lines))
    
    # Overwrite the file with the sorted unique lines
    with open(file_path, 'w', encoding='utf-8') as file:
        for line in unique_lines:
            file.write(line + '\n')
def mrun_lines_alphabetize_and_remove_duplicates():
    pass
#if __name__ == "__main__":
    lines_alphabetize_and_remove_duplicates('data/deutsch/eval_dev/cur_proper_names_o1-preview.txt')
def lines_compare_files(file_path_1, file_path_2, print_same=False, silent=False):
    """
    Compares lines between two files and returns lists of differences and matches.
    
    :param file_path_1: Path to first file
    :param file_path_2: Path to second file
    :param print_same: Boolean to control whether to print lines that appear in both files
    :return: Tuple of (lines only in file 1, lines only in file 2, lines in both files)
    """
    # Read and process lines from both files
    with open(file_path_1, 'r', encoding='utf-8') as file:
        lines_1 = set(line.strip() for line in file.readlines())
    
    with open(file_path_2, 'r', encoding='utf-8') as file:
        lines_2 = set(line.strip() for line in file.readlines())
    
    # Get base filenames for headers
    file_1_name = os.path.basename(file_path_1)
    file_2_name = os.path.basename(file_path_2)
    
    # Find differences and matches
    lines_only_in_1 = sorted(lines_1 - lines_2)
    lines_only_in_2 = sorted(lines_2 - lines_1)
    lines_in_both = sorted(lines_1 & lines_2)
    
    # Print results in markdown format if requested
    if not silent:
        print(f"\n## Lines only in {file_1_name}")
        for line in lines_only_in_1:
            print(line)
        
        print(f"\n\n## Lines only in {file_2_name}")
        for line in lines_only_in_2:
            print(line)

        if print_same:
            print("\n\n## Lines in both files")
            for line in lines_in_both:
                print(line)
    
    return lines_only_in_1, lines_only_in_2, lines_in_both
def mrun_lines_compare_files():
    pass
#if __name__ == "__main__":
    cur_file_path_1 = "data/deutsch/eval_dev/2024-03-06_PB_nova2gen_propernames.txt"
    cur_file_path_2 = "data/deutsch/eval_dev/2024-03-06_PB_dgwhspm_propernames.txt"
    lines_compare_files(cur_file_path_1, cur_file_path_2, print_same=False, silent=False)
def normalize_text(text):
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    text = text.replace('__', '')  # Remove double underscores
    text = text.replace('**', '')  # Remove double asterisks
    text = text.strip()
    return text
def format_divider(title, total_length=69, start_pos=None, char='=', md_level=3, start_newline=False, end_newline=True):
    """
    Creates a formatted header with equal signs and optional markdown heading level.
    
    :param total_length: Total desired length of the header line
    :param title: Title text to display in the middle
    :param start_pos: Position where title should start (if None, centers the title)
    :param md_level: Number of markdown hashtags to prepend (None for no markdown)
    :param start_newline: Whether to start with a newline
    :param end_newline: Whether to end with a newline
    :param char: Character to use for the header line (default '=')
    :return: Formatted header string
    """
    # Calculate markdown prefix if needed
    md_prefix = '#' * md_level + ' ' if md_level else ''
    
    if start_pos is not None:
        # Calculate space needed before and after title based on start position
        left_count = start_pos - len(md_prefix)
        right_count = total_length - left_count - len(title)
        
        # Ensure minimum padding
        if left_count < 2 or right_count < 2:
            left_count = 2
            right_count = 2
            
        left_chars = char * left_count
        right_chars = char * right_count
    else:
        # Center the title as before
        remaining_space = total_length - len(title) - len(md_prefix)
        if remaining_space < 4:  # Minimum 2 chars on each side
            remaining_space = 4
            
        chars_count = remaining_space // 2
        left_chars = char * chars_count
        right_chars = char * (remaining_space - chars_count)  # Handle odd remaining space
    
    # Build the header
    header = f"{md_prefix}{left_chars} {title} {right_chars}"
    
    # Add newlines as requested
    if start_newline:
        header = '\n' + header
    if end_newline:
        header = header + '\n'
        
    return header
def get_context(text, position, surrounding_chars=None, surrounding_words=None, complete_words=True):
    """
    Extract surrounding context from text around a specific position.

    :param text: str, the full text to extract context from
    :param position: int, the center position to get context around
    :param surrounding_chars: int or None, number of characters to include on each side
    :param surrounding_words: int or None, number of words to include on each side
    :param complete_words: bool, whether to expand to complete words
    :return context: str, the extracted context snippet
    """
    if surrounding_chars is None and surrounding_words is None:
        surrounding_chars = 20  # Default if neither specified
        
    # Get initial character-based bounds
    if surrounding_chars is not None:
        start = max(0, position - surrounding_chars)
        end = min(len(text), position + surrounding_chars)
    else:
        start = 0
        end = len(text)
        
    # Expand to word boundaries if needed
    if surrounding_words is not None or complete_words:
        # Find word boundaries
        while start > 0 and text[start-1].isalnum():
            start -= 1
        while end < len(text) and text[end].isalnum():
            end += 1
            
        if surrounding_words is not None:
            # Count words and expand if needed
            left_text = text[start:position]
            right_text = text[position:end]
            
            left_words = left_text.split()
            right_words = right_text.split()
            
            if len(left_words) > surrounding_words:
                start = position - len(' '.join(left_words[-surrounding_words:]))
            if len(right_words) > surrounding_words:
                end = position + len(' '.join(right_words[:surrounding_words]))
    
    return text[start:end]
def remove_extraneous_spaces_in_words(text, verbose=False):
    """
    Removes extraneous spaces that split valid words in text.
    Uses NLTK's word list with custom additions.
    
    :param text: str, text to process for split words
    :param verbose: bool, whether to print debug info
    :return: str, processed text with split words rejoined
    """
    global _word_set
    if _word_set is None:
        raise RuntimeError("NLTK resources not initialized. Call initialize_nltk() first.")
    
    lines = text.split('\n')
    changes = defaultdict(int)
    
    for i, line in enumerate(lines):
        words_in_line = line.split()
        j = 0
        while j < len(words_in_line) - 1:
            current_word = words_in_line[j]
            next_word = words_in_line[j + 1]
            combined = current_word + next_word
            
            if combined.lower() in _word_set:
                if verbose:
                    print(f"Found split word: '{current_word} {next_word}' -> '{combined}'")
                words_in_line[j] = combined
                words_in_line.pop(j + 1)
                changes[f"{current_word} {next_word} -> {combined}"] += 1
            else:
                j += 1
                
        lines[i] = ' '.join(words_in_line)
    
    if verbose and changes:
        print("\nChanges made:")
        for change, count in changes.items():
            print(f"- {change}: {count} occurrences")
            
    return '\n'.join(lines)
def mtest_remove_extraneous_spaces_in_words():
    pass
#if __name__ == "__main__":
    initialize_nltk(silent=False)
    test_text = "Humorously, school is about college, and college is about getting a job and sustaining a life. And only then, *in your twen ties*, can food and bathing and clothes and entertainment be about those things in themselves. Shouldn't childhood be the time when kids are free to explore those things that are integral to life, to learn about and develop relationships with them for their own sake? The magic of childhood is that kids don't have dependents or even a responsibility to ensure their own sur vival, so it is precisely during this time that a person is most free to engage with the world directly."
    print(remove_extraneous_spaces_in_words(test_text, verbose=True))

### MARKDOWN
def convert_csv_to_md_table(csv_content):
    """
    Convert CSV content to a markdown table.
    """
    csv_reader = csv.reader(io.StringIO(csv_content))
    rows = list(csv_reader)
    
    if not rows:
        return ""

    md_table = "| " + " | ".join(rows[0]) + " |\n"
    md_table += "|" + "|".join(["---"] * len(rows[0])) + "|\n"
    
    for row in rows[1:]:
        md_table += "| " + " | ".join(row) + " |\n"
    
    return md_table + "\n"
def analyze_quotes_characters(md_file_path):
    """
    Analyzes a markdown file for different types of quotes and apostrophes.
    Displays a formatted table of quote types, their Unicode values, and counts.
    """
    # Define quotes using Unicode values
    quotes = {
        '\u0027': "Straight single quote/apostrophe",  # Basic ASCII single quote
        '\u0022': "Straight double quote",             # Basic ASCII double quote
        '\u2018': "Left single quote",                 # Left single curly quote
        '\u2019': "Right single quote/apostrophe",     # Right single curly quote
        '\u201C': "Left double quote",                 # Left double curly quote
        '\u201D': "Right double quote"                 # Right double curly quote
    }

    with open(md_file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Print header
    print(f"\nQuote Analysis Report for: {md_file_path}")
    print("=" * 80)
    
    # Find the longest description for padding
    max_desc_length = max(len(desc) for desc in quotes.values())
    
    # Print formatted table header
    print(f"\n{'Description':<{max_desc_length}} {'Unicode':<10} {'Count':<10}")
    print("-" * (max_desc_length + 20))
    
    # Print each quote's information
    for unicode_char, description in quotes.items():
        count = content.count(unicode_char)
        unicode_val = f"U+{ord(unicode_char):04X}"
        print(f"{description:<{max_desc_length}} {unicode_val:<10} {count:<10}")

    return {unicode_char: content.count(unicode_char) for unicode_char in quotes}
def mrun_analyze_quotes_characters():
    pass
#if __name__ == "__main__":
    from core.docwork import analyze_quotation_marks
    md_file_path = "data/floodlamp/reg/fda-townhalls/f5_fixnames/a_run_auto/2020-12-02_Virtual Town Hall 35_fixnames.md"
    analyze_quotes_characters(md_file_path)
    # print("\n=======\n")
    # text = read_complete_text(md_file_path)
    # print(analyze_quotation_marks(text))
def convert_markdown_to_md_mod_text(md_file_path):
    """
    Converts a markdown file to a modified text file with specific replacements.
    Changes the suffix to 'md-mod' and extension to '.txt'.
    Creates a copy of the input file before making modifications.
    
    :param md_file_path: string, path to the markdown file to be converted
    :return: string, path to the modified text file
    """
    # Define the find-replace pairs
    find_replace_pairs = [
        ("## ", "# "),
        ("QUESTION: ", "#### "),
        ("\nTIMESTAMP:", ""),
        ("ANSWER: ", ""),
        #("QUESTION NAME:.*\n(?:.*\n)*?STARS:.*\n", ""),
        ("## transcript", "## Transcript"),
        ("## qa", "## Questions and Answers (AI DRAFT - NOT APPROVED BY PVSD AND WFPD)"),
        ("## meeting chat log", "## Meeting Chat Log"),
        ("\n", "<<NL>>")
    ]

    txt_path = md_file_path.rsplit('.', 1)[0] + '.txt'
    shutil.copy2(md_file_path, txt_path)

    # change the suffix to md-mod by creating a copy
    txt_path = sub_suffix_in_file(txt_path, '_md-mod')
    
    # Apply the find-replace pairs
    total_replacements = find_and_replace_pairs(txt_path, find_replace_pairs, use_regex=True)
    
    print(f"Completed markdown to modified text conversion with {total_replacements} replacements")
    return txt_path
def mrun_convert_markdown_to_md_mod_text():
    pass
#if __name__ == "__main__":
    md_file_path = "data/pv/pv_epc_evac/2024-10-23_PVSD WFPD - Wildfire Preparedness Parent Presentation 3_combo.md"
    md_mod_file_path = convert_markdown_to_md_mod_text(md_file_path)
def combine_files_into_md(file_paths, target_file_path, max_file_size_mb=10, number_order=True, strip_extensions=False):
    """
    Combine multiple files into a single markdown file.

    :param file_paths: list, file paths to combine (relative to repo root)
    :param target_file_path: string, path for the output markdown file (relative to repo root)
    :param max_file_size_mb: int, maximum allowed file size in MB (default: 10)
    :param number_order: bool, whether to sort files by first number in filename (default: True)
    :param strip_extensions: bool, whether to strip file extensions in headers (default: False)
    :return target_file_path: string, relative path of the combined markdown file
    """
    supported_extensions = ['.txt', '.md', '.py', '.js', '.css', '.html', '.json', '.csv']
    max_file_size_bytes = max_file_size_mb * 1024 * 1024

    # Sort files by number if requested
    if number_order:
        def extract_first_number(filepath):
            # Get just the filename without path
            filename = os.path.basename(filepath)
            # Find all numbers in the filename
            numbers = re.findall(r'\d+', filename)
            # Return first number if found, otherwise return infinity (to put at end)
            return float('inf') if not numbers else int(numbers[0])
        
        file_paths = sorted(file_paths, key=extract_first_number)

    # Get the repo root directory
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    combined_file_path = os.path.join(repo_root, target_file_path)
    files_combined = 0

    with open(combined_file_path, 'w', encoding='utf-8') as output_file:
        for relative_path in file_paths:
            file_path = os.path.join(repo_root, relative_path)
            file_name = os.path.basename(file_path)
            file_extension = os.path.splitext(file_name)[1].lower()
            if strip_extensions:
                file_name = os.path.splitext(file_name)[0]
            
            if file_extension not in supported_extensions:
                print(f"Skipping unsupported file: {file_name}")
                continue

            if os.path.getsize(file_path) > max_file_size_bytes:
                print(f"Skipping file exceeding size limit: {file_name}")
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as input_file:
                    content = input_file.read()

                output_file.write(f"# {file_name}\n\n")

                if file_extension in ['.py', '.js', '.css', '.html', '.json']:
                    lang = file_extension[1:]  # Remove the dot
                    output_file.write(f"```{lang}\n{content}\n```\n\n")
                elif file_extension == '.csv':
                    output_file.write(convert_csv_to_md_table(content))
                else:
                    output_file.write(f"{content}\n\n")

                files_combined += 1

            except Exception as e:
                print(f"Error processing file {file_name}: {str(e)}")

    print(f"Successfully combined {files_combined} files into {combined_file_path}")
    return target_file_path
def mrun_combine_files_into_md():
    pass
#if __name__ == "__main__":
    file_paths = [
    "apps/math_quiz/math_analysis.html",
    "apps/math_quiz/math_analysis.js",
    # "apps/math_quiz/math_analysis.css",
    "apps/math_quiz/math_quiz.html",
    "apps/math_quiz/math_quiz.js",
    "apps/math_quiz/math_quiz.css"
    ]
    combine_files_into_md(file_paths, 'apps/math_quiz/combined_math_quiz.md')
def combine_md_files_in_folder(folder_path, target_filename='combined.md', number_order=True, strip_extensions=True):
    """
    Combines multiple markdown files into a single file.

    :param folder_path: string, path to folder containing markdown files
    :param target_filename: string, name for combined output file
    :return: string, path to combined markdown file
    """
    target_file_path = os.path.join(folder_path, target_filename)
    if os.path.exists(target_file_path):
        os.remove(target_file_path)
    file_paths = get_files_in_folder(folder_path, suffixpat_include='.md', include_subfolders=False)
    combine_files_into_md(file_paths, target_file_path, number_order=number_order, strip_extensions=strip_extensions)
def mrun_combine_md_files():
    pass
#if __name__ == "__main__":
    folder_path = "data/deutsch/f8__"
    combine_md_files_in_folder(folder_path)


### OPENAI CHAT TO MD
### CHATGPT SHARE: HTML -> MARKDOWN
def _extract_text_md_from_html(html_fragment):
    """
    Convert an HTML fragment to Markdown using markdownify with sane defaults.
    Keeps code blocks, tables, and links readable.
    """
    # Tweaked settings: ATX headings, keep line breaks, and fence code blocks
    return markdownify(
        html_fragment,
        heading_style="ATX",
        bullets="*",
        strip=["style", "script", "noscript"]
    ).strip()
def _guess_title_and_date(soup):
    """
    Try multiple strategies to get the thread title and date from a ChatGPT shared HTML page.
    Returns (title, date_str) where unknowns may be empty strings.
    """
    title = ""
    date_str = ""

    # 1) <meta property="og:title"> or <title>
    og_title = soup.find("meta", attrs={"property": "og:title"})
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()

    if not title and soup.title and soup.title.string:
        title = soup.title.string.strip()

    # 2) Any prominent H1/H2 in header
    if not title:
        hdr = soup.find(["header"])
        if hdr:
            h = hdr.find(["h1", "h2"])
            if h and h.get_text(strip=True):
                title = h.get_text(strip=True)

    if not title:
        h1 = soup.find("h1")
        if h1 and h1.get_text(strip=True):
            title = h1.get_text(strip=True)

    # 3) Date often appears in <time> or in small/caption text near header
    t = soup.find("time")
    if t and (t.get("datetime") or t.get_text(strip=True)):
        date_str = (t.get("datetime") or t.get_text(strip=True)).strip()

    if not date_str:
        # Look for elements with 'date' in class/name
        date_like = soup.find(lambda tag: tag.name in ["span", "div", "p", "time"]
                                        and any(("date" in (c or "").lower() or "time" in (c or "").lower())
                                                for c in (tag.get("class") or [""])))
        if date_like and date_like.get_text(strip=True):
            date_str = date_like.get_text(strip=True)

    # Final normalization
    title = title or "Untitled Chat"
    date_str = date_str or "Unknown Date"
    return title, date_str
def _iter_messages(soup):
    """
    Yield (role, content_html) for each message in order.
    Attempts multiple selectors to be resilient to markup changes.
    role is 'user' or 'assistant' (fallbacks default unknown to assistant).
    """
    candidates = []

    # Strategy A: elements carrying an explicit author/role attribute
    for tag in soup.find_all(True):
        role = None
        # Common attributes we may see
        for attr in ["data-message-author", "data-author", "data-role", "data-testid"]:
            val = tag.get(attr)
            if isinstance(val, str) and val:
                v = val.lower()
                if "assistant" in v or "bot" in v or "gpt" in v:
                    role = "assistant"
                elif "user" in v or "you" in v:
                    role = "user"
        # Class-based heuristics
        classes = " ".join(tag.get("class") or []).lower()
        if not role:
            if "assistant" in classes or "bot" in classes or "gpt" in classes:
                role = "assistant"
            elif "user" in classes or "author-user" in classes:
                role = "user"

        # Message content-ish: often includes prose, markdown, code, etc.
        if role and (
            tag.name in ["article", "section", "div"] and
            (
                "message" in classes or
                "prose" in classes or
                "markdown" in classes or
                "content" in classes
            )
        ):
            # Try to avoid duplicates by requiring some textual content
            textish = tag.get_text(strip=True)
            if textish and len(textish) > 0:
                candidates.append((role, str(tag)))
    if candidates:
        # De-duplicate while preserving order (some parents/children can both match)
        seen = set()
        pruned = []
        for role, html_block in candidates:
            key = (role, html_block[:200])  # short hash
            if key in seen:
                continue
            seen.add(key)
            pruned.append((role, html_block))
        return pruned

    # Strategy B: find obvious message containers by class keywords, then infer role from nearby labels
    blocks = soup.find_all(lambda t:
        t.name in ["article", "div", "section"]
        and any(k in " ".join((t.get("class") or [])).lower() for k in ["message", "prose", "markdown", "chat", "content"])
    )
    out = []
    for b in blocks:
        role = None
        # Look upward for a label like "You" or "ChatGPT"
        label = b.find_previous(lambda t: t.name in ["span", "div", "strong"] and t.get_text(strip=True) in ["You", "User", "ChatGPT", "Assistant"])
        if label:
            txt = label.get_text(strip=True).lower()
            if "chatgpt" in txt or "assistant" in txt:
                role = "assistant"
            elif "you" in txt or "user" in txt:
                role = "user"
        role = role or "assistant"
        out.append((role, str(b)))
    return out
def _pair_exchanges(messages):
    """
    Pair messages into user->assistant exchanges.
    If the sequence starts with assistant, we'll create an exchange with empty user.
    If there are multiple assistants in a row, they are concatenated.
    Returns a list of dicts: {"user_html": "...", "assistant_html": "..."}
    """
    exchanges = []
    cur_user = ""
    cur_assistant_chunks = []

    def flush():
        nonlocal cur_user, cur_assistant_chunks
        if cur_user or cur_assistant_chunks:
            exchanges.append({
                "user_html": cur_user,
                "assistant_html": "".join(cur_assistant_chunks)
            })
        cur_user = ""
        cur_assistant_chunks = []

    for role, html_block in messages:
        if role == "user":
            # Starting a new exchange
            if cur_user or cur_assistant_chunks:
                flush()
            cur_user = html_block
        else:  # assistant
            cur_assistant_chunks.append(html_block)

    flush()
    return exchanges
def convert_chatgpt_share_html_to_md(html_file_path, suffix_new="_chatmd"):
    """
    Convert a ChatGPT 'Share' HTML page into Markdown with the following shape:

    # <DATE> — <TITLE>
    ## 1. User
    <prompt md>
    ## 1. Assistant
    <response md>
    ## 2. User
    ...
    
    :param html_file_path: str, path to the saved shared HTML page
    :param suffix_new: str, suffix for the output .md file
    :return: str, path to the output markdown file
    """
    # Read HTML
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_text = f.read()

    soup = BeautifulSoup(html_text, "html.parser")

    title, date_str = _guess_title_and_date(soup)
    msgs = _iter_messages(soup)
    if not msgs:
        print("Warning: No messages detected; falling back to full-page conversion.")
        # Fallback: whole page to md
        md_content = _extract_text_md_from_html(html_text)
        base = os.path.splitext(html_file_path)[0]
        md_path = base + suffix_new + ".md"
        with open(md_path, "w", encoding="utf-8") as out:
            out.write(f"# {date_str} — {title}\n\n")
            out.write(md_content + "\n")
        print(f"Completed ChatGPT share HTML→MD (fallback) for: {html_file_path}")
        return md_path

    exchanges = _pair_exchanges(msgs)

    # Build Markdown
    md_lines = []
    md_lines.append(f"# {date_str} — {title}\n")

    for i, ex in enumerate(exchanges, start=1):
        user_md = _extract_text_md_from_html(ex.get("user_html", "")) if ex.get("user_html") else ""
        asst_md = _extract_text_md_from_html(ex.get("assistant_html", "")) if ex.get("assistant_html") else ""

        # Normalize whitespace a bit to avoid accidental triple blank lines
        if user_md:
            md_lines.append(f"## {i}. User\n")
            md_lines.append(user_md.strip() + "\n")
        else:
            # Even if missing user (share pages sometimes start with assistant)
            md_lines.append(f"## {i}. User\n\n_(no user message captured)_\n")

        if asst_md:
            md_lines.append(f"## {i}. Assistant\n")
            md_lines.append(asst_md.strip() + "\n")
        else:
            md_lines.append(f"## {i}. Assistant\n\n_(no assistant message captured)_\n")

    # Write file
    md_file_path = os.path.splitext(html_file_path)[0] + suffix_new + ".md"
    with open(md_file_path, "w", encoding="utf-8") as md_file:
        md_file.write("\n".join(md_lines).strip() + "\n")

    print(f"Completed ChatGPT share HTML→MD for: {html_file_path}")
    return md_file_path
def convert_chatgpt_share_url_to_md(chat_url, output_dir="data/chat_converts"):
    """
    Convert a ChatGPT share URL into Markdown and save both HTML and MD files.
    
    :param chat_url: str, URL of the ChatGPT share page
    :param output_dir: str, directory to save the output files (default: "data/chat_converts")
    :return: tuple, (html_path, md_path) paths to the saved HTML and markdown files
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Download the HTML page
    html_text = requests.get(chat_url).text
    soup = BeautifulSoup(html_text, "html.parser")
    title, date_str = _guess_title_and_date(soup)
    
    # Generate a clean filename based on title, date, and URL
    clean_title = re.sub(r'[^\w\s-]', '', title).strip()
    clean_title = re.sub(r'[-\s]+', '-', clean_title)[:50]  # Limit length
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Extract a short identifier from the URL
    url_id = urlparse(chat_url).path.split('/')[-1][:8] if urlparse(chat_url).path else "unknown"
    base_filename = f"{timestamp}_{clean_title}_{url_id}"
    
    # Save HTML file
    html_output_path = os.path.join(output_dir, f"{base_filename}.html")
    with open(html_output_path, "w", encoding="utf-8") as f:
        f.write(html_text)
    
    # Create a temporary HTML file to use with the existing convert function
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as temp_file:
        temp_file.write(html_text)
        temp_html_path = temp_file.name
    
    try:
        # Use the existing convert function to create markdown
        temp_md_path = convert_chatgpt_share_html_to_md(temp_html_path, suffix_new="_chatmd")
        
        # Move the markdown file to the desired location with our filename
        md_output_path = os.path.join(output_dir, f"{base_filename}_chatmd.md")
        
        # Read the temporary markdown and add source URL, then write to final location
        with open(temp_md_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        # Add source URL after the title
        lines = md_content.split('\n')
        if lines:
            lines.insert(1, f"Source URL: {chat_url}")
            lines.insert(2, "")  # Add blank line
        
        with open(md_output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        # Clean up temporary files
        os.unlink(temp_html_path)
        os.unlink(temp_md_path)
        
    except Exception as e:
        # Clean up temporary file in case of error
        if os.path.exists(temp_html_path):
            os.unlink(temp_html_path)
        raise e
    
    print(f"Completed ChatGPT share URL→MD for: {chat_url}")
    print(f"Saved HTML: {html_output_path}")
    print(f"Saved MD: {md_output_path}")
    return html_output_path, md_output_path
def mrun_convert_chatgpt_share_html_to_md():
    pass
#if __name__ == "__main__":
    chat_url = "https://chatgpt.com/share/68ea6e42-ba60-8006-ad86-c2e9ef7c76e1"
    print(convert_chatgpt_share_url_to_md(chat_url))

### SCRAPING
def format_date_for_filename(date_str):
    """
    Convert various date formats to YYYY-MM-DD.
    Handles partial dates by using the first of the month/year.
    
    :param date_str: str, date string from RSS feed
    :return: str, formatted date YYYY-MM-DD
    """
    try:
        # Try to parse the full date string
        date_obj = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
        return date_obj.strftime('%Y-%m-%d')
    except ValueError:
        # Handle partial dates
        year_match = re.search(r'\b\d{4}\b', date_str)
        month_match = re.search(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\b', date_str)
        
        if year_match and month_match:
            # Year and month only
            year = year_match.group()
            month = datetime.strptime(month_match.group(), '%B').strftime('%m')
            return f"{year}-{month}-01"
        elif year_match:
            # Year only
            return f"{year_match.group()}-01-01"
        else:
            return "1900-01-01"  # Default date if parsing fails
def extract_articles_from_feed(feed_file, output_dir, heading="article"):
    """
    Extract articles from an RSS feed file and save as markdown files.
    
    :param feed_file: str, path to the RSS feed file
    :param output_dir: str, directory where markdown files will be saved
    :param heading: str, heading to use for the content section (default: "article")
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Parse the XML feed
    tree = ET.parse(feed_file)
    root = tree.getroot()
    
    # Find all item elements (articles)
    channel = root.find('channel')
    for item in channel.findall('item'):
        # Extract article metadata
        title = item.find('title').text
        date_str = item.find('pubDate').text
        formatted_date = format_date_for_filename(date_str)
        
        # Get content and unescape HTML entities
        content = item.find('{http://purl.org/rss/1.0/modules/content/}encoded').text
        content = html.unescape(content)
        
        # Convert HTML to markdown
        md_content = markdownify(content)
        
        # Get link if available
        link = item.find('link')
        link_text = link.text if link is not None else ""
        
        # Create filename in the specified format
        safe_title = title.replace('/', '-').replace('\\', '-')
        filename = f"{formatted_date}_TCS Site_{safe_title}.md"
        filename = ''.join(c for c in filename if c.isalnum() or c in '-_. ')
        
        # Prepare markdown file content with new format
        full_content = f"""## metadata
last updated: {formatted_date}
link: {link_text}


## content

{heading}

{md_content}
"""
        
        # Save to file
        output_path = os.path.join(output_dir, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        print(f"Saved: {filename}")

def mrun_extract_articles_from_feed():
    pass
#if __name__ == "__main__":
    feed_file = "data/deutsch/essays/tcs/httrack from dd tag/by-david-deutsch/feed/index.html"
    output_dir = "data/deutsch/essays/tcs/dd"
    extract_articles_from_feed(feed_file, output_dir, heading="### article")

### HTML
def wrap_qa_blocks_in_details(html_file_path, question_field, answer_field):
    """
    Wraps QA blocks in nested details tags for collapsible viewing.
    
    :param html_file_path: string, path to the HTML file to modify
    :param question_field: string, field name for questions
    :param answer_field: string, field name for answers
    :return: None
    """
    with open(html_file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Check if content has block IDs (e.g., "1-1", "2-12")
    if 'QA BLOCK:' in content or 'QA Block' in content:
        # Has block IDs - determine specific format
        if 'QA BLOCK:' in content:
            # Sovereign Child format (uppercase with colon)
            qa_block_pattern = (
                r'<p>\s*QA BLOCK:\s*(\d+-\d+)\s*<br\s*/?>\s*'
                r'QUESTION:\s*(.*?)\s*<br\s*/?>\s*'
                r'(?:.*?<br\s*/?>\s*)*?'  # Match any intermediate lines non-greedily
                r'ANSWER:\s*(.*?)\s*<br\s*/?>\s*'
                r'(?:.*?)</p>'
            )
        else:
            # FDA townhall format (title case without colon)
            qa_block_pattern = (
                r'<p>QA Block (\d+-\d+)<br>\n'
                + f'{question_field}: (.*?)<br>\n'
                + f'{answer_field}: (.*?)<br>\n'
                + r'.*?</p>'
            )
        def wrap_qa_block(match):
            full_block = match.group(0)  # Use group(0) for the entire match
            block_num = match.group(1)
            question = match.group(2)
            answer = match.group(3)
            
            return f'''  <details>
    <summary>{block_num}. {question}</summary>
    <details>
      <summary>{answer}</summary>
      {full_block}</details>
  </details>'''
    else:
        # Check for multi-question format (like Gad Saad file)
        multi_question_pattern = (
            r'<p>\s*'
            r'<strong>\s*'
            r'QUESTION 1:\s*(.*?)\s*'
            r'</strong>\s*'
            r'<br\s*/?>\s*'
            r'((?:QUESTION \d+:.*?<br\s*/?>\s*)*)'  # Capture additional questions
            r'(?:.*?<br\s*/?>\s*)*?'  # Match any intermediate lines
            r'ANSWER:\s*(.*?)\s*<br\s*/?>\s*'
            r'(?:.*?)</p>'
        )
        
        def wrap_multi_question_block(match):
            full_block = match.group(0)
            first_question = match.group(1).strip()
            additional_questions = match.group(2).strip() if match.group(2) else ""
            answer = match.group(3).strip()
            
            return f'''  <details>
    <summary>{first_question}</summary>
    {full_block}
  </details>'''
        
        # Try multi-question pattern first
        matches = list(re.finditer(multi_question_pattern, content, flags=re.DOTALL))
        
        if matches:
            print(f"Found {len(matches)} multi-question blocks to wrap")
            modified_content = re.sub(multi_question_pattern, wrap_multi_question_block, content, flags=re.DOTALL)
        else:
            # Fall back to simple Q&A format
            qa_block_pattern = (
                r'<p>\s*'
                + f'{question_field}:\s*(.*?)\s*<br\s*/?>\s*'
                + r'(?:.*?<br\s*/?>\s*)*?'  # Match any intermediate lines non-greedily
                + f'{answer_field}:\s*(.*?)(?=\s*<br|</p>)'
                + r'.*?</p>'
            )
            
            def wrap_qa_block(match):
                full_block = match.group(0)
                question = match.group(1)
                answer = match.group(2).strip()
                
                return f'''  <details>
    <summary>{question}</summary>
    {full_block}
  </details>'''
            
            matches = list(re.finditer(qa_block_pattern, content, flags=re.DOTALL))
            
            if not matches:
                print("\nPattern not matching. Debug info:")
                print(f"Pattern used: {qa_block_pattern}")
                print("\nContent sample:")
                print(content[:500])
                return
            
            modified_content = re.sub(qa_block_pattern, wrap_qa_block, content, flags=re.DOTALL)
    
    # Write the modified content back
    with open(html_file_path, 'w', encoding='utf-8') as file:
        file.write(modified_content)

def has_section_titles(md_file_path, heading="### transcript"):
    """
    Detects if a markdown file has section titles (h4 headings) in the specified heading.
    
    :param md_file_path: string, path to the markdown file to check
    :param heading: string, heading section to check for h4 elements
    :return: bool, True if h4 headings are found, False otherwise
    """
    content = get_heading(md_file_path, heading)
    if not content:
        return False
    
    # Look for h4 headings (#### )
    import re
    h4_pattern = r'^\s*####\s+.+'  
    matches = re.findall(h4_pattern, content, re.MULTILINE)
    return len(matches) > 0

def wrap_qa_blocks_in_details_enhanced(html_file_path, question_field, answer_field):
    """
    Enhanced version that handles both old QA BLOCK format and new multi-question format.
    
    :param html_file_path: string, path to the HTML file to modify
    :param question_field: string, field name for questions
    :param answer_field: string, field name for answers
    :return: None
    """
    with open(html_file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Check if content has old-style QA BLOCK IDs 
    if 'QA BLOCK:' in content or 'QA Block' in content:
        # Use existing logic for old format
        wrap_qa_blocks_in_details(html_file_path, question_field, answer_field)
        return
    
    # New multi-question format - look for numbered questions
    # Pattern matches: QUESTION: text<br>ANSWER: text<br>optional_other_fields</p>
    qa_block_pattern = (
        r'<p>\s*'
        + f'{question_field}:\s*(.*?)\s*<br\s*/?>\s*'
        + f'{answer_field}:\s*(.*?)\s*<br\s*/?>\s*'
        + r'(?:.*?)</p>'  # Capture any additional fields
    )
    
    def wrap_qa_block(match):
        full_block = match.group(0)
        question = match.group(1).strip()
        answer = match.group(2).strip()
        
        # For new format, just wrap question with answer nested inside
        return f'''  <details>
    <summary>{question}</summary>
    <details>
      <summary>{answer}</summary>
      {full_block}
    </details>
  </details>'''
    
    # Find all matches before replacing
    matches = list(re.finditer(qa_block_pattern, content, flags=re.DOTALL))
    
    if not matches:
        print(f"\nNo QA blocks found in {html_file_path}")
        print(f"Pattern used: {qa_block_pattern}")
        print("\nContent sample:")
        print(content[:500])
        return
    
    print(f"Found {len(matches)} QA blocks to wrap")
    
    # Replace QA blocks with wrapped versions
    modified_content = re.sub(qa_block_pattern, wrap_qa_block, content, flags=re.DOTALL)
    
    with open(html_file_path, 'w', encoding='utf-8') as file:
        file.write(modified_content)
def clean_summaries_in_html_file(html_file_path):
    """
    Removes href links from all summary tags in an HTML file while preserving the link text.
    Processes all levels of nested summaries.
    
    :param html_file_path: string, path to the HTML file to clean
    :return: None
    """
    # Read the HTML file
    with open(html_file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Counter for summaries processed
    summaries_checked = 0
    summaries_cleaned = 0
    
    def clean_summary_content(match):
        nonlocal summaries_checked, summaries_cleaned
        summary_content = match.group(0)  # Get the full match including summary tags
        summaries_checked += 1
        
        # Only process if there's an href
        if 'href=' in summary_content:
            cleaned_content = re.sub(
                r'<a\s+[^>]*href="[^"]*"[^>]*>(.*?)</a>', 
                r'\1', 
                summary_content, 
                flags=re.DOTALL
            )
            if cleaned_content != summary_content:
                summaries_cleaned += 1
            return cleaned_content
        
        return summary_content
    
    # Process summaries recursively until no more changes
    prev_content = ""
    while content != prev_content:
        prev_content = content
        content = re.sub(
            r'(<summary>.*?</summary>)', 
            clean_summary_content, 
            content, 
            flags=re.DOTALL | re.IGNORECASE
        )
    
    #print(f"Processed {summaries_checked} summaries, cleaned {summaries_cleaned} with hrefs\n")
    
    # Write the modified content back
    with open(html_file_path, 'w', encoding='utf-8') as file:
        file.write(content)
def add_additional_html_from_template(html_file_path, template_file_path):
    """
    Adds non-empty HTML elements from a template file to their corresponding parent locations in the target HTML file.
    
    :param html_file_path: string, path to the HTML file to modify
    :param template_file_path: string, path to the template file to add
    :return: None
    """
    from bs4 import BeautifulSoup
    
    # Read both files
    with open(template_file_path, 'r', encoding='utf-8') as file:
        template_content = file.read()
    with open(html_file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()
    
    # Parse both files
    template_soup = BeautifulSoup(template_content, 'html.parser')
    html_soup = BeautifulSoup(html_content, 'html.parser')
    
    # Process control panel
    template_control_panel = template_soup.find('div', class_='control-panel')
    if template_control_panel:
        target_header = html_soup.find('header')
        if target_header:
            # Remove existing control panel if it exists
            existing_control_panel = target_header.find('div', class_='control-panel')
            if existing_control_panel:
                existing_control_panel.decompose()
            # Add new control panel after h1
            h1_tag = target_header.find('h1')
            if h1_tag:
                h1_tag.insert_after(template_control_panel)
    
    # Process header-row and h3
    template_header_row = template_soup.find('div', class_='header-row')
    if template_header_row:
        target_header = html_soup.find('header')
        if target_header:
            # Find the h3 in the source
            h3_tag = html_soup.find('h3')
            if h3_tag:
                # Get the template h3 placeholder
                template_h3 = template_header_row.find('h3')
                if template_h3:
                    # Replace template h3 with actual h3
                    h3_tag.extract()
                    template_h3.replace_with(h3_tag)
                
                # Add the header-row to target header
                target_header.append(template_header_row)
    
    # Process script
    template_script = template_soup.find('script')
    if template_script:
        # Remove existing script if it exists
        existing_script = html_soup.find('script')
        if existing_script:
            existing_script.decompose()
        # Add new script at end of body
        body_tag = html_soup.find('body')
        if body_tag:
            body_tag.append(template_script)
    
    # Write modified content back to file
    with open(html_file_path, 'w', encoding='utf-8') as file:
        file.write(str(html_soup.prettify()))
def h_tune_html_file(html_file_path, new_heading_text, h_level, insert=True, remove_suffixext=True):
    """
    Modifies heading text in an HTML file at specified heading level.
    
    :param html_file_path: string, path to the HTML file to modify
    :param new_heading_text: string, text to either:
                           - insert after first underscore (if insert=True)
                           - completely replace existing heading with (if insert=False)
    :param h_level: int, heading level to modify (1-6)
    :param insert: bool, if True inserts new_heading_text after first underscore,
                       if False replaces entire heading
    :param remove_suffixext: bool, if True removes text after and including last underscore
    :return: None
    """
    # Read the HTML file
    with open(html_file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Pattern to find the specified heading level
    pattern = f'<h{h_level}[^>]*>(.*?)</h{h_level}>'
    
    def modify_heading(match):
        heading_text = match.group(1)
        
        if insert:
            # Split on first underscore
            parts = heading_text.split('_', 1)
            if len(parts) > 1:
                base = parts[1]
                # Remove suffix if requested
                if remove_suffixext:
                    base = base.rsplit('_', 1)[0]
                return f'<h{h_level}>{parts[0]}_{new_heading_text} {base}</h{h_level}>'
            return match.group(0)  # No underscore found, return unchanged
        else:
            # Simply replace the entire heading text
            return f'<h{h_level}>{new_heading_text}</h{h_level}>'
    
    # Replace the heading content
    modified_content = re.sub(pattern, modify_heading, content, flags=re.DOTALL)
    
    # Write back to the file
    with open(html_file_path, 'w', encoding='utf-8') as file:
        file.write(modified_content)
def convert_markdown_to_html(md_file_path, heading, collapse_h=4, css_file_path=None, cap_first=True, debug=True, bold_first_line=True, wrap_subsections=False):
    """
    Converts a markdown file to an html file using pypandoc with enhanced formatting options.

    :param md_file_path: string, path to the markdown file to convert
    :param heading: string, heading to use for the document
    :param collapse_h: int, heading level to wrap with details/summary elements (default: 4)
    :param css_file_path: string or None, path to CSS file to link
    :param cap_first: bool, whether to capitalize first letter of headings
    :param debug: bool, whether to print debug information
    :param bold_first_line: bool, whether to bold first line of paragraphs
    :param wrap_subsections: bool, whether to wrap subsections in details tags
    :return: string, path to the output HTML file
    """
    import re  # Add explicit import at function start
    
    html_file_path = md_file_path.replace('.md', '.html')
    convert_text = get_heading(md_file_path, heading)
    
    if convert_text is None:
        raise ValueError(f"No content found for heading '{heading}' in file {md_file_path}")
        
    if (heading == "CONTENT"):
        verbose_print(debug, "For heading= 'CONTENT'")
        convert_text = convert_text.replace("CONTENT", "")
        
        # Debug print to check content before scaling
        verbose_print(debug, f"Content before scaling:\n{convert_text[:200]}...")
        
        # Only scale headings if there is exactly one h1 heading
        h1_count = len(re.findall(r'^\s*#\s+', convert_text, re.MULTILINE))
        h2_count = len(re.findall(r'^\s*##\s+', convert_text, re.MULTILINE))
        
        verbose_print(debug, f"Found {h1_count} h1 headings and {h2_count} h2 headings")
        
        if h1_count == 1:
            verbose_print(debug, "  Found exactly one h1 heading - scaling all headings down by 2 levels")
            convert_text = scale_headings(convert_text, 2)
        elif h1_count > 1:
            verbose_print(debug, "  Found multiple h1 headings - scaling all headings down by 3 levels") 
            convert_text = scale_headings(convert_text, 3)
        else:
            if h2_count == 1:
                verbose_print(debug, "  Found exactly one h2 heading - scaling all headings down by 1 level")
                convert_text = scale_headings(convert_text, 1)
            elif h2_count > 1:
                verbose_print(debug, "  Found multiple h2 headings - scaling all headings down by 2 levels")
                convert_text = scale_headings(convert_text, 2)
        
        # Debug print to check content after scaling
        verbose_print(debug, f"Content after scaling:\n{convert_text[:200]}...")

    # Strip any blank lines from the beginning of the text
    convert_text = convert_text.lstrip('\n')
    
    # Create temporary file with the text to convert
    temp_file_path = 'temp_convert_md_to_html.md'
    with open(temp_file_path, 'w', encoding='utf-8') as f:
        f.write(convert_text)

    title = os.path.basename(md_file_path)
    
    pypandoc.convert_file(temp_file_path, 'html5', outputfile=html_file_path, 
        extra_args=[
            '--wrap=none',  # Prevents text wrapping
            '-f', 'gfm+hard_line_breaks',  # Input format
            '-t', 'html5',  # Explicitly set output format to HTML5
            '--standalone',  # Include full document structure with DOCTYPE,
            f'--metadata=title:{title}',  # Use filename as title
            '--columns=999999'  # Use a very large column width  
        ]
    )
    os.remove(temp_file_path)

    # Convert self-closing br tags to HTML5 format
    with open(html_file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    content = content.replace('<br />', '<br>')
    
    # Bold first line of paragraphs if requested
    if bold_first_line:
        content = re.sub(r'(<p>)(.*?)(<br|</p>)', 
                        lambda m: f'{m.group(1)}<strong>{m.group(2)}</strong>{m.group(3)}', 
                        content, flags=re.DOTALL)

    # Add details/summary around subsections if requested
    if wrap_subsections:
        # Pattern matches any h5 tag and its content up to the next h5 or h4
        subsection_pattern = r'(<h5.*?</h5>)(.*?)(?=<h[45]|$)'
        def wrap_subsection(match):
            heading = match.group(1)
            content = match.group(2)
            return f'''<details class="subsection">
  <summary>{heading}</summary>{content}
</details>'''
        
        # Process subsections before main collapse_h
        content = re.sub(subsection_pattern, wrap_subsection, content, flags=re.DOTALL)

    # Handle main section collapsing
    if collapse_h:
        pattern = f'(<h{collapse_h}.*?</h{collapse_h}>)(.*?)(?=<h{collapse_h}|$)'
        def wrap_section(match):
            heading = match.group(1)  # The complete h4 tag
            content = match.group(2)  # The content after the h4
            return f'<details>\n  <summary>{heading}</summary>{content}\n</details>'
        content = re.sub(pattern, wrap_section, content, flags=re.DOTALL)
    
    # Handle CSS styling
    if css_file_path is not None:  # Check if we should modify styles
        style_start = content.find('<style')
        style_end = content.find('</style>') + 8  # +8 to include '</style>'
        
        if style_start != -1 and style_end != -1:
            if css_file_path == "":  # Empty string - remove styles completely
                content = content[:style_start] + content[style_end:]
            else:  # Non-empty string - replace with CSS link
                css_link = f'<link rel="stylesheet" href="{css_file_path}">'
                content = content[:style_start] + css_link + content[style_end:]
    # Capitalize first letter of headings if requested
    if cap_first:
        def capitalize_heading(match):
            tag_start = match.group(1)  # The opening h tag
            content = match.group(2)     # The heading text
            tag_end = match.group(3)     # The closing h tag
            # Capitalize first letter of actual text content
            content = content[0].upper() + content[1:] if content else content
            return f"{tag_start}{content}{tag_end}"
            
        content = re.sub(r'(<h\d[^>]*>)(.*?)(</h\d>)', capitalize_heading, content)

    # Write the modified content back
    with open(html_file_path, 'w', encoding='utf-8') as file:
        file.write(content)
    
    print(f"Successful markdown to html conversion for file: {html_file_path}")
    return html_file_path
def mrun_convert_markdown_to_html():
    pass
#if __name__ == "__main__":
    md_file_path = "tests/test_data_files/fileops/document.md"
    css_file_path = "transcript-with-section-titles.css"
    html_file_path = convert_markdown_to_html(md_file_path, heading="### transcript", css_file_path=css_file_path)
    h_tune_html_file(html_file_path, "COVID-19 Diagnostics FDA", 1)
def convert_html_to_png(html_file_path, css_selector=None, viewport_width=1500, viewport_height=900):
    """
    Converts an HTML file to a PNG screenshot using Playwright headless Chromium.

    :param html_file_path: string, path to the HTML file to convert.
    :param css_selector: string or none, CSS selector to screenshot a specific element (screenshots full page if none).
    :param viewport_width: int, browser viewport width in pixels.
    :param viewport_height: int, browser viewport height in pixels.
    :return png_file_path: string, path to the output PNG file.
    """
    from playwright.sync_api import sync_playwright
    from pathlib import Path

    html_path = Path(html_file_path).resolve()
    png_file_path = str(html_path.with_suffix(".png"))

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": viewport_width, "height": viewport_height})
        page.goto(f"file://{html_path}")
        page.wait_for_load_state("networkidle")
        if css_selector:
            element = page.locator(css_selector)
            element.screenshot(path=png_file_path)
        else:
            page.screenshot(path=png_file_path, full_page=True)
        browser.close()

    print(f"Completed HTML to PNG conversion: {png_file_path}")
    return png_file_path
def mrun_convert_html_to_png():
    pass
#if __name__ == "__main__":
    html_file_path = "data/floodlamp/regulatory/irb/_clin-study-diagram.html"
    convert_html_to_png(html_file_path, css_selector=".diagram-container")


### OCR IMAGES
import cv2
import pytesseract
from PIL import Image
import numpy as np

def do_ocr_on_image(image_path, mode='color', binary_threshold=None):
    """
    Performs OCR on an image file using specified processing parameters.
    
    :param image_path: string path to the image file (JPEG, PNG, etc.)
    :param mode: string, 'binary', 'grayscale', or 'color' processing mode
    :param binary_threshold: int, binary threshold value (used if mode is 'binary')
    :return: string of the extracted text
    """
    # Read the image using cv2
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not load image at path: {image_path}")

    if mode == 'binary':
        # Convert to grayscale then apply binary thresholding
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        if binary_threshold is not None:
            _, processed_image = cv2.threshold(gray, binary_threshold, 255, cv2.THRESH_BINARY)
        else:
            # Use Otsu's thresholding if no threshold is provided
            _, processed_image = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # Convert back to RGB as required by pytesseract
        processed_image = cv2.cvtColor(processed_image, cv2.COLOR_GRAY2RGB)
    elif mode == 'grayscale':
        # Convert to grayscale
        processed_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Convert back to RGB as required by pytesseract
        processed_image = cv2.cvtColor(processed_image, cv2.COLOR_GRAY2RGB)
    elif mode == 'color':
        # Use original color image, just convert from BGR to RGB
        processed_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    else:
        raise ValueError("Invalid mode specified. Use 'binary', 'grayscale', or 'color'.")

    # Get OCR text
    text = pytesseract.image_to_string(processed_image)
    
    # Clean and return the text
    return text.strip()
def vary_ocr_on_image(image_path):
    """
    Performs OCR on an image using different modes and binary thresholds,
    outputting results to a markdown file.
    
    :param image_path: string path to the image file
    :return: string path to the output markdown file
    """
    # Constants
    SUFFIX_PAT = '_ocr-vary.md'
    BINARY_THRESHOLDS = [75, 100, 125, 150, 175]  # Range of thresholds to try
    
    # Create output markdown path
    output_path = image_path.rsplit('.', 1)[0] + SUFFIX_PAT
    
    # List to store all results
    results = []
    
    # Try different modes
    for mode in ['color', 'grayscale', 'binary']:
        if mode == 'binary':
            # Try different thresholds for binary mode
            for threshold in BINARY_THRESHOLDS:
                text = do_ocr_on_image(image_path, mode=mode, binary_threshold=threshold)
                results.append((f"## Binary Mode (threshold={threshold})", text))
        else:
            # Process color and grayscale modes
            text = do_ocr_on_image(image_path, mode=mode)
            results.append((f"## {mode.title()} Mode", text))
    
    # Write results to markdown file
    with open(output_path, 'w', encoding='utf-8') as f:
        for heading, text in results:
            f.write(f"{heading}\n\n{text}\n\n")
    
    print(f"OCR variations written to: {output_path}")
    return output_path
def mtest_do_ocr_on_image():
    pass
#if __name__ == "__main__":
    image_path = 'data/education/mentava/screenshots/IMG_2878.PNG'
    #print(do_ocr_on_image(image_path)) 
    print(vary_ocr_on_image(image_path))

SUPPORTED_IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']
def create_md_ocr_on_image_folder(folder_path, mode='color', binary_threshold=None):
    """
    Performs OCR on all supported images in a folder and creates a single markdown file
    with the results. Each image's text will be under its own heading.
    
    :param folder_path: string path to the folder containing images
    :param mode: string, 'binary', 'grayscale', or 'color' processing mode
    :param binary_threshold: int, binary threshold value (used if mode is 'binary')
    :return: string path to the output markdown file
    """
    # Get all image files in the folder
    image_files = []
    for ext in SUPPORTED_IMAGE_EXTENSIONS:
        image_files.extend(get_files_in_folder(folder_path, suffixpat_include=ext))
        image_files.extend(get_files_in_folder(folder_path, suffixpat_include=ext.upper()))
    
    if not image_files:
        print(f"No supported image files found in {folder_path}")
        return None
    
    # Create output markdown file path using the folder name
    folder_name = os.path.basename(os.path.normpath(folder_path))
    output_path = os.path.join(folder_path, f"{folder_name}_ocr.md")
    
    # Process each image and write results to markdown file
    with open(output_path, 'w', encoding='utf-8') as f:
        for image_path in image_files:
            # Get filename for heading
            filename = os.path.basename(image_path)
            
            # Perform OCR
            try:
                text = do_ocr_on_image(image_path, mode=mode, binary_threshold=binary_threshold)
                
                # Write to markdown file
                f.write(f"## {filename}\n\n{text}\n\n")
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")
                f.write(f"## {filename}\n\nError processing image: {str(e)}\n\n")
    
    print(f"OCR results written to: {output_path}")
    return output_path
def mtest_create_md_ocr_on_image_folder():
    pass
#if __name__ == "__main__":
    folder_path = 'data/education/mentava/screenshots'
    print(create_md_ocr_on_image_folder(folder_path)) 

# FOR FL PATENT CONVERSION
def convert_numbering_format_fix_number(file_path):
    """
    Converts numbered list items from "1. " format to "[0001] " format in the "## fix number" section.

    :param file_path: string, path to the input file.
    :return: string, path to the output file with numbering format converted.
    """
    # Read the entire file
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Find the "## fix number" section
    fix_number_pattern = r'(## fix number\s*\n)(.*?)(?=\n## |\Z)'
    match = re.search(fix_number_pattern, content, re.DOTALL)
    
    if not match:
        print(f"Warning: '## fix number' section not found in {file_path}")
        # Still create output file with same content
        output_file_path = file_path.rsplit('.', 1)[0] + '_fixednumber.' + file_path.rsplit('.', 1)[1]
        with open(output_file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        return output_file_path
    
    # Extract the section content
    section_header = match.group(1)
    section_content = match.group(2)
    
    # Convert numbered items in the section
    # Pattern matches lines starting with a number followed by period and space
    def replace_number(match_obj):
        number = int(match_obj.group(1))
        rest_of_line = match_obj.group(2)
        return f"[{number:04d}] {rest_of_line}"
    
    # Replace numbered items (e.g., "1. " -> "[0001] ")
    converted_content = re.sub(
        r'^(\d+)\.\s+(.*)$',
        replace_number,
        section_content,
        flags=re.MULTILINE
    )
    
    # Reconstruct the file with converted section
    before_section = content[:match.start()]
    after_section = content[match.end():]
    modified_content = before_section + section_header + converted_content + after_section
    
    # Create output file path with suffix
    file_dir = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    name_parts = file_name.rsplit('.', 1)
    if len(name_parts) == 2:
        output_file_name = name_parts[0] + '_fixednumber.' + name_parts[1]
    else:
        output_file_name = file_name + '_fixednumber'
    output_file_path = os.path.join(file_dir, output_file_name)
    
    # Write the modified content
    with open(output_file_path, 'w', encoding='utf-8') as file:
        file.write(modified_content)
    
    print(f"Completed numbering format conversion for file: {file_path}")
    return output_file_path
def increment_numbering_format_fix_number(file_path):
    """
    Increments all numbered items in "[####] " format by 1 in the "## fix number" section.

    :param file_path: string, path to the input file.
    :return: string, path to the output file with numbering incremented.
    """
    # Read the entire file
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Find the "## fix number" section
    fix_number_pattern = r'(## fix number\s*\n)(.*?)(?=\n## |\Z)'
    match = re.search(fix_number_pattern, content, re.DOTALL)
    
    if not match:
        print(f"Warning: '## fix number' section not found in {file_path}")
        # Still create output file with same content
        output_file_path = file_path.rsplit('.', 1)[0] + '_incremented.' + file_path.rsplit('.', 1)[1]
        with open(output_file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        return output_file_path
    
    # Extract the section content
    section_header = match.group(1)
    section_content = match.group(2)
    
    # Convert numbered items in the section
    # Pattern matches lines starting with [####] format
    def increment_number(match_obj):
        number = int(match_obj.group(1))
        rest_of_line = match_obj.group(2)
        incremented_number = number + 1
        return f"[{incremented_number:04d}] {rest_of_line}"
    
    # Replace numbered items (e.g., "[0130] " -> "[0131] ")
    converted_content = re.sub(
        r'^\[(\d+)\]\s+(.*)$',
        increment_number,
        section_content,
        flags=re.MULTILINE
    )
    
    # Reconstruct the file with converted section
    before_section = content[:match.start()]
    after_section = content[match.end():]
    modified_content = before_section + section_header + converted_content + after_section
    
    # Create output file path with suffix
    file_dir = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    name_parts = file_name.rsplit('.', 1)
    if len(name_parts) == 2:
        output_file_name = name_parts[0] + '_incremented.' + name_parts[1]
    else:
        output_file_name = file_name + '_incremented'
    output_file_path = os.path.join(file_dir, output_file_name)
    
    # Write the modified content
    with open(output_file_path, 'w', encoding='utf-8') as file:
        file.write(modified_content)
    
    print(f"Completed numbering increment for file: {file_path}")
    return output_file_path
def add_numbering_format_fix_number(file_path, starting_number):
    """
    Adds sequential numbering in "[0###] " format starting from a given number to every line in the "## fix number" section.

    :param file_path: string, path to the input file.
    :param starting_number: int, the starting number for the sequential numbering.
    :return: string, path to the output file with numbering added.
    """
    # Read the entire file
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Find the "## fix number" section
    fix_number_pattern = r'(## fix number\s*\n)(.*?)(?=\n## |\Z)'
    match = re.search(fix_number_pattern, content, re.DOTALL)
    
    if not match:
        print(f"Warning: '## fix number' section not found in {file_path}")
        # Still create output file with same content
        output_file_path = file_path.rsplit('.', 1)[0] + '_numbered.' + file_path.rsplit('.', 1)[1]
        with open(output_file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        return output_file_path
    
    # Extract the section content
    section_header = match.group(1)
    section_content = match.group(2)
    
    # Track current number (continuous for every line)
    current_number = starting_number
    
    # Process each line in the section
    lines = section_content.split('\n')
    converted_lines = []
    
    for line in lines:
        # Add numbering format to every line (including empty lines)
        replacement = f"[{current_number:04d}] {line}"
        converted_lines.append(replacement)
        current_number += 1
    
    converted_content = '\n'.join(converted_lines)
    
    # Reconstruct the file with converted section
    before_section = content[:match.start()]
    after_section = content[match.end():]
    modified_content = before_section + section_header + converted_content + after_section
    
    # Create output file path with suffix
    file_dir = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    name_parts = file_name.rsplit('.', 1)
    if len(name_parts) == 2:
        output_file_name = name_parts[0] + '_numbered.' + name_parts[1]
    else:
        output_file_name = file_name + '_numbered'
    output_file_path = os.path.join(file_dir, output_file_name)
    
    # Write the modified content
    with open(output_file_path, 'w', encoding='utf-8') as file:
        file.write(modified_content)
    
    print(f"Completed adding numbering format starting from {starting_number} for file: {file_path}")
    return output_file_path

# ===== END OF FILE core/conversion.py =====
