## game mechanics
Have a mob that you fight and then once you kill it you have to do a quiz, do a math quiz and be successful which could mean achieve targets by the current graduation success metric of answering X number of times in under 2000 or 3000 milliseconds or it could be achieve demonstration of provisional fluency in a category but the mechanic I'm imagining is if you have to achieve this in order for the mob to stay dead and not reappear

## KEY MODE
would this be a criteria that the player could always achieve or is it a test or a quiz that they can fail?
Meaning is this a quiz that's just open-ended and they can continue until they achieve the success state like x number in under two seconds or is it a quiz as we normally think of a quiz where they get 20 questions and if they don't achieve the success criteria then you know they pass or fail.

## Questions

### Can the mod play a particular sound file (e.g. an MP3), including text-to-speech audio like "Hi"?
**Yes — but not as a raw MP3 through Minecraft’s normal sound path.** MathQuest today only plays built-in vanilla sounds (`EXPERIENCE_ORB_PICKUP`, `VILLAGER_NO`, `PLAYER_LEVELUP`) via `player.playSound(...)`. There are no custom audio assets yet.

The standard Minecraft/Fabric way to play *your own* audio is:

1. Put the file in mod resources as **`.ogg`** (not MP3 — Minecraft’s sound engine does not load MP3).
2. Register it in `assets/mathquest/sounds.json`.
3. Play it through a registered `SoundEvent`, same API as today.

So a TTS line like “Hi” works well if you **generate it ahead of time**, convert MP3 → OGG (ffmpeg), and either bundle it in the jar or drop it into a folder the mod knows about.

**Runtime / dynamic audio** (generate or fetch a new clip while the game is running) is possible but is a separate feature:

- Fetching or reading an MP3/OGG from disk or from the control-panel HTTP server on the client is doable.
- You would still want **OGG on the client** for the cleanest integration with Minecraft volume/settings, or add a small Java-side audio player (more work, less integrated with game audio sliders).
- Sending large audio blobs over Minecraft networking is awkward; better pattern is **URL or file path + client-side fetch/play**.

**Bottom line:** playing a specific prerecorded TTS clip (“Hi”) is straightforward once it is OGG. Playing arbitrary MP3 at runtime is feasible but needs deliberate plumbing; MP3 should be converted or played outside Minecraft’s built-in sound registry.

### Should text-to-speech live inside the mod, or outside it (control panel / server) with the mod only receiving and playing delivered MP3 audio?
**Better outside the mod** — control panel and/or existing Python tooling (`apps/voice/tts.py`), with the mod responsible only for **playback**.

Reasons:

| Inside the mod | Outside (control panel / Python) |
|---|---|
| Heavy TTS libraries or cloud SDKs in Java | Reuse existing Python TTS (OpenAI, Kokoro, etc.) |
| API keys would ship in or near the client mod | Keys stay on the parent/operator machine |
| Harder to iterate voices, scripts, caching | Easy to preview, regenerate, and batch-generate clips |
| Bloats the jar and complicates builds | Mod stays focused on gameplay |

Recommended flow for MathQuest:

1. **Parent/coach side:** control panel (or a small Python script) turns NPC dialogue text into audio → MP3 → **OGG**.
2. **Delivery:** either pre-stage OGG files where the mod/server can read them, or serve them from the existing localhost control panel (`:8765`) and tell the client what to play (new API + optional S2C “play this clip” payload).
3. **Mod/client:** convert to registered custom sounds for fixed lines, or add a thin “play clip by id/path/url” client hook for session-specific dialogue.

**When inside the mod *does* make sense:** a small fixed library of lines shipped as bundled OGG assets (no live TTS) — e.g. always the same “Great job!” sting. That is asset packaging, not a TTS engine.

**Practical default:** generate speech outside; deliver OGG (or MP3 converted at the edge); mod plays audio. Matches how the control panel already owns quiz content, NPC dialogue overrides, and session orchestration.
