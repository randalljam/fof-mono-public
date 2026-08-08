file: skills/media/youtube-transcript/references/example-yt-transcript-02-single-speaker-transitions-adjusted.md
title: Example 02 — single speaker, transitions adjusted

**Synthetic format example only.** All names, channel, URLs, and spoken text below are invented for documenting this skill's markdown layout (including default chapter-transition adjustment). Not a real video or transcript.


## Metadata
file: 2026-04-18_Dana Orth | Desk Systems_How DeskPilot's Inventor Starts EVERY Project_yt.md
title: How DeskPilot's Inventor Starts EVERY Project
url: https://www.youtube.com/watch?v=ExAmPlEvid02
source: youtube
channel: Dana Orth | Desk Systems
length: 12:40
speakers: single
diarized: no


## Summary
Dana Orth walks through how Riley Voss — the fictional inventor of DeskPilot — actually uses the tool, distilled from Riley's public posts into an adoptable workflow. The default pattern most people learn (one chat, type, wait, repeat) is the opposite of how Riley works: roughly eight parallel sessions at once, each dedicated to a single job, using separate folders on disk plus a few browser tabs, often kicked off from a phone before sitting down.

The highest-leverage piece is PROJECT.md, a project-root rules file loaded automatically at session start. Riley treats mistakes as permanent lessons — asking the agent to draft new rules whenever it errs — and even comments on shared checklists to update the file, creating what they call a "compound desk loop." Other practices include plan mode (iterate on the plan, then one-shot the work), reusable slash commands, local /loop jobs for daytime repetition, cloud /schedule routines for overnight work, and verification prompts that force the agent to check its own output.

Orth adapts the setup for non-builders: two or three parallel sessions instead of eight, a rules document referenced every prompt, plan-first discipline, named prompts for recurring tasks, one daytime loop and one overnight schedule, and a verification line on important work — while skipping multi-folder checkouts and pull-request workflows unless you ship code.


## Description
More courses & support: https://example.com/desk-systems/join
Transform your desk with imaginary tools: https://example.com/deskpilot-demo
Join the best community for notebook tinkerers: https://example.com/skool/desk-systems

Sign up to our weekly desk newsletter - https://example.com/desk-core

Connect With Me!
Instagram - / dana.orth.example
X - https://example.com/x/DanaOrth
LinkedIn - https://example.com/in/dana-orth-example


## Chapters
- [0:00](https://www.youtube.com/watch?v=ExAmPlEvid02&t=0) How the person who built DeskPilot actually uses it
- [0:53](https://www.youtube.com/watch?v=ExAmPlEvid02&t=53) Eight parallel sessions: one session, one job
- [2:55](https://www.youtube.com/watch?v=ExAmPlEvid02&t=175) PROJECT.md: the file that learns
- [4:03](https://www.youtube.com/watch?v=ExAmPlEvid02&t=243) The compound desk loop
- [5:37](https://www.youtube.com/watch?v=ExAmPlEvid02&t=337) Plan mode: pour energy into the plan
- [7:03](https://www.youtube.com/watch?v=ExAmPlEvid02&t=423) Slash commands & helpers
- [8:43](https://www.youtube.com/watch?v=ExAmPlEvid02&t=523) Slash loop: background processes
- [10:20](https://www.youtube.com/watch?v=ExAmPlEvid02&t=620) Verification: the number one tip
- [11:30](https://www.youtube.com/watch?v=ExAmPlEvid02&t=690) What to copy vs skip as a non-builder


## Transcript
### 0:00 How the person who built DeskPilot actually uses it
[0:00](https://www.youtube.com/watch?v=ExAmPlEvid02&t=0)
Most people use DeskPilot completely wrong, and honestly, it's not their fault. The defaults teach you to type into one chat, hit enter, wait, and then type again. And that's the loop that everyone learns first. The person who actually built DeskPilot does basically the opposite. Their name is Riley Voss. They run about eight DeskPilot sessions at the same time, and they barely type most of their own prompts, and they've been writing about exactly how they do this for months now. I've read every public post they've made about how they use DeskPilot, and I put this entire thing on this one page so that we could walk through it together. So, if you've never run an agent a day in your life, it does not matter. You can copy this today, but let's get into it. Now, some quick context before we actually jump into it. Everything that Riley has said publicly is going to be sourced on this page, and everything that I am adapting for people who do not write code is going to be labeled separately. So, I will have this available to download inside of my free school community. The link will be down below in the description. So, make sure to join that if you want access.

### 0:53 Eight parallel sessions: one session, one job
[0:53](https://www.youtube.com/watch?v=ExAmPlEvid02&t=53)
Now, Riley has about four DeskPilot sessions open in the terminal at the same time. Each one is its own separate folder checkout, so the changes never clash. They number the tabs one through four just to keep them straight. On top of that, they've been running another three to four sessions inside the browser. And before they're even at the desk in the morning, they're already kicking off new sessions from the phone, then picking them up on the computer when they sit down. The big rule that makes this whole thing work is one session, one job. They never ask the same session to do two different things. Each one gets its own single task, its own context, and nothing else. Personally, I run about two at a time. I have one for research, generally one for writing, and the number isn't really the point. The point is just going from one session to more than one.

### 2:55 PROJECT.md: the file that learns
[2:55](https://www.youtube.com/watch?v=ExAmPlEvid02&t=175)
Now, this next piece is the one that most people miss when they actually try and copy this. And honestly, it's the highest leverage thing on this entire page, and it is the PROJECT.md file. This is effectively just the file that learns. You drop a file called PROJECT.md inside the root of your project folder. DeskPilot then reads that file automatically every single time you start a session in that folder. You don't have to attach it. You don't have to paste it in. You don't have to remind the agent that it exists. It's just loaded into context before anything else. What goes inside is simple rules: project context, things to do, things to never do, stuff like never delete files in the assets folder without asking, or when you draft an email always read the offer document first. Anything you would otherwise re-explain in every chat, write into this file once and you are done.

### 4:03 The compound desk loop
[4:03](https://www.youtube.com/watch?v=ExAmPlEvid02&t=243)
Now, what actually makes this compound is every time the agent does something wrong inside a session, the fix gets written into the file as a permanent rule. Riley's exact words: anytime we see DeskPilot do something incorrectly, we add it to PROJECT.md. And the agent is very good at writing rules for itself. So you can literally ask the session, "Update PROJECT.md so you don't make that mistake again." It'll draft the rule; you read it, save it, and you're done. An entire team can share the same PROJECT.md by checking it into version control. When one person adds a rule, everyone gets it on their next session. Riley calls this whole loop the compound desk loop, and the name is accurate because week one your PROJECT.md maybe has five rules and month three it has fifty, and each rule compounds across every session that follows.

### 5:37 Plan mode: pour energy into the plan
[5:37](https://www.youtube.com/watch?v=ExAmPlEvid02&t=337)
Anyone can paste the same prompts into DeskPilot; nobody else is going to have your same PROJECT.md. Moving on to section number three: plan mode. In any active session, when you hit the plan toggle twice, the prompt indicator shows you that you are in plan mode. When you type your task, the agent doesn't just do the work; it writes the plan first. You read it, fix whatever may be wrong, and then tell it to proceed. Riley starts most sessions this way: iterate on the plan until it's solid, then switch to auto-accept and let the model one-shot the implementation. The phrase for it is pour your energy into the plan so DeskPilot can one-shot the implementation. I use this every day before pretty much anything that is not a one-liner. First prompt: don't do it yet, just write me the plan step-by-step. Second prompt: good, go ahead and do it. If the work goes off the rails halfway through, don't patch it in the same mode — drop back into plan mode and replan from there.

### 7:03 Slash commands & helpers
[7:03](https://www.youtube.com/watch?v=ExAmPlEvid02&t=423)
Section number four: slash commands and helpers. Inside your project folder you create a folder called .desk/commands. Inside that you drop a markdown file. The file name becomes the command name. So a file called tidy-inbox.md becomes /tidy-inbox. The contents of the file are just the prompt itself, and that is the entire setup. Riley's actual commands are /tidy-inbox, /simplify, /verify, and /go. They use these dozens of times a day. Helpers are the next layer up: same idea, bigger scope. You define them in .desk/agents, each its own markdown file with a role and permissions. I have around five of these saved. The one I use the most is a /sponsor-reply command that pulls my rate card from a file and drafts the response in my voice.

### 8:43 Slash loop: background processes
[8:43](https://www.youtube.com/watch?v=ExAmPlEvid02&t=523)
Moving on to number five, the /loop. /loop turns a one-shot agent into a process that runs in the background. In any active session you type /loop, then an interval like 5m or 1h, then the prompt or slash command you want repeating. Hit enter and it runs on that schedule until you cancel it or three days pass. The catch that matters: your machine has to stay on. If you close the lid, the loop dies. Overnight work belongs in /schedule on the next section. Personally I tried three loops at once for a week, turned them all off, and found that two is the sweet spot. The two I keep are an inbox sweep every fifteen minutes during the work day and a lead status check about every hour.

### 10:20 Verification: the number one tip
[10:20](https://www.youtube.com/watch?v=ExAmPlEvid02&t=620)
Now, if you take one thing away from this video, take verification. Riley's exact words: give DeskPilot a way to verify its work. This has always been a way to two or three X what you can get out of it. Challenge prompts at the end of a task: grill me on these changes, prove to me this works, scrap this and implement the elegant solution. Each one forces the session to switch from doing the work to checking the work. For a draft email, maybe: reread this against my offer doc and flag anything inaccurate. For a research report: list every claim that has no source. Add this as a skill if you want — /prove — and run it whenever the work matters.

### 11:30 What to copy vs skip as a non-builder
[11:30](https://www.youtube.com/watch?v=ExAmPlEvid02&t=690)
Moving on, I'm going to be honest that a lot of this is developer-shaped. The split I would go with: copy two or three sessions in parallel, a rules document you reference every prompt, plan-first discipline, named prompts for anything you do twice, one loop during the day, one schedule overnight, and a verification line on every important task. Skip eight parallel sessions, multi-folder checkouts if you don't ship code, and anything that ends in a pull request. That's it for today's video. If you're not subscribed, hit subscribe, grab the free resources in the description, and tell me in the comments what you're using. Thanks for watching. Hopefully you found some value, and I'll see you in the next one.
