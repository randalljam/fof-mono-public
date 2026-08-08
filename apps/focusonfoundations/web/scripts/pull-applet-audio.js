#!/usr/bin/env node
// Pull gitignored applet TTS clips from [S3-FILES-BUCKET] into public/audio/.
// Usage: npm run audio:pull
import { pullAppletAudio } from './applet-audio.js';

pullAppletAudio();
console.log('\nApplet audio pull complete.');
