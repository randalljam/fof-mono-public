file: apps/math-quiz/docs/2026-07-02_ai-rts-browser-game-spec-prompt.md
title: AI race RTS — browser game spec prompt (extracted)
last-updated: 2026-07-02_1621
ai: Cursor - Composer 2.5 Fast
session: `OCR game spec extraction`

OCR transcription of a game-design prompt (screenshot, 2026-07-02). Items below are split by concern so you can pick which requirements to keep, drop, or adapt. Source text is preserved at the bottom for reference.

## Genre & camera
- [ ] Playable **3D real-time strategy (RTS)** game
- [ ] Runs in the **browser**
- [ ] **Age of Empires–style** gameplay loop (gather → build → advance → conflict)
- [ ] **Bird's-eye view** camera (top-down / isometric-style RTS framing)

## Theme & narrative frame
- [ ] Core metaphor: the **AI race to superintelligence**
- [ ] Mechanics should be **invented from the metaphor**, not a thin reskin of a generic RTS
- [ ] The experience should feel like labs **racing each other** toward an endgame breakthrough

## Factions
- [ ] Four factions: **OpenAI**, **Anthropic**, **Google DeepMind**, **xAI**
- [ ] Each faction has a **brand-inspired visual identity**
- [ ] Each faction gets a **unique gameplay bonus** aligned with its real-world "personality" / positioning


## Economy & resources
Derived from what AI labs actually compete over — turn these into gatherable/spendable resources, building costs, and upgrade gates:
- [ ] **Compute** as a core resource
- [ ] **Data** as a core resource
- [ ] **Talent** as a core resource
- [ ] **Government favor** as a core resource
- [ ] **Public perception** as a core resource


## Progression & win condition
- [ ] **Tech progression** maps to AI-development milestones (not generic "Age II / Age III" alone)
- [ ] **Win condition:** first faction to reach **superintelligence**
- [ ] Match should **end when someone wins** — a decisive superintelligence finish, not an open-ended sandbox

## Opponents
- [ ] Rival labs are **real AI-controlled opponents** (not human-only skirmish)
- [ ] Opponents **race the player** toward superintelligence on the same map/timeline

## Tech stack
- [ ] **Three.js** for 3D rendering
- [ ] **Plain ES modules** — no bundler / build step
- [ ] Served via a **local static file server** (e.g. `python3 -m http.server`)

## Architecture & dev process
- [ ] **Simulation logic separate from rendering** (game state / rules not tangled with Three.js scene code)
- [ ] **Verify each system live in the browser** as you build — not a big-bang integration at the end

## Assets (source & quality)
- [ ] Built from **real downloaded assets** (licensed / free / purchased — not procedural placeholders forever)
- [ ] **High quality** art and models
- [ ] **Never AI-generated assets** (explicit constraint in the prompt)

## Characters & animation
- [ ] Characters are **rigged 3D models**
- [ ] **Skeletal animations** for:
  - [ ] **Walking**
  - [ ] **Working** (gather / build / research)
  - [ ] **Fighting** (combat)

## Visual presentation ("cinematic & juicy")
- [ ] **Dramatic lighting**
- [ ] **Real-time shadows**
- [ ] **Feedback effects on every action** (selection, build start/complete, hits, alerts, etc.)
- [ ] Overall feel: **cinematic and juicy** — polish and punch over bare-minimum RTS

## Audio
- [ ] **Full soundscape** — not silent or placeholder-only
- [ ] Real **sound effects** for:
  - [ ] **Combat**
  - [ ] **Building**
  - [ ] **Alerts**
- [ ] **Quiet background music** underneath gameplay SFX

## Controls
- [ ] **Trackpad-first** input design (scroll/pan, select, command without requiring a mouse or keyboard-first layout)

## UI & onboarding
- [ ] **Clean overlay HUD** (resources, selection, minimap-style info as needed — keep clutter low)
- [ ] **In-game how-to-play guide** (tutorial or reference panel accessible during play)

## Source text (OCR)
> Build me a playable 3D real-time strategy game in the browser — Age of Empires-style gameplay from a bird's-eye view — as a metaphor for the AI race to superintelligence. The factions are OpenAI, Anthropic, Google DeepMind, and xAI, each with brand-inspired identity and a bonus matching their personality. Don't just reskin an RTS: invent the mechanics *from* the metaphor — think about what these labs actually compete over (compute, data, talent, government favor, public perception) and turn those into the economy, the tech progression, and the win condition. Rival labs should be real AI opponents racing you, and the whole thing should end with someone reaching superintelligence first.
>
> Use Three.js (plain ES modules, no build step, local static server), built entirely from real downloaded assets — high quality ones, never AI-generated. Characters should be rigged models that genuinely walk, work, and fight with skeletal animations. Make it cinematic and juicy — dramatic lighting, real shadows, feedback effects on every action — and give it a full soundscape: real sound effects for combat, building, and alerts, with quiet background music underneath. Trackpad-first controls, a clean overlay HUD, and an in-game how-to-play guide. Keep the simulation separate from the rendering, and verify each system live in the browser as you build rather than at the end.
