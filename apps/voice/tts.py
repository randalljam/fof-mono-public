import os
import sys
#print("Python interpreter path:", sys.executable)
import requests
import click
import re
from openai import OpenAI, NotFoundError
from pathlib import Path
from pydub import AudioSegment
from time import sleep
from playsound import playsound
from datetime import datetime


from core.fileops import *
from core.audio import *

# Construct the absolute path to the directory containing config.py
root_dir = '/Users/randytrue/Documents/Code/corpus-tools'  # Update with the actual path
sys.path.insert(0, root_dir)

# ---API KEYS AND SECRETS---
from dotenv import load_dotenv
load_dotenv(override=True)  # Load environment variables from .env file
ELEVENLABS_API_KEY = os.environ["ELEVENLABS_API_KEY"]
OPENAI_API_KEY_TTS = os.environ["OPENAI_API_KEY_TTS"]


### TTS HELPER
# "Onyx", "Echo", "Alloy", "Fable", "Nova", "Shimmer", "Deustch", "Kid1", "TL", "Santa"
def get_voice_from_dict(my_voice_name):
    # Create a dictionary mapping voice names to their respective TTS service and voice string
    voice_dict = {
        "onyx": ("openai", "onyx"), "echo": ("openai", "echo"), "alloy": ("openai", "alloy"), "fable": ("openai", "fable"), "nova": ("openai", "nova"), "shimmer": ("openai", "shimmer"), 
        "santa": ("elevenlabs", "knrPHWnBmmDHMoiMeP3l"),
        "deutsch": ("elevenlabs", "ShJL555B5W2jJkspEHtU"),
        "Kid1": ("elevenlabs", "3DHgkdP078JfImgsMYx5"),
        "tl": ("elevenlabs", "1vUr6Zwq6COjbwGiSIhQ"),
        "chris": ("elevenlabs", "iP95p4xoKVk53GoZ742B"),
    }
    tts_service, tts_voice_string = voice_dict.get(my_voice_name, (None, None))
    if not tts_service:
        print(f"Error: Voice name '{my_voice_name}' not found.")
        return None, None
    return tts_service, tts_voice_string
    # DONE fill in code to create voice dictionary with following fields: my_voice_name, tts_service, tts_voice_string and then do the lookup from the input argument
def get_tts_filename(text_input, voice): # made obsolete by implementing in swift code 12-25-2023 Randy
    """
    Generates a unique filename for a text-to-speech audio file based on timestamp, voice, and text content.

    :param text_input: string, the text to be converted to speech
    :param voice: string, the voice name to be used for speech synthesis
    :return speech_file_path: pathlib.Path, the full path to the generated audio file
    """
    from datetime import datetime
    folder_path = Path(__file__).parents[1] / "data" / "0_gitignore" / "voice_mp3s"
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    first_words = ' '.join(text_input.strip().split()[:5])
    sanitized_first_words = re.sub(r'[^\w\s]', '', first_words)
    file_name = f"{timestamp}_{voice}_{sanitized_first_words}.mp3"
    speech_file_path = folder_path / file_name
    return speech_file_path


### TTS ELEVENLABS
HEADERS_ELEVENLABS = {
    "Accept": "audio/mpeg",
    "Content-Type": "application/json",
    "xi-api-key": ELEVENLABS_API_KEY
    }
def list_available_voices_elevenlabs():
    voices_url = "https://api.elevenlabs.io/v1/voices"
    voices_response = requests.get(voices_url, headers=HEADERS_ELEVENLABS)
    if voices_response.status_code == 200:
        voices = voices_response.json().get('voices', [])
        sorted_voices = sorted(voices, key=lambda v: v.get('name', ''))
        with open('voices.txt', 'w') as file:
            for voice in sorted_voices:
                file.write(f"{voice.get('name')} {voice.get('voice_id')}\n")
    else:
        print(f"Failed to retrieve voices. Status code: {voices_response.status_code}, Response: {voices_response.text}")
def tts_elevenlabs(output_file_path, text_input, voice_name):
    CHUNK_SIZE = 1024
    elevenlabs_url = "https://api.elevenlabs.io/v1/text-to-speech/"
    # "https://api.elevenlabs.io/v1/text-to-speech/<voice-id>"

    data = {
        "text": text_input,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }
    voice_info = get_voice_from_dict(voice_name)
    if voice_info == (None, None):
        # print("DEBUG - get_voice_from_dict function should already have printed error message if voice_name is not found")
        return None
    if voice_info[0] != "elevenlabs":
        print(f"Error: Voice name '{voice_name}' is not supported by ElevenLabs. It's for the service: {voice_info[0]}")
        return None
    voice_id = voice_info[1]
    full_url = elevenlabs_url + voice_id
    response = requests.post(full_url, json=data, headers=HEADERS_ELEVENLABS)
    
    if response.status_code == 200:
        with open(output_file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
        print("Audio file created successfully.")
        check_mp3_file(output_file_path)
    else:
        print(f"Failed to create audio file. Status code: {response.status_code}, Response: {response.text}")

    return output_file_path
def mrun_tts_elevenlabs():
    pass
#if __name__ == "__main__":
    file_path = "data/0_gitignore/voice_mp3s/2025-01-02_1029_Sov Child_our_oldest_daughter.mp3"
    text_input='''
Our oldest daughter was leaning against the glass door and pointing outside. She had recently learned how to walk, and with this came a burst of curiosity about the world. It was 7:00 a.m. on a spring morning, and everything was cold and wet. She wanted to go outside, but I really didn’t. As she slapped at the door and babbled about going out, I noticed her demeanor shift from bubbly curiosity to visible annoyance at my refusal to open it. I didn’t bother voicing my objection because I knew she wouldn’t understand that Daddy likes to be dry and relaxed in the morning and not braced against the cold and wet. So I didn’t say anything.

As she continued to slap at the door and demand to go out, I stared blankly at her, thinking. I couldn’t just let her be upset—I needed to do something. But I couldn’t reprimand her for making a fuss because what did she know? From her perspective, she was locked in a house-shaped box, and her father was mutely standing by instead of helping her get out. I could have distracted her with a game or by horsing around, but I didn’t like those options, either. I wanted her to go outside and explore. I wanted her to be curious, to experience her first spring, and a part of me definitely wanted to do it with her.

I decided to bite the bullet and take her outside. I reached down and started putting her boots on, but she resisted. She didn’t want to put on boots; she wanted to go outside. Was I going to use my grown-up muscles to restrain her, for her own good? “You want to see the planet? Not before I wrestle you to the floor and shove things on your feet.” I could imagine telling her that I was putting the boots on so her feet wouldn’t get cold, but she could barely talk. She’d never encountered the concept of cold, wet feet. In fact, that’s exactly what she was clamoring for—an opportunity to learn just that. So I opened the door, and out she toddled. I snatched my coat and shoved my feet into shoes and dashed after her.

The deck boards were rectangular puddles crusted with a paper-thin layer of ice. She crashed through them like a miniature Godzilla, oblivious to the cold wetness seeping through her pajama feet and up her calves. She sat down in the ice-cold water and excitedly splatted the deck puddles with her hands, utterly uncaring about the water that seeped into her diaper and chilled her bottom. Then she got up and trundled off to the sidewalk and into the neighbor’s yard. She put her hands in puddles, grabbed at dirt, and put some of it in her mouth. She was having a ball, squealing and laughing and stomping around. And, come to think of it, I was having a good time, too. I had drunk coffee and read the news on thousands of mornings, but I hadn’t stood outside and breathed fresh morning spring air in a good while. And I’d never seen a new human discover wetness and coldness and ice and dirt for the first time. She got to use her newfound power of walking to see and feel new things. She also learned about something else, that Dad opens doors to fun—literally. And when she’s had enough of the coldness and wetness, Dad picks her up and gets her warm and dry. We were outside for less than ten minutes. When we came in, I plopped my daughter in a warm bath, threw our clothes in the washing machine, and got changed. Later, while sipping my coffee as she splashed around in the tub, I reflected on what had just happened. She’d been right and I’d been wrong— going outside in the cold and wet was better than staying inside. She enjoyed the wetness even without boots, and she learned enough about the discomfort of being cold and wet that she might be interested in putting on boots next time. The whole experience was actually delightful. We both got dirty, but we’d both needed to change out of our morning clothes, anyway. And I ended up enjoying my coffee even more so than usual, since I was sipping it over a backdrop of happy child sounds, reflecting on something more profound than the morning news.
'''
    voice_name = "chris"
    mp3_file_path = tts_elevenlabs(file_path, text_input, voice_name)
    print(mp3_file_path)


### TTS OPENAI
client = OpenAI(api_key=OPENAI_API_KEY_TTS)  # Set your OpenAI API key
def tts_openai(output_file_path, text_input, voice_name="shimmer"):
    voice_info = get_voice_from_dict(voice_name)
    if voice_info == (None, None):
        return None
    if voice_info[0] != "openai":
        print(f"Error: Voice name '{voice_name}' is not supported by OpenAI. It's for the service: {voice_info[0]}")
        return None
    voice_id = voice_info[1]
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice_id,
            input=text_input,
            speed=1
        )
        response.stream_to_file(output_file_path)
            
    except NotFoundError as e:
        print(f"ERROR in tts_openai - Failed to create audio file. Error: {e}")
        return None
    except Exception as e:
        print(f"ERROR in tts_openai - An error occurred: {e}")
        return None
    return output_file_path
def mrun_tts_openai():
    pass
#if __name__ == "__main__":
    mp3_file_path = "data/0_gitignore/voice_mp3s/Kid1 - Bye bye baby poop.mp3"
    voice_name = "echo"
    text_input_1="Bye bye boo boo baby poop."
    text_input_2='''
CONCLUSION 

Fortunately, everything seems to be going well in our household. Our kids are all within normal weight. Our daughters have palates at least as broad as that of a typical kid, and they genuinely enjoy all of the foods they eat. Since their palates are authentic, they are progressively refining their tastes, rather than forming preferences based on their parents’ expectations. I have not detected anything like a sugar high after they eat sweets, and I’m convinced this is one of many tropes that have evolved to exert control. They do seem to get grumpy when they’re hungry, but so do kids who are restricted by conventional food rules. And again, since they manage their eating without our input, they can make the connection between mood and food them selves. When someone is angry and irritable, they don’t want to hear about how they should eat better or sleep more, and when they are pressured to fix the problem by eating or sleeping, this can trigger defensiveness that obscures rather than reveals the connection. As with adults, so with kids.
'''
    # mp3_file_path = "apps/voice/openai_tts_test.mp3"
    # text_input = "This is a test of the openai tts service"
    mp3_file_path = tts_openai(mp3_file_path, text_input_1, voice_name)
    print(mp3_file_path)



    

### TTS ANY SERVICE
def tts_anyservice(file_path, text_input, voice_name="shimmer"):
    voice_name = voice_name.lower() # convert voice_name to all lower case
    voice_info = get_voice_from_dict(voice_name) 
    if voice_info == (None, None):
        return None
    tts_service, voice_id = voice_info
    if tts_service == "openai":
        return tts_openai(file_path, text_input, voice_name)
    elif tts_service == "elevenlabs":
        return tts_elevenlabs(file_path, text_input, voice_name)
    else:
        print(f"Error: Service '{tts_service}' for voice name '{voice_name}' is not supported.")
        return None
def get_speaker_segs(text_dialogue):
    # converts raw text into list of speaker segments - accepts 2 speaker formats
    # format1 is my format with speaker lines that have name and timestamps, optionally timestamp links
    # format2 is speaker names followed by a colon, with and without newline before speaker text
    speaker_segs = [] # list of tuples with speaker_name and speaker_text
    lines = text_dialogue.split('\n')
    for i, line in enumerate(lines):
        # Attempt to extract a timestamp to determine if the line is in format one
        timestamp, index = get_timestamp(line)
        if timestamp and i + 1 < len(lines):  # If a timestamp is found and there is a next line
            # Assuming the speaker's name is on the same line as the timestamp
            speaker_name = line[:index].rstrip()
            # Speaker text is on the next line
            speaker_text = lines[i + 1].strip().strip('"').strip("'")
            speaker_segs.append((speaker_name, speaker_text))
        elif ':' in line:  # Check for format two
            speaker_name, speaker_text = line.split(':', 1)
            speaker_name = speaker_name.strip()
            speaker_text = speaker_text.strip().strip('"').strip("'")
            if not speaker_text or speaker_text.isspace():  # If there's only whitespace or nothing after the colon
                if i + 1 < len(lines):  # Check if there is a next line
                    speaker_text = lines[i + 1].strip().strip('"').strip("'")
                    i += 1  # Skip the next line as it's already used
            speaker_segs.append((speaker_name, speaker_text))
    return speaker_segs
    # DONE fill in code to process text_dialogue by first breaking into lines
    # DONE fill in code to process lines to identify speaker segments, comprising speaker names and speaker text, that fit acceptable speaker formats
    # DONE fill in code to assign speaker_name and speaker_text for accepted speaker segments
    # DONE fill in code to strip starting and ending single and double quotes from speaker_text if present
    # this didn't work from the direct code and I went to chat which took a few iterations
def play_tts_anyservice(text_input, voice_name="shimmer"):
    audio_filename = get_tts_filename(text_input, voice_name)
    returned_audio_filename = tts_anyservice(audio_filename, text_input, voice_name)
    playsound(returned_audio_filename)
def mrun_do_and_play_any_service():
    pass
#if __name__ == "__main__":
    #list_available_voices()
    tts_input='''
Our oldest daughter was leaning against the glass door and pointing outside. She had recently learned how to walk, and with this came a burst of curiosity about the world. It was 7:00 a.m. on a spring morning, and everything was cold and wet. She wanted to go outside, but I really didn’t. As she slapped at the door and babbled about going out, I noticed her demeanor shift from bubbly curiosity to visible annoyance at my refusal to open it. I didn’t bother voicing my objection because I knew she wouldn’t understand that Daddy likes to be dry and relaxed in the morning and not braced against the cold and wet. So I didn’t say anything.

As she continued to slap at the door and demand to go out, I stared blankly at her, thinking. I couldn’t just let her be upset—I needed to do something. But I couldn’t reprimand her for making a fuss because what did she know? From her perspective, she was locked in a house-shaped box, and her father was mutely standing by instead of helping her get out. I could have distracted her with a game or by horsing around, but I didn’t like those options, either. I wanted her to go outside and explore. I wanted her to be curious, to experience her first spring, and a part of me definitely wanted to do it with her.

I decided to bite the bullet and take her outside. I reached down and started putting her boots on, but she resisted. She didn’t want to put on boots; she wanted to go outside. Was I going to use my grown-up muscles to restrain her, for her own good? “You want to see the planet? Not before I wrestle you to the floor and shove things on your feet.” I could imagine telling her that I was putting the boots on so her feet wouldn’t get cold, but she could barely talk. She’d never encountered the concept of cold, wet feet. In fact, that’s exactly what she was clamoring for—an opportunity to learn just that. So I opened the door, and out she toddled. I snatched my coat and shoved my feet into shoes and dashed after her.

The deck boards were rectangular puddles crusted with a paper-thin layer of ice. She crashed through them like a miniature Godzilla, oblivious to the cold wetness seeping through her pajama feet and up her calves. She sat down in the ice-cold water and excitedly splatted the deck puddles with her hands, utterly uncaring about the water that seeped into her diaper and chilled her bottom. Then she got up and trundled off to the sidewalk and into the neighbor’s yard. She put her hands in puddles, grabbed at dirt, and put some of it in her mouth. She was having a ball, squealing and laughing and stomping around. And, come to think of it, I was having a good time, too. I had drunk coffee and read the news on thousands of mornings, but I hadn’t stood outside and breathed fresh morning spring air in a good while. And I’d never seen a new human discover wetness and coldness and ice and dirt for the first time. She got to use her newfound power of walking to see and feel new things. She also learned about something else, that Dad opens doors to fun—literally. And when she’s had enough of the coldness and wetness, Dad picks her up and gets her warm and dry. We were outside for less than ten minutes. When we came in, I plopped my daughter in a warm bath, threw our clothes in the washing machine, and got changed. Later, while sipping my coffee as she splashed around in the tub, I reflected on what had just happened. She’d been right and I’d been wrong— going outside in the cold and wet was better than staying inside. She enjoyed the wetness even without boots, and she learned enough about the discomfort of being cold and wet that she might be interested in putting on boots next time. The whole experience was actually delightful. We both got dirty, but we’d both needed to change out of our morning clothes, anyway. And I ended up enjoying my coffee even more so than usual, since I was sipping it over a backdrop of happy child sounds, reflecting on something more profound than the morning news.
'''
    play_tts_anyservice(text_input)



@click.command()
@click.argument('file_path')
@click.argument('text_input')
@click.option('--voice', default='alloy', help='Name of the voice to use.')
def cli_wrapper(file_path, text_input, voice):
    result = tts_anyservice(file_path, text_input, voice)
    if result:
        print(result)  # Or handle the output as required
    else:
        print("No output generated.")

#if __name__ == "__main__":
    #list_available_voices()
    #cli_wrapper()

def tts_combine_old(combine_text, combine_voices):
    # Parse the combine_voices into a dictionary
    voice_assignments = {}
    for line in combine_voices.strip().split('\n'):
        speaker, voice = line.split(':')
        voice_assignments[speaker.strip()] = voice.strip()

    # Process the combine_text and generate the TTS service calls
    lines = combine_text.strip().split('\n')
    for line in lines:
        speaker_segment, dialogue = line.split(':', 1)
        speaker_name = speaker_segment.strip()
        dialogue = dialogue.strip()

        # Get the voice for the narrator
        narrator_voice = voice_assignments.get('narrator')

        # Generate TTS for the speaker name using the narrator's voice
        speaker_file_path = get_tts_filename(speaker_name, narrator_voice)
        
        # Get the voice for the speaker's dialogue
        dialogue_voice = voice_assignments.get(speaker_name)

        # Generate TTS for the dialogue using the speaker's assigned voice
        dialogue_file_path = get_tts_filename(dialogue, dialogue_voice)
        
def tts_combine(combine_text, combine_voices):
    voice_assignments = {}
    mp3_files = []

    for line in combine_voices.strip().split('\n'):
        speaker, voice = line.split(':')
        voice_assignments[speaker.strip()] = voice.strip()

    print(voice_assignments)
    lines = combine_text.strip().split('\n')
    for line in lines:
        speaker_segment, dialogue = line.split(':', 1)
        speaker_name = speaker_segment.strip()
        dialogue = dialogue.strip()

        narrator_voice = voice_assignments.get('narrator')
        dialogue_voice = voice_assignments.get(speaker_name)

        # Generate TTS for the speaker name using the narrator's voice
        speaker_file_path = get_tts_filename(speaker_name, narrator_voice)
        speaker_name = speaker_segment.replace("GM", "Game Master").replace(" (", ". ").replace(")", ".").strip()
        print(f"tts_anyservice(speaker_file_path, '{speaker_name}', '{narrator_voice}')")
        sleep(1)
        # Add silence to the beginning and end of the speaker's audio
        tts_anyservice(speaker_file_path, speaker_name, narrator_voice)
        #add_silence_to_mp3(speaker_file_path, 0, 1)
        mp3_files.append(speaker_file_path)

        # Generate TTS for the dialogue using the speaker's assigned voice
        dialogue_file_path = get_tts_filename(dialogue, dialogue_voice)
        print(f"tts_anyservice(dialogue_file_path, '{dialogue}', '{dialogue_voice}')")
        sleep(1)
        tts_anyservice(dialogue_file_path, dialogue, dialogue_voice)
        add_silence_to_mp3(speaker_file_path, 0, 1)
        mp3_files.append(dialogue_file_path)

    return mp3_files

