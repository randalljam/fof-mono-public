# ===== START OF FILE core/fileops_mtests.py =====
# Library for testing fileops functions

from fileops import *
from transcribe import *

""" Overwrite Logic Table:
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
*note - if desired, could add 2 other replace cases to prompt
"""

           
### INITIAL
def mtest_verbose_print():
    verbose_print(True, "Simple case")
    verbose_print(False, "False Simple case")
    verbose_print(True, "This is", "a test", 123)  
def mtest_check_file_exists():
    pass
#if __name__ == "__main__":        
    cur_file_path = "tests/test_data_files/fileops/document.md"
    check_file_exists(cur_file_path, "my_func - optional message") # no return value, should not raise ValueError
    #check_file_exists(cur_file_path+"X", "my_func - optional message") # should raise ValueError
def mtest_check_and_warn_file_overwrite():
    cur_file_path = "tests/test_data_files/fileops/document.md"
    #check_and_warn_file_overwrite(cur_file_path)
    warn_file_overwrite(cur_file_path+"X")

### SUFFIX
def mtest_get_suffix():
    pass
if __name__ == "__main__":
    cur_file_path = "data/floodlamp/guides/Resulting Decision (Single Triplicate Re-run) Flow Chart v1.2_fixed"
    print(get_suffix(cur_file_path))
    #cur_file_path = "tests/test_data_files/fileops/document.md"
    #print(get_suffix("data/test file string.md")) # expected: None
    #print(get_suffix("data/test file string_vrb.md")) # expected: '_vrb'
    #print(get_suffix("data/test file string with a extra .period_vrb.md")) # expected: Value Error
    #print(get_suffix("data/test file string_with space.md")) # expected: None
    #print(get_suffix("data/test file string_vrb_dq.md")) # expected: '_dq'
    #print(get_suffix("data/test file string_vrb-dq.md")) # expected: 'vrb-dq'
    #print(get_suffix("data/2024-03-02_test file string_vrb@dq.md")) # expected: ValueError
    #print(get_suffix("data/2024-03-02_test.md")) # expected: None
    #print(get_suffix("tests/test file string_")) # expected '_'
    #print(get_suffix("filename_v 1.txt")) # expected None
def mtest_add_suffix_in_str():
    #print(add_suffix_in_str("2099-01-01_Test file.md", suffix_add="_addme", delimiter="_"))  # expected: gives 2099-01-01_Test file_addme.md
    #print(add_suffix_in_str("2099-01-01_Test file_orig.md", suffix_add="_addme", delimiter="_"))  # expected: 2099-01-01_Test file_orig_addme.md
    print(add_suffix_in_str("2099-01-01_Test file_same.md", suffix_add="_same", delimiter="_"))  # expected: 2099-01-01_Test file_orig_same_same.md
def mtest_sub_suffix_in_str():
    cur_file_path = "tests/test_data_files/fileops/document.md"
    #print(sub_suffix_in_str("2099-01-01_Test file.md", suffix_sub="_subme", delimiter="_"))  # expected 2099-01-01_Test file_subme.md - suffix_new is added because there is no orig suffix
    #print(sub_suffix_in_str("2099-01-01_Test file_orig.md", suffix_sub="_subme", delimiter="_"))  # expected 2099-01-01_Test file_subme.md - suffix_new is substituted
    print(sub_suffix_in_str("2099-01-01_Test file_same.md", suffix_sub="_same", delimiter="_"))  # 2099-01-01_Test file_same.md
def mtest_sub_suffix_in_file():    
    pass
#if __name__ == "__main__":        
    cur_file_path="tests/test_data_files/fileops/document.md"
    print(sub_suffix_in_file(cur_file_path, "_mynewsuf"))  # expected removes the last suffix
    #print(sub_suffix_in_file(cur_file_path, ""))  # expected removes the last suffix

### FOLDER
def mtest_get_files_in_folder():  # updated 7-24-24 RT after suffixpat mod
    pass
#if __name__ == "__main__": 
    cur_folder="tests/test_data_files/fileops"
    #files = get_files_in_folder(cur_folder)  # 3 files
    #files = get_files_in_folder(cur_folder, include_subfolders=True)  # all 5 files
    #files = get_files_in_folder(cur_folder, suffixpat_include='_dgwhspm')  # 2 files
    #files = get_files_in_folder(cur_folder, suffixpat_exclude='_flaws')  # 2 files
    #files = get_files_in_folder(cur_folder, suffixpat_include='_prepqa', include_subfolders=True)  # none
    #files = get_files_in_folder(cur_folder+'X')  # EXPECTED ERROR - ValueError 
    #files = get_files_in_folder(cur_folder, suffixpat_include='_qatest', suffixpat_exclude='_prepqa')  # EXPECTED ERROR - ValueError
    #files = get_files_in_folder(cur_folder, suffixpat_include='.md')  # 2 files
    #files = get_files_in_folder(cur_folder, suffixpat_exclude='.json')  # 2 files
    #files = get_files_in_folder(cur_folder, suffixpat_include='.md', include_subfolders=True)  # 4 files
    #files = get_files_in_folder(cur_folder, suffixpat_exclude='.md', include_subfolders=True)  # 1 file
    #files = get_files_in_folder(cur_folder, suffixpat_include='.json')  # 1 file
    #files = get_files_in_folder(cur_folder, suffixpat_exclude='.json', include_subfolders=True)  # 4 files
    print('\n'.join(str(file) for file in files))
def mtest_apply_to_folder():
    pass
#if __name__ == "__main__":        
    cur_folder="tests/test_data_files/fileops"
    #print(apply_to_folder(get_suffix, cur_folder))
    print(apply_to_folder(get_suffix, cur_folder, include_subfolders=True))
    #more mtests can be added to check other parameters

### TIME AND TIMESTAMP
def mtest_convert_timezone_to_utc():
    pass
#if __name__ == "__main__":        
    print(convert_timezone_to_utc("PDT"))  # Expected output: UTC-07:00
    print(convert_timezone_to_utc("Pacific Daylight Time"))  # Expected output: UTC-07:00
    print(convert_timezone_to_utc("ABC"))  # Expected output: ValueError: Time zone not recognized: ABC
def mtest_get_current_datetime():
    pass
#if __name__ == "__main__":        
    print(get_current_datetime_humanfriendly(include_timezone=False))  # expected see below
    print(get_current_datetime_humanfriendly())  # expected see below
    print(get_current_datetime_filefriendly())  # expected see below
    print(get_current_datetime_filefriendly(include_utc=True))  # expected see below
    # 2024-05-04 11:42:26
    # 2024-05-04 11:42:26 UTC-07:00 PDT America/Los_Angeles
    # 2024-05-04_114226
    # 2024-05-04_114226_UTC-0700
def mtest_convert_to_epoch_seconds():
    pass
#if __name__ == "__main__":        
    datetime_list = [
        "2024-05-04 11:42:26",
        "2024-05-04 11:42:26 UTC-07:00 America/Los_Angeles",
        "2024-05-04 11:42:26 America/Los_Angeles",
        "2024-05-04 11:42:26 America/Denver",
        "2024-05-04_114226",
        "2024-05-04_114226_UTC-0600"
    ]
    # for datetime_string in datetime_list:
    #     print(datetime_string)
    #     print(convert_to_epoch_seconds(datetime_string, verbose=True))
    #     print("\n")
    print(convert_to_epoch_seconds(get_current_datetime_humanfriendly()))
    print(convert_to_epoch_seconds(get_current_datetime_filefriendly()))
def mtest_get_elapsed_seconds():
    cur_file_path = "tests/test_data_files/fileops/document.md"
    print(get_elapsed_seconds(convert_to_epoch_seconds("2024-03-07 06:52:18 PST")))

### READ
def mtest_read_complete_text():
    cur_file_path = "tests/test_data_files/fileops/document.md"
    print(read_complete_text(cur_file_path))  # WORKS
def mtest_read_metadata_and_content():
    pass
#if __name__ == "__main__":        
    #cur_file_path = "tests/test_data_files/fileops/document.md"
    cur_file_path = "data/misc_books/Sovereign Child/The Sovereign Child_sections.md"
    print(read_metadata_and_content(cur_file_path))

### WRITE
def mtest_handle_overwrite_prompt():
    cur_base_path = "tests/test_data_files/fileops"
    #print(handle_overwrite_prompt(cur_base_path+"_xxx.md", cur_base_path+"_prepqa_new.md")) # EXPECTED ValueError
    #print(handle_overwrite_prompt(cur_base_path+"_prepqa.md", cur_base_path+"_xxx.md")) # EXPECTED ValueError 
    print(handle_overwrite_prompt(cur_base_path+"_prepqa.md", cur_base_path+"_prepqa_new.md")) # WORKS - n=no change to files, y=overwrites orig file, _new file deleted, s=sustitute suffixes in new file
def mtest_write_complete_text():
    pass
#if __name__ == "__main__":        
    cur_file_path = "tests/test_data_files/fileops/document.md"
    #write_complete_text(cur_file_path, "Boring", suffix_new="_no", overwrite='no', verbose=True)  # file will be created if it does not exist
    #write_complete_text(cur_file_path, "Boring", suffix_new="_no-sub", overwrite='no-sub', verbose=True)  # file will be created if it does not exist
    # write_complete_text(cur_file_path, "Boring", suffix_new="_replace", overwrite='replace', verbose=True)  # file will be created if it does not exist
    # write_complete_text(cur_file_path, "Boring", suffix_new="_replace-sub", overwrite='replace-sub', verbose=True)  # file will be created if it does not exist
    # write_complete_text(cur_file_path, "Boring", suffix_new="_yes", overwrite='yes', verbose=True)  # file will be created if it does not exist
    # write_complete_text(cur_file_path, "Boring", suffix_new="_prompt", overwrite='prompt', verbose=True)  # file will be created if it does not exist
def mtest_write_metadata_and_content():
    pass
#if __name__ == "__main__":        
    cur_file_path = "tests/test_data_files/fileops/document.md"
    cur_metadata, cur_content = read_metadata_and_content(cur_file_path)
    write_metadata_and_content(cur_file_path, cur_metadata, cur_content, suffix_new="_rewrite", overwrite='no', verbose=True)

### MISC FILE
def mtest_delete_files_with_suffix():
    cur_file_path = "tests/test_data_files/fileops/document.md"
    #print(delete_file(cur_file_path+"X"))
    #print(delete_file(cur_file_path))
    print(delete_files_with_suffix("tests/test_data_files/fileops","_suf1"))
def mtest_move_files_with_suffix():
    pass
#if __name__ == "__main__":
    print(move_files_with_suffix("data/floodlamp_fda/townhalls/ft2_md_asconverted", "data/floodlamp_fda/townhalls/ft4_md_cleaned", "_cleaned"))
def mtest_tune_title():
    #print(tune_title('Whoa!'))
    print(tune_title('Title with spaces should have no change'))     
def mtest_create_full_path():
    pass
#if __name__ == "__main__":        
    #print(create_full_path('Lost Lecture', '_xyz.md', 'data/audio_inbox'))  # expected: data/audio_inbox/Lost Lecture_xyz.md
    #print(create_full_path('Lost Lecture_blah.txt', '_xyz.md', 'data/audio_inbox'))  # expected: data/audio_inbox/Lost Lecture_blah_xyz.md
    #print(create_full_path('tests/2099-01-01_Test file with link_ex.md', '_xyz.md', 'data/audio_inbox'))  # expected: tests/2099-01-01_Test file with link_ex_xyz.md
    #print(create_full_path('tests/2099-01-01_Test file with link_same.md', '_same.md', 'data/audio_inbox'))  # expected: tests/2099-01-01_Test file with link_same.md
    #print(create_full_path('tests/2099-01-01_Test file with link.md', '_xyz.md'))  # expected: tests/2099-01-01_Test file with link_xyz.md
    print(create_full_path('2099-01-01_Test file with link.md', '_xyz.md'))  # expected: ValueError
def mtest_zip_files_in_folders():    
    pass
#if __name__ == "__main__":        
    cur_folders=["tests/test_data_files/vectordb"]
    zip_files_in_folders(cur_folders, suffix_include="_qafixed", zip_file_path="tests/test_data_files/manual_output/synthetic_files.zip")
def mtest_get_text_between_delimiters():
    cur_file_path = "tests/test_data_files/fileops/document.md"
    _, cur_content = read_header_and_content_from_file(cur_file_path)
    print(get_text_between_delimiters(cur_content, "### summaries", "###"))
def mtest_check_if_duplicate_filename():
    pass
#if __name__ == "__main__":        
    cur_folder = "data/trucks/dev-test"
    test_filename_same_suffix = "2017_martinez_ford-super-duty-250-srw_7771635761.md"
    test_filename_diff_suffix = "2017_martinez_ford-super-duty-250-srw_7771635555.md"

    result = check_if_duplicate_filename(test_filename_same_suffix, cur_folder)
    print(f"Same suffix result: {result}")  # Expected: True
    result = check_if_duplicate_filename(test_filename_diff_suffix, cur_folder)
    print(f"Diff suffix result: {result}")  # Expected: True
    result = check_if_duplicate_filename(test_filename_diff_suffix, cur_folder, exclude_suffix=False)
    print(f"Diff suffix result with exclude_suffix=True: {result}")  # Expected: False
def mtest_find_and_replace_in_filenames_in_folder():
    pass
#if __name__ == "__main__":        
    cur_folder = "data/floodlamp/reg/fda-townhalls/dev-qa-extract"
    find_and_replace_in_filenames_in_folder(cur_folder, "zz-", "z1B-")

### TIMESTAMP LINKS
def mtest_remove_timestamp_links():
    pass
#if __name__ == "__main__":        
    cur_file_path = "tests/test_data_files/fileops/document.md"
    remove_timestamp_links(cur_file_path)
def mtest_add_timestamp_links_to_content():
    cur_file_path = "tests/test_data_files/fileops/document.md"
    _, content = read_metadata_and_content(cur_file_path)
    print(add_timestamp_links_to_content(content, "dummylink"))
def mtest_add_timestamp_links():
    pass
#if __name__ == "__main__":        
    cur_file_path = "tests/test_data_files/fileops/document.md"
    add_timestamp_links(cur_file_path)
def mtest_timestamp_links_ffops_OLD():  # both remove and add with compare_file
    pass
#if __name__ == "__main__":        
    #cur_file_path = "tests/test_data_files/fileops/document.md"
    cur_file_path = "tests/test_data_files/fileops/document.md"
    #cur_file_path = "tests/test_data_files/fileops/document.md"
    #cur_file_path = "tests/test_data_files/fileops/document.md"
    #cur_file_path = "tests/test_data_files/fileops/document.md"
    #remove_timestamp_links_ffop(cur_file_path)
    #remove_file_path = do_ffop(remove_timestamp_links_ffop, cur_file_path, overwrite="no")
    #add_file_path = do_ffop(add_timestamp_links_ffop, remove_file_path, overwrite="no-sub", suffix_new="_tsaddback")
    #compare_files_text(cur_file_path, add_file_path)
    #print(repr(remove_timestamp_links_from_content("Test newlines\n\n\n")))  # WORKS - does not strip newline
    
    # cur_file_path = "tests/test_data_files/fileops/document.md"
    # add1_file_path = do_ffop(add_timestamp_links_ffop, cur_file_path, overwrite="no-sub", suffix_new="_add1")
    # add2_file_path = do_ffop(add_timestamp_links_ffop, add1_file_path, overwrite="no-sub", suffix_new="_add2")
    # rem_file_path = do_ffop(remove_timestamp_links_ffop, add1_file_path, overwrite="no-sub", suffix_new="_rem")
        
    cur_file_path = "tests/test_data_files/fileops/document.md"
    do_ffop(add_timestamp_links_ffop, cur_file_path, overwrite="no", suffix_new="_fixadd")

### FIND AND REPLACE
def mtest_count_num_instances():
    pass
#if __name__ == "__main__":        
    cur_file_path = "tests/test_data_files/fileops/document.md"
    print(count_num_instances(cur_file_path, "sensor"))
def mtest_find_and_replace_pairs():
    pass
#if __name__ == "__main__":        
    cur_file_path = 'tests/test_data_files/fileops/document.md'
    cur_find_replace_pairs = [("Mervin Praison", "John Smith"), ("Summary", "Tamagotchi")]
    print(find_and_replace_pairs(cur_file_path, cur_find_replace_pairs, content_only=False))
def mtest_find_and_replace_from_csv():
    pass
#if __name__ == "__main__":        
    cur_folder= "tests/test_data_files/fileops"
    cur_find_replace_csv = "tests/test_data_files/fileops/find_replace.csv"
    find_and_replace_from_csv(cur_folder, cur_find_replace_csv, suffix_include="_dgwhspm", verbose=True)

### HEADING
def mtest_get_heading():
    pass
#if __name__ == "__main__":
    cur_file_path = "tests/test_data_files/fileops/document.md"
    print(f"Manual test get_heading for format 1 on file {cur_file_path}")
    print(get_heading(cur_file_path, "### transcript"))
    print(f"\n\nManual test get_heading for format 2 on file {cur_file_path}")
    cur_file_path = "tests/test_data_files/fileops/document_format2.md"
    print(get_heading(cur_file_path, "CONTENT", strip_heading_line=True))
def mtest_set_heading():
    pass
#if __name__ == "__main__":
    cur_file_path = "tests/test_data_files/fileops/document.md"
    #set_heading(cur_file_path, "\nSimpler code!\n\n", "### summaries")
    set_heading(cur_file_path, "\nZZZZZZ!\n\n", "### sleepy")
    # BELOW IS FOR set_heading_OLD from 7-11-24 refactor when the new_heading was included in the text
    # existing_heading = "### summaries"
    # set_heading(cur_file_path, existing_heading+"\nGood ideas!\n\n", existing_heading)  # replaces text in ### summaries
    #new_heading = "### sleepy"
    #set_heading(cur_file_path, new_heading+"\nZZZ\n\n", new_heading)  # adds new heading ### sleepy and it's text
    #set_heading(cur_file_path, "### summaries\n\n", "### summaries")  # blanks out text in heading
    #set_heading(cur_file_path, "", "### summaries")  # deletes heading
    #set_heading(cur_file_path, "", "### notfound") # ValueError
def mtest_delete_heading():
    pass
#if __name__ == "__main__":
    cur_file_path = "tests/test_data_files/fileops/document.md"
    delete_heading(cur_file_path, "### summaries")
    #delete_heading(cur_file_path, "### notexist")
def mtest_appeand_heading_to_file():
    pass
#if __name__ == "__main__":
    #cur_file_path = "tests/test_data_files/fileops/document.md"
    cur_file_path = "tests/test_data_files/fileops/document.md"
    append_heading_to_file(cur_file_path, "mtest_combined.md", "### summaries")
def mtest_create_new_file_from_heading():
    pass
#if __name__ == "__main__":        
    cur_file_path = "tests/test_data_files/fileops/document.md"
    print(create_new_file_from_heading(cur_file_path, "### transcript"))

### METADATA
def mtest_set_metadata_field():
    pass
#if __name__ == "__main__":        
    cur_header = "## metadata\nlast updated: 11-19-2023 by Randy\nlink: https://www.youtube.com/dummylink\n\n## content\n\n"
    #cur_header = "## metadata\n## content"  # edge case identified in unittest
    #print(set_metadata_field(cur_header, "last updated", "NOW"))  # WORKS
    # print(repr(cur_header))
    # print(repr(set_metadata_field(cur_header, "last updated", "11-19-2023 by Susan"))) # WORKS - same newlines
    # print(set_metadata_field(cur_header, "length", "4:30"))  # WORKS  
    # ALTERNATE METADATA FORMAT
    cur_file_path = "data/misc_books/Sovereign Child/The Sovereign Child_sections.md"
    #cur_file_path = "data/floodlamp/reg/fda-townhalls/dev-qa-extract/test_transcript_just2/VTH 36 just2_trans.md"
    metadata, content = read_metadata_and_content(cur_file_path)
    print(f"original metadata:\n{metadata}")
    print(f"original content:\n{content[:50]}")
    metadata = set_metadata_field(metadata, "source file", cur_file_path)
    print(f"\n\nupdated metadata:\n{metadata}")
def mtest_remove_metadata_field():
    cur_header = "## metadata\nlast updated: 11-19-2023 by Randy\nlink: https://www.youtube.com/dummylink\n\n## content\n\n"
    cur_header = "## metadata\n## content"  # edge case identified in unittest
    #print(remove_metadata_field(cur_header, "last updated"))  # WORKS
    #print(repr(cur_header))
    print(repr(remove_metadata_field(cur_header, "last updated"))) # WORKS - same newlines
    #print(remove_metadata_field(cur_header, "length"))  # WORKS
def mtest_set_last_updated():
    initial_header = create_initial_header()
    updated_header = set_last_updated(initial_header, "Updated by quick test")
    print(updated_header)
def mtest_read_metadata_field_from_file():
    cur_file_path = "tests/test_data_files/fileops/document.md"
    print(read_metadata_field_from_file(cur_file_path, "link")) # expected: (2, 'https://www.youtube.com/dummylink')
    #print(read_metadata_field_from_file(cur_file_path+"X", "link")) # expected: ValueError: The file path does not exist
def mtest_set_metadata_fields_from_csv():
    pass
#if __name__ == "__main__":        
    cur_folder_path = "data/floodlamp_fda/townhalls/ft3_md_metadata_from_csv"
    cur_csv_file_path = "data/floodlamp_fda/townhalls/townhalls_metadata_fields.csv"
    set_metadata_fields_from_csv(cur_folder_path, cur_csv_file_path, ".md")
def mtest_create_csv_from_fields():
    pass
#if __name__ == "__main__":  
    cur_folder_path = "data/deutsch/f8_done_qafixed_and_vrb"
    create_csv_from_fields(cur_folder_path,('STARS',))


    create_csv_from_fields()

### JSON
def mtest_pretty_print_json_structure():
    pass
#if __name__ == "__main__":
    cur_json_file_path = "tests/test_data_files/transcribe/deepgram_response.json"
    print(pretty_print_json_structure(cur_json_file_path, level_limit=None))



# ===== END OF FILE core/fileops_mtests.py =====
