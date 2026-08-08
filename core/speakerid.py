# START OF FILE core/speakerid.py
import os
import torch  # run 'pip install torch torchvision torchaudio' for PyTorch with Apple Silicon support
import torchaudio
from speechbrain.inference.speaker import SpeakerRecognition
import numpy as np
from pydub import AudioSegment
import time
import glob


### SPEECHBRAIN INITIALIZATION
def initialize_speakerid():
    """
    Initializes the speaker identification model using SpeechBrain.
    Checks for Apple Silicon GPU (MPS) availability and sets up the device accordingly.
    Loads the pre-trained ECAPA-TDNN model trained on VoxCeleb.
    
    :return: None
    """
    # Check for MPS (Metal Performance Shaders) availability instead of CUDA
    print(f"MPS (Apple Silicon GPU) available: {torch.backends.mps.is_available()}")
    print(f"MPS backend enabled: {torch.backends.mps.is_built()}")

    # Set device
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Using device: {device}")

    # Initialize the pre-trained model
    verification = SpeakerRecognition.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        savedir="pretrained_models/spkrec-ecapa-voxceleb"
    )
def mrun_initialize_speakerid():
  pass
#if __name__ == "__main__":
  initialize_speakerid()

### AUDIO PROCESSING
def extract_clip_from_audio_file(audio_file_path, start_time, duration, clip_dir='data/0_gitignore/audio_clips'):
    """
    Extracts an audio clip from a larger audio file.
    
    :param audio_file_path: string path to the source audio file
    :param start_time: integer start time in seconds
    :param duration: integer duration in seconds
    :param clip_dir: string path to output directory for clips
    :return: string path to the created audio clip file
    """
  
    # Create output directory if it doesn't exist
    if not os.path.exists(clip_dir):
        os.makedirs(clip_dir)
        
    # Load audio file
    audio = AudioSegment.from_file(audio_file_path)
    
    # Convert to milliseconds for pydub
    start_ms = start_time * 1000
    duration_ms = duration * 1000
    
    # Extract clip
    clip = audio[start_ms:start_ms + duration_ms]
    
    # Generate output filename
    clip_filename = f"clip_{start_time}_{duration}s.mp3"
    clip_path = os.path.join(clip_dir, clip_filename)
    
    # Export clip
    clip.export(clip_path, format="mp3")
    
    return clip_path

def get_clip_duration(current_timestamp, next_timestamp, default_duration=10):
    """
    Determines clip duration based on current and next timestamp.
    
    :param current_timestamp: integer current timestamp in seconds
    :param next_timestamp: integer or None next timestamp in seconds
    :param default_duration: integer default duration if no next timestamp
    :return: integer duration in seconds
    """
    if next_timestamp is None:
        return default_duration
    
    duration = next_timestamp - current_timestamp - 1  # Subtract 1 second for gap
    return min(duration, default_duration)  # Cap at default duration

def create_audio_dict_from_transcript_file(transcript_file_path, duration=10, output_dir='data/0_gitignore'):
    """
    Creates a dictionary of speaker audio clips from a transcript file.
    Downloads the full audio and extracts clips for each speaker segment.
    
    :param transcript_file_path: string path to transcript markdown file
    :param duration: integer default clip duration in seconds
    :param output_dir: string path to output directory
    :return: list of dicts containing speaker info and clip paths
    """
    from core.fileops import read_metadata_field_from_file, convert_timestamp_to_seconds
    from core.transcribe import download_mp3_from_youtube
    from core.docwork import extract_transcript_data
    
    # Get YouTube URL from metadata
    _, youtube_url = read_metadata_field_from_file(transcript_file_path, 'link')
    if not youtube_url:
        raise ValueError(f"No YouTube URL found in {transcript_file_path}")
    
    # Download audio file using existing function
    audio_output = download_mp3_from_youtube(youtube_url, output_title='audio_download', output_dir=output_dir, skip_download=True)
    
    # Get transcript data using existing function
    transcript_data = extract_transcript_data(transcript_file_path)
    if transcript_data is None:
        raise ValueError(f"No transcript data found in {transcript_file_path}")
    
    print(f"Starting to create speaker clips as files ...")
    # Create speaker clips from transcript data
    speaker_clips = []
    for i, entry in enumerate(transcript_data):
        current_timestamp = convert_timestamp_to_seconds(entry['timestamp'])
        
        # Get next timestamp if available
        next_timestamp = None
        if i + 1 < len(transcript_data):
            next_timestamp = convert_timestamp_to_seconds(transcript_data[i + 1]['timestamp'])
        
        # Get clip duration
        clip_duration = get_clip_duration(current_timestamp, next_timestamp, duration)
        
        # Extract clip
        clip_path = extract_clip_from_audio_file(
            audio_output,
            current_timestamp,
            clip_duration
        )
        
        # Add to results
        speaker_clips.append({
            'orig_speaker': entry['speaker_name'],
            'start_time': current_timestamp,
            'audio_clip_file_path': clip_path
        })
    
    return speaker_clips
def mrun_create_audio_dict_from_transcript_file():
    pass
#if __name__ == "__main__":
    transcript_file = "data/pv/meetings_tc_2024/2024-10-30_PV-TC_spasgn.md"
    speaker_clips = create_audio_dict_from_transcript_file(transcript_file)
    print(f"Created {len(speaker_clips)} speaker clips")

def create_speaker_embedding(audio_file, start_time=0, duration=10):
    """
    Create a speaker embedding from an audio clip
    
    :param audio_file: Path to the audio file
    :param start_time: Start time in seconds
    :param duration: Duration in seconds (aim for 10s of clean speech)
    :return: Speaker embedding
    """
    print(f"Loading speaker recognition model...")
    # Load the pre-trained model
    verification = SpeakerRecognition.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        savedir="pretrained_models/spkrec-ecapa-voxceleb"
    )
    
    print(f"Loading audio file: {audio_file}")
    # Load and trim audio to desired segment
    waveform, sample_rate = torchaudio.load(audio_file)
    start_frame = int(start_time * sample_rate)
    end_frame = int((start_time + duration) * sample_rate)
    segment = waveform[:, start_frame:end_frame]
    
    print(f"Generating embedding for segment starting at {start_time}s...")
    # Create embedding
    embedding = verification.encode_batch(segment)
    print("Embedding generated successfully")
    return embedding

def generate_speaker_enrollment_set(speaker_name, transcript_file_path, set_number, 
                                  duration=10, output_dir='data/0_gitignore/audio_embeddings'):
    """
    Generates a set of speaker embeddings from a transcript file for a specific speaker.
    
    :param speaker_name: Name of the speaker to generate embeddings for
    :param transcript_file_path: Path to the transcript file
    :param set_number: Number of embeddings to generate
    :param duration: Duration in seconds for each embedding (default 10)
    :param output_dir: Directory to save embeddings
    """
    from core.fileops import track_progress, read_metadata_field_from_file, convert_timestamp_to_seconds
    from core.transcribe import download_mp3_from_youtube
    from core.docwork import extract_transcript_data
    
    print(f"\nGenerating speaker embeddings for {speaker_name}")
    print(f"Using transcript file: {transcript_file_path}")
    print(f"Requesting {set_number} embeddings of {duration}s each")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}")
    
    # Get YouTube URL and download audio
    print("\nRetrieving YouTube URL from transcript...")
    _, youtube_url = read_metadata_field_from_file(transcript_file_path, 'link')
    if not youtube_url:
        raise ValueError(f"No YouTube URL found in {transcript_file_path}")
    
    print("Downloading audio file...")
    audio_file = download_mp3_from_youtube(youtube_url, output_title='audio_download', 
                                         output_dir=output_dir, skip_download=True)
    
    # Extract transcript data
    print("Extracting transcript data...")
    transcript_data = extract_transcript_data(transcript_file_path)
    if transcript_data is None:
        raise ValueError(f"No transcript data found in {transcript_file_path}")
    
    # Filter for specified speaker and get first set_number entries
    speaker_entries = [entry for entry in transcript_data 
                      if entry['speaker_name'] == speaker_name][:set_number]
    
    if not speaker_entries:
        raise ValueError(f"No entries found for speaker {speaker_name}")
    
    print(f"Found {len(speaker_entries)} entries for {speaker_name}")
    
    print("\nInitializing SpeechBrain model...")
    print("This may take a while on first run as it downloads the model (~1GB)...")
    try:
        verification = SpeakerRecognition.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir="pretrained_models/spkrec-ecapa-voxceleb",
            run_opts={"device":"cpu"}  # Force CPU to debug
        )
        print("SpeechBrain model initialized successfully!")
    except Exception as e:
        print(f"Error initializing SpeechBrain: {str(e)}")
        raise
    
    # Process each entry
    print("\nStarting embedding generation...")
    embedding_paths = []
    start_time = time.time()
    last_percentage = 0
    
    for i, entry in enumerate(speaker_entries):
        if i == 0:
            print(f"Generating first embedding at timestamp {entry['timestamp']}...")
            
        # Convert timestamp to seconds
        start_time_seconds = convert_timestamp_to_seconds(entry['timestamp'])
        
        # Create embedding
        embedding = create_speaker_embedding(
            audio_file,
            start_time=start_time_seconds,  # Now passing seconds as a number
            duration=duration
        )
        
        # Generate filename: speaker_name_transcriptbase_HHMMSS.pt
        transcript_base = os.path.splitext(os.path.basename(transcript_file_path))[0]
        
        # Convert timestamp to seconds then format as HHMMSS
        seconds = convert_timestamp_to_seconds(entry['timestamp'])
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        timestamp = f"{hours:02d}{minutes:02d}{secs:02d}"  # Format as HHMMSS
        
        embedding_filename = f"{speaker_name}_{transcript_base}_{timestamp}.pt"
        embedding_path = os.path.join(output_dir, embedding_filename)
        
        # Save embedding
        torch.save(embedding, embedding_path)
        embedding_paths.append(embedding_path)
        
        # Update progress
        last_percentage = track_progress(i + 1, len(speaker_entries),
            start_time, last_percentage, "embeddings")
    
    print(f"\nGenerated {len(embedding_paths)} embeddings for {speaker_name} from {transcript_file_path}")
    return embedding_paths
def mrun_generate_speaker_enrollment_set():
    pass
#if __name__ == "__main__":
    transcript_file = "data/pv/meetings_tc_2024/2024-10-30_PV-TC_spasgn.md"
    speaker_name = "Craig Taylor"
    set_number = 5
    
    embedding_paths = generate_speaker_enrollment_set(
        speaker_name,
        transcript_file,
        set_number
    )

def evaluate_enrollment_set(speaker_name, embedding_dir='data/0_gitignore/audio_embeddings'):
    """
    Evaluate similarity between all embeddings for a speaker in the given directory.
    Returns similarity scores between embeddings to help identify best reference samples.
    
    :param speaker_name: Name of the speaker whose embeddings to evaluate
    :param embedding_dir: Directory containing the speaker embeddings (.pt files)
    :return: Dictionary of embedding files and their average similarity scores
    """
    print(f"\nEvaluating enrollment set for {speaker_name}")
    print(f"Looking in directory: {embedding_dir}")
    
    # Find all .pt files for this speaker
    pattern = os.path.join(embedding_dir, f"{speaker_name}_*.pt")
    embedding_files = glob.glob(pattern)
    
    if not embedding_files:
        raise ValueError(f"No embedding files found for {speaker_name} in {embedding_dir}")
    
    print(f"Found {len(embedding_files)} embedding files")
    
    # Load all embeddings
    embeddings = {}
    for file_path in embedding_files:
        file_name = os.path.basename(file_path)
        embedding = torch.load(file_path)
        # Ensure embedding is properly shaped: [1, embedding_dim]
        if embedding.dim() > 2:
            embedding = embedding.squeeze(0)
        embeddings[file_name] = embedding
    
    # Compare each embedding against all others using cosine similarity
    print("\nComparing embeddings...")
    scores = {}
    for file1 in embeddings:
        total_score = 0
        count = 0
        emb1 = embeddings[file1].flatten()  # Flatten to 1D tensor
        
        for file2 in embeddings:
            if file1 != file2:
                emb2 = embeddings[file2].flatten()  # Flatten to 1D tensor
                score = torch.nn.functional.cosine_similarity(
                    emb1.unsqueeze(0), 
                    emb2.unsqueeze(0)
                )
                total_score += score.item()  # Now definitely a scalar
                count += 1
                
        avg_score = total_score / count if count > 0 else 0
        scores[file1] = avg_score
    
    # Sort and print results
    print("\nSimilarity Scores:")
    sorted_scores = dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))
    for file_name, score in sorted_scores.items():
        print(f"{file_name}: {score:.3f}")
    
    return sorted_scores

def mrun_evaluate_enrollment_set():
    pass
if __name__ == "__main__":
    speaker_name = "Craig Taylor"
    scores = evaluate_enrollment_set(speaker_name)

# END OF FILE core/speakerid.py
