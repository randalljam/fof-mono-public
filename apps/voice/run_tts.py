from tts import *

combine_text = '''
Maria (Lady Monster Truck): We've got to get Penny out of here! I push on her legs to get her moving out of the room past the witch.
Abdul (GM): She goes with you! But the witch is super angry, and as you race down the next hallway you hear her chanting some sort of spell!
Jimmy (Tiger): Eek! Tiger hides!
'''

combine_voices = '''
narrator: shimmer
Abdul (GM): onyx
Josie (Snowball): alloy
Jimmy (Tiger): echo
Maria (Lady Monster Truck): fable
'''

if __name__ == "__main__":
    mp3_files = tts_combine(combine_text, combine_voices)
    combined_mp3 = combine_mp3_files(mp3_files)
    