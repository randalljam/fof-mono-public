# ===== START OF FILE core/corpuses.py =====
# Library of functions and execution code to do corpus tasks

import os
import re
import warnings
from pathlib import Path
import csv
from collections import defaultdict
import urllib.parse
import pickle
import zipfile

from core.fileops import *
from core.transcribe import *
from core.conversion import *
from core.structured import *
from core.llm import *
from core.aws import *
from core.dbgen import *
from core.webflow_api import *
from core.vectordb import *
from core.rag import *
from core.rag_prompts_routes import *

# ---START OF SYNCED CODE--- only code below will be synchronized with chalicelib.


# Set the warnings to use a custom format
warnings.formatwarning = custom_formatwarning
# USAGE: warnings.warn(f"Insert warning message here")

CUSTOM_VALIDATORS = {
    "STARS": validate_stars,
    "TOPICS": validate_topics
}

### MRUN GUARD
def _guard_multiple_mrun_blocks():
    """
    Checks for multiple uncommented 'if __name__ == "__main__":' blocks.
    Warns and prompts user if more than one is found. Only runs when file is executed directly.
    """
    if __name__ != "__main__":
        return
    with open(__file__, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    active_blocks = []
    for i, line in enumerate(lines, 1):
        stripped = line.lstrip()
        # Only match 'if __name__ == "__main__":' (not != checks)
        if stripped.startswith('if __name__') and '==' in stripped and '__main__' in stripped and stripped.rstrip().endswith(':'):
            active_blocks.append((i, line.rstrip()))
    if len(active_blocks) > 1:
        print(f"\n⚠️  WARNING: {len(active_blocks)} uncommented 'if __name__' blocks found!")
        for line_num, line_text in active_blocks:
            print(f"  Line {line_num}: {line_text}")
        response = input("\nPress N to abort, any other key to continue: ")
        if response in ('n', 'N'):
            import sys
            sys.exit(0)
_guard_multiple_mrun_blocks()

### S3 WEBFLOW UPLOADS
def collect_s3_source_files(folder_path, transcript_suffix, qa_suffix):
    transcript_html = get_files_in_folder(folder_path, suffixpat_include=transcript_suffix + ".html")
    transcript_md   = get_files_in_folder(folder_path, suffixpat_include=transcript_suffix + ".md")
    qa_html         = get_files_in_folder(folder_path, suffixpat_include=qa_suffix + ".html")
    qa_md           = get_files_in_folder(folder_path, suffixpat_include=qa_suffix + ".md")
    return transcript_html, transcript_md, qa_html, qa_md
def build_s3_source_file_mapping(files_group, config, s3_upload=True, s3_prompt_overwrite=True):
    # files_group is a tuple of file lists (transcript_html, transcript_md, qa_html, qa_md)
    transcript_html, transcript_md, qa_html, qa_md = files_group
    file_mapping = defaultdict(dict)
    total_base_names = set()
    total_files = 0

    file_groups = [
        (transcript_html, "transcripts-html/", "transcript_html"),
        (transcript_md, "transcripts-md/", "transcript_md"),
        (qa_html, "qa-html/", "qa_html"),
        (qa_md, "qa-md/", "qa_md")
    ]
    
    for files, s3_subfolder, key_suffix in file_groups:
        for file_path in files:
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            base_name = re.sub(f'{config["transcript_suffix"]}$|{config["qa_suffix"]}$', '', base_name)
            total_base_names.add(base_name)
            
            if s3_upload:
                upload_file_to_s3(
                    file_path, 
                    bucket=config["bucket"], 
                    s3_path=config["s3_path"] + s3_subfolder, 
                    prompt_overwrite=s3_prompt_overwrite
                )
                total_files += 1
            
            encoded_filename = urllib.parse.quote(os.path.basename(file_path))
            s3_url = f"https://{config['bucket']}.s3.us-west-2.amazonaws.com/{config['s3_path']}{s3_subfolder}{encoded_filename}"
            file_mapping[base_name][key_suffix] = s3_url

            # Handle metadata fields for transcript MD files
            if key_suffix == "transcript_md":
                # Get metadata field mapping from config, or use empty dict if not provided
                metadata_mapping = config.get("metadata_field_mapping", {})
                
                # Read each metadata field and map to the corresponding CMS field name
                for md_field, cms_field in metadata_mapping.items():
                    _, field_value = read_metadata_field_from_file(file_path, md_field)
                    # Convert 'link youtube' -> 'youtube_url' for internal mapping
                    internal_key = cms_field.replace('-', '_').lower()
                    file_mapping[base_name][internal_key] = field_value

    print(f"S3 Upload Summary: {len(total_base_names)} base names processed, {total_files} files uploaded.")
    return file_mapping
def create_cms_item_list(file_mapping, config):
    cms_items = []
    metadata_mapping = config.get("metadata_field_mapping", {})
    # Create reverse mapping from internal keys to CMS field names
    reverse_mapping = {cms_field.replace('-', '_').lower(): cms_field 
                      for _, cms_field in metadata_mapping.items()}
    
    for base_name, urls in file_mapping.items():
        if all(key in urls for key in ["transcript_html", "transcript_md", "qa_html", "qa_md"]):
            cms_name = base_name
            if config.get("cms_item_name_old") and config.get("cms_item_name_new"):
                cms_name = base_name.replace(config["cms_item_name_old"], config["cms_item_name_new"])
            
            # Start with required fields
            cms_item = {
                "name": cms_name,
                "s3-transcript-html-url": urls["transcript_html"],
                "s3-qa-html-url": urls["qa_html"],
                "s3-transcript-md-url": urls["transcript_md"],
                "s3-qa-md-url": urls["qa_md"],
            }
            
            # Add mapped metadata fields
            for internal_key, cms_field in reverse_mapping.items():
                cms_item[cms_field] = urls.get(internal_key, "")
            
            cms_items.append(cms_item)
    
    return cms_items
def process_webflow_cms(cms_items, config, webflow_cms_prompt_overwrite=True):
    collection_details = webflow_cms_get_collection_details(config["collection_id"], verbose=True)
    if not collection_details:
        print("Failed to fetch collection details for validation")
        return
    
    existing_items = webflow_cms_list_items(config["collection_id"], verbose=True)
    is_updating = False
    existing_items_map = {}
    if existing_items:
        existing_names = [item['fieldData'].get('name', '') for item in existing_items]
        existing_items_map = {item['fieldData'].get('name', ''): item['id'] for item in existing_items}
        overlapping_items = [cms_name for cms_name in 
                             [item["name"] for item in cms_items] if cms_name in existing_names]
        if overlapping_items:
            print("The following items already exist in the Webflow CMS:")
            for name in overlapping_items:
                print(f"- {name}")
            if webflow_cms_prompt_overwrite:
                response = input("Press Enter to proceed with updating these items, or 'x' to abort: ").lower()
                if response == 'x':
                    print("Aborting operation.")
                    return
            is_updating = True
    
    for item in cms_items:
        if is_updating and item['name'] in existing_items_map:
            result = webflow_cms_update_item(
                collection_id=config["collection_id"],
                item_id=existing_items_map[item['name']],
                field_data=item,
                collection_validation=False,
                verbose=True
            )
            if not result:
                print(f"Failed to update CMS item for {item['name']}")
        else:
            result = webflow_cms_create_item(
                collection_id=config["collection_id"],
                field_data=item,
                collection_validation=False,
                verbose=True
            )
            if not result:
                print(f"Failed to create CMS item for {item['name']}")
def process_corpus_s3_webflow_upload(config, s3_upload=True, webflow_upload=True, s3_prompt_overwrite=True, webflow_cms_prompt_overwrite=True):
    # Step 1: Collect Files
    files = collect_s3_source_files(config["folder_path"], config["transcript_suffix"], config["qa_suffix"])
    
    # Step 2: Build File Mapping and Upload to S3
    file_mapping = build_s3_source_file_mapping(files, config, s3_upload, s3_prompt_overwrite)
    
    # Step 3: Pause for confirmation before Webflow operations (if desired)
    if webflow_upload:
        response = input("Press Enter to continue with Webflow CMS operations, or 'x' to abort: ").lower()
        if response == 'x':
            print("Aborting operation.")
            return
    
    # Step 4: Create CMS Item List
    cms_items = create_cms_item_list(file_mapping, config)
    
    # Step 5: Process Webflow CMS Items
    if webflow_upload:
        process_webflow_cms(cms_items, config, webflow_cms_prompt_overwrite)
def mrun_process_corpus_s3_webflow_upload():
    pass
#if __name__ == "__main__":
    config = CONFIG_S3_WEBFLOW_UPLOAD_MY_CORPUS_HERE
    process_corpus_s3_webflow_upload(config, s3_upload=True, webflow_upload=True, s3_prompt_overwrite=True, webflow_cms_prompt_overwrite=True)

### GENERIC CORPUS
def count_chars_words_tokens(text):
    """
    Counts the number of characters, words, and tokens in a given text.

    :param text: string of text to be analyzed.
    :return: tuple of integers representing the number of characters, words, and tokens in the input text.
    """
    num_chars = len(text)
    num_words = len(text.split())
    num_tokens = count_tokens(text)  # in llm.py
    return num_chars, num_words, num_tokens
def count_chars_words_tokens_in_file(file_path):
    """
    Counts the number of characters, words, and tokens in a given file.

    :param file_path: string of the path to the file to be analyzed.
    :return: tuple of integers representing the number of characters, words, and tokens in the input file.
    """
    try:
        _, content = read_metadata_and_content(file_path)
    except:
        # If read_metadata_and_content fails, read the entire file
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
    
    # Check if content is actually text
    if not isinstance(content, str):
        raise ValueError(f"File content is not text: {file_path}")
    
    return count_chars_words_tokens(content)
def mtest_count_chars_words_tokens_in_file():
    pass
#if __name__ == "__main__":
    file_path = "data/sovereign-child/book/2025-01-11_Book - The Sovereign Child by Dr Aaron Stupple_section-titles.md"
    num_chars, num_words, num_tokens = count_chars_words_tokens_in_file(file_path)
    print(f"{'Number of characters:':<22} {num_chars:>10,}")
    print(f"{'Number of words:':<22} {num_words:>10,}")
    print(f"{'Number of tokens:':<22} {num_tokens:>10,}")
def create_csv_with_chars_words_tokens(output_file_path, folder_list, suffixpat_include=None, include_subfolders=False):
    """
    Creates a CSV file with the number of characters, words, and tokens for each file in a given folder.

    :param output_file_path: string of the path to the output CSV file.
    :param folder_list: list of strings representing paths to folders to be analyzed.
    :param suffixpat_include: string of the suffix pattern to be included in the analysis.
    :param include_subfolders: boolean indicating whether to include subfolders in the analysis.
    """
    # Create a list to store the results
    results = []
    
    # Process each folder separately
    for folder_path in folder_list:
        print(f"Processing folder: {folder_path}")
        
        # Get files for this folder
        folder_files = get_files_in_folder(folder_path, suffixpat_include=suffixpat_include, include_subfolders=include_subfolders)
        
        # Process each file in this folder
        for file_path in folder_files:
            file_name = os.path.basename(file_path)
            num_chars, num_words, num_tokens = count_chars_words_tokens_in_file(file_path)
            results.append([file_path, file_name, num_chars, num_words, num_tokens])
            print(f"  {file_name}: {num_chars} chars, {num_words} words, {num_tokens} tokens")
        
        # Print blank line after each folder to delineate sections
        print("\n")

    # Write the combined results to a CSV file
    with open(output_file_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['File Path', 'File Name', 'Characters', 'Words', 'Tokens'])
        writer.writerows(results)

#### TRANSCRIBE
def mrun_transcribe_using_callback():
    pass
#if __name__ == "__main__":
    videos_to_process = [  #  (title, link)
        ("2025-09-24_Alex Springer Award - Sam Altman and David Deutsch discuss AGI", "https://youtu.be/WZ22AJmuKKQ"),
    ] 
    process_multiple_videos(videos_to_process) # default set to audio_inbox, 'whisper-medium' 'nova-2-general' 'whisper-large' 'nova-2-meeting' 'enhanced-meeting'

    print("TESTING DOWNLOAD DEEPGRAM CALLBACK WAITING")     
    download_deepgram_callback_waiting()
def mrun_transcribe_with_audio_only():
    pass
#if __name__ == "__main__":
    audio_file_path = "data/audio_inbox/2025-09-24_Alex Springer Award - Sam Altman and David Deutsch discuss AGI.mp3"
    link = "https://youtu.be/WZ22AJmuKKQ"  # Can be None if no YouTube link exists
    model = "whisper-medium"  # Or other Deepgram model like "whisper-medium"
    process_deepgram_transcription_sync_from_audio_file(audio_file_path, link, model)

### DEUTSCH CORPUS
def mrun_create_deustch_qa_from_prepqa():
    pass
#if __name__ == "__main__":
    apply_to_folder(create_qa_file_select_speaker, 'data/deutsch/f5_run_qa_now', 'David Deutsch', FCALL_PROMPT_QA_DEUTSCH, suffixpat_include='_prepqa')
def mrun_create_deustch_qa_multi():
    pass
#if __name__ == "__main__":
    source_folder = 'data/deutsch/f6_needs_qafixed'
    for qa_file in os.listdir(source_folder):
        if qa_file.endswith('_qafixed.md'):
            qa_file_path = os.path.join(source_folder, qa_file)
            qa_multi_file_path = create_qa_multi_file_from_qa(qa_file_path, verbose=True)
            
            # Create copy with space appended to filename
            copy_folder = 'data/deutsch/fx_archive'
            qa_multi_file_name = os.path.basename(qa_multi_file_path)
            qa_multi_file_name_copy = qa_multi_file_name.replace('.md', ' copy.md')
            qa_multi_file_path_copy = os.path.join(copy_folder, qa_multi_file_name_copy)
            
            # Copy the file
            shutil.copy2(qa_multi_file_path, qa_multi_file_path_copy)
            print(f"Processed {qa_file}")

            set_last_updated(qa_multi_file_path, "RT multi-QA manual edits")


DEUTSCH_REQUIRED_FIELDS = ["QUESTION", "TIMESTAMP", "ANSWER", "TOPICS", "STARS"]  
DEUTSCH_FOLDER_PATHS = ["data/deutsch/f8_done_qafixed_and_vrb", "data/deutsch/f8_qafixed_talks"]
def mrun_renumber_multi_qa_deutsch():
    pass
#if __name__ == "__main__":
    for folder in ["data/deutsch/f9_process"]: #DEUTSCH_FOLDER_PATHS:
        apply_to_folder(renumber_multi_qa, folder, suffixpat_include="_qa-multi.md")
def mrun_get_num_questions_multi_qa_deutsch():
    pass
#if __name__ == "__main__":
    total_questions = 0
    for folder in DEUTSCH_FOLDER_PATHS:
        for file in os.listdir(folder):
            if file.endswith("_qa-multi.md"):
                file_path = os.path.join(folder, file)
                num_questions = get_num_questions_multi_qa(file_path)
                total_questions += num_questions
                #print(f"{file}: {num_questions} questions")
    print(f"\nTotal questions across all files: {total_questions}")
def validate_corpus_deutsch():
    validate_blocks_in_folders(DEUTSCH_FOLDER_PATHS, DEUTSCH_REQUIRED_FIELDS, CUSTOM_VALIDATORS, suffixpat_include="_qa-multi")
def mrun_validate_corpusdeutsch():
    pass
#if __name__ == "__main__":
    validate_corpus_deutsch()
def mrun_create_qrag_vector_db_deutsch(): # RUN VALIDATION FIRST
    pass
#if __name__ == "__main__":
    create_qrag_vectordb(DEUTSCH_FOLDER_PATHS, "deutsch-transcript-qrag", suffixpat_include="_qa-multi.md", embedding_field="QUESTION", date_from_filename=True, dummy_run=False)
def mrun_misc_corpus_deutsch():
    pass
#if __name__ == "__main__":
    cur_topics_matrix_csv = "data/deutsch/topics_matrix.csv"
    # cur_topics_matrix_csv = create_topics_matrix(DEUTSCH_FOLDER_PATHS)
    
    # cur_find_replace_pairs = [("%", " percent")]
    # for folder_path in DEUTSCH_FOLDER_PATHS:
    #     apply_to_folder(find_and_replace_pairs, folder_path, cur_find_replace_pairs)
    
    # change_topic_in_folders(DEUTSCH_FOLDER_PATHS, "quantum computer", "quantum computation")
    # review_singlet_topic(DEUTSCH_FOLDER_PATHS, cur_topics_matrix_csv, "z")
def mrun_deutsch_download_new_s3_files():
    pass
#if __name__ == "__main__":
    bucket = '[S3-BUCKET]'
    s3_path = 's3-qrag-deutsch-v3'
    local_folder = 'exchanges/deutsch_qrag'
    download_new_s3_files(bucket, s3_path, local_folder)
def mrun_deutsch_index_exchanges_and_pii():
    pass
#if __name__ == "__main__":
    root_folder = 'exchanges/deutsch_qrag'  # Replace with your root folder
    exclude_subfolders = None  # ['not-reviewed']
    db_path = index_exchanges_in_db(root_folder, exclude_subfolders)

    # db_path = 'exchanges/deutsch_qrag/exchanges.db'
    users_csv_path = 'exchanges/deutsch_qrag/pii-users.csv'
    copy_exchanges_db_with_user_pii(db_path, users_csv_path) 
def mtest_qrag_2step_deutsch():
    pass
#if __name__ == "__main__":
    cur_query = "What is the meaning of life?"
    cur_routes_dict = ROUTES_DICT_DEUTSCH_M1
    cur_vector_index_name = 'deutsch-transcript-qrag-95f-20250923'
    qrag_2step(cur_query, cur_vector_index_name, 10, cur_routes_dict)

def mrun_find_and_replace_on_deutsch():
    pass
#if __name__ == "__main__":  
    csv_file_path = "data/deutsch/findandreplace_deutsch.csv"
    # folder_path = "data/deutsch/dd_test_files"
    # suffixpat_include = "_vrb.md"
    # find_and_replace_from_csv(folder_path, csv_file_path, suffixpat_include=suffixpat_include, include_subfolders=False, include_metadata=True, verbose=True)
    # # ALL
    folders = ["data/deutsch/f8_done_qafixed_and_vrb", "data/deutsch/f8_qafixed_talks", "data/deutsch/f8_vrb_talks_only"]
    suffix_pats = ["_vrb.md", "_qafixed.md"]
    for folder in folders:
        for suffix_pat in suffix_pats:
            find_and_replace_from_csv(folder, csv_file_path, suffixpat_include=suffix_pat, include_subfolders=False, include_metadata=True, verbose=True)
def mrun_move_files_deutsch():
    pass
#if __name__ == "__main__":
    source_folders = DEUTSCH_FOLDER_PATHS
    destination_folder = "data/deutsch/fx_archive"
    suffixpat_include = "_propernames.md"
    for source_folder in source_folders:
        move_files_with_suffix(source_folder, destination_folder, suffixpat_include)

def mrun_create_top_stars_files_deutsch():  # 2-4-25 RT
    pass
#if __name__ == "__main__":
    folders = DEUTSCH_FOLDER_PATHS
    #folders = ["data/deutsch/f9_process"]  # 1st copy orig _qafixed and _vrb to this folder, then delete them after and copy new top-stars files there
    destination_folder = "data/deutsch/dd_top-stars_qa-multi"
    for folder in folders:
        qafixed_files = get_files_in_folder(folder, suffixpat_include='_qa-multi.md')
        for qafixed_file in qafixed_files:
            qa_top_stars_file_path = create_qa_top_stars_file(qafixed_file, num_blocks=5)
            print(create_transcript_top_stars_file(qa_top_stars_file_path))
        move_files_with_suffix(folder, destination_folder, suffixpat_include='_qa-topstars.md')
        move_files_with_suffix(folder, destination_folder, suffixpat_include='_vrb-topstars.md')
def mrun_create_html_files_for_deutsch():  # 2-3-25 RT
    pass
#if __name__ == "__main__":
    cur_folder_path = "data/deutsch/dd_top-stars_qa-multi"
    #cur_folder_path = "data/deutsch/dd_test_files"
    transcript_md_files_to_run = get_files_in_folder(cur_folder_path, suffixpat_include='_vrb-topstars.md')
    qa_md_files_to_run = get_files_in_folder(cur_folder_path, suffixpat_include='_qa-topstars.md')
    css_file_path = ""  # was "transcript-with-section-titles.css" for local testing
    new_heading_text = "David Deutsch Corpus" # 9-23-25 comment out h_tune_html_file(html_file_path, new_heading_text, 1)

    # transcripts
    for i, md_file_path in enumerate(transcript_md_files_to_run, 1):
        html_file_path = convert_markdown_to_html(md_file_path, heading="### transcript", css_file_path=css_file_path)
        #h_tune_html_file(html_file_path, new_heading_text, 1)
        clean_summaries_in_html_file(html_file_path)
        add_additional_html_from_template(html_file_path, "web-shared/md_to_html_dev/additions_transcript.html")

    # qa
    for i, md_file_path in enumerate(qa_md_files_to_run, 1):
        html_file_path = convert_markdown_to_html(md_file_path, heading="### qa", css_file_path=css_file_path)
        #h_tune_html_file(html_file_path, new_heading_text, 1)
        h_tune_html_file(html_file_path, "Extracted Question and Answer", 3, insert=False)
        wrap_qa_blocks_in_details(html_file_path, "QUESTION", "ANSWER")
        clean_summaries_in_html_file(html_file_path)
        add_additional_html_from_template(html_file_path, "web-shared/md_to_html_dev/additions_qa.html")
    
WEBFLOW_CMS_COLLECTION_ID_DEUTSCH_TRANSCRIPTS = "67a249cf5625c057b2fd345c"
CONFIG_S3_WEBFLOW_UPLOAD_DEUTSCH_TRANSCRIPTS = {
    "folder_path": "data/deutsch/f9_process", #"data/deutsch/dd_top-stars_qa-multi",
    "transcript_suffix": "_vrb-topstars",
    "qa_suffix": "_qa-topstars",
    "bucket": "fofpublic",
    "s3_path": "deutsch-sources-top-stars/",
    "collection_id": WEBFLOW_CMS_COLLECTION_ID_DEUTSCH_TRANSCRIPTS,
    "cms_item_name_old": "",
    "cms_item_name_new": "",
    "metadata_field_mapping": {
        "link youtube": "youtube-url",
        "link spotify": "spotify-url"
    }
}
def mrun_process_corpus_s3_webflow_upload():
    pass
#if __name__ == "__main__":
    config = CONFIG_S3_WEBFLOW_UPLOAD_DEUTSCH_TRANSCRIPTS
    process_corpus_s3_webflow_upload(config, s3_upload=True, webflow_upload=False, s3_prompt_overwrite=False, webflow_cms_prompt_overwrite=True)

def mrun_copy_suffix_files_deutsch():
    pass
#if __name__ == "__main__":
    # source_folder_list = DEUTSCH_FOLDER_PATHS
    # destination_folder = "/Users/randytrue/Documents/Code/copyrighted-files-private/dd-transcripts"
    # suffixpat_include_list = ["_vrb", "_read-qafixed"]
    
    # FOR RAW _dgwhspm files
    source_folder_list = ["data/deutsch/f9_raw"]
    destination_folder = "/Users/randytrue/Documents/Code/copyrighted-files-private/dd-transcripts"
    suffixpat_include_list = ["_dgwhspm.json", "_dgwhspm.md"]
    
    for source_folder in source_folder_list:
        for suffixpat_include in suffixpat_include_list:
            results = copy_files_with_suffix(source_folder, destination_folder, suffixpat_include)
            file_count = len(results)
            print(f"{file_count} files copied from '{source_folder}' with suffix '{suffixpat_include}'")
def mrun_create_csv_with_chars_words_tokens_deutsch():
    pass
#if __name__ == "__main__":
    source_folder_list = ["data/deutsch/f8_done_qafixed_and_vrb", "data/deutsch/f8_qafixed_talks", "data/deutsch/f8_vrb_talks_only"]
    output_file_path = "data/deutsch/dd_chars_words_tokens.csv"
    suffixpat_include = "_vrb"
    include_subfolders = False
    create_csv_with_chars_words_tokens(output_file_path, source_folder_list, suffixpat_include, include_subfolders)


### PV EVAC CORPUS
PV_EVAC_FULL_FIELDS = ["QUESTION", "TIMESTAMP", "ANSWER", "QUESTION NAME", "ANSWER NAME", "ORIGINAL QUESTION", "STATUS", "TOPICS", "STARS"]
PV_EVAC_REQUIRED_FIELDS = ["QUESTION", "TIMESTAMP", "ANSWER", "QUESTION NAME", "ANSWER NAME", "STATUS", "TOPICS", "STARS"]
def mrun_propagate_fields_pv_evac():
    pass
#if __name__ == "__main__":
    file_path = 'data/pv/pv_epc_evac/2023-09-20_PVSD WFPD - Wildfire Preparedness Parent Presentation 1_qaman.md'
    #file_path = "data/pv/pv_epc_evac/2023-11-15_PVSD WFPD - Wildfire Preparedness Parent Presentation 2_qaman.md"
    #file_path = "data/pv/pv_epc_evac/2024-10-23_PVSD WFPD - Wildfire Preparedness Parent Presentation 3_qaman.md"
    propagate_fields_by_subheading(file_path, PV_EVAC_FULL_FIELDS, PV_EVAC_REQUIRED_FIELDS, delete_fields=["QUESTION NUMBER"], heading = "### qa")   

PV_EVAC_FOLDER_PATHS = ["data/pv/pv_epc_evac"]
def validate_corpus_pv_evac():
    validate_blocks_in_folders(PV_EVAC_FOLDER_PATHS, PV_EVAC_REQUIRED_FIELDS, CUSTOM_VALIDATORS, suffixpat_include="_qaprop")
def mrun_pv_epc_corpus():
    pass
#if __name__ == "__main__":
    #validate_corpus_pv_evac()

    # from core.conversion import convert_markdown_to_md_mod_text
    # file_path = 'data/pv/pv_epc_evac/2023-09-20_PVSD WFPD - Wildfire Preparedness Parent Presentation 1_combo.md'
    # convert_markdown_to_md_mod_text(file_path)
    # file_path = "data/pv/pv_epc_evac/2023-11-15_PVSD WFPD - Wildfire Preparedness Parent Presentation 2_combo.md"
    # convert_markdown_to_md_mod_text(file_path)
    # file_path = "data/pv/pv_epc_evac/2024-10-23_PVSD WFPD - Wildfire Preparedness Parent Presentation 3_combo.md"
    # convert_markdown_to_md_mod_text(file_path)
    
    create_qrag_vectordb(PV_EVAC_FOLDER_PATHS, "pv-evac-qrag", suffixpat_include="_qaprop", embedding_field="QUESTION", date_from_filename=True)
def mtest_qrag_2step_pv_evac():
    pass
#if __name__ == "__main__":
    cur_query = "What are the most important things parents need to know about related to evacuation in schools?"
    cur_routes_dict = ROUTES_DICT_PV_EVAC_V1
    cur_vector_index_name = 'pv-evac-qrag-3f-20241106'
    qrag_2step(cur_query, cur_routes_dict, cur_vector_index_name)
def mrun_create_pv_evac_multi_qa():  # 10-11-2025 RT
    pass
#if __name__ == "__main__":
    qa_file_path = "data/pv/pv_epc_evac/f2_draftqa/2024-10-23_PVSD WFPD - Wildfire Preparedness Parent Presentation 3_qafixed.md"
    qa_multi_file_path = create_qa_multi_file_from_qa(qa_file_path, verbose=True)
def mrun_renumber_pv_evacmulti_qa():
    pass
#if __name__ == "__main__":
    cur_file_path = "data/pv/pv_epc_evac/2024-10-23_PVSD WFPD - Wildfire Preparedness Parent Presentation 3_qa-multi.md"
    renumber_multi_qa(cur_file_path, verbose=True)

### FDA TOWNHALLS CORPUS
FDA_TOWNHALLS_REQUIRED_FIELDS = ["CLARIFIED QUESTION", "CLARIFIED ANSWER", "VERBATIM QUESTION", "VERBATIM ANSWER", "SPEAKER QUESTION", "SPEAKER ANSWER", "TOPICS", "REVIEW FLAG"]
FDA_TOWNHALLS_QA_FOLDER = "data/floodlamp/reg/fda-townhalls/f5_fixnames/a_done_site"
def remove_lines_fda_townhall(text):
    """ 
    Remove lines from a string of FDA townhall transcript text that match certain patterns.

    :param text: string of the transcript text to be cleaned.
    :return: string of the cleaned transcript text.
    """
    # Matches "Page X" where X is a number, or a line that starts with a number followed by whitespace, indicating a page header or footer.
    page_pattern = re.compile(r"^(Page \d+|\d+)\s*$", re.IGNORECASE)
    
    # Matches dates in various formats, e.g., "July 14, 2021", "3-25-20", followed by any text.
    date_pattern = re.compile(r"^(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}.*$|\d{1,2}-\d{1,2}-\d{2,4}.*$", re.IGNORECASE)
    
    # Matches time formats, e.g., "12:15 pm ET", "3:00 pm ET".
    time_pattern = re.compile(r"^\d{1,2}:\d{2} (?:am|pm) ET\s*$", re.IGNORECASE)
    
    # Matches introductory lines that typically start with the document title or section,
    # e.g., "Virtual Townhall", "FDA Virtual Town Hall Series – ", "FDA Virtual Town", "Virtual Town", "FDA Virtual Townhall"
    title_pattern = re.compile(r"^(?:Virtual Townhall|FDA Virtual Town Hall Series – |FDA Virtual Town|Virtual Town|FDA CDRH|Immediately in Effect Guidance|FDA Virtual Townhall)\s*$", re.MULTILINE)
    
    # Matches ending lines that typically say "END", "[ Event concluded ]", or a line with any number of asterisks with any amount of white space before or after
    end_pattern = re.compile(r"^(END|\[\s*Event concluded\s*\]|\s*\*+\s*)\s*$", re.IGNORECASE)
    
    # Matches moderator lines that include the moderator's name, e.g., "Moderator: Irene Aihie".
    # These lines are often part of the introductory section that precedes the actual content.
    moderator_pattern = re.compile(r"^Moderator: [A-Za-z\s]+\s*$", re.MULTILINE)
    
    # List of all patterns for iteration
    patterns = [page_pattern, date_pattern, time_pattern, title_pattern, end_pattern, moderator_pattern]
    
    # Split the text into lines
    lines = text.splitlines()
    
    # Apply each pattern and remove matching lines on a per-line basis
    cleaned_lines = []
    for line in lines:
        if not any(pattern.match(line) for pattern in patterns):
            cleaned_lines.append(line)
    
    # Join the cleaned lines back into a single string
    cleaned_text = "\n".join(cleaned_lines)
    # Remove extra newlines and spaces that might be left after removal
    #cleaned_text = re.sub(r'\n\s*\n', '\n\n', cleaned_text).strip()
    return cleaned_text
# TODO test after July refactor
def clean_fda_townhall_file(file_path):
    """
    Cleans the FDA townhall file by removing unnecessary lines and fixing speaker text.

    :param file_path: string of the path to the file to be cleaned.
    :param suffix_new: string of the suffix to be added to the cleaned file. Default is '_cleaned'.
    :return: The cleaned text with the heading set.
    """
    from core.fileops import get_heading, set_heading
    from core.docwork import reformat_transcript_text

    heading = "### transcript"
    text = get_heading(file_path, heading)
    
    cleaned1_text = remove_lines_fda_townhall(text)
    cleaned2_text = reformat_transcript_text(cleaned1_text)
    
    set_heading(file_path, '\n' + cleaned2_text, heading)
# TODO test after July refactor
def mtest_clean_fda_townhalls_file():
    pass
#if __name__ == "__main__":        
    cur_file_path = "tests/test_data_files/transcription/alignment_source.md"
    #cur_file_path = "data/floodlamp_fda/townhalls/f3_md_metadata/2022-06-15_Virtual Town Hall 87.md"
    clean_fda_townhall_file(cur_file_path)
def clean_fda_townhalls_folder(source_folder, destination_folder):
    """
    Cleans the files in the source folder and moves the cleaned files to the destination folder.

    :param source_folder: string of the path to the source folder containing the files to be cleaned.
    :param destination_folder: string of the path to the destination folder where the cleaned files will be moved.
    :return: None
    """
    apply_to_folder(clean_fda_townhall_file, source_folder)
    move_files_with_suffix(source_folder, destination_folder, "_cleaned")
# TODO WIP - add path to find_replace_csv after testing fileops func
def mtest_clean_fda_townhalls_folder():
    pass
#if __name__ == "__main__": 
    source_folder = "data/floodlamp_fda/townhalls/f3_md_metadata"
    destination_folder = "data/floodlamp_fda/townhalls/f4_md_cleaned"
    clean_fda_townhalls_folder(source_folder, destination_folder)
def mrun_fda_townhalls_create_speaker_matrix():
    pass
#if __name__ == "__main__": 
    from core.docwork import create_speaker_matrix
    create_speaker_matrix('data/floodlamp/reg/fda-townhalls/f5_fixnames','_fixnames', 'matrix_speakers_fdatownhalls.csv')
def mrun_find_and_replace_on_fda_townhalls():
    pass
#if __name__ == "__main__":     
    from core.fileops import find_and_replace_from_csv, apply_to_folder, sub_suffix_in_file
    
    # ***NOTE*** must manually copy orig-folder to create fixnames_folder, enter that new path below
    orig_folder = 'data/floodlamp_fda/townhalls/f4_md_cleaned_manualedits'
    suffix_orig = '_cleaned'
    fixnames_folder = 'data/floodlamp/reg/fda-townhalls/f5_fixnames/done_auto'
    suffix_new = '_section-titles'
    csv_file_path = 'data/floodlamp/reg/fda-townhalls/names_findandreplace_fda_townhalls.csv'
    
    # TODO need to fix in docwork
    #print(validate_townhalls(cur_folder_path))
    #print(create_speakers_matrix(cur_folder_path))
    #apply_to_folder(sub_suffix_in_file, fixnames_folder, suffix_new, suffixpat_include='_fixnamed')
    # ***NOTE*** must copy files before running
    #find_and_replace_from_csv(fixnames_folder, csv_file_path, suffixpat_include=suffix_orig, verbose=True)
    #apply_to_folder(sub_suffix_in_file, fixnames_folder, suffix_new, suffixpat_include=suffix_orig)
    # NEXT PASS
    find_and_replace_from_csv(fixnames_folder, csv_file_path, suffixpat_include=suffix_new, include_subfolders=True, verbose=True)
def mrun_corpus_fda_townhalls():
    pass
#if __name__ == "__main__":
    #validate_blocks_in_folders([FDA_TOWNHALLS_QA_FOLDER], FDA_TOWNHALLS_REQUIRED_FIELDS, CUSTOM_VALIDATORS, suffixpat_include="_qa-qonly.md")
    #validate_iso_dates_in_filename([FDA_TOWNHALLS_QA_FOLDER], suffixpat_include="_qa-qonly.md")
    create_qrag_vectordb([FDA_TOWNHALLS_QA_FOLDER], "fda-townhalls-qrag", suffixpat_include="_qa-qonly.md", embedding_field="CLARIFIED QUESTION", date_from_filename=True)

def csv_of_num_characters_transcript_and_qa(folder_path, transcript_suffix='_fixnames', qa_suffix='_qa-qonly'):
    """
    Creates a CSV file with character counts for transcript and QA files.

    :param folder_path: string, path to folder containing transcript and QA files
    :param transcript_suffix: string, suffix for transcript files
    :param qa_suffix: string, suffix for QA files
    :return csv_path: string, path to the created CSV file
    """
    # Get all transcript files
    transcript_file_paths = get_files_in_folder(folder_path, suffixpat_include=transcript_suffix)
    
    # Create CSV path in the folder
    csv_path = os.path.join(folder_path, 'character_counts.csv')
    
    # Write to CSV
    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # Write header
        writer.writerow(['base_name', 'transcript_chars', 'qa_chars'])
        
        # Process each file pair
        for transcript_file_path in transcript_file_paths:
            # Get base name (remove suffix and extension)
            base_name = os.path.basename(transcript_file_path)
            base_name = os.path.splitext(base_name)[0]  # Remove extension
            base_name = base_name[:-len(transcript_suffix)]  # Remove suffix
            
            # Get corresponding QA file path
            qa_file_path = sub_suffix_in_str(transcript_file_path, qa_suffix)
            
            # Get text content
            transcript_text = get_heading(transcript_file_path, '### transcript')
            qa_text = get_heading(qa_file_path, '### qa')
            
            # Get character counts
            transcript_chars = len(transcript_text) if transcript_text else 0
            qa_chars = len(qa_text) if qa_text else 0
            
            # Write row
            writer.writerow([base_name, transcript_chars, qa_chars])
    
    return csv_path
def mrun_csv_of_num_characters_transcript_and_qa():
    pass
#if __name__ == "__main__":
    cur_folder_path = "data/floodlamp/reg/fda-townhalls/f5_fixnames/done_auto"
    print(csv_of_num_characters_transcript_and_qa(cur_folder_path))
def mrun_section_titles():
    pass
#if __name__ == "__main__":
    cur_folder_path = "data/floodlamp/reg/fda-townhalls/f5_fixnames/a_run_auto"
    files_to_run = get_files_in_folder(cur_folder_path, suffixpat_include='_section-titles')

    for i, file_path in enumerate(files_to_run, 1):
        #write_section_titles(file_path, SCALL_PROMPT_SECTION_TITLE)
        propagate_section_titles_to_qa(file_path)
def mrun_convert_fda_townhalls_transcript_to_html():
    pass
#if __name__ == "__main__":
    md_file_path = "tests/test_data_files/fileops/document.md"
    css_file_path = "transcript-with-section-titles.css"
    html_file_path = convert_markdown_to_html(md_file_path, heading="### transcript", css_file_path=css_file_path)
    h_tune_html_file(html_file_path, "COVID-19 Diagnostics FDA", 1)
    add_additional_html_from_template(html_file_path, "tests/test_data_files/fileops/additions.html")
def mrun_convert_fda_townhalls_qa_to_html():
    pass
#if __name__ == "__main__":
    md_file_path = "tests/test_data_files/vectordb/synthetic_qafixed.md"
    css_file_path = "transcript-with-section-titles.css"
    html_file_path = convert_markdown_to_html(md_file_path, heading="### qa", css_file_path=css_file_path)
    h_tune_html_file(html_file_path, "COVID-19 Diagnostics FDA", 1)
    h_tune_html_file(html_file_path, "AI Extracted Question and Answer", 3, insert=False)
    wrap_qa_blocks_in_details(html_file_path, "CLARIFIED QUESTION", "CLARIFIED ANSWER")
    add_additional_html_from_template(html_file_path, "tests/test_data_files/fileops/additions.html")
def mrun_create_html_files_for_fda_townhalls():
    pass
#if __name__ == "__main__":
    cur_folder_path = "data/floodlamp/reg/fda-townhalls/f5_fixnames/a_run_auto"
    transcript_md_files_to_run = get_files_in_folder(cur_folder_path, suffixpat_include='_section-titles.md')
    qa_md_files_to_run = get_files_in_folder(cur_folder_path, suffixpat_include='_qa-qonly.md')
    css_file_path = ""  # was "transcript-with-section-titles.css"

    # transcripts
    for i, md_file_path in enumerate(transcript_md_files_to_run, 1):
        html_file_path = convert_markdown_to_html(md_file_path, heading="### transcript", css_file_path=css_file_path)
        h_tune_html_file(html_file_path, "FDA COVID-19 Diagnostics", 1)
        clean_summaries_in_html_file(html_file_path)
        add_additional_html_from_template(html_file_path, "web-shared/md_to_html_dev/additions_transcript.html")
    # save transcript html files

    # qa
    for i, md_file_path in enumerate(qa_md_files_to_run, 1):
        html_file_path = convert_markdown_to_html(md_file_path, heading="### qa", css_file_path=css_file_path)
        h_tune_html_file(html_file_path, "FDA COVID-19 Diagnostics", 1)
        h_tune_html_file(html_file_path, "AI Extracted Question and Answer", 3, insert=False)
        wrap_qa_blocks_in_details(html_file_path, "CLARIFIED QUESTION", "CLARIFIED ANSWER")
        clean_summaries_in_html_file(html_file_path)
        add_additional_html_from_template(html_file_path, "web-shared/md_to_html_dev/additions_qa.html")
def upload_s3_and_webflow_fda_townhalls(s3_upload=True, s3_prompt_overwrite=True, webflow_upload=True):
    """
    Uploads FDA townhall files to S3 and creates corresponding Webflow CMS items.

    :param s3_upload: bool, whether to upload files to S3
    :param s3_prompt_overwrite: bool, whether to prompt before overwriting S3 files
    :param webflow_upload: bool, whether to create Webflow CMS items
    :return: None
    """
    cur_folder_path = "data/floodlamp/reg/fda-townhalls/f5_fixnames/a_run_auto"
    transcript_suffix = "_section-titles"
    qa_suffix = "_qa-qonly"
    cur_bucket = "fofpublic"
    cur_s3_path = "fl-c19-fda-townhalls/"
    collection_id = FDA_C19_TOWNHALLS_ID
    CMS_OLD_NAME = "Virtual Town Hall"
    CMS_NEW_NAME = "FDA C19 Dx Town Hall"

    transcript_html_files_to_run = get_files_in_folder(cur_folder_path, suffixpat_include=transcript_suffix+".html")
    transcript_md_files_to_run = get_files_in_folder(cur_folder_path, suffixpat_include=transcript_suffix+".md")
    qa_html_files_to_run = get_files_in_folder(cur_folder_path, suffixpat_include=qa_suffix+".html")
    qa_md_files_to_run = get_files_in_folder(cur_folder_path, suffixpat_include=qa_suffix+".md")
    
    cms_items = []

    # Initialize counters
    total_base_names = set()
    total_files = 0

    # Build mapping of base names to file paths and metadata
    file_mapping = defaultdict(dict)
    for files, s3_subfolder, key_suffix in [
        (transcript_html_files_to_run, "transcripts-html/", "transcript_html"),
        (transcript_md_files_to_run, "transcripts-md/", "transcript_md"),
        (qa_html_files_to_run, "qa-html/", "qa_html"),
        (qa_md_files_to_run, "qa-md/", "qa_md")
    ]:
        for file_path in files:
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            base_name = re.sub(f'{transcript_suffix}$|{qa_suffix}$', '', base_name)
            
            # Print status in blue for each base name's first file
            if base_name not in total_base_names:
                total_base_names.add(base_name)
            
            # Upload to S3 if not skipped
            if s3_upload:
                upload_file_to_s3(file_path, bucket=cur_bucket, s3_path=cur_s3_path + s3_subfolder, prompt_overwrite=s3_prompt_overwrite)
                total_files += 1
            
            # Store S3 URL with URL-encoded filename
            encoded_filename = urllib.parse.quote(os.path.basename(file_path))
            s3_url = f"https://{cur_bucket}.s3.us-west-2.amazonaws.com/{cur_s3_path}{s3_subfolder}{encoded_filename}"
            file_mapping[base_name][key_suffix] = s3_url

            # For transcript MD files, read metadata fields
            if key_suffix == "transcript_md":
                _, youtube_url = read_metadata_field_from_file(file_path, "link youtube")
                _, pdf_url = read_metadata_field_from_file(file_path, "link pdf")
                _, slides_url = read_metadata_field_from_file(file_path, "link slides")
                
                file_mapping[base_name]["youtube_url"] = youtube_url
                file_mapping[base_name]["pdf_url"] = pdf_url
                file_mapping[base_name]["slides_url"] = slides_url

    # Print summary after all uploads complete
    print(colored(f"\nS3 Upload Summary:", "green"))
    print(colored(f"  Total base names processed: {len(total_base_names)}", "green"))
    print(colored(f"  Total files uploaded: {total_files}", "green"))
    # Prompt user before proceeding
    response = input("\nPress Enter to continue with Webflow CMS operations, or 'x' to abort: ").lower()
    if response == 'x':
        print("Aborting operation.")
        return

    # Validate Webflow collection once before creating items
    if webflow_upload:
        collection_details = webflow_cms_get_collection_details(collection_id, verbose=True)
        if not collection_details:
            print(colored("Failed to fetch collection details for validation", "red"))
            return

        # Check for existing items
        existing_items = webflow_cms_list_items(collection_id, verbose=True)
        if existing_items:
            existing_names = [item['fieldData'].get('name', '') for item in existing_items]
            existing_items_map = {item['fieldData'].get('name', ''): item['id'] for item in existing_items}
            
            # Check if any of our new items already exist
            overlapping_items = [cms_name for base_name, urls in file_mapping.items() 
                               if (cms_name := base_name.replace(CMS_OLD_NAME, CMS_NEW_NAME)) in existing_names]
            
            if overlapping_items:
                print(colored("\nThe following items already exist in the Webflow CMS:", "blue"))
                for name in overlapping_items:
                    print(f"- {name}")
                
                response = input("\nPress Enter to proceed with updating these Webflow CMS items, or 'x' to abort: ").lower()
                if response == 'x':
                    print("Aborting operation.")
                    return
                
                # Store whether we're updating for later use
                is_updating = True
            else:
                is_updating = False
        else:
            is_updating = False

    # Create CMS items list
    for base_name, urls in file_mapping.items():
        if all(key in urls for key in ["transcript_html", "transcript_md", "qa_html", "qa_md"]):
            cms_name = base_name.replace(CMS_OLD_NAME, CMS_NEW_NAME)
            cms_item = {
                "name": cms_name,
                "s3-transcript-html-url": urls["transcript_html"],
                "s3-qa-html-url": urls["qa_html"],
                "s3-transcript-md-url": urls["transcript_md"],
                "s3-qa-md-url": urls["qa_md"],
                "youtube-url-3": urls.get("youtube_url", ""),  # this has -3 because it was recreated multiple times and it cannot be reset
                "pdf-url": urls.get("pdf_url", ""),
                "slides-url": urls.get("slides_url", "")
            }
            cms_items.append(cms_item)

    # Create or update Webflow CMS items
    if webflow_upload:
        for item in cms_items:
            if is_updating and item['name'] in existing_items_map:
                # Update existing item
                result = webflow_cms_update_item(
                    collection_id=collection_id,
                    item_id=existing_items_map[item['name']],
                    field_data=item,
                    collection_validation=False,  # Skip validation since we did it once
                    verbose=True
                )
                if not result:
                    print(colored(f"Failed to update CMS item for {item['name']}", "red"))
            else:
                # Create new item
                result = webflow_cms_create_item(
                    collection_id=collection_id,
                    field_data=item,
                    collection_validation=False,  # Skip validation since we did it once
                    verbose=True
                )
                if not result:
                    print(colored(f"Failed to create CMS item for {item['name']}", "red"))
def mrun_upload_s3_and_webflow_fda_townhalls():
    pass
#if __name__ == "__main__":
    upload_s3_and_webflow_fda_townhalls(s3_upload=True, s3_prompt_overwrite=False, webflow_upload=True)
def mrun_flex_fda_townhalls_folder():  # for running whatever you want on the folder it's flexible!
    pass
#if __name__ == "__main__":
    cur_folder_path = "data/floodlamp/reg/fda-townhalls/f5_fixnames/done_auto"
    transcript_md_files_to_run = get_files_in_folder(cur_folder_path, suffixpat_include='_section-titles.md')

    for i, md_file_path in enumerate(transcript_md_files_to_run, 1):
        filename = os.path.basename(md_file_path)
        if "Virtual Town Hall" not in filename:
            print(colored(f"File does not contain 'Virtual Town Hall': {filename}", "red"))
        else:
            print(colored(f"File contains 'Virtual Town Hall': {filename}", "green"))

        
        # _, link_slides = read_metadata_field_from_file(md_file_path, "link slides")
        # if link_slides:
        #     print(f"link_slides: {link_slides} for file: {md_file_path}")

def mtest_pinecone_retrieve_fda_townhalls():
    pass
#if __name__ == "__main__":
    test_vector_index_name = 'fda-townhalls-qrag-4f-20250114'
    test_query = "What is the FDA's response to the COVID-19 pandemic?"
    fetched_chunks, retrieved_ids_scores = pinecone_retriever(test_query, test_vector_index_name, num_chunks=5)
    print("Retrieved IDs and scores:")
    for id, score in retrieved_ids_scores.items():
        print(f"{id}: {score}")
    
    print(colored("Retrieving chunks with date range", "yellow"))
    date_range = ["2020-03-01", "2020-03-29"]
    fetched_chunks, retrieved_ids_scores = pinecone_retriever(test_query, test_vector_index_name, num_chunks=5, date_range=date_range)
    print(f"Retrieved IDs and scores with date range of {date_range}:")
    for id, score in retrieved_ids_scores.items():
        print(f"{id}: {score}")
def mtest_qrag_2step_fda_townhalls():
    pass
#if __name__ == "__main__":
    cur_query = "What is the approach to open source EUAs?"
    cur_routes_dict = ROUTES_DICT_FDA_TOWNHALLS_V1
    cur_vector_index_name = 'fda-townhalls-qrag-100f-20250114'
    qrag_2step(cur_query, cur_routes_dict, cur_vector_index_name)
def mtest_s3_upload_fda_townhalls():
    pass
#if __name__ == "__main__":
    json_file_path = "tests/test_data_files/rag/qrag_routing.json"
    s3_path = "s3-qrag-fda-townhalls"
    upload_file_to_s3(json_file_path, bucket='[S3-BUCKET]', s3_path=s3_path)
def run_qrag_timed(query, vector_index_name, num_chunks, routes_dict, llm_model, output_folder, reasoning_effort=None):
    """
    Runs qrag routing and LLM call with timing, saves JSON and markdown to output folder.

    :param query: string, the user question.
    :param vector_index_name: string, name of the vector index.
    :param num_chunks: int, number of chunks to retrieve.
    :param routes_dict: dict, routing configuration.
    :param llm_model: string, LLM model name.
    :param output_folder: string, folder to save JSON and markdown files.
    :param reasoning_effort: string, optional reasoning effort level ('low', 'medium', 'high').
    :return result: dict, qrag JSON object with elapsed_time_seconds added to metadata.
    """
    start_time = time.time()
    routing_json_obj = qrag_routing_call(query, vector_index_name, num_chunks, routes_dict)
    result = qrag_llm_call(routing_json_obj, llm_model=llm_model, reasoning_effort=reasoning_effort)
    elapsed = time.time() - start_time
    result['metadata']['elapsed_time_seconds'] = round(elapsed, 1)
    cost = result['content'].get('cost_pennies_mycalc', 0)
    input_tokens = result['content'].get('input_tokens', 0)
    output_tokens = result['content'].get('output_tokens', 0)
    reasoning_tokens = result['content'].get('reasoning_tokens', 0)
    cached_input_tokens = result['content'].get('cached_input_tokens', 0)
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    token_detail = f"Input: {input_tokens:,}"
    if cached_input_tokens:
        token_detail += f" (cached: {cached_input_tokens:,})"
    token_detail += f"  Output: {output_tokens:,}"
    if reasoning_tokens:
        token_detail += f" (reasoning: {reasoning_tokens:,})"
    print(f"  Cost: {cost:.1f}¢  Time: {minutes}:{seconds:02d}  {token_detail}")
    os.makedirs(output_folder, exist_ok=True)
    datetime_str = get_current_datetime_filefriendly()
    json_filename = f"qrag_{datetime_str}_{llm_model}.json"
    json_file_path = os.path.join(output_folder, json_filename)
    write_json_file_from_json_data(result, json_file_path, overwrite="yes")
    md_file_path = create_md_from_qrag_exchange_json(json_file_path)
    print(f"  JSON saved: {json_file_path}")
    print(f"  MD saved: {md_file_path}")
    return result
def mrun_qrag_batch_fda_townhalls():
    pass
if __name__ == "__main__":
    queries = [
        "What was the number of FDA reviewers for diagnostic test EUA submissions and how did that change during the pandemic from 2020 to 2022?",
        "What was discussed with respect to the FDA Reference Panel for COVID-19 diagnostic tests?",
    ]
    cur_routes_dict = ROUTES_DICT_FDA_TOWNHALLS_V1
    cur_vector_index_name = 'fda-townhalls-qrag-100f-20250114'
    cur_model = 'gpt-5.4'
    cur_reasoning_effort = 'medium'
    cur_num_chunks = 20
    output_folder = "data/floodlamp/regulatory/fda-townhalls/_exclude-from-archive/_qrag-townhall-examples"
    results = []
    for i, query in enumerate(queries, 1):
        print(f"\n{'='*60}\nQuery {i}/{len(queries)}: {query}\n{'='*60}")
        result = run_qrag_timed(query, cur_vector_index_name, cur_num_chunks, cur_routes_dict, cur_model, output_folder, reasoning_effort=cur_reasoning_effort)
        results.append((query, result))
    print(f"\n{'='*60}")
    print(f"Batch Summary ({len(queries)} queries, model={cur_model}, reasoning_effort={cur_reasoning_effort})")
    print(f"{'='*60}")
    total_cost = 0
    total_time = 0
    for query, result in results:
        cost = result['content'].get('cost_pennies_mycalc', 0)
        elapsed = result['metadata'].get('elapsed_time_seconds', 0)
        input_tokens = result['content'].get('input_tokens', 0)
        output_tokens = result['content'].get('output_tokens', 0)
        reasoning_tokens = result['content'].get('reasoning_tokens', 0)
        cached_input_tokens = result['content'].get('cached_input_tokens', 0)
        total_cost += cost
        total_time += elapsed
        query_short = query[:70] + ('...' if len(query) > 70 else '')
        token_detail = f"Input: {input_tokens:,}"
        if cached_input_tokens:
            token_detail += f" (cached: {cached_input_tokens:,})"
        token_detail += f"  Output: {output_tokens:,}"
        if reasoning_tokens:
            token_detail += f" (reasoning: {reasoning_tokens:,})"
        print(f"  {query_short}")
        print(f"    Cost: {cost:.1f}¢  Time: {elapsed:.1f}s  {token_detail}")
    print(f"\n  TOTAL: Cost: {total_cost:.1f}¢  Time: {total_time:.1f}s")
    print(f"{'='*60}")


### SOVEREIGN CHILD
SOVEREIGN_CHILD_REQUIRED_FIELDS = ["QUESTION", "ANSWER", "TOPICS", "STARS"]
SOVEREIGN_CHILD_FOLDER = "data/sovereign-child/new_processed"
SUFFIXPAT_INCLUDE = "_qa-multi.md"
def mrun_corpus_sovereign_child():
    pass
#if __name__ == "__main__":
    #validate_blocks_in_folders([SOVEREIGN_CHILD_FOLDER], SOVEREIGN_CHILD_REQUIRED_FIELDS, CUSTOM_VALIDATORS, suffixpat_include=SUFFIXPAT_INCLUDE)
    #validate_iso_dates_in_filename([SOVEREIGN_CHILD_FOLDER], suffixpat_include=SUFFIXPAT_INCLUDE)
    create_qrag_vectordb([SOVEREIGN_CHILD_FOLDER], "sovereign-child-qrag", suffixpat_include=SUFFIXPAT_INCLUDE, embedding_field="QUESTION", date_from_filename=True)
def mtest_qrag_2step_sovereign_child():
    pass
# if __name__ == "__main__":
    cur_query = "Is delayed gratification good for kids?"
    cur_routes_dict = ROUTES_DICT_SOVEREIGN_CHILD_M1
    cur_vector_index_name = 'sovereign-child-qrag-7f-20250805'
    #print(cur_routes_dict)
    qrag_2step(cur_query, cur_vector_index_name, 10, cur_routes_dict)
def mrun_deepseek_sovereign_child():
    pass
#if __name__ == "__main__":
    start_time = time.time()
    #model = "o3-mini"
    model = "deepseek-reasoner"
    query = "What is a thorough response to a parent who thinks compulsory school is good?"
    routes_dict = ROUTES_DICT_SOVEREIGN_CHILD_V1
    vector_index_name = "sovereign-child-qrag-2f-20250208"
    num_chunks = 20
    qrag_routing_response = qrag_routing_call(query, vector_index_name, num_chunks, routes_dict)
    quoted_qa = qrag_routing_response["content"]["quoted_qa"]
    #print(quoted_qa)
    prompt_initial = "Answer the USER QUESTION below the following multiple sources of context:\nUse as the top priority context the QUOTED QA which have been extracted from the sources that are the primary subject for this AI tool.\nUse the BOOK TEXT as additional important context.\nUse as background context your knowledge of the parenting philosophy Taking Children Seriously, as well as the ideas of David Deutsch in his books The Fabric of Reality and The Beginning of Infinity.\n\n"
    query_context = "<USER_QUESTION>\n" + query + "\n</USER_QUESTION>\n\n"
    rag_context = "<QUOTED_QA>\n" + quoted_qa.rstrip() + "\n</QUOTED_QA>\n\n"
    large_context_file_path = "data/misc_books/Sovereign Child/2025-01-13_Book - The Sovereign Child by Dr Aaron Stupple_trimmed.md"
    #large_context_file_path = "data/misc_books/Sovereign Child/2025-01-13_Book - The Sovereign Child by Dr Aaron Stupple_trimmed-TEST.md"
    _, book_text = read_file_flex(large_context_file_path)
    book_text = book_text.split('\n', 1)[1].lstrip()  # remove CONTENT line and any blank lines that follow that
    book_text = book_text.rstrip()
    large_context = "<BOOK_TEXT>\n" + book_text.rstrip() + "\n</BOOK_TEXT>\n\n"
    prompt_parts = {
        'prompt_initial': prompt_initial,
        'query': query,
        'query_context': query_context,
        'rag_context': rag_context,
        'large_context': large_context,
        'large_context_file_path': large_context_file_path
    }
    md_file_path = "data/misc_books/Sovereign Child/deepseek_sovereign_child_include-both.md"
    response = reasoning_prompt_to_md_multipart(prompt_parts, model=model, md_file_path=md_file_path, heading_level=1)

    elapsed_time = time.time() - start_time
    minutes = int(elapsed_time // 60)
    seconds = int(elapsed_time % 60)
    print(f"Total execution time: {minutes}:{seconds:02d}")
def mrun_count_tokens_sovereign_child():
    pass
#if __name__ == "__main__":
    cur_file_path = "data/misc_books/Sovereign Child/2025-01-13_Book - The Sovereign Child by Dr Aaron Stupple_trimmed.md"
    text = read_complete_text(cur_file_path)
    print(count_tokens(text))
def mrun_create_html_files_for_sovereign_child_v1():
    pass
#if __name__ == "__main__":
    cur_folder_path = SOVEREIGN_CHILD_FOLDER
    #transcript_md_files_to_run = get_files_in_folder(cur_folder_path, suffixpat_include='_section-titles.md')
    #qa_md_files_to_run = get_files_in_folder(cur_folder_path, suffixpat_include='_qa-qonly.md')
    #qa_md_files_to_run = ["data/misc_books/Sovereign Child/2025-01-17_Tim Ferriss Show - Naval and Aaron Stupple on Sovereign Child_qa-qonly.md"]
    css_file_path = ""  # was "transcript-with-section-titles.css"

    # transcripts
    # for i, md_file_path in enumerate(transcript_md_files_to_run, 1):
    #     html_file_path = convert_markdown_to_html(md_file_path, heading="### transcript", css_file_path=css_file_path)
    #     h_tune_html_file(html_file_path, "", 1)
    #     clean_summaries_in_html_file(html_file_path)
    #     add_additional_html_from_template(html_file_path, "web-shared/md_to_html_dev/additions_transcript.html")

    # qa
    # for i, md_file_path in enumerate(qa_md_files_to_run, 1):
    #     html_file_path = convert_markdown_to_html(md_file_path, heading="### qa", css_file_path=css_file_path)
    #     h_tune_html_file(html_file_path, "", 1)
    #     h_tune_html_file(html_file_path, "AI Extracted Question and Answer", 3, insert=False)
    #     wrap_qa_blocks_in_details(html_file_path, "QUESTION", "ANSWER")
    #     clean_summaries_in_html_file(html_file_path)
    #     add_additional_html_from_template(html_file_path, "web-shared/md_to_html_dev/additions_qa.html")
def mrun_create_html_files_for_sovereign_child_v2():  # for _qa-multi
    pass
#if __name__ == "__main__":
    cur_folder_path = SOVEREIGN_CHILD_FOLDER
    transcript_md_files_to_run = get_files_in_folder(cur_folder_path, suffixpat_include='_vrb.md')
    qa_md_files_to_run = get_files_in_folder(cur_folder_path, suffixpat_include='_qa-multi.md')
    css_file_path = ""  # was "transcript-with-section-titles.css"

    # transcripts
    for i, md_file_path in enumerate(transcript_md_files_to_run, 1):
        html_file_path = convert_markdown_to_html(md_file_path, heading="### transcript", css_file_path=css_file_path)
        h_tune_html_file(html_file_path, "", 1)
        clean_summaries_in_html_file(html_file_path)
        add_additional_html_from_template(html_file_path, "web-shared/md_to_html_dev/additions_transcript.html")

    # qa
    for i, md_file_path in enumerate(qa_md_files_to_run, 1):
        html_file_path = convert_markdown_to_html(md_file_path, heading="### qa", css_file_path=css_file_path)
        h_tune_html_file(html_file_path, "", 1)
        h_tune_html_file(html_file_path, "AI Extracted Question and Answer", 3, insert=False)
        wrap_qa_blocks_in_details(html_file_path, "QUESTION", "ANSWER")
        clean_summaries_in_html_file(html_file_path)
        add_additional_html_from_template(html_file_path, "web-shared/md_to_html_dev/additions_qa.html")
def mrun_create_html_file_for_book():
    pass
#if __name__ == "__main__":
    # md_file_path = "data/misc_books/Sovereign Child/2025-01-13_Book - The Sovereign Child by Dr Aaron Stupple_section-titles.md"
    # html_file_path = convert_markdown_to_html(md_file_path, heading="CONTENT", collapse_h=4, css_file_path="", bold_first_line=False, wrap_subsections=True)
    # h_tune_html_file(html_file_path, "", 1)
    # #h_tune_html_file(html_file_path, "Book", 3, insert=False)
    # clean_summaries_in_html_file(html_file_path)
    # add_additional_html_from_template(html_file_path, "web-shared/md_to_html_dev/additions_transcript.html")

    #html_file_path = "data/misc_books/Sovereign Child/2025-01-13_Book - The Sovereign Child by Dr Aaron Stupple_section-titles.html"
    
    # Upload to S3
    cur_bucket = "fofpublic"
    # cur_s3_path = "sources-sovereign-child/transcripts-html/"
    # upload_file_to_s3(html_file_path, bucket=cur_bucket, s3_path=cur_s3_path, prompt_overwrite=False)

    html_file_path = "data/misc_books/Sovereign Child/2025-01-13_Book - The Sovereign Child by Dr Aaron Stupple_qa-qonly.html"
    cur_s3_path = "sources-sovereign-child/qa-html/"
    upload_file_to_s3(html_file_path, bucket=cur_bucket, s3_path=cur_s3_path, prompt_overwrite=False)
def mrun_create_sovereign_child_qa_from_prepqa():
    pass
#if __name__ == "__main__":
    CUR_FILE_PATH = 'data/sovereign-child/new_to_process/2025-06-26_Infinite Loops - The Sovereign Child Liberating Kids from the Tyranny of Rules_prepqa.md'
    create_qa_file_select_speaker(CUR_FILE_PATH, 'Aaron Stupple', FCALL_PROMPT_QA_DIALOGUE_FROMANSWER)
def mrun_create_sovereign_child_multi_qa():
    pass
#if __name__ == "__main__":
    qa_file_path = "data/sovereign-child/new_to_process/2025-06-02_Walk Ins Welcome - Raising Kids To Think For Themselves_qafixed.md"
    qa_multi_file_path = create_qa_multi_file_from_qa(qa_file_path, verbose=True)

def mrun_propagate_heading4_placeholders():
    pass
#if __name__ == "__main__":
    cur_file_path = "data/misc_books/Sovereign Child/2025-01-13_Book - The Sovereign Child by Dr Aaron Stupple_qa-qonly.md"
    extract_log_text = get_heading(cur_file_path, "### extract log")
    qa_text = get_heading(cur_file_path, "### qa")
    
    if not extract_log_text or not qa_text:
        ValueError(f"No extract log text or qa text found in file: {cur_file_path}")

    questions = []
    
    # Process each line
    lines = extract_log_text.split('\n')
    for i, line in enumerate(lines):
        # Look for heading level 5 "Questions Extraction"
        if line.strip() == "##### Questions Extraction":
            # Get the next line after the heading
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line.startswith('Q '):
                    # Get everything after the colon, strip whitespace
                    question_parts = next_line.split(':', 1)
                    if len(question_parts) > 1:
                        question = question_parts[1].strip()
                        questions.append(question)
    
    # Now find each question in the qa and add placeholder heading
    qa_lines = qa_text.split('\n')
    insertions = 0
    for question in questions:
        # Find the line number containing this question
        for i, line in enumerate(qa_lines):
            if line.strip().startswith('QUESTION: ' + question):
                # Add placeholder heading before the question
                qa_lines.insert(i, '#### X')
                insertions += 1
                break
    
    print(f"Added {insertions} placeholder headings")
    print(f"First 5 questions: {questions[:5]}")
    print(f"Total questions: {len(questions)}")
    set_heading(cur_file_path, '\n'.join(qa_lines), "### qa")
def get_timestamps_for_qa_from_transcript(qa_file_path, transcript_file_path, debug=True):
    """
    Adds timestamps to QA blocks by matching answers with transcript dialogue.

    :param qa_file_path: string, path to QA markdown file
    :param transcript_file_path: string, path to transcript markdown file
    :return: None, updates QA file in place
    """
    # Get all H4 headings from both files
    qa_text = get_heading(qa_file_path, "### qa")
    transcript_text = get_heading(transcript_file_path, "### transcript")
    
    qa_h4_headings = [line.strip() for line in qa_text.split('\n') if line.startswith('#### ')]
    transcript_h4_headings = [line.strip() for line in transcript_text.split('\n') if line.startswith('#### ')]
    
    # for i in range(len(qa_h4_headings)):
    #     print(f"qa: {qa_h4_headings[i]}")
    #     print(f"tr: {transcript_h4_headings[i]}")
    #     print()

    # Verify headings match
    if qa_h4_headings != transcript_h4_headings:
        raise ValueError("H4 headings in QA and transcript files do not match exactly")
    
    print(f"H4 headings match in both files. Found {len(qa_h4_headings)} sections.")
    
    # Initialize counters and lists
    match_count = 0
    mismatch_count = 0
    no_match_count = 0
    total_blocks = 0
    mismatch_blocks = []
    no_match_blocks = []
    
    # Build new QA text with sections
    new_qa_sections = []
    
    # Process each section
    for section_heading in qa_h4_headings:
        # Add section heading to new text
        new_qa_sections.append(section_heading)
        
        # Get QA blocks and transcript text for this section
        qa_blocks = get_blocks_from_file(qa_file_path, section_heading)
        section_transcript = get_heading(transcript_file_path, section_heading)
        
        section_updated_blocks = []
        
        # Process each QA block in this section
        for block in qa_blocks:
            fields = get_all_fields_dict(block)
            qa_block_id = get_field_value(block, 'QA BLOCK')
            qa_speaker = get_field_value(block, 'SPEAKER ANSWER')
            verbatim_answer = get_field_value(block, 'VERBATIM ANSWER')
            
            if not qa_speaker or not verbatim_answer:
                ValueError(f"No speaker question or verbatim answer found for block: {block}")
            
            # Extract all dialogue segments with timestamps and create list of dictionaries
            dialogue_segments = []
            timestamp = None
            
            lines = section_transcript.split('\n')
            for i in range(len(lines)-1):  # -1 to avoid index error
                line = lines[i]
                if '[' in line and ']' in line and 'http' in line:
                    # Extract timestamp and speaker
                    parts = line.split('[')
                    if len(parts) > 1:
                        transcript_speaker = parts[0].strip()
                        # Get the dialogue from the next line
                        dialogue = lines[i + 1].strip()
                        segment = {
                            'line': line,
                            'speaker': transcript_speaker,
                            'dialogue': dialogue,
                            'score': 0
                        }
                        dialogue_segments.append(segment)
                        if not timestamp:
                            timestamp = line
            
            # Calculate scores for each segment
            verbatim_answer_trimmed = ' '.join(verbatim_answer.split()[:10]).lower()
            
            def clean_text(text):
                # Remove punctuation, convert to lowercase, and normalize whitespace
                import re
                text = re.sub(r'[.,!?"]', '', text.lower())
                return ' '.join(text.split())
            
            def get_match_score(text1, text2):
                # Clean both texts
                text1 = clean_text(text1)
                text2 = clean_text(text2)
                
                # Get words from both texts
                words1 = set(text1.split())
                words2 = set(text2.split())
                
                # Calculate word overlap
                common_words = words1.intersection(words2)
                if not words1:
                    return 0
                
                # Score based on how many words match
                word_match_ratio = len(common_words) / len(words1)
                
                # Bonus for sequential words matching
                from difflib import SequenceMatcher
                sequence_ratio = SequenceMatcher(None, text1, text2).ratio()
                
                # Combine scores with more weight on word matches
                return (word_match_ratio * 0.7) + (sequence_ratio * 0.3)
            
            best_score = 0
            best_segment = None
            
            for segment in dialogue_segments:
                score = get_match_score(verbatim_answer_trimmed, segment['dialogue'])
                segment['score'] = score
                if score > best_score:
                    best_score = score
                    best_segment = segment
            
            total_blocks += 1
            
            # Now check speaker match only for the best matching segment
            match_threshold = 0.5
            should_debug = False

            if best_segment and best_score > match_threshold:  # Threshold for good match
                if best_segment['speaker'] == qa_speaker:
                    # Strip everything before the first '[' for the timestamp
                    timestamp_line = best_segment['line'][best_segment['line'].find('['):]
                    fields['TIMESTAMP'] = timestamp_line
                    match_count += 1
                else:
                    timestamp_line = best_segment['line'][best_segment['line'].find('['):]
                    fields['TIMESTAMP'] = timestamp_line
                    mismatch_count += 1
                    mismatch_blocks.append(qa_block_id)
                    should_debug = True
            else:
                timestamp_line = timestamp[timestamp.find('['):]
                fields['TIMESTAMP'] = timestamp_line
                no_match_count += 1
                no_match_blocks.append(qa_block_id)
                should_debug = True

            # Reconstruct block with new timestamp before ANSWER
            updated_block = []
            for field, content in fields.items():
                if field == 'ANSWER':
                    # Insert TIMESTAMP before ANSWER
                    updated_block.append(f"TIMESTAMP: {fields['TIMESTAMP']}")
                if field != 'TIMESTAMP':  # Skip TIMESTAMP in normal iteration
                    updated_block.append(f"{field}: {content}")
            section_updated_blocks.append('\n'.join(updated_block) + '\n')  # Add newline after each block

            if debug and should_debug:
                print("\nDebug info:")
                print(f"QA Block: '{qa_block_id}'")
                print(f"Expected speaker: '{qa_speaker}'")
                print(f"Best match speaker: '{best_segment['speaker'] if best_segment else 'None'}'")
                print(f"Verbatim answer (trimmed): '{verbatim_answer_trimmed}'")
                print("\nAll segments sorted by score:")
                sorted_segments = sorted(dialogue_segments, key=lambda x: x['score'], reverse=True)
                for segment in sorted_segments:
                    print(f"Score: {segment['score']:.3f}")
                    print(f"Speaker line: {segment['speaker']} [{segment['line'].split('[')[1]}")
                    print(f"Dialogue: {segment['dialogue'][:100]}...")
                    print()
                debug = False  # Turn off debug after first error
        
        # Add all blocks for this section
        new_qa_sections.extend(section_updated_blocks)
        new_qa_sections.append('')  # Add blank line between sections
    
    # Print statistics
    print(f"Matches found: {match_count}")
    print(f"\nSpeaker mismatches: {mismatch_count}  {mismatch_blocks}")
    print(f"\nNo matches found: {no_match_count}  {no_match_blocks}")
    print(f"\nTotal blocks processed: {total_blocks}")
    
    # Write entire QA text with all sections
    final_qa_text = '\n'.join(new_qa_sections)
    set_heading(qa_file_path, final_qa_text, "### qa")
def mrun_get_timestamps_for_qa_from_transcript():
    pass
#if __name__ == "__main__":
    qa_file_path = "data/misc_books/Sovereign Child/2025-01-17_Tim Ferriss Show - Naval and Aaron Stupple on Sovereign Child_qa-qonly.md"
    transcript_file_path = "data/misc_books/Sovereign Child/2025-01-17_Tim Ferriss Show - Naval and Aaron Stupple on Sovereign Child_section-titles.md"
    get_timestamps_for_qa_from_transcript(qa_file_path, transcript_file_path)

WEBFLOW_CMS_COLLECTION_ID_SOVCHILD_TRANSCRIPTS = "68bf0edd549d72aa1a32bf7f"
CONFIG_S3_WEBFLOW_UPLOAD_SOVCHILD_TRANSCRIPTS = {
    "folder_path": "data/sovereign-child/new_processed",
    "transcript_suffix": "_vrb",
    "qa_suffix": "_qa-multi",
    "bucket": "fofpublic",
    "s3_path": "index-sovereign-child/",
    "collection_id": WEBFLOW_CMS_COLLECTION_ID_SOVCHILD_TRANSCRIPTS,
    "cms_item_name_old": "",
    "cms_item_name_new": "",
    "metadata_field_mapping": {
        "link youtube": "youtube-url",
        "link spotify": "spotify-url"
    }
}
def mrun_process_corpus_s3_webflow_upload():
    pass
#if __name__ == "__main__":
    config = CONFIG_S3_WEBFLOW_UPLOAD_SOVCHILD_TRANSCRIPTS
    process_corpus_s3_webflow_upload(config, s3_upload=True, webflow_upload=True, s3_prompt_overwrite=False, webflow_cms_prompt_overwrite=False)


#### OLD SOVEREIGN CHILD UPLOAD FUNCTION ####
def upload_s3_and_webflow_sovereign_child(s3_upload=True, s3_prompt_overwrite=True, webflow_upload=True):
    """
    Uploads Sovereign Child files to S3 and creates corresponding Webflow CMS items.

    :param s3_upload: bool, whether to upload files to S3
    :param s3_prompt_overwrite: bool, whether to prompt before overwriting S3 files
    :param webflow_upload: bool, whether to create Webflow CMS items
    :return: None
    """
    cur_folder_path = "data/misc_books/Sovereign Child"
    transcript_suffix = "_section-titles"
    qa_suffix = "_qa-qonly"
    cur_bucket = "fofpublic"
    cur_s3_path = "sources-sovereign-child/"
    collection_id = SOVEREIGN_CHILD_ID
    cms_name = "Sovereign Child"

    # transcript_html_files_to_run = get_files_in_folder(cur_folder_path, suffixpat_include=transcript_suffix+".html")
    # transcript_md_files_to_run = get_files_in_folder(cur_folder_path, suffixpat_include=transcript_suffix+".md")
    # qa_html_files_to_run = get_files_in_folder(cur_folder_path, suffixpat_include=qa_suffix+".html")
    # qa_md_files_to_run = get_files_in_folder(cur_folder_path, suffixpat_include=qa_suffix+".md")
    
    transcript_html_files_to_run = []
    transcript_md_files_to_run = []
    single_qa_md_file_to_run = "data/misc_books/Sovereign Child/2025-01-17_Tim Ferriss Show - Naval and Aaron Stupple on Sovereign Child_qa-qonly.md"
    single_qa_html_file_to_run = single_qa_md_file_to_run.replace(".md", ".html")
    qa_md_files_to_run = [single_qa_md_file_to_run]
    qa_html_files_to_run = [single_qa_html_file_to_run]

    cms_items = []

    # Initialize counters
    total_base_names = set()
    total_files = 0

    # Build mapping of base names to file paths and metadata
    file_mapping = defaultdict(dict)
    for files, s3_subfolder, key_suffix in [
        (transcript_html_files_to_run, "transcripts-html/", "transcript_html"),
        (transcript_md_files_to_run, "transcripts-md/", "transcript_md"),
        (qa_html_files_to_run, "qa-html/", "qa_html"),
        (qa_md_files_to_run, "qa-md/", "qa_md")
    ]:
        for file_path in files:
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            base_name = re.sub(f'{transcript_suffix}$|{qa_suffix}$', '', base_name)
            
            # Print status in blue for each base name's first file
            if base_name not in total_base_names:
                total_base_names.add(base_name)
            
            # Upload to S3 if not skipped
            if s3_upload:
                upload_file_to_s3(file_path, bucket=cur_bucket, s3_path=cur_s3_path + s3_subfolder, prompt_overwrite=s3_prompt_overwrite)
                total_files += 1
            
            # Store S3 URL with URL-encoded filename
            encoded_filename = urllib.parse.quote(os.path.basename(file_path))
            s3_url = f"https://{cur_bucket}.s3.us-west-2.amazonaws.com/{cur_s3_path}{s3_subfolder}{encoded_filename}"
            file_mapping[base_name][key_suffix] = s3_url

            # For transcript MD files, read metadata fields
            if key_suffix == "transcript_md":
                _, youtube_url = read_metadata_field_from_file(file_path, "youtube link")
                _, pdf_url = read_metadata_field_from_file(file_path, "pdf link")  # not working for book
                
                file_mapping[base_name]["youtube_url"] = youtube_url
                file_mapping[base_name]["pdf_url"] = pdf_url

    # Print summary after all uploads complete
    print(colored(f"\nS3 Upload Summary:", "green"))
    print(colored(f"  Total base names processed: {len(total_base_names)}", "green"))
    print(colored(f"  Total files uploaded: {total_files}", "green"))
    
    if webflow_upload:
        # Prompt user before proceeding
        response = input("\nPress Enter to continue with Webflow CMS operations, or 'x' to abort: ").lower()
        if response == 'x':
            print("Aborting operation.")
            return

        # Validate Webflow collection once before creating items
        collection_details = webflow_cms_get_collection_details(collection_id, verbose=True)
        if not collection_details:
            print(colored("Failed to fetch collection details for validation", "red"))
            return

        # Check for existing items
        existing_items = webflow_cms_list_items(collection_id, verbose=True)
        if existing_items:
            existing_names = [item['fieldData'].get('name', '') for item in existing_items]
            existing_items_map = {item['fieldData'].get('name', ''): item['id'] for item in existing_items}
            
            # Check if any of our new items already exist
            overlapping_items = [cms_name for base_name, urls in file_mapping.items()]
            
            if overlapping_items:
                print(colored("\nThe following items already exist in the Webflow CMS:", "blue"))
                for name in overlapping_items:
                    print(f"- {name}")
                
                response = input("\nPress Enter to proceed with updating these Webflow CMS items, or 'x' to abort: ").lower()
                if response == 'x':
                    print("Aborting operation.")
                    return
                
                # Store whether we're updating for later use
                is_updating = True
            else:
                is_updating = False
        else:
            is_updating = False

    # Create CMS items list
    for base_name, urls in file_mapping.items():
        if all(key in urls for key in ["transcript_html", "transcript_md", "qa_html", "qa_md"]):
            cms_item = {
                "name": base_name,
                "s3-transcript-html-url": urls["transcript_html"],
                "s3-qa-html-url": urls["qa_html"],
                "s3-transcript-md-url": urls["transcript_md"],
                "s3-qa-md-url": urls["qa_md"],
                "youtube-url": urls.get("youtube_url", ""),
                "pdf-url": urls.get("pdf_url", "")
            }
            cms_items.append(cms_item)

    # Create or update Webflow CMS items
    if webflow_upload:
        for item in cms_items:
            if is_updating and item['name'] in existing_items_map:
                # Update existing item
                result = webflow_cms_update_item(
                    collection_id=collection_id,
                    item_id=existing_items_map[item['name']],
                    field_data=item,
                    collection_validation=False,  # Skip validation since we did it once
                    verbose=True
                )
                if not result:
                    print(colored(f"Failed to update CMS item for {item['name']}", "red"))
            else:
                # Create new item
                result = webflow_cms_create_item(
                    collection_id=collection_id,
                    field_data=item,
                    collection_validation=False,  # Skip validation since we did it once
                    verbose=True
                )
                if not result:
                    print(colored(f"Failed to create CMS item for {item['name']}", "red"))
def mrun_upload_s3_and_webflow_sovereign_child():
    pass
#if __name__ == "__main__":
    upload_s3_and_webflow_sovereign_child(s3_upload=True, s3_prompt_overwrite=False, webflow_upload=False)



''' ’,'   ''' # curvy apostrophe

### CORPUS ORGANIZATION
def create_csv_of_files_by_suffix(folder_path, suffixpat_include=None, suffixpat_exclude=None, include_subfolders=False):
    """
    Creates a CSV file organizing files by their base names and suffixes.
    The CSV will have file base names as rows and suffixes as columns.
    Cell values will be the relative file paths if the file exists, None otherwise.

    :param folder_path: string of the path to the folder from which to retrieve files.
    :param suffixpat_include: string of the suffix pattern that included files must have.
    :param suffixpat_exclude: string of the suffix pattern that files must not have to be included.
    :param include_subfolders: boolean indicating whether to include files from subfolders.
    :return: string of the path to the created CSV file.
    """
    # Get all files using get_files_in_folder
    files = get_files_in_folder(folder_path, suffixpat_include, suffixpat_exclude, include_subfolders)
    
    # Create dictionaries to store base names and suffixes
    base_names = set()
    suffixes = set()
    file_dict = defaultdict(dict)
    suffix_extensions = {}  # Store extension for each suffix
    
    # Process each file
    for file_path in files:
        # Get relative path
        rel_path = os.path.relpath(file_path, folder_path)
        
        # Get base name without extension
        file_base = os.path.splitext(os.path.basename(file_path))[0]
        extension = os.path.splitext(file_path)[1]
        
        # Get suffix
        suffix = get_suffix(file_path)
        if suffix is None:
            base_name = file_base
        else:
            # Remove suffix from base name
            base_name = file_base[:-len(suffix)]
        
        # Add to sets and dictionary
        base_names.add(base_name)
        if suffix:
            suffixes.add(suffix)
            suffix_extensions[suffix] = extension
        file_dict[base_name][suffix if suffix else ''] = file_path
    
    # Convert sets to sorted lists
    base_names = sorted(base_names)
    suffixes = sorted(suffixes)
    
    # Create CSV file path
    csv_path = os.path.join(folder_path, 'files_by_suffix.csv')
    
    # Write to CSV
    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header row with suffixes and extensions
        header = ['base_filename'] + [(suffix + suffix_extensions[suffix]) if suffix else 'no_suffix' for suffix in suffixes]
        writer.writerow(header)
        
        # Write data rows
        for base_name in base_names:
            row = [base_name]
            for suffix in suffixes:
                row.append(file_dict[base_name].get(suffix, ''))
            writer.writerow(row)
    
    return csv_path
def mrun_create_csv_of_files_by_suffix():
    pass
#if __name__ == "__main__":
    create_csv_of_files_by_suffix("data/deutsch/f8_done_qafixed_and_vrb", suffixpat_include=".md")
def create_csv_of_files_by_suffix_folders_NOCALL(folders, suffixpat_include=None, suffixpat_exclude=None, include_subfolders=False):
    """
    Creates a CSV file organizing files from multiple folders by their base names and suffixes.
    Handles multiple instances of the same file/suffix combination by creating MULTI entries.

    :param folders: list of strings of folder paths to process
    :param suffixpat_include: string of the suffix pattern that included files must have
    :param suffixpat_exclude: string of the suffix pattern that files must not have
    :param include_subfolders: boolean indicating whether to include files from subfolders
    :return: string of the path to the created CSV file
    """
    if not folders:
        raise ValueError("No folders provided")

    # Initialize collections for all folders
    all_base_names = set()
    all_suffixes = set()
    file_dict = defaultdict(lambda: defaultdict(list))  # Nested defaultdict to store lists of paths
    suffix_extensions = {}  # Store extension for each suffix
    
    # Process each folder
    for folder_path in folders:
        files = get_files_in_folder(folder_path, suffixpat_include, suffixpat_exclude, include_subfolders)
        
        # Process each file
        for file_path in files:
            file_base = os.path.splitext(os.path.basename(file_path))[0]
            extension = os.path.splitext(file_path)[1]
            
            suffix = get_suffix(file_path)
            if suffix is None:
                base_name = file_base
            else:
                base_name = file_base[:-len(suffix)]
                suffix_extensions[suffix] = extension
            
            # Add to collections
            all_base_names.add(base_name)
            if suffix:
                all_suffixes.add(suffix)
            
            # Add path to the list for this base_name/suffix combination
            file_dict[base_name][suffix if suffix else ''].append(file_path)
    
    # Create CSV in the first folder
    csv_path = os.path.join(folders[0], 'files_by_suffix.csv')
    
    # Convert sets to sorted lists
    all_base_names = sorted(all_base_names)
    all_suffixes = sorted(all_suffixes)
    
    # Write to CSV
    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header row with suffixes and extensions
        header = ['base_filename'] + [(suffix + suffix_extensions[suffix]) if suffix else 'no_suffix' 
                                    for suffix in all_suffixes]
        writer.writerow(header)
        
        # Write data rows
        for base_name in all_base_names:
            row = [base_name]
            for suffix in all_suffixes:
                paths = file_dict[base_name].get(suffix, [])
                if not paths:
                    row.append('')  # Empty cell if no files exist
                elif len(paths) == 1:
                    row.append(paths[0])  # Single path if only one file exists
                else:
                    # MULTI entry if multiple files exist
                    row.append('MULTI=' + ','.join(paths))
            writer.writerow(row)
    
    return csv_path
def create_csv_of_files_by_suffix_folders(folders, suffixpat_include=None, suffixpat_exclude=None, include_subfolders=False):
    """
    Creates a CSV file organizing files from multiple folders by their base names and suffixes.
    Makes initial call to create_csv_of_files_by_suffix for the first folder, then appends data
    from additional folders. Handles multiple instances of same file/suffix with MULTI entries.

    :param folders: list of strings of folder paths to process
    :param suffixpat_include: string of the suffix pattern that included files must have
    :param suffixpat_exclude: string of the suffix pattern that files must not have
    :param include_subfolders: boolean indicating whether to include files from subfolders
    :return: string of the path to the created CSV file
    """
    if not folders:
        raise ValueError("No folders provided")

    # Create initial CSV from first folder
    csv_path = create_csv_of_files_by_suffix(folders[0], suffixpat_include, suffixpat_exclude, include_subfolders)
    
    if len(folders) == 1:
        return csv_path

    # Read existing CSV into memory
    data = []
    headers = []
    with open(csv_path, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        headers = next(reader)  # Get header row
        data = list(reader)

    # Process additional folders
    base_name_idx = {row[0]: i for i, row in enumerate(data)}  # Index of existing base names
    suffix_idx = {col: i for i, col in enumerate(headers)}  # Index of existing suffixes

    for folder in folders[1:]:
        # Get files from current folder
        files = get_files_in_folder(folder, suffixpat_include, suffixpat_exclude, include_subfolders)
        
        for file_path in files:
            file_base = os.path.splitext(os.path.basename(file_path))[0]
            extension = os.path.splitext(file_path)[1]
            
            suffix = get_suffix(file_path)
            if suffix is None:
                base_name = file_base
                col_header = 'no_suffix'
            else:
                base_name = file_base[:-len(suffix)]
                col_header = suffix + extension

            # Add new suffix column if needed
            if col_header not in suffix_idx:
                headers.append(col_header)
                suffix_idx[col_header] = len(headers) - 1
                for row in data:
                    row.append('')

            # Add new base name row if needed
            if base_name not in base_name_idx:
                new_row = [''] * len(headers)
                new_row[0] = base_name
                data.append(new_row)
                base_name_idx[base_name] = len(data) - 1

            # Update cell value
            col_idx = suffix_idx[col_header]
            row_idx = base_name_idx[base_name]
            current_value = data[row_idx][col_idx]
            
            if not current_value:
                data[row_idx][col_idx] = file_path
            else:
                # Handle multiple files
                if current_value.startswith('MULTI='):
                    data[row_idx][col_idx] = current_value + ',' + file_path
                else:
                    data[row_idx][col_idx] = 'MULTI=' + current_value + ',' + file_path

    # Sort rows by base name
    data.sort(key=lambda x: x[0])

    # Write updated CSV
    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        writer.writerows(data)

    return csv_path
def mrun_create_csv_of_files_by_suffix_folders():
    pass
#if __name__ == "__main__":
    create_csv_of_files_by_suffix_folders(DEUTSCH_FOLDER_PATHS, suffixpat_include=".md")

# ===== END OF FILE core/corpuses.py =====
