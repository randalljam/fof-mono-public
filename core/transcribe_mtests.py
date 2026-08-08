# ===== START OF FILE core/transcribe_mtests.py =====
# Library for manual testing of transcribe functions

from fileops import *
from transcribe import *


### YOUTUBE FUNCTIONS
def mtest_download_mp3_from_youtube():
    pass
#if __name__ == "__main__":        
    cur_url = "https://youtu.be/RNNfkIE7uYs"
    output_title = 'Youtube_download_test_Feynman'
    cur_output_dir = "data/0_gitignore"
    print(download_mp3_from_youtube(cur_url, output_title=output_title, output_dir=cur_output_dir))  # WORKS 3-2 RT
def mtest_get_youtube_title_length():
    pass
#if __name__ == "__main__":        
    cur_url = "https://youtu.be/RNNfkIE7uYs"
    print(get_youtube_title_length(cur_url))  # WORKS 3-3 RT
    # should print ('Richard Feynman on Getting Arrested by Los Alamos Fence Security - Funny Clip!', '0:39')
def mtest_download_link_list_to_mp3s():
    cur_urls = ["https://youtu.be/RNNfkIE7uYs", "https://youtu.be/VW6LYuli7VU"]
    print(download_link_list_to_mp3s(cur_urls))  # WORKS 3-3 RT
    # should print {'https://youtu.be/RNNfkIE7uYs': 'Richard Feynman on Getting Arrested by Los Alamos Fence Security - Funny Clip!', 'https://youtu.be/VW6LYuli7VU': 'Richard Feynman talks about Algebra'}
def mtest_get_youtube_subtitles():
    pass
#if __name__ == "__main__":        
    cur_url = "https://youtu.be/RNNfkIE7uYs"  # Feynman
    #cur_url = "https://youtu.be/yAj5EnyuakI"  # Arjun Naval interview
    print(get_youtube_subtitles(cur_url))  # WORKS 3-3 RT
    # should print 'there  was  a  little  annoyances  from   censorship ...'
def mtest_get_youtube_all():
    pass
#if __name__ == "__main__":        
    #cur_url = "https://youtu.be/RNNfkIE7uYs"
    cur_url = "https://youtu.be/mNP5w4n9sFU"
    print(get_youtube_all(cur_url))
    # should print {'title': 'Richard Feynman on Getting Arrested by Los Alamos Fence Security - Funny Clip!', 'length': '0:00:39', 'chapters': '', 'description': 'Please Help Support This Channel:https://www.paypal.com/donate/?cmd=_s-xclick&hosted_button_id=BLJ283JMTMT7S\nThe famous physicist Richard P. Feynman always loved to test complex systems in the spirit of curiosity and fun and nowhere was this more true than in the security systems of the most complex scientific project in history, the Manhattan Project, where the greatest scientists of the age were gathered to create the first atomic bomb and in the process develop much of the scientific underpinnings of our modern civilization. \n\nFeynman, being Feynman, found that the best way to challenge the rigor of the establishment was with good old-fashioned mischief. He earned fame (or infamy) inside the safes of Los Alamos, cracking them with ease and leaving cryptic messages pretending to be a spy (all while real Soviet spies were inside and really learning the new nuclear secrets!) - hence his seemingly bizarre mischief making was indeed prophetic in many ways. \n\nHere, Richard Feynman talks briefly about how he tested fence security simply by "taking the path of least action" - through the holes in the fence! Funny stuff straight from the legendary man\'s mouth! Enjoy!', 'transcript': "there was a little annoyances from censorship and so forth but and checking in at gates and all kinds of things but there was it was understandable that such a thing had to go in fact most of the complaints was of a security was rather lacks in places there would be big holes in the outside fence the demand could walk through standing up and I used to enjoy going out through the gate coming in through the fence hole and going out through the gate again and then through the fence hole until the poor sergeant at the gate would gradually realize that this guy's come out of place four times without going in once and he kind of arrests me sort of", 'transcript source': 'auto-captions'}
def mtest_is_valid_youtube_url():
    pass
#if __name__ == "__main__":        
    print(is_valid_youtube_url("https://youtu.be/RNNfkIE7uYs"))  # WORKS True 3-3 RT
    print(is_valid_youtube_url("https://youtu.be/RNNfkIE7uYsXXXX"))  # WORKS True 3-3 RT
    print(is_valid_youtube_url("https://youtu.be/XXXXXXX"))  # expected: False - ERROR: Unsupported URL:
def mtest_create_youtube_md():
    pass
#if __name__ == "__main__":        
    # Make sure to delete all files with this video title in the audio inbox and at any of the specified file paths below.
    cur_url = "https://youtu.be/RNNfkIE7uYs"
    #print(create_youtube_md(cur_url))  # expected: data/audio_inbox/Richard Feynman on Getting Arrested by Los Alamos Fence Security - Funny Clip_yt.md
    #print(create_youtube_md(cur_url, title_or_path="Feynman Arrested"))  # expected: data/audio_inbox/Feynman Arrested_yt.md
    #print(create_youtube_md(cur_url, title_or_path="tests/test_data_files/manual_output/synthetic_video"))
    cur_file_path = "tests/test_data_files/manual_output/synthetic_video_yt.md"
    print(create_youtube_md(cur_url, title_or_path=cur_file_path))
def mtest_create_youtube_md_from_file_link():
    pass
#if __name__ == "__main__":        
    cur_file_path = "tests/test_data_files/transcribe/deepgram_reference.md"
    print(create_youtube_md_from_file_link(cur_file_path))  # expected: same file_path with suffix replaced with _yt
def mrun_create_youtube_md_from_file_link():
    pass
#if __name__ == "__main__":        
    cur_file_path = "data/misc_books/Sovereign Child/2025-01-17_Tim Ferriss Show - Naval and Aaron Stupple on Sovereign Child_cemanual.md"
    print(create_youtube_md_from_file_link(cur_file_path))  # expected: same file_path with suffix replaced with _yt
def mtest_extract_feature_from_youtube_md():
    pass
#if __name__ == "__main__":        
    #cur_file_path = "tests/test_data_files/transcribe/deepgram_reference.md"
    cur_file_path = "data/misc_books/Sovereign Child/2025-01-17_Tim Ferriss Show - Naval and Aaron Stupple on Sovereign Child_yt.md"
    chapters = extract_feature_from_youtube_md(cur_file_path, "chapters")
    print(chapters)


### JSON AND TRANSCRIPT SUPPORT
def mtest_get_media_length():
    pass
#if __name__ == "__main__":        
    cur_file_path = "tests/test_data_files/transcribe/synthetic_audio.mp3"
    cur_url = "https://youtu.be/1j0X9QMF--M"
    print(get_media_length(cur_file_path))
    print(get_media_length(cur_url))
def mtest_extract_feature_from_deepgram_json():
    pass
#if __name__ == "__main__":        
    cur_json_file_path = "tests/test_data_files/transcribe/deepgram_response.json"
    #print(extract_feature_from_deepgram_json(cur_json_file_path, "summaries"))
    # print(repr(extract_feature_from_deepgram_json(cur_json_file_path, "sentiments")))
    # print(extract_feature_from_deepgram_json(cur_json_file_path, "topics"))
    # print(extract_feature_from_deepgram_json(cur_json_file_path, "intents"))
    print(repr(extract_feature_from_deepgram_json(cur_json_file_path, "intents")))    
def mtest_validate_transcript_json():
    cur_json_file_path = "tests/test_data_files/transcribe/deepgram_response.json"
    print(validate_transcript_json(cur_json_file_path))
def mtest_set_various_transcript_headings_ffop():  # NOT TESTED AFTER REMOVING FFOP
    pass
#if __name__ == "__main__":        
    cur_file_path = "tests/test_data_files/transcribe/deepgram_reference.md"
    set_various_transcript_headings(cur_file_path, "intents", "deepgram")
    #set_various_transcript_headings(cur_file_path, "description", "youtube")
    #cur_file_path = "data/p_Mervin Praison/2023-11-06_Mervin Praison - OpenAI Assistants plus Python_dgwhspm.md"
    #set_various_transcript_headings_ffop(cur_file_path, "chapters", "youtube")
    #set_various_transcript_headings_ffop(cur_file_path, "summaries", "deepgram")
    # expected: UserWarning when feature not present
def mtest_get_transcript_speaker_lines():
    pass
#if __name__ == "__main__":        
    cur_file_path = "data/misc_books/Sovereign Child/2025-01-17_Tim Ferriss Show - Naval and Aaron Stupple on Sovereign Child_section-titles.md"
    transcript_text = get_heading(cur_file_path, '### transcript')
    print(get_transcript_speaker_lines(transcript_text))
def mrun_apply_youtube_chapters_as_section_titles():
    pass
#if __name__ == "__main__":        
    cur_file_path = "data/misc_books/Sovereign Child/2025-01-17_Tim Ferriss Show - Naval and Aaron Stupple on Sovereign Child_section-titles.md"
    apply_youtube_chapters_as_section_titles(cur_file_path)

### DEEPGRAM ALTERNATIVES
def mtest_test_deepgram_client():
    pass
#if __name__ == "__main__":        
    test_deepgram_client()
def mtest_transcribe_deepgram_sync():
    pass
#if __name__ == "__main__":        
    #cur_audio_file_path = "tests/test_data_files/transcribe/synthetic_audio.mp3"
    cur_audio_file_path = "tests/test_data_files/transcribe/synthetic_audio.mp3"
    transcribe_deepgram_sync(cur_audio_file_path, model='nova-2-general')
    #transcribe_deepgram(cur_audio_file_path, model='whisper-medium')
def mtest_transcribe_deepgram_sync_sdk_prerecorded():
    pass
#if __name__ == "__main__":        
    #cur_audio_file_path = "tests/test_data_files/transcribe/synthetic_audio.mp3"
    cur_audio_file_path = "tests/test_data_files/transcribe/synthetic_audio.mp3"
    #transcribe_deepgram_sdk_prerecorded(cur_audio_file_path, model='nova-2-general')
    transcribe_deepgram_sync_sdk_prerecorded(cur_audio_file_path, model='whisper-medium')
def mtest_transcribe_deepgram_callback_lambda():
    pass
#if __name__ == "__main__":        
    cur_audio_file_path = "tests/test_data_files/transcribe/synthetic_audio.mp3"
    cur_callback_url = "https://[API-GATEWAY-ID].execute-api.us-west-2.amazonaws.com/api/transcription"
    #print(transcribe_deepgram_sdk_prerecorded_callback(cur_audio_file_path, "nova-2-general", cur_callback_url))
    print(transcribe_deepgram_callback_lambda(cur_audio_file_path, "nova-2-general", cur_callback_url))
    
def mtest_add_dg_summaries_to_md():
    pass
#if __name__ == "__main__":        
    cur_file_path = "tests/test_data_files/transcribe/deepgram_reference.md"

### NUMERAL CONVERT FUNCTIONS
def mtest_convert_ordinals_in_content():
    content = "This is the 1st example. now we move to the 2nd one."
    print(convert_ordinals_in_content(content, ['.', '?', '!']))
      # expected: "This is the first example. Now we move to the second one."
    content = "Here's the 3rd example? do you get it? here's the 4th."
    print(convert_ordinals_in_content(content, ['.', '?', '!'])) 
      # expected: "Here's the third example? Do you get it? Here's the fourth."
    content = "Wow, this is the 5th! isn't it great? now for the 6th."
    print(convert_ordinals_in_content(content, ['.', '?', '!']))
      # expected: "Wow, this is the fifth! Isn't it great? now for the sixth."
def mtest_extract_context():
    line = "apple banana coconut donut egg fig sample alex betty carl dan eliot fern."
    print(extract_context(line, re.search("sample", line), 3))  # expected: "donut egg fig sample alex betty carl"
    print(extract_context(line, re.search("sample", line), 4))  # expected: "coconut donut egg fig sample alex betty carl dan"
    print(extract_context(line, re.search("banana", line), 4))  # expected: "coconut donut egg fig sample alex betty carl dan"
    #print(extract_context(line, re.search("absent", line), 4))  # expected ValueError: Match not found
def mtest_convert_nums_to_words():   # NOT TESTED AFTER REMOVING FFOP
    pass
#if __name__ == "__main__":        
    #cur_file_path = "tests/test_data_files/transcribe/deepgram_reference.md"
    cur_file_path = "tests/test_data_files/transcribe/numbers_input.md"
    ref_file_path = "tests/test_data_files/transcribe/numbers_expected.md"
    new_file_path = convert_nums_to_words(cur_file_path, overwrite='no', verbose=True)
    compare_files_text(ref_file_path, new_file_path)
    new2_file_path = copy_file_and_append_suffix(cur_file_path, suffix_new='_convertnums2')
    convert_nums_to_words(new2_file_path, verbose=True)
    compare_files_text(ref_file_path, new2_file_path)
    # cur_file_path = "data/training_old1-20_md/FloodLAMP_Demo13_Plate_v1.md"
    # print(convert_nums_to_words(cur_file_path, overwrite='no')

### SPEAKER NAMES FUNCTIONS
def mtest_find_unassigned_speakers():
    cur_md_file_path = 'tests/test_data_files/transcribe/deepgram_reference.md'
    print(find_unassigned_speakers(cur_md_file_path, verbose=True))
def mtest_propagate_speaker_names_throughout_md():
    pass
#if __name__ == "__main__":        
    cur_md_file_path = 'tests/test_data_files/transcribe/deepgram_reference.md'
    cur_input_speaker_names = [(0, 'Alice'), (1, 'Bob')]
    print(propagate_speaker_names_throughout_md(cur_md_file_path, cur_input_speaker_names))
def mtest_iterate_input_speaker_names():
    pass
#if __name__ == "__main__":        
    cur_md_file_path = 'tests/test_data_files/transcribe/deepgram_reference.md'
    print(iterate_input_speaker_names(cur_md_file_path))
def mtest_assign_speaker_names():
    pass
#if __name__ == "__main__":        
    cur_md_file_path = 'tests/test_data_files/transcribe/deepgram_reference.md'
    assign_speaker_names(cur_md_file_path)

### WRAPPER FUNCTIONS TO PROCESS DEEPGRAM TRANSCRIPTION
def mtest_create_transcript_md_from_json():
    pass
#if __name__ == "__main__":        
    cur_json = 'data/deutsch/f9_done_json_yt_host/2024-03-06_Peter Boghossian Podcast - Ideological Contagion_nova2gen.json'
    #cur_json = 'tests/test_data_files/transcribe/deepgram_response.json'
    print(create_transcript_md_from_json(cur_json))
def mtest_process_deepgram_transcription():
    pass
#if __name__ == "__main__":        
    test_deepgram_client()
    # cur_title = 'Shortest Interview Ever'  # this is not creating multiple speaker segments 4-23 RT
    # cur_link = 'https://youtu.be/6pMcXSixdVQ'
    # print(process_deepgram_transcription(cur_title, cur_link, model='nova-2'))
    cur_title = 'Closer to Truth - for test'
    cur_link = 'https://www.youtube.com/watch?v=mNP5w4n9sFU'
    print(process_deepgram_transcription(cur_title, cur_link, model='nova-2-general'))
def mtest_process_deepgram_transcription_from_audio_file():
    pass
#if __name__ == "__main__":        
    test_deepgram_client()
    cur_audio_file_path = 'tests/test_data_files/transcribe/synthetic_audio.mp3'
    cur_link = 'https://youtu.be/6pMcXSixdVQ'
    print(process_deepgram_transcription_from_audio_file(cur_audio_file_path, cur_link, model='nova-2'))
def mtest_process_deepgram_transcription_callback():
    pass
#if __name__ == "__main__":
    # cur_title = "2023-11-10_Lex Clip - Elon Musk on the existence of a soul"
    # cur_link = "https://youtu.be/1_wT3NEGT6s"
    # process_deepgram_transcription_callback(cur_title, cur_link, model='nova-2-general')
    
    cur_title = "Shortest Interview Ever - Audio file test"
    cur_link = "https://open.spotify.com/episode/1ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    cur_audio_file_path = 'tests/test_data_files/transcribe/synthetic_audio.mp3'
    process_deepgram_transcription_callback(cur_title, cur_link, model='whisper-medium', audio_file_path=cur_audio_file_path)
def mrun_process_deepgram_transcription_callback():
    pass
#if __name__ == "__main__":
    # cur_title = "2025-01-17_Tim Ferriss Show - Naval and Aaron Stupple on Sovereign Child"
    # cur_link = "https://youtu.be/2bZSzObqAjE"
    # cur_audio_file_path = "data/0_gitignore/2025-01-17_Tim Ferriss Show - Naval and Aaron Stupple on Sovereign Child.mp3"

    cur_title = "2025-01-13_OurKarlPopper Zoom - Logan Chipkin and Aaron Stupple on Sovereign Child"
    cur_link = "NO LINK"
    cur_audio_file_path = "data/audio_inbox/2025-01-13_OurKarlPopper Zoom - Logan Chipkin and Aaron Stupple on Sovereign Child.mp3"
    #process_deepgram_transcription_callback_presigneds3(cur_title, cur_link, model='nova-2-general', audio_file_path=cur_audio_file_path)
    process_deepgram_transcription_callback_presigneds3(cur_title, cur_link, model='whisper-medium', audio_file_path=cur_audio_file_path)
def mrun_download_deepgram_callback_waiting():
    pass
if __name__ == "__main__":
    print("RUNNING DOWNLOAD DEEPGRAM CALLBACK WAITING")
    download_deepgram_callback_waiting()
def mtest_process_multiple_videos():
    pass
#if __name__ == "__main__":        
    videos_to_process = [("2023-11-10_Lex Clip - Elon Musk on the existence of a soul", "https://youtu.be/1_wT3NEGT6s")
    ] 
    process_multiple_videos(videos_to_process)  # default set to audio_inbox   
    input("Hit enter after verifying the JSON file is in S3 OR hit ctrl C to abort and run download_deepgram_callback_waiting() manually ...")
    download_deepgram_callback_waiting()    
def mrun_process_multiple_videos():
    pass
#if __name__ == "__main__":        
    videos_to_process = [  #  (title, link)
        #("2024-12-19_Arjun Khemani - Naval Ravikant on The Beginning of Infinity", "https://youtu.be/yAj5EnyuakI"),
        #("2024-11-11_Arjun Khemani - David Deutsch on the Era of Man Popper and Western Civilization", "https://youtu.be/I3FzAjgPztU"),
        
    ] 
    process_multiple_videos(videos_to_process, model='nova-2-general', bool_youtube=False)  # default set to audio_inbox
def mtest_download_deepgram_callback_waiting():
    pass
#if __name__ == "__main__":
    download_deepgram_callback_waiting()
def mtest_schedule_recurring_task():
    pass
#if __name__ == "__main__":        
    local_folder = "data/audio_inbox"
    prefix = "WAITING-CALLBACK_"
    schedule_recurring_task(
        interval_minutes=5,
        check_function=lambda: check_for_waiting_files(local_folder, prefix),
        work_function=lambda: download_deepgram_callback_waiting(local_folder, prefix),
        max_runs=1
    )

# ===== END OF FILE core/transcribe_mtests.py =====
