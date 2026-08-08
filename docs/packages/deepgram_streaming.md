# Deepgram Streaming

## Getting Started
An introduction to getting transcription data from live streaming audio in real time.

Suggest Edits
Streaming
In this guide, you'll learn how to automatically transcribe live streaming audio in real time using Deepgram's SDKs, which are supported for use with the Deepgram API. (If you prefer not to use a Deepgram SDK, jump to the section Non-SDK Code Examples.)

📘
Before you start, you'll need to follow the steps in the Make Your First API Request guide to obtain a Deepgram API key, and configure your environment if you are choosing to use a Deepgram SDK.

## SDKs
To transcribe audio from an audio stream using one of Deepgram's SDKs, follow these steps.

Install the SDK
Open your terminal, navigate to the location on your drive where you want to create your project, and install the Deepgram SDK.

JavaScript
Python
C#
Go

#Install the Deepgram JS SDK
#https://github.com/deepgram/deepgram-js-sdk

npm install @deepgram/sdk
Add Dependencies
JavaScript
Python
C#
Go

#Install cross-fetch: Platform-agnostic Fetch API with typescript support, a simple interface, and optional polyfill.
#Install dotenv to protect your api key

npm install cross-fetch dotenv
Transcribe Audio from a Remote Stream
The following code shows how to transcribe audio from a remote audio stream. If you would like to learn how to stream audio from a microphone, check out our Live Audio Starter Apps or specific examples in the readme of each of the Deepgram SDKs.

JavaScript
Python
C#
Go

// Example filename: index.js

const { createClient, LiveTranscriptionEvents } = require("@deepgram/sdk");
const fetch = require("cross-fetch");
const dotenv = require("dotenv");
dotenv.config();

// URL for the realtime streaming audio you would like to transcribe
const url = "http://stream.live.vc.bbcmedia.co.uk/bbc_world_service";

const live = async () => {
  // STEP 1: Create a Deepgram client using the API key
  const deepgram = createClient(process.env.DEEPGRAM_API_KEY);

  // STEP 2: Create a live transcription connection
  const connection = deepgram.listen.live({
    model: "nova-2",
    language: "en-US",
    smart_format: true,
  });

  // STEP 3: Listen for events from the live transcription connection
  connection.on(LiveTranscriptionEvents.Open, () => {
    connection.on(LiveTranscriptionEvents.Close, () => {
      console.log("Connection closed.");
    });

    connection.on(LiveTranscriptionEvents.Transcript, (data) => {
      console.log(data.channel.alternatives[0].transcript);
    });

    connection.on(LiveTranscriptionEvents.Metadata, (data) => {
      console.log(data);
    });

    connection.on(LiveTranscriptionEvents.Error, (err) => {
      console.error(err);
    });

    // STEP 4: Fetch the audio stream and send it to the live transcription connection
    fetch(url)
      .then((r) => r.body)
      .then((res) => {
        res.on("readable", () => {
          connection.send(res.read());
        });
      });
  });
};

live();

ℹ️
The above example includes the parameter model=nova-2, which tells the API to use Deepgram's most powerful and affordable model. Removing this parameter will result in the API using the default model, which is currently model=base.

It also includes Deepgram's Smart Formatting feature, smart_format=true. This will format currency amounts, phone numbers, email addresses, and more for enhanced transcript readability.

## Non-SDK Code Examples
If you would like to try out making a Deepgram speech-to-text request in a specific language (but not using Deepgram's SDKs), we offer a library of code-samples in this Github repo. However, we recommend first trying out our SDKs.

Results
In order to see the results from Deepgram, you must run the application. Run your application from the terminal. Your transcripts will appear in your shell.

JavaScript
Python
C#
Go

#Run your application using the file you created in the previous step
#Example: python main.py

python YOUR_PROJECT_NAME.py
⚠️
Deepgram does not store transcripts, so the Deepgram API response is the only opportunity to retrieve the transcript. Make sure to save output or return transcriptions to a callback URL for custom processing.

Analyze the Response
The responses that are returned will look similar to this:

JSON

{
  "type": "Results",
  "channel_index": [
    0,
    1
  ],
  "duration": 1.98,
  "start": 5.99,
  "is_final": true,
  "speech_final": true,
  "channel": {
    "alternatives": [
      {
        "transcript": "Tell me more about this.",
        "confidence": 0.99964225,
        "words": [
          {
            "word": "tell",
            "start": 6.0699997,
            "end": 6.3499994,
            "confidence": 0.99782443,
            "punctuated_word": "Tell"
          },
          {
            "word": "me",
            "start": 6.3499994,
            "end": 6.6299996,
            "confidence": 0.9998324,
            "punctuated_word": "me"
          },
          {
            "word": "more",
            "start": 6.6299996,
            "end": 6.79,
            "confidence": 0.9995466,
            "punctuated_word": "more"
          },
          {
            "word": "about",
            "start": 6.79,
            "end": 7.0299997,
            "confidence": 0.99984455,
            "punctuated_word": "about"
          },
          {
            "word": "this",
            "start": 7.0299997,
            "end": 7.2699995,
            "confidence": 0.99964225,
            "punctuated_word": "this"
          }
        ]
      }
    ]
  },
  "metadata": {
    "request_id": "52cc0efe-fa77-4aa7-b79c-0dda09de2f14",
    "model_info": {
      "name": "2-general-nova",
      "version": "2024-01-18.26916",
      "arch": "nova-2"
    },
    "model_uuid": "c0d1a568-ce81-4fea-97e7-bd45cb1fdf3c"
  },
  "from_finalize": false
}
In this default response, we see:

transcript: the transcript for the audio segment being processed.

confidence: a floating point value between 0 and 1 that indicates overall transcript reliability. Larger values indicate higher confidence.

words: an object containing each word in the transcript, along with its start time and end time (in seconds) from the beginning of the audio stream, and a confidence value.

Because we passed the smart_format: true option to the transcription.prerecorded method, each word object also includes its punctuated_word value, which contains the transformed word after punctuation and capitalization are applied.
speech_final: tells us this segment of speech naturally ended at this point. By default, Deepgram live streaming looks for any deviation in the natural flow of speech and returns a finalized response at these places. To learn more about this feature, see Endpointing.

is_final: If this says false, it is indicating that Deepgram will continue waiting to see if more data will improve its predictions. Deepgram live streaming can return a series of interim transcripts followed by a final transcript. To learn more, see Interim Results.

ℹ️
Endpointing can be used with Deepgram's Interim Results feature. To compare and contrast these features, and to explore best practices for using them together, see Using Endpointing and Interim Results with Live Streaming Audio.

If your scenario requires you to keep the connection alive even while data is not being sent to Deepgram, you can send periodic KeepAlive messages to essentially "pause" the connection without closing it. To learn more, see KeepAlive.

What's Next?
Now that you've gotten transcripts for streaming audio, enhance your knowledge by exploring the following areas. You can also check out our Live Streaming API Reference for a list of all possible parameters.

Try the Starter Apps
Clone and run one of our Live Audio Starter App repositories to see a full application with a frontend UI and a backend server streaming audio to Deepgram.
Read the Feature Guides
Deepgram's features help you to customize your transcripts.

Language: Learn how to transcribe audio in other languages.
Feature Overview: Review the list of features available for streaming speech-to-text. Then, dive into individual guides for more details.
Tips and tricks
End of speech detection - Learn how to pinpoint end of speech post-speaking more effectively.
Using interim results - Learn how to use preliminary results provided during the streaming process which can help with speech detection.
Measuring streaming latency - Learn how to measure latency in real-time streaming of audio.
Add Your Audio
Ready to connect Deepgram to your own audio source? Start by reviewing how to determine your audio format and format your API request accordingly.
Then, check out our Live Streaming Starter Kit. It's the perfect "102" introduction to integrating your own audio.
Explore Use Cases
Learn about the different ways you can use Deepgram products to help you meet your business objectives. Explore Deepgram's use cases.
Transcribe Pre-recorded Audio
Now that you know how to transcribe streaming audio, check out how you can use Deepgram to transcribe pre-recorded audio. To learn more, see Getting Started with Pre-recorded Audio.