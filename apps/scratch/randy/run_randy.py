from core.aws import *
from core.dbgen import *
from core.fileops import *
from core.transcribe import *
from core.llm import *
from core.structured import *

# sys.path.append('mod_corpus')  # 10-10-24 think this can be removed

def mrun_process_deepgram_transcription_callback():
    pass
#if __name__ == "__main__":
    cur_title = "Jordan Peterson - Advice for new fathers"
    cur_link = "https://youtu.be/eXzavsGOQXk"
    #cur_model = 'nova-2-general'
    cur_model = 'whisper-medium'
    process_multiple_videos([(cur_title, cur_link)], model=cur_model, bool_callback=False, bool_youtube=True)


def mrun_download_deepgram_callback_waiting():
    pass
#if __name__ == "__main__":
    download_deepgram_callback_waiting()

# LIST FILES
    # cur_folder = 'data/trucks/dev-test'
    # print(get_files_in_folder(cur_folder, suffixpat_include=".md"))

if __name__ == "__main__":
# COUNT TOKENS
    #cur_folder = "ms-graphrag/input"
    #cur_folder = "data/deutsch/f8_done_qafixed_and_vrb"
    #cur_folder = "data/deutsch/f8_qafixed_talks"
    # cur_folder = "data/deutsch/f8_vrb_talks_only"
    # cur_prompt = "This is a short prompt just for demonstration purposes to estimate total tokens and cost."
    #cost_llm_on_corpus(cur_folder, cur_prompt, "gpt-4o", TOKEN_COST_DICT, suffix_include="_vrb")

    # cur_file_path = "data/deutsch/essays/2019-07-15_Beyond Reward and Punishment.md"
    # cost_llm_on_file(cur_file_path, "", "gpt-4o", TOKEN_COST_DICT, verbose=True)

# RENAME EXTENSION
    # new_ext = ".txt"
    # cur_folder = "ms-graphrag/input"
    # extension_results = apply_to_folder(rename_file_extension, cur_folder, new_ext)

# FDA TOWNHALLS VALIDATE AND QA
    #cur_file_path = 'data/floodlamp_fda/townhalls/f5_md_fixnames/2020-03-25_Virtual Town Hall 1_fixnames.md'
    #print(validate_transcript(cur_file_path, verbose=True))
    #cur_folder = 'data/floodlamp_fda/townhalls/f5_md_fixnames'
    #apply_to_folder(validate_transcript, cur_folder, verbose=True, suffix_include='_fixnames')
    #print(create_speaker_matrix(cur_folder))

# DEEPGRAM CALLBACK
    # cur_audio_file_path = "data/audio_inbox/2023-11-10_Lex Clip - Soul.mp3"
    # cur_callback_url = "https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/transcription"
    # print(transcribe_deepgram_callback(cur_audio_file_path, "enhanced-meeting", cur_callback_url))

# CREATE DEEPGRAM MD
    #cur_json = "data/audio_inbox/086108e4-60ef-4a47-8915-9f7b0841b037.json"
    # cur_json = "data/audio_inbox/2023-11-10_Lex Clip - Elon Musk on the existence of a soul_nova2.json"
    # print(create_transcript_md_from_json(cur_json, combine_segs=True))
    #print(validate_transcript_json(cur_json))
    #pretty_print_json_structure(cur_json)

# DOWNLOAD YOUTUBE MP3
    # cur_url = "https://youtu.be/1_wT3NEGT6s"
    # cur_title = "2023-11-10_Lex Clip - Soul"
    # print(download_mp3_from_youtube(cur_url, output_title=cur_title))

# PV NAMES (5-2-24)
    # cur_folder = "data/pv/_run_matrix"
    # #print(create_speaker_matrix(cur_folder))

    # cur_find_replace_csv = "data/pv/meetings_epc/epc_find-and-replace.csv"
    # find_and_replace_from_csv(cur_folder, cur_find_replace_csv, verbose=True)

# FDA TOWNHALLS FIXNAMES
    # ***NOTE*** must manually copy orig-folder to create fixnames_folder, enter that new path below
    # orig_folder = 'data/floodlamp_fda/townhalls/f4_md_cleaned_manualedits'
    # suffix_orig = '_cleaned'
    # fixnames_folder = 'data/floodlamp_fda/townhalls/f5_md_fixnames'
    # suffix_new = '_fixnames'
    # csv_file_path = 'data/floodlamp_fda/townhalls/names_findandreplace_fda_townhalls.csv'
    
    # TODO need to fix in docwork
    #print(validate_townhalls(cur_folder_path))
    #print(create_speaker_matrix(cur_folder_path))
    #apply_to_folder(sub_suffix_in_file, fixnames_folder, suffix_new, suffix_include='_fixnamed')
    # ***NOTE*** must copy files before running
    #find_and_replace_from_csv(fixnames_folder, csv_file_path, suffix_include=suffix_orig, verbose=True)
    #apply_to_folder(sub_suffix_in_file, fixnames_folder, suffix_new, suffix_include=suffix_orig)
    # NEXT PASS
    #find_and_replace_from_csv(fixnames_folder, csv_file_path, suffix_include=suffix_new, verbose=True)

# DEUTSCH QA
    #cur_file_path = "data/f_c5_done_after_dq/2023-04-22_Reason Is Fun podcast - Ep0 Effective Altruism_qafixed.md"      
    #print(extract_topic_counts_csv_lines(cur_file_path, True))
    #get_blocks_from_file(cur_file_path, True)

    #cur_folder_paths = ["data/deutsch/deutsch8_done_qafixed_and_vrb", "data/deutsch/deutsch8_qafixed_talks"]   
    #print(validate_all_qa(cur_folder_paths))
    #create_topics_matrix(cur_folder_paths, "test_matrix.csv")
    #print(count_blocks(cur_folder_paths))
    #change_topic(cur_folder_paths, "university", "universities")

# ADD timestamp links with overwrite='yes'
    # cur_file_path = "data/pv/meetings_epc/2024-02-01_PV-EPC_pub.md"
    # add_timestamp_links(cur_file_path)

# TEST append_heading_to_file
    #cur_folder = "data/f_c7_done_early"
    #apply_to_folder(append_heading_to_file, cur_folder, "combined.md", "### qa", suffix_include="_qafixed2")

# FIX youtu.be
    # cur_file_path=""
    # do_ffop(find_and_replace_ffop, "www.youtube.com/watch?v=", "youtu.be/", overwrite="yes")

# DEMO OF SIMPLE LLM CALL
    # PROMPT_FALLACIES = "analyze the text for any logical fallacies that the speaker makes and if they make any, describe what the logical fallacy is and why the speaker, why their text exhibits that logical fallacy."

# CHECKING FOR qa heading
    # cur_folder = "data/f_c6_done_talks_dq"
    # count_suffixes_in_folder(cur_folder)
    # apply_to_folder(count_num_instances, cur_folder, "### qa", suffix_include="_qafixed", verbose=True)

    #apply_to_folder(sub_suffix_in_file, "data/f_c6_done_talks_dq", "", suffix_include="_dq", verbose=True)
    
    #cur_file_path = "data/f_c6_done_after_dq/1995-01-01_The Multiverse Documentary by Noorderlicht_qafixed_dq.md"
    #print(sub_suffix_in_file(cur_file_path, ""))

    # cur_file_path = "data/f_c6_done_after_dq/2024-03-04_Alex OConnor Podcast - The Multiverse is Real_vrb.md"
    # create_youtube_md_from_file_link(cur_file_path)
    
# Process Deepgram Transcription
    #test_deepgram_client()
    # cur_title = "2023-01-05_PV-EPC"
    # cur_link ="https://youtu.be/c0XqicnUjqQ"
    #print(process_deepgram_transcription(cur_title, cur_link, model='enhanced-meeting'))
    # 'nova-2-general' 'nova-2-meeting' 'enhanced-meeting' 'whisper-medium' 'whisper-large'

    # cur_audio_file_path = 'data/audio_inbox/Feynman - Key to Science.mp3'
    # transcribe_deepgram(cur_audio_file_path, model='whisper-medium')

    #create_transcript_md_from_json("data/pv/meetings_epc/f6_json_yt/2023-11-02_PV-EPC_enhmeet.json")

# RUN TRANSCIRBE 
    #("2023-07-15_Ilya Sutskever - Interview with Sven Strohband from Khosla Ventures","https://youtu.be/xym5f0XYlSc"),
    # videos_to_process_f = [  #  (title, link)
    #     ("Feynman - Key to Science", "https://youtu.be/b240PGCMwV0"),
    #     #("Feynman - There are No Miracle People", "https://youtu.be/IIDLcaQVMqw"),
    # ] 
    # videos_to_process_checkifdone= [  #  (title, link)
    #     ("2024-03-08_Lex Fridman Pdocast Clip - Yann LeCun on AI System Breaking Fundamental Law", "https://youtu.be/bOnBPGkxUuw"),
    #     ("2024-03-08_All-In Podcast - OpenAI Elon Lawsuit and AGI", "https://youtu.be/snbTCWL6rxo"),
    # ] 
    # videos_to_process_mm= [  #  (title, link)
    #     ("2023-11-14_Mindful Machines - The Unsettling Truth Linking Human and AI", "https://youtu.be/hgUkV6zb9-A"),
    #     ("DATE_Mindful Machines - YOU TUBE TITLE", "https://youtu.be/LCHQA7IMUj8"),
    #     ("DATE_Mindful Machines - YOU TUBE TITLE", "https://youtu.be/50Xi8cclWzU")
    # ]
    # videos_to_process= [  #  (title, link)
    #     ("Prompt Engineering - Claude Update to Control Your Computer", "https://youtu.be/lnWrF-xcwq0"),
        
    # ]
    # cur_path = "data/audio_inbox"
    # process_multiple_videos(videos_to_process, model='whisper-medium', bool_youtube=True)  # default set to audio_inbox

    #print(create_youtube_md_from_file_link('data/audio_inbox/Peak Prosperity - As The Data Floods In The Narrative Crumbles_nova2gen.md'))

# PROPER NAMES
    # cur_file_path = "data/pv/meetings_epc/2024-03-07_PV-EPC_spfixBA.md"
    # custom_proper_names_files = ['data/pv/cspell_dictionary_pv2.txt','data/pv/compound_proper_names.txt']
    #print(create_proper_names_triples(cur_file_path, custom_proper_names_files, True))
    #print_proper_names(cur_file_path, custom_proper_names_files, False, True)

# HISTORY MISC

# 2024-11-24 Renaming Deutsch files
#if __name__ == "__main__":
    # find_str = "2024-01-01_Arjun Khemani interview on TCS"
    # replace_str = "2024-01-01_Arjun Khemani - Free-Will TCS and Anarcho-Capitalism" 
    # find_str = "2018-04-18_John Horgan interview"
    # replace_str = "2018-04-18_Bloggingheads TV with John Horgan"
    # find_str = "2022-01-01_Universal Constructor with Logan Chipkin"
    # replace_str = "2022-01-01_Logan Chipkin - Universal Constructor"
    # find_str = "Robin Hanson conversation"
    # replace_str = "Robin Hanson"
    # find_str = "2021-06-02_Conversations with Tyler Cowen interview"
    # replace_str = "2021-06-02_Tyler Cowen - Multiple Worlds and Our Place in Them"
    # find_str = "2020-03-18_Interview by Visa about The Beginning of Infinity"
    # replace_str = "2020-03-18_Visa - chat about The Beginning of Infinity"
    # find_str = "2019-12-13_What is the Fun Criterion with Lulie Tanett"
    # replace_str = "2019-12-13_Lulie Tanett - What is the Fun Criterion"
    # find_str = "2019-12-04_Brexit and Error Correction with Joe Boswell"
    # replace_str = "2019-12-04_Joe Boswell - Brexit and Error Correction"
    # find_str = "2018-12-08_Constructor Theory with Joe Boswell"
    # replace_str = "2018-12-08_Joe Boswell - Constructor Theory"
    # find_str = "2018-10-23_TED interview 1 with Chris Anderson"
    # replace_str = "2018-10-23_The TED Interview with Chris Anderson"
    # find_str = "2018-06-19_Are There Many Worlds with Markus Arndt"
    # replace_str = "2018-06-19_Markus Arndt - Are There Many Worlds"
    # find_str = "2018-06-01_CBC Tapestry interview on AGI and other"
    # replace_str = "2018-06-01_CBC Tapestry - on AGI and the multiverse"
    # find_str = "2011-09-01_Sci-Fi London interview"
    # replace_str = "2011-09-01_Sci-Fi London"
    # find_str = "1995-01-01_The Multiverse Documentary by Noorderlicht"
    # replace_str = "1995-01-01_Noorderlicht - The Multiverse Documentary"

    # find_str = "Popperian Podcast "
    # replace_str = "Popperian Podcast Podcast "    
    # find_str = "podcast "
    # replace_str = ""    
    # find_str = " interview with"
    # replace_str = " with"

    # find_str = "interview on"
    # replace_str = "-"
    # find_str = "Interview -"
    replace_str = "-"
    find_str = "Interview -"
    # replace_str = "-"
    # find_and_replace_in_filenames_in_folder("data/deutsch/f8_done_qafixed_and_vrb", find_str, replace_str)
    # find_and_replace_in_filenames_in_folder("data/deutsch/f9_raw", find_str, replace_str)
    # find_and_replace_in_filenames_in_folder("data/deutsch/fx_archive", find_str, replace_str)