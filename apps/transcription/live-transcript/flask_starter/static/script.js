let isRecording = false;
let socket;
let microphone;

const socket_port = 5001;
socket = io(
  "http://" + window.location.hostname + ":" + socket_port.toString()
);

let fullTranscript = '';
let lastSpeaker = null;

socket.on("transcription_update", (data) => {
  //console.log("Received transcription data:", data.words);  // Add this line
  const words = data.words;
  if (words && words.length > 0) {
    let transcriptSegment = '';
    words.forEach((wordInfo) => {
      // Check if speaker has changed
      if (wordInfo.speaker !== lastSpeaker) {
        lastSpeaker = wordInfo.speaker;
        transcriptSegment += `<br><strong>Speaker ${lastSpeaker}:</strong> `;
      }
      transcriptSegment += wordInfo.word + ' ';
    });

    // Append the new segment to the full transcript
    fullTranscript += transcriptSegment;
    document.getElementById("captions").innerHTML = fullTranscript;
  }
});

async function getMicrophone() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    return new MediaRecorder(stream, { mimeType: "audio/webm" });
  } catch (error) {
    console.error("Error accessing microphone:", error);
    throw error;
  }
}

async function openMicrophone(microphone, socket) {
  return new Promise((resolve) => {
    microphone.onstart = () => {
      console.log("Client: Microphone opened");
      document.body.classList.add("recording");
      resolve();
    };
    microphone.ondataavailable = async (event) => {
      if (event.data.size > 0) {
        socket.emit("audio_stream", event.data);
      }
    };
    microphone.start(20000);  // controls audio chunk size in ms
  });
}

async function startRecording() {
  isRecording = true;
  microphone = await getMicrophone();
  console.log("Client: Waiting to open microphone");
  await openMicrophone(microphone, socket);
}

async function stopRecording() {
  if (isRecording === true) {
    microphone.stop();
    microphone.stream.getTracks().forEach((track) => track.stop());
    socket.emit("toggle_transcription", { action: "stop" });
    microphone = null;
    isRecording = false;
    console.log("Client: Microphone closed");
    document.body.classList.remove("recording");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const recordButton = document.getElementById("record");

  recordButton.addEventListener("click", () => {
    if (!isRecording) {
      socket.emit("toggle_transcription", { action: "start" });
      startRecording().catch((error) =>
        console.error("Error starting recording:", error)
      );
    } else {
      stopRecording().catch((error) =>
        console.error("Error stopping recording:", error)
      );
    }
  });
});
