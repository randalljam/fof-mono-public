import sys
import os
import re
import mutagen
from mutagen.mp3 import MP3
from pydub import AudioSegment

from core.fileops import *


### MP3 FILES

def check_mp3_file(mp3_file_path):
    file_size = os.path.getsize(mp3_file_path)
    audio = MP3(mp3_file_path)
    bitrate_kbps = audio.info.bitrate // 1000  # Convert bps to kbps
    is_playable = audio.info.sketchy == 0
    length_seconds = audio.info.length

    print(f"MP3 File Size: {file_size / (1024 * 1024):.1f} MB")
    print(f"MP3 Bitrate: {bitrate_kbps} kbps")  # Display in kbps
    print(f"Is Playable MP3?: {'Yes' if is_playable else 'No'}")
    print(f"Audio Length: {convert_seconds_to_timestamp(length_seconds)}")

def convert_wav_to_mp3(wav_file_path, bitrate=192, prompt_wav_delete=True):
    # Check if the file already exists and handle overwriting
    mp3_file_path = wav_file_path.replace('.wav', '.mp3')
    if os.path.exists(mp3_file_path):
        print(f"{mp3_file_path} already exists and will be overwritten.")

    # Load the WAV file
    sound = AudioSegment.from_wav(wav_file_path)

    # Calculate and print original WAV file size in MB
    original_size = os.path.getsize(wav_file_path)
    print(f"Original WAV file size: {original_size / (1024 * 1024):.1f} MB")

    # Calculate and print audio length
    audio_length = sound.duration_seconds
    hours, remainder = divmod(audio_length, 3600)
    minutes, seconds = divmod(remainder, 60)
    print(f"Audio Length: {int(hours)}:{int(minutes)}:{int(seconds)}")

    print("\nDEBUG INFO:")
    print(f"Requested bitrate: {bitrate}k")
    
    # Export parameters - convert kbps to bps
    params = [
        "-b:a", f"{bitrate}k",    # Use the requested bitrate
        "-codec:a", "libmp3lame", # Use the libmp3lame codec for MP3
        "-ac", "2",              # Stereo (2 audio channels)
        "-ar", "44100"           # Sample rate of 44100 Hz
    ]

    print(f"FFmpeg parameters: {params}")

    try:
        # Export with parameters
        sound.export(
            mp3_file_path,
            format="mp3",
            parameters=params
        )
        
        # Verify the output file
        from mutagen.mp3 import MP3
        audio = MP3(mp3_file_path)
        print(f"\nActual output bitrate: {audio.info.bitrate // 1000}k")
        print(f"FFmpeg command line used: {audio.info.encoder_info}")
        
    except Exception as e:
        print(f"Error during conversion: {str(e)}")

    # Calculate and print new MP3 file size in MB
    new_size = os.path.getsize(mp3_file_path)
    print(f"New MP3 file size: {new_size / (1024 * 1024):.1f} MB")

    # Check and print MP3 file details
    check_mp3_file(mp3_file_path)

    # Prompt to delete the original WAV file
    if prompt_wav_delete:
        confirm = input(f"Delete the original WAV file {wav_file_path}? (y/n): ")
        if confirm.lower() == 'y':
            os.remove(wav_file_path)
            print("Original WAV file deleted.")
        else:
            print("Original WAV file retained.")
def mrun_convert_wav_to_mp3():
    pass
#if __name__ == "__main__":
    wav_file_path = "data/pv/pv_epc_resources/pv_epc_evac/2024-10-23_NBLM Deep Dive - PV School SIP.wav"
    convert_wav_to_mp3(wav_file_path, bitrate=192, prompt_wav_delete=False)


def add_silence_to_mp3(file_path, silence_at_start, silence_at_end):
    sound = AudioSegment.from_mp3(file_path)
    silence_start = AudioSegment.silent(duration=silence_at_start * 1000)
    silence_end = AudioSegment.silent(duration=silence_at_end * 1000)
    sound_with_silence = silence_start + sound + silence_end
    sound_with_silence.export(file_path, format="mp3")

def combine_mp3_files(mp3_files):
    combined = AudioSegment.empty()
    for mp3_file in mp3_files:
        sound = AudioSegment.from_mp3(str(mp3_file))  # Convert PosixPath to string
        combined += sound

    # Convert the first PosixPath to a string and then split
    parts = str(mp3_files[0]).split('_')
    combined_filename = '_'.join(parts[:3] + ['combined'] + parts[3:])
    
    # Export the combined MP3 file
    combined.export(combined_filename, format="mp3")
    # Delete all the individual mp3 files
    for mp3_file in mp3_files:
        os.remove(mp3_file)
    return combined_filename

def trim_mp3_by_timestamps(file_path, start_timestamp, end_timestamp, suffix_new='_trimmed'):
    """
    Trims an MP3 file from a start timestamp to an end timestamp.
    
    :param file_path: string, path to the MP3 file to trim
    :param start_timestamp: string, start time in format 'hh:mm:ss' or 'mm:ss'
    :param end_timestamp: string, end time in format 'hh:mm:ss' or 'mm:ss'
    :param suffix_new: string, suffix to add to the output filename. Default is '_trimmed'
    :return: string, path to the trimmed MP3 file
    """
    # Convert timestamps to milliseconds (pydub works in milliseconds)
    start_ms = convert_timestamp_to_seconds(start_timestamp) * 1000
    end_ms = convert_timestamp_to_seconds(end_timestamp) * 1000
    
    # Load the audio file
    audio = AudioSegment.from_mp3(file_path)
    
    # Validate timestamps
    if end_ms > len(audio):
        raise ValueError(f"End timestamp {end_timestamp} exceeds audio length of {convert_seconds_to_timestamp(len(audio)/1000)}")
    if start_ms >= end_ms:
        raise ValueError("Start timestamp must be before end timestamp")
    
    # Extract the segment
    trimmed_audio = audio[start_ms:end_ms]
    
    # Create output filename
    output_path = add_suffix_in_str(file_path, suffix_new)
    
    # Export the trimmed audio
    trimmed_audio.export(output_path, format="mp3")
    
    # Print duration information
    original_duration = convert_seconds_to_timestamp(len(audio) / 1000)
    trimmed_duration = convert_seconds_to_timestamp(len(trimmed_audio) / 1000)
    print(f"Original duration: {original_duration}")
    print(f"Trimmed duration: {trimmed_duration}")
    
    return output_path
def mtest_trim_mp3_by_timestamps():
    pass   
#if __name__ == "__main__":
    cur_file_path = "data/0_gitignore/2024-03-06_PB.mp3"
    trim_mp3_by_timestamps(cur_file_path, "0:00", "29:50")

def extract_audio_from_video(video_file_path, bitrate=192, output_dir='data/audio_inbox'):
    """
    Extracts audio from a video file and saves it as MP3. Supports common video formats:
    - MP4 (.mp4): MPEG-4 Part 14 video files
    - AVI (.avi): Audio Video Interleave files
    - MOV (.mov): Apple QuickTime Movie files
    - MKV (.mkv): Matroska Video files

    :param video_file_path: string, path to the input video file
    :param bitrate: int, desired bitrate for the output MP3 in kbps
    :param output_dir: string, directory to save the output MP3. If None, saves in same directory as video
    :return mp3_file_path: string, path to the output MP3 file
    """
    # Check if input file exists
    if not os.path.exists(video_file_path):
        raise FileNotFoundError(f"Video file not found: {video_file_path}")

    # Determine output directory and create MP3 filename
    video_filename = os.path.basename(video_file_path)
    mp3_filename = re.sub(r'\.(mp4|avi|mov|mkv)$', '.mp3', video_filename, flags=re.IGNORECASE)
    
    if output_dir is None:
        # Save in same directory as source video
        output_dir = os.path.dirname(video_file_path)
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    mp3_file_path = os.path.join(output_dir, mp3_filename)
    if os.path.exists(mp3_file_path):
        print(f"{mp3_file_path} already exists and will be overwritten.")

    # Calculate and print original video file size in MB
    original_size = os.path.getsize(video_file_path)
    print(f"Original video file size: {original_size / (1024 * 1024):.1f} MB")

    # Load the video file and extract audio
    video = AudioSegment.from_file(video_file_path)
    
    # Calculate and print audio length
    audio_length = video.duration_seconds
    print(f"Original video audio length: {convert_seconds_to_timestamp(audio_length)}")

    print("\nDEBUG INFO:")
    print(f"Requested bitrate: {bitrate}k")
    
    # Export parameters
    params = [
        "-b:a", f"{bitrate}k",    # Use the requested bitrate
        "-codec:a", "libmp3lame", # Use the libmp3lame codec for MP3
        "-ac", "2",               # Stereo (2 audio channels)
        "-ar", "44100"            # Sample rate of 44100 Hz
    ]

    print(f"FFmpeg parameters: {params}")

    try:
        # Export with parameters
        video.export(
            mp3_file_path,
            format="mp3",
            parameters=params
        )
        
        # Verify the output file
        audio = MP3(mp3_file_path)
        print(f"\nActual output bitrate: {audio.info.bitrate // 1000}k")
        print(f"FFmpeg command line used: {audio.info.encoder_info}")
        
    except Exception as e:
        print(f"Error during extraction: {str(e)}")
        return None

    # Calculate and print new MP3 file size in MB
    new_size = os.path.getsize(mp3_file_path)

    # Check and print MP3 file details
    check_mp3_file(mp3_file_path)

    print(f"Extracted mp3 audio from video into file: {mp3_file_path}")
    return mp3_file_path
def mrun_extract_audio_from_video():
    pass
if __name__ == "__main__":
    video_file_path = "/Users/randytrue/Documents/Focus on Foundations/OurKarlPopper Zoom w Aaron and Logan.mp4"
    extract_audio_from_video(video_file_path)

