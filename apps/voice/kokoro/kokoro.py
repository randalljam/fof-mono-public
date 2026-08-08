import os
import soundfile as sf
import numpy as np
from kokoro_onnx import Kokoro
from datetime import datetime
import re


# python apps/voice/kokoro/kokoro.py

### TTS KOKORO
'''
python3.12 -m venv .venv_python12
source .venv_python12/bin/activate

pip install kokoro-onnx soundfile
pip install requests click openai pydub
pip install playsound==1.2.2

https://github.com/thewh1teagle/kokoro-onnx/blob/main/README.md
https://github.com/santinic/audiblez/blob/main/README.md

'''
### PORTED FILEOPS
def read_file_flex(file_path):
    """
    Reads a file and returns metadata and content sections if they exist, otherwise returns empty string and complete text.

    :param file_path: string, path to the file to be read.
    :return: tuple (metadata, content) where both are strings.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
            
        # Check if file has METADATA and CONTENT markers
        metadata_start = text.find('METADATA')
        content_start = text.find('CONTENT')
        
        if metadata_start != -1 and content_start != -1:
            metadata = text[metadata_start:content_start].strip()
            content = text[content_start:].strip()
            content = content.replace('CONTENT', '', 1).strip()
            return metadata, content
        else:
            return "", text
    except Exception as e:
        print(f"Error reading file: {e}")
        return "", ""

def strip_initial_headings_in_text(input_text):
    """
    Preprocesses markdown text by removing specific heading lines and their following blank lines.
    Handles both '## content' and 'CONTENT' markers, and removes h3 heading lines.

    :param input_text: str, the input markdown text to process
    :return: str, the processed text with heading lines removed but content preserved
    """
    print(f"Initial text length: {len(input_text)}")
    
    # Check for '## content' pattern
    content_start = input_text.find('## content\n\n')
    if content_start != -1:
        input_text = input_text[content_start + len('## content\n\n'):]
        #print(f"After '## content' removal: {len(input_text)} chars")
    
    # Check for 'CONTENT' marker
    content_marker = input_text.find('CONTENT')
    if content_marker != -1:
        input_text = input_text[content_marker:].strip()
        input_text = input_text.replace('CONTENT', '', 1).strip()
        #print(f"After 'CONTENT' removal: {len(input_text)} chars")
    
    # Remove h3 heading lines and following blank lines only
    lines = input_text.splitlines()
    output_lines = []
    skip_blanks = False
    
    for line in lines:
        if line.startswith('### '):
            skip_blanks = True
            continue
        if skip_blanks and not line.strip():
            continue
        skip_blanks = False
        output_lines.append(line)
    
    input_text = '\n'.join(output_lines)
    #print(f"After h3 removal: {len(input_text)} chars")
    
    # Clean up any extra newlines
    input_text = re.sub(r'\n{3,}', '\n\n', input_text)
    #print(f"After newline cleanup: {len(input_text)} chars")
    
    return input_text

### TTS KOKORO
KOKORO_MODEL_PATH = "apps/voice/kokoro/kokoro models - gitignore/kokoro-v0_19.onnx"
KOKORO_VOICES_PATH = "apps/voice/kokoro/kokoro models - gitignore/voices.bin"
def tts_kokoro(output_file_path, text_input, voice_name, add_kokoro_suffix=True):
    """
    Convert text to audio using Kokoro TTS.

    :param output_file_path: str, path where the audio file will be saved
    :param text_input: str, text to convert to speech
    :param voice_name: str, voice to use (e.g., 'af_sky', 'af_nicole')
    :param add_kokoro_suffix: bool, if True adds '_kokoro-{voice}' to output filename
    :return output_file: str, path to the generated audio file or None if failed
    """
    try:
        # Start timing
        start_time = datetime.now()
        
        # Count characters
        char_count = len(text_input)
        
        # Generate audio
        # Override numpy's default pickle security
        np.load.__defaults__ = (None, True, True, 'ASCII')
        kokoro = Kokoro(KOKORO_MODEL_PATH, KOKORO_VOICES_PATH)
        audio, sample_rate = kokoro.create(text_input, voice=voice_name)
        
        # Modify output path if kokoro suffix is requested
        if add_kokoro_suffix:
            base_path = output_file_path.rsplit('.', 1)[0]
            voice_name_clean = voice_name.split('_')[1]  # Remove the 'af_' prefix
            output_file_path = f"{base_path}_kokoro-{voice_name_clean}.mp3"
        
        # Save the audio file
        sf.write(output_file_path, audio, sample_rate)
        
        # Calculate and print processing time
        elapsed_minutes = (datetime.now() - start_time).total_seconds() / 60
        minutes_per_thousand = (elapsed_minutes * 1000) / char_count
        time_now = datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')
        print(f"Processed kokoro {char_count//1000} K characters in {elapsed_minutes:.1f} minutes - current time: {time_now}")
        print(f"Rate: {minutes_per_thousand:.1f} minutes per 1K characters")
        return output_file_path
            
    except ImportError as e:
        print(f"ERROR in tts_kokoro - Required module not found: {e}")
        return None
    except Exception as e:
        print(f"ERROR in tts_kokoro - An error occurred: {e}")
        return None
def mrun_tts_kororo():
    pass
#if __name__ == "__main__":
    mp3_file_path = "apps/voice/kokoro/kokoro_audio/test1.mp3"
    text_input='''
The truth is that these companies can't control us simply by knowing what we want, any more than television or print advertising can. We aren't passively controlled by our information diet—we make choices based on our interpretation of it. Most advertising doesn't work, and the ads that do work do so by telling us things about products that are true. False advertising fails in the long run because people get disappointed in the product, and the brand suffers as a result. Successful companies supply exaggerated but mostly true information about their products. The same is true with tech algorithms—they have to be mostly true in order to work. 
'''
    #voice_name = "af_bella"
    voice_name = "af_emma"
    mp3_file_path = tts_kokoro(mp3_file_path, text_input, voice_name)
    print(mp3_file_path)

def create_kokoro_voice_samples(sample_text, output_dir="apps/voice/kokoro/kokoro_audio/samples"):
    """
    Create audio samples for all available Kokoro voices.

    :param output_dir: str, directory where voice samples will be saved
    :param sample_text: str, text to use for the voice samples
    :return samples: list, paths to all generated sample files
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize Kokoro
        # Override numpy's default pickle security
        np.load.__defaults__ = (None, True, True, 'ASCII')
        kokoro = Kokoro(KOKORO_MODEL_PATH, KOKORO_VOICES_PATH)
        
        # Track generated samples
        generated_samples = []
        
        # Generate sample for each voice
        for voice in kokoro.get_voices():
            output_path = os.path.join(output_dir, f"{voice}.mp3")
            samples, sample_rate = kokoro.create(
                sample_text,
                voice=voice,
                speed=1.0
            )
            sf.write(output_path, samples, sample_rate)
            print(f"Created {output_path}")
            generated_samples.append(output_path)
            
        return generated_samples
            
    except ImportError as e:
        print(f"ERROR in create_kokoro_voice_samples - Required module not found: {e}")
        return None
    except Exception as e:
        print(f"ERROR in create_kokoro_voice_samples - An error occurred: {e}")
        return None
def mrun_create_kokoro_voice_samples():
    pass
#if __name__ == "__main__":
    sample_text = "The truth is that these companies can't control us simply by knowing what we want, any more than television or print advertising can."
    create_kokoro_voice_samples(sample_text)

def create_list_of_strings_from_md_file(md_file_path, heading_level, strip_md_headings=True, verbose=True):
    """
    Creates a list of strings from a markdown file, where each string contains the text between headings of the specified level.

    :param md_file_path: string, path to the markdown file to process.
    :param heading_level: int, the heading level to split on (e.g., 2 for '## ' headings).
    :param strip_md_headings: bool, if True removes markdown heading markers from the text.
    :param verbose: bool, if True prints character counts for each section.
    :return: list of strings, where each string contains the text between headings of the specified level.
    """
    # Read the complete text from the file
    try:
        with open(md_file_path, 'r', encoding='utf-8') as file:
            complete_text = file.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return []
    
    # Create the heading pattern to match (e.g., '## ' for level 2)
    heading_pattern = '#' * heading_level + ' '
    
    # Split the text into sections based on the heading pattern
    sections = []
    current_section = []
    lines = complete_text.splitlines()
    
    for line in lines:
        # Check if this line is a heading of our target level
        if line.startswith(heading_pattern):
            # If we have accumulated text in current_section, join it and add to sections
            if current_section:
                sections.append('\n'.join(current_section))
            # Start a new section with this heading
            if strip_md_headings:
                # Remove any number of hashtags followed by a space at start of line
                line = line.lstrip('#').lstrip()
            current_section = [line]
        # Check if this line is a heading of a lower level (more #'s)
        elif line.startswith('#') and len(line) - len(line.lstrip('#')) < heading_level:
            # Skip headings of lower levels (e.g., skip '# ' when looking for '## ')
            continue
        # If we're inside a section, add the line
        elif current_section:
            if strip_md_headings and line.startswith('#'):
                # Remove any number of hashtags followed by a space at start of line
                line = line.lstrip('#').lstrip()
            current_section.append(line)
    
    # Add the last section if it exists
    if current_section:
        sections.append('\n'.join(current_section))
    if verbose:
      total_chars = 0
      for string in sections:
          first_line = string.split('\n')[0]
          char_count = len(string)
          total_chars += char_count
          print(f"{first_line}   {char_count//1000} K characters")
      print(f"Total: {total_chars//1000} K characters\n")

    return sections
def strip_text_between(text, strip_patterns):
    """
    Strips text between specified patterns. Each pattern is a tuple of (start, end) strings.
    If start is None, strips from beginning to end pattern.
    If end is None, strips from start pattern to end of text.
    
    :param text: str, the input text to process
    :param strip_patterns: None or list of tuples, each tuple contains (start, end) strings
    :return: str, the processed text with specified sections removed
    """
    if not strip_patterns:
        return text
    
    result = text
    for start_pat, end_pat in strip_patterns:
        if start_pat is None and end_pat is not None:
            # Strip from start to end_pat
            end_idx = result.find(end_pat)
            if end_idx != -1:
                end_idx += len(end_pat)
                result = result[end_idx:]
        elif start_pat is not None and end_pat is None:
            # Strip from start_pat to end
            start_idx = result.find(start_pat)
            if start_idx != -1:
                result = result[:start_idx]
        elif start_pat is not None and end_pat is not None:
            # Strip between start_pat and end_pat
            while True:
                start_idx = result.find(start_pat)
                if start_idx == -1:
                    break
                end_idx = result.find(end_pat, start_idx)
                if end_idx == -1:
                    break
                end_idx += len(end_pat)
                result = result[:start_idx] + result[end_idx:]
    
    return result

def tts_kokoro_on_input_md_file(md_file_path, heading_level=None, voice_name="af_nicole", output_dir="output", strip_text=None, skip_existing=True):
    """
    Converts markdown file content to speech using Kokoro TTS, either as a single file or split by headings.

    :param md_file_path: str, path to the markdown file to process
    :param heading_level: int or None, level of headings to split on (e.g., 2 for '## '), or None for single file
    :param voice_name: str, name of the Kokoro voice to use for TTS
    :param output_dir: str, directory where output MP3 files will be saved
    :param strip_text: None or list of tuples, patterns to strip from text before processing
    :param skip_existing: bool, whether to skip processing if output file already exists
    :return output_files: list, paths to all generated MP3 files
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    output_files = []
    
    if heading_level is None:
        # Get content using read_file_flex
        _, input_text = read_file_flex(md_file_path)
        print(f"After read_file_flex: {len(input_text)} chars")
        
        # Preprocess the text
        input_text = strip_initial_headings_in_text(input_text)
        #print(f"After preprocessing: {len(input_text)} chars")
        
        # Strip specified text patterns
        input_text = strip_text_between(input_text, strip_text)
        #print(f"After strip_text_between: {len(input_text)} chars")
        
        if len(input_text.strip()) == 0:
            print("WARNING: Input text is empty after processing!")
            return output_files
        
        # Create output filepath using the markdown filename
        base_name = os.path.splitext(os.path.basename(md_file_path))[0]
        output_file_path = os.path.join(output_dir, f"{base_name}.mp3")
        
        # Skip if file exists and skip_existing is True
        if os.path.exists(output_file_path) and skip_existing:
            print(f"Skipping existing file: {output_file_path}")
            return [output_file_path]
            
        # Process the entire file
        chars = len(input_text)
        if chars < 1000:
            print(f"Processing kokoro tts for {output_file_path} with {chars} chars")
        else:
            print(f"Processing kokoro tts for {output_file_path} with K chars: {chars//1000}")
        tts_kokoro(output_file_path, input_text, voice_name, add_kokoro_suffix=False)
        output_files.append(output_file_path)
    
    else:
        # Original code for splitting by heading level
        list_of_strings = create_list_of_strings_from_md_file(md_file_path, heading_level)
        for string in list_of_strings:
            # Get the first line and clean it to create the filename
            first_line = string.split('\n')[0]
            # Remove heading markers and clean the filename
            clean_title = first_line.lstrip('#').strip()
            # Create output filepath
            output_file_path = os.path.join(output_dir, f"{clean_title}.mp3")
            
            # Skip if file exists and skip_existing is True
            if os.path.exists(output_file_path) and skip_existing:
                print(f"Skipping existing file: {output_file_path}")
                print()
                output_files.append(output_file_path)
                continue
                
            # Call tts_kokoro with add_kokoro_suffix=False
            chars = len(string)
            if chars < 1000:
                print(f"Processing kokoro tts for {output_file_path} with {chars} chars")
            else:
                print(f"Processing kokoro tts for {output_file_path} with K chars: {chars//1000}")
            tts_kokoro(output_file_path, string, voice_name, add_kokoro_suffix=False)
            output_files.append(output_file_path)
            print()
    
    return output_files
def mrun_tts_kokoro_sovereign_child():
    pass
#if __name__ == "__main__":
    md_file_path = "data/misc_books/Sovereign Child/The Sovereign Child_sections.md"
    heading_level = 2
    voice_name = "af_nicole"
    output_dir = "data/misc_books/Sovereign Child/kokoro"
    tts_kokoro_on_input_md_file(md_file_path, heading_level, voice_name, output_dir)
def mrun_tts_kokoro_tcs_articles():
    pass
if __name__ == "__main__":
    md_file_path = "data/deutsch/essays/tcs/dd/2002-12-18_TCS Site_Enacting a theory.md"
    
    # Verify file exists
    if not os.path.exists(md_file_path):
        print(f"ERROR: File not found: {md_file_path}")
        exit(1)
        
    # Try reading file directly
    try:
        with open(md_file_path, 'r', encoding='utf-8') as f:
            print(f"File can be read, size: {len(f.read())} chars")
    except Exception as e:
        print(f"ERROR reading file: {e}")
        exit(1)
    
    heading_level = None
    voice_name = "am_michael"
    strip_patterns = [("**See also:**", None)]
    output_dir = "data/deutsch/essays/tcs/dd/audio-kokoro"
    tts_kokoro_on_input_md_file(md_file_path, heading_level, voice_name, output_dir, strip_patterns)