## Streaming Audio

### Getting Started

An introduction to getting transcription data from live streaming audio in real time.

#### Suggest Edits

In this guide, you'll learn how to automatically transcribe live streaming audio in real time using Deepgram's SDKs, which are supported for use with the Deepgram API. (If you prefer not to use a Deepgram SDK, jump to the section Non-SDK Code Examples.)

> 📘
> Before you start, you'll need to follow the steps in the Make Your First API Request guide to obtain a Deepgram API key, and configure your environment if you are choosing to use a Deepgram SDK.

### SDKs

To transcribe audio from an audio stream using one of Deepgram's SDKs, follow these steps.

#### Install the SDK

Open your terminal, navigate to the location on your drive where you want to create your project, and install the Deepgram SDK.

JavaScript
Python
C#
Go


## Pre-Recorded Audio

### Getting Started

An introduction to getting transcription data from pre-recorded audio files.

### Suggest Edits

This guide will walk you through how to transcribe pre-recorded audio with the Deepgram API. We provide two scenarios to try: transcribe a remote file and transcribe a local file.

> 📘
> Before you start, you'll need to follow the steps in the Make Your First API Request guide to obtain a Deepgram API key, and configure your environment if you are choosing to use a Deepgram SDK.

### API Playground

First, quickly explore Deepgram Speech to Text in our API Playground.

> 🛝
> Try this feature out in our API Playground!

### CURL

Next, try it with CURL. Add your own API key where it says YOUR_DEEPGRAM_API_KEY and then run the following examples in a terminal or your favorite API client.

If you run the "Local file CURL Example," be sure to change @youraudio.wav to the path/filename of an audio file on your computer. (Read more about supported audio formats here).

#### Remote File CURL Example
#### Local File CURL Example

curl \
  --request POST \
  --header 'Authorization: Token YOUR_DEEPGRAM_API_KEY' \
  --header 'Content-Type: application/json' \
  --data '{"url":"https://dpgr.am/spacewalk.wav"}' \
  --url 'https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true'

> ℹ️
> The above example includes the parameter model=nova-2, which tells the API to use Deepgram's most powerful and affordable model. Removing this parameter will result in the API using the default model, which is currently model=base.
> 
> It also includes Deepgram's Smart Formatting feature, smart_format=true. This will format currency amounts, phone numbers, email addresses, and more for enhanced transcript readability.

### SDKs

To transcribe pre-recorded audio using one of Deepgram's SDKs, follow these steps.

#### Install the SDK

Open your terminal, navigate to the location on your drive where you want to create your project, and install the Deepgram SDK.

JavaScript
Python
C#
Go

Install the Deepgram JS SDK
https://github.com/deepgram/deepgram-js-sdk

npm install @deepgram/sdk

#### Add Dependencies

JavaScript
Python
C#
Go

Install dotenv to protect your api key

npm install dotenv

#### Transcribe a Remote File

This example shows how to analyze a remote audio file (a URL that hosts your audio file) using Deepgram's SDKs. In your terminal, create a new file in your project's location, and populate it with the code.

JavaScript
Python
C#
Go

// index.js (node example)

const { createClient } = require("@deepgram/sdk");
require("dotenv").config();

const transcribeUrl = async () => {
  // STEP 1: Create a Deepgram client using the API key
  const deepgram = createClient(process.env.DEEPGRAM_API_KEY);

  // STEP 2: Call the transcribeUrl method with the audio payload and options
  const { result, error } = await deepgram.listen.prerecorded.transcribeUrl(
    {
      url: "https://dpgr.am/spacewalk.wav",
    },
    // STEP 3: Configure Deepgram options for audio analysis
    {
      model: "nova-2",
      smart_format: true,
    }
  );

  if (error) throw error;
  // STEP 4: Print the results
  if (!error) console.dir(result, { depth: null });
};

transcribeUrl();

#### Transcribe a Local File

This example shows how to analyze a local audio file (an audio file on your computer) using Deepgram's SDKs. In your terminal, create a new file in your project's location, and populate it with the code. (Be sure to replace the audio filename with a path/filename of an audio file on your computer.)

JavaScript
Python
C#
Go

// index.js (node example)

const { createClient } = require("@deepgram/sdk");
const fs = require("fs");

const transcribeFile = async () => {
  // STEP 1: Create a Deepgram client using the API key
  const deepgram = createClient(process.env.DEEPGRAM_API_KEY);

  // STEP 2: Call the transcribeFile method with the audio payload and options
  const { result, error } = await deepgram.listen.prerecorded.transcribeFile(
    // path to the audio file
    fs.readFileSync("spacewalk.mp3"),
    // STEP 3: Configure Deepgram options for audio analysis
    {
      model: "nova-2",
      smart_format: true,
    }
  );

  if (error) throw error;
  // STEP 4: Print the results
  if (!error) console.dir(result, { depth: null });
};

transcribeFile();

### Non-SDK Code Examples

If you would like to try out making a Deepgram speech-to-text request in a specific language (but not using Deepgram's SDKs), we offer a library of code-samples in this Github repo. However, we recommend first trying out our SDKs.

### Results

In order to see the results from Deepgram, you must run the application. Run your application from the terminal. Your transcripts will appear in your shell.

JavaScript
Python
C#
Go

Run your application using the file you created in the previous step
Example: node index.js

node YOUR_PROJECT_NAME.js

> ⚠️
> Deepgram does not store transcripts, so the Deepgram API response is the only opportunity to retrieve the transcript. Make sure to save output or return transcriptions to a callback URL for custom processing.

### Analyze the Response

When the file is finished processing (often after only a few seconds), you'll receive a JSON response:

JSON

{
  "metadata": {
    "transaction_key": "deprecated",
    "request_id": "2479c8c8-8185-40ac-9ac6-f0874419f793",
    "sha256": "154e291ecfa8be6ab8343560bcc109008fa7853eb5372533e8efdefc9b504c33",
    "created": "2024-02-06T19:56:16.180Z",
    "duration": 25.933313,
    "channels": 1,
    "models": [
      "30089e05-99d1-4376-b32e-c263170674af"
    ],
    "model_info": {
      "30089e05-99d1-4376-b32e-c263170674af": {
        "name": "2-general-nova",
        "version": "2024-01-09.29447",
        "arch": "nova-2"
      }
    }
  },
  "results": {
    "channels": [
      {
        "alternatives": [
          {
            "transcript": "Yeah. As as much as, it's worth celebrating, the first, spacewalk, with an all female team, I think many of us are looking forward to it just being normal. And, I think if it signifies anything, It is, to honor the the women who came before us who, were skilled and qualified, and didn't get the the same opportunities that we have today.",
            "confidence": 0.99902344,
            "words": [
              {
                "word": "yeah",
                "start": 0.08,
                "end": 0.32,
                "confidence": 0.9975586,
                "punctuated_word": "Yeah."
              },
              {
                "word": "as",
                "start": 0.32,
                "end": 0.79999995,
                "confidence": 0.9921875,
                "punctuated_word": "As"
              },
              {
                "word": "as",
                "start": 0.79999995,
                "end": 1.04,
                "confidence": 0.96777344,
                "punctuated_word": "as"
              },
              {
                "word": "much",
                "start": 1.04,
                "end": 1.28,
                "confidence": 1,
                "punctuated_word": "much"
              },
              {
                "word": "as",
                "start": 1.28,
                "end": 1.5999999,
                "confidence": 0.9926758,
                "punctuated_word": "as,"
              },
            ...
            "paragraphs": {
              "transcript": "\nYeah. As as much as, it's worth celebrating, the first, spacewalk, with an all female team, I think many of us are looking forward to it just being normal. And, I think if it signifies anything, It is, to honor the the women who came before us who, were skilled and qualified, and didn't get the the same opportunities that we have today.",
              "paragraphs": [
                {
                  "sentences": [
                    {
                      "text": "Yeah.",
                      "start": 0.08,
                      "end": 0.32
                    },
                    {
                      "text": "As as much as, it's worth celebrating, the first, spacewalk, with an all female team, I think many of us are looking forward to it just being normal.",
                      "start": 0.32,
                      "end": 12.495001
                    },
                    {
                      "text": "And, I think if it signifies anything, It is, to honor the the women who came before us who, were skilled and qualified, and didn't get the the same opportunities that we have today.",
                      "start": 12.715,
                      "end": 25.52
                    }
                  ],
                  "num_words": 63,
                  "start": 0.08,
                  "end": 25.52
                }
              ]
            }
          }
        ]
      }
    ]
  }
}

In this default response, we see:

transcript: the transcript for the audio segment being processed.

confidence: a floating point value between 0 and 1 that indicates overall transcript reliability. Larger values indicate higher confidence.

words: an object containing each word in the transcript, along with its start time and end time (in seconds) from the beginning of the audio stream, and a confidence value.

Because we passed the smart_format: true option to the transcription.prerecorded method, each word object also includes its punctuated_word value, which contains the transformed word after punctuation and capitalization are applied.

> 📘
> The transaction_key in the metadata field can be ignored. The result will always be "transaction_key": "deprecated".

### Limits

There are a few limits to be aware of when making a pre-recorded speech-to-text request.

#### File Size

The maximum file size is limited to 2 GB.
For large video files, extract the audio stream and upload only the audio to Deepgram. This reduces the file size significantly.

#### Rate Limits

Nova, Base, and Enhanced Models:

Maximum of 100 concurrent requests per project.
Whisper Model:

Paid plan: 15 concurrent requests.
Pay-as-you-go plan: 5 concurrent requests.
Exceeding these limits will result in a 429: Too Many Requests error.

#### Maximum Processing Time

Fast Transcription Models (Nova, Base, and Enhanced)

These models offer extremely fast transcription.
Maximum processing time: 10 minutes.
Slower Transcription Model (Whisper)

Whisper transcribes more slowly compared to other models.
Maximum processing time: 20 minutes.
Timeout Policy

If a request exceeds the maximum processing time, it will be canceled.
In such cases, a 504: Gateway Timeout error will be returned.

### What's Next?

Now that you've transcribed pre-recorded audio, enhance your knowledge by exploring the following areas.

#### Try the Starter Apps

Clone and run one of our Starter App repositories to see a full application with a frontend UI and a backend server sending audio to Deepgram.

#### Read the Feature Guides

Deepgram's features help you to customize your transcripts.

Language: Learn how to transcribe audio in other languages.
Profanity Filtering and Redaction: Discover how to remove profanity or redact personal information like credit card numbers.
Feature Overview: Review the list of features available for pre-recorded speech-to-text. Then, dive into individual guides for more details.

#### Explore Use Cases

Learn about the different ways you can use Deepgram products to help you meet your business objectives. Explore Deepgram's use cases.

#### Transcribe Streaming Audio

Now that you know how to transcribe pre-recorded audio, check out how you can use Deepgram to transcribe streaming audio in real time. To learn more, see Getting Started with Streaming Audio.
