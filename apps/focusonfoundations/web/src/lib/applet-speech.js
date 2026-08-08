// Speech for applets: plays pre-generated OpenAI TTS clips from
// /audio/<applet>/, falling back to the browser's speechSynthesis for any
// line without a clip. SSR-safe: touches window/document only inside
// functions and guards.
//
// createAppletSpeech() builds a speech instance for one applet; the named
// exports at the bottom are the Counting Creatures instance (kept so existing
// imports don't change).

import { utteranceId } from "./utterance-id.js";
import { AUDIO_CLIP_IDS } from "./counting-creatures-audio-manifest.js";

// One clip/utterance plays at a time across all applets on a page.
let currentAudio = null;

export function stopSpeech() {
  if (currentAudio) {
    try { currentAudio.pause(); currentAudio.src = ""; } catch (e) {}
    currentAudio = null;
  }
  try { window.speechSynthesis && window.speechSynthesis.cancel(); } catch (e) {}
}

function fallbackSpeak(text) {
  try {
    const s = window.speechSynthesis;
    if (!s || !text) return;
    s.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 0.95; u.pitch = 1.12; u.lang = "en-US";
    const v = s.getVoices().find((x) => /en[-_]?US/i.test(x.lang)) || s.getVoices().find((x) => /^en/i.test(x.lang));
    if (v) u.voice = v;
    s.speak(u);
  } catch (e) {}
}

export function createAppletSpeech({ audioBase, clipIds, muteKey }) {
  const ids = new Set(clipIds);
  let muted = null;
  function readStoredMute() {
    try { return window.localStorage.getItem(muteKey) === "1"; } catch (e) { return false; }
  }
  function isMuted() {
    if (muted === null) muted = typeof window === "undefined" ? false : readStoredMute();
    return muted;
  }
  function setMuted(m) {
    muted = !!m;
    try { window.localStorage.setItem(muteKey, muted ? "1" : "0"); } catch (e) {}
    if (muted) stopSpeech();
  }
  function speak(text) {
    if (!text || typeof window === "undefined" || isMuted()) return;
    stopSpeech();
    const id = utteranceId(text);
    if (!ids.has(id)) { fallbackSpeak(text); return; }
    const audio = new Audio(audioBase + id + ".mp3");
    currentAudio = audio;
    audio.play().catch(() => { if (currentAudio === audio) fallbackSpeak(text); });
  }
  // Warm the voices list so the speechSynthesis fallback picks a voice on first use.
  function primeSpeech() {
    try { window.speechSynthesis && window.speechSynthesis.getVoices(); } catch (e) {}
  }
  return { speak, primeSpeech, isMuted, setMuted, stopSpeech };
}

const countingCreatures = createAppletSpeech({
  audioBase: "/audio/counting-creatures/",
  clipIds: AUDIO_CLIP_IDS,
  muteKey: "counting-creatures-muted",
});
export const speak = countingCreatures.speak;
export const primeSpeech = countingCreatures.primeSpeech;
export const isMuted = countingCreatures.isMuted;
export const setMuted = countingCreatures.setMuted;
