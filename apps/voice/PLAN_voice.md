12-18 Randy 
GOALS
- read dialogue in manually or auto selected voices from SS
- solid dialogue python code can use in future
START 3:08am
- X fix/add support functions in fileops to get text after ### transcript
  - X update trim_content
  - X add get_content_from_file
  - X test 3:31am
- X add import for fileops to voice
  - X copy over test lines and run from tts.py 3:41am
- code core dialogue functions in tts.py
  - X handle my format with timestamp
    - X look for reusable code to parse speaker segs in fileops and transcribe
  - X handle colon only format with and without newline DONE 4:48am commit
  - X do voice lookup if voice names provided
  - X assign default voices if no voice names provided (3 nova echo onyx) DONE 6:00am
  - X create seg mp3s
  - X combine into single mp3 DONE 7:09am woo hoo

 *** HERE is where I am ***
- update and test cli version of dialogue voice function
  - fix pydub in local environment
  - colon only format
  - with timestamp links
  - without timestamp links
- clone voices Deutsch again and Rorty
- implement in SS
- clone more voices!
  TL
  Randy
  BS
  EA
  Kid1
  what other fun ones



12-18 Randy COPY AT 3:08
GOALS
- read dialogue in manually or auto selected voices from SS
- solid dialogue python code can use in future
START
- fix/add support functions in fileops to get text after ### transcript
  - update trim_content
  - add get_content_from_file
  - test
- add import for fileops to voice
- code core dialogue functions in voice.py
- update and test cli version of dialogue voice function
  - colon only format
  - with timestamp links
  - without timestamp links
- implement in SS
- clone voices
  Deutsch again
  Rorty
  TL
  Randy
  BS
  Kid1
  what other fun ones
