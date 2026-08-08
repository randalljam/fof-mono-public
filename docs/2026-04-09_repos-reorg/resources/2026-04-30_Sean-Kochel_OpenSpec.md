## OpenSpec Will Change How You Vibe Code Forever

**Channel:** Sean Kochel  
**Date:** April 30, 2026  
**URL:** https://www.youtube.com/watch?v=nFq4POtqom4  
**Length:** 21:00

**Creator description:** In this video I break down my new favorite spec-driven vibe coding tool, OpenSpec. It's a lighter-weight version of GitHub's Speckit, and is great for developing on top of existing projects.


### Chapters

| Time | Section |
| --- | --- |
| 00:00 | Intro |
| 00:29 | Tool Ecosystem |
| 02:26 | Parts of App to Change |
| 03:50 | Onboard Command |
| 04:09 | Explore Command |
| 06:34 | Generate Proposal |
| 09:29 | Apply Command |
| 10:52 | Results of New Design |
| 13:05 | Archive Command |
| 15:35 | New & Continue Command |
| 18:55 | Fast Forward Command |
| 19:27 | Sync Command |


### Resources

- https://github.com/Fission-AI/OpenSpec


## Categories of AI Software
Sean Kochel groups AI coding tools into three categories. OpenSpec falls into the first. There is crossover between categories, and you can chain tools from different categories together.

### CAT 1 · Spec-First / Alignment
**Core idea:**
- Spec is the primary artifact
- Code is downstream of it
- Human orchestrates, agent assists

Best for vibe coders and people new to AI coding — forces clarity on what you're building before implementation.

#### OpenSpec
- **Characteristics:** Lightweight · brownfield · iterative
- **Workflow:** Proposal → Apply → Archive

#### GitHub SpecKit
- **Characteristics:** Rigid 4-phase · greenfield · GitHub-native
- **Workflow:** Spec → Plan → Tasks → Implement

### CAT 2 · SDLC Enforcement
**Core idea:**
- Full lifecycle with discipline baked into every phase gate
- Enforcement mechanism varies by tool

Real value is enforcing best practices and discipline onto the coding process — not just moving you through a workflow.

#### Agent Skills — Addy Osmani
- **Characteristics:** Google engineering culture · 6 phases
- **Workflow:** Anti-rationalization tables · `/spec` → `/ship`

#### Obra Superpowers
- **Characteristics:** TDD before any code · auto-triggering skills
- **Workflow:** Subagent-driven execution
- **Notable:** Red-green-refactor test-driven development

#### Compound Engineering
- Mentioned in the video alongside the above; includes an ideate/exploration function similar in spirit to OpenSpec's explore command


### CAT 3 · Autonomous Pipeline
**Core idea:**
- System orchestrates the full SDLC
- Human sets goals and approves gates
- Minimal moment-to-moment involvement

Define something, walk away, come back to a built result.

#### BMAD
- **Characteristics:** Persona-driven · 20+ role agents
- **Workflow:** Analyst → PM → Arch → SM → Dev → QA

#### GSD (Get Shit Done)
- **Characteristics:** Context-engineering · anti-rot
- **Workflow:** Fresh sub-agent per phase · walk-away mode


## Transcript

### 00:00 — Intro

Today we're looking at one of the best AI coding frameworks on planet Earth. It's a spec-driven tool called OpenSpec, and it solves some of the biggest problems that I have faced with other vibe coding frameworks, plugins, and tools.

So if you've never used it before and you're tired of screaming into the void as Claude Code doesn't do what you said to do for the millionth time, well, you clicked on the right video. And if you have used it before, they've recently added a new expanded workflow which we will take a look at later.


### 00:29 — Tool Ecosystem

So really quickly, where does this tool sit in the ecosystem of all of these different tools that we have like OBRA and GitHub Spec Kit and BMAD and all of these other things? I think these tools kind of work out into roughly three different categories.

The first category, which this one falls into, I would consider spec-driven tools. These are going to be things like GitHub Spec Kit and obviously OpenSpec, which we are looking at now, where the spec that you create is the primary artifact that drives everything. A lot of time is typically spent making sure you're aligned on exactly what you are going to build, and then everything typically follows through nicely from there. The mental model is mostly that the human is orchestrating the thing but the agent is assisting. I personally think this is the best approach if you are a vibe coder or if you're new to AI coding in general, because it forces you to get really clear on what it is exactly that you are building and what it needs to do.

The second category I would call software development life cycle enforcement. These are things like agent skills, Obra Superpowers, and Compound Engineering. Yes, they have certain workflows that they move you through, but the real value in these tools from my perspective is that they enforce best practices and discipline onto the actual coding process. For example, with OBRA, something like test-driven development—their red-green-refactor—is a really strong thing to do anytime you're going to build something. And that is not something that's going to be built in necessarily to these other tools.

The third group I would call the more autonomous pipeline. These are where we tend to see tools like BMAD, for example, or Get Done, where there's a lot of tooling around you being able to define something and then literally walk away and come back and hey, now it's built something for you without necessarily a ton of intervention. Obviously there's crossover between a lot of these categories, but what we are going to be looking at today is OpenSpec and how it works.


### 02:26 — Parts of App to Change

So what we're going to be doing in this video is solving a problem that I hear from a lot of people, especially in my free group and my paid group, but also in the comments on my videos, which is: you get this first version of something and you end up thinking like this is kind of ugly and it's not really looking like what I want it to look like, but you've spent a lot of work building things and you really want to make it pop.

In this case, I went into Claw Design and I spent a little bit of time going through and trying to build things out so that it looks a lot more professional and is something I would actually want to use. For example, this is what the recipe page looks like right now, and this is ideally what it would end up looking like. We're going to try to use a spec-driven development tool to bridge this gap and build all of these screens out step by step.

Something I'm really big on is that you can chain skills together. Just because you're using one of these doesn't mean you can't use the others. So I'm still going to use Obra's working-with-git-worktrees skill in order to spin up this work tree, run all of my tests, and make sure we have a clean baseline before we start.

To get this thing working it's pretty simple. All you need to do is install the package via the install command, then move into your project and type in `openspec init`, choose your environment, and from there you are ready to go.

One of the things that's really cool that I like about this library is they have this onboarding skill. So if you're new to this and this is going to be the first time using it and you want it to kind of guide you through the process, if you use this onboard command—


### 03:50 — Onboard Command

—it's going to actually take you through building your first feature with this system. But for purposes of showing you all the steps and how we're going to use them, I'm going to run this thing manually.

What I'm going to do is hop back into Claw Design and copy the command that they give you to allow Claude Code to fetch these designs. And then I'm going to come through and run the—


### 04:09 — Explore Command

—first command, which is explore. I'm going to kick this off and then we can chat about it.

Like most good libraries, it has this optional exploration phase where you can actually think about the ideas before you commit to exactly how you want to move through and do it. The thing that I really like is you're not locked into some very specific way of doing things. With a lot of other tools, that's what happens—they have their opinionated approach to how you should move through and do exploration, and that gets tied very specifically to the rest of the process, so there's not a ton of flexibility in being able to use those things sometimes. But you can call this command at really any point in the process when you want to dive deeper into what you're about to change.

This is a nice benefit over something like Spec Kit that kind of assumes that you're going to hop in directly to the spec and know the thing that you want to build. OpenSpec has this opportunity for you to really hash that thing out ahead of time. If you've used other libraries like Compound Engineering, they have that ideate function. This is kind of similar but again a little bit more flexible.

Once it's read through all of that context, it's going to start reasoning about what we asked for. In this case, there are a few different ambiguities that we need to go through and answer, because we're completely changing the established design system that we have documented inside of `design.md` and that gets referenced to be used in `agents.md`. All of those things need to be updated obviously, and then we're going to have to also change the structure of the repo, because based on the information architecture that's in the new designs, that's not going to map very cleanly onto what we have. So there's a good amount of work that's going to need to be done.

I pasted in a little bit of extra context that it needed, and now it is working on clarifying pieces of the plan. One thing that I really like about this: it will flag things that we need to be aware of before we move forward. This process is really valuable because too many people tend to jump straight into trying to build the thing. What that means is that any of these assumptions that are surfacing as we have this conversation, the language model is just going to decide what to do at the time of building the thing, and then you might not be happy with the output.

So this explore feature is a really nice way to sidestep those problems without a ton of ceremony and processes that we tend to have in other tools like Spec Kit or BMAD or some of those other systems. But what do we do from here?


### 06:34 — Generate Proposal

Once we have this fully explored, the next step is to generate a proposal. What you're going to get out the other side is a proposal markdown file, a system design markdown file, and then your task list.

In the design system file, we're going to get a few different things. Number one are going to be the primary architecture decisions. For example, in this case for this project: how are we going to migrate over all of the tokens for the design system? How are we going to actually build these components inside of our system, because they're obviously different from what was inside of Claw Design? How is our app routing and the actual architecture of the app itself going to change? We get a bunch of cool details like that.

Then the proposal is more about what is going to actually change inside of this project—for example, design system migration, building out the new screens, building out the new component library, making sure that we're keeping note of how our data models and our APIs are going to need to change based on the new UI that we're building, because I told it that I didn't want to do all the backend changes right now. So it's a very clear changelog of what exactly we are intending to change with this spec, and then we get a phase-by-phase series of actual tasks that need to be done in order to implement this thing.

We're getting the what and the why of what we're doing from the proposal, the how it's going to be done on a high level from the design markdown file, and then we get the implementation steps from the task file. This convention is awesome because all of the assumptions and all of the decisions are very clearly documented and we have really concrete tasks at each step.

The last piece of this: we get this new specs directory where for every major chunk of what we need to do—for example, the bookmarks migration, the discovery page, the people that you're following, the actual design system migration—each of these gets an individual spec that has very clear scenarios about exactly what needs to be there.

Before we move on to actually apply these changes and show what the work process looks like, one thing that I really love about this tool is that they have this validate function. In this case, I wanted to make sure it has an extra pass where it is going to actually verify its work using the Chrome browser extension MCP. And that's not something that's built into the process. A lot of these tools tend to functionally describe how something should work, but they do not often describe visually how the thing really needs to look. That becomes a problem if you're trying to migrate a design system from another tool.

All we asked it to do was add a step where it has to verify that. Now that it's made this new spec, it's going to run through and validate it to make sure that we haven't lost any of the critical details inside of our spec that we're going to be using to actually build this stuff with. So now we're going to run the final—


### 09:29 — Apply Command

—command, which is apply. We're just going to pass in the directory that it gave us for this project, or the identifier for this project, and we are going to let it run.

One little note: I did boot up Claude with the Chrome flag so that it can actually interact with the browser as it's going through and verifying its work.

This process of having a front-end visual check is actually one of the things that is in the Claude Code creators' stack of tips that can have some of the biggest improvement on what you get out the other side of these types of vibe coding tasks.

All right, guys. So this thing ran through for about two hours straight without really any intervention taken from me. The only thing I did was at a certain point I turned on auto mode so that it would stop pausing to ask me questions. So in reality, with those stops in place, this took maybe three or four hours to actually do. But if we had it on auto mode, the actual processing time would have been two hours and eight minutes.

Again, this includes actually doing all of the work as well as doing the verification that we put in place, where it was using Chrome to actually look at the screens. We haven't seen what this is going to look like yet, but it should be at least pretty close to our designs. So let's go check it out real quick and then we'll come back and do the final step.


### 10:52 — Results of New Design

There's a few different things that I specifically want to look at, because there were some aspects of the app that were bothering me the most. The first is this discovery page that we have. We can see it's a very clear design. We have this sidebar—obviously the sidebar needs to be cleaned up a little bit because it didn't do it to spec. But then we have this hero section, "What's Cooking Now." We have these little filter search options. Then we have this kind of hero section which are updated more recent things. And then it kind of continues through in a little bit of an editorial way.

If we pop over into the screen, it is looking pretty close to that. I'm on a very large screen, and so some of the spacing of how close the sidebar actually is to this middle column—that spacing is a little messed up. So we can address those sorts of things. But overall, this top section, how it's styled, the little details of having the person's name and what the recipe was, the trending forks, the editorial pick—all of that stuff is pretty spot-on. So I'm really happy with that.

The other thing that was really bothering me was the user profile page. If we were to click into Ren, for example, before this was very vanilla—it was nothing. And now if we pop in and go look at what the design was supposed to be, we can see here there's a few things that are off. This is supposed to be an accent color. The alignment on some of these buttons—these should be roughly the same size, one should be accented. So there's a few things that we would need to dial in on this.

But overall, for doing such a large-scale refactor of the design system, it got very close to what we were asking it to do. Even this recipe page is a huge update from what was there in the past. I'm very pleased with how it got through that first version of what we are asking it to do.

Again, the specific aspect of what we were doing is why it was able to do this so effectively. It had the clear functional requirements and clear verification steps, and then it also had those reference designs that it knew to go check. So this is great—things work.

But one of the surprisingly helpful things is how they finish up a feature branch. And that is one of the things that makes this an awesome tool to use. So if we were to come through here now and run the archive command, basically what this—


### 13:05 — Archive Command

—does is it's now going to sync all of the different specs and the context that was built up and gathered around it with the root source of truth about your app. And that's one of the things that I really love about this library. A lot of people complain about how it's difficult to manage the documentation of their app over time, and this is how OpenSpec helps you manage that.

If we were to go look at this OpenSpec folder where all of this lives, you'll notice that all of the work we were doing was inside of this changes folder. The way this works is that every single net-new feature that you have built—in this case we built out a few of them: this new bookmarks view, the discovery page, the following page, the update to the design system—all of those different things are going to get their own spec file. The reason that this is valuable is that when a change gets made, then in the future we're going to have a persistent source of truth that describes how this thing should actually work.

For example, if we were to come down now and look at the bookmarks spec, we have a very clear set of requirements and then user story scenarios that explain functionally what should be happening in this area. The reason that this is valuable is that down the line, if we were to go make a change to our bookmarks functionality in the app, when we go to archive that change like we just did, if we've done something that now breaks a critical piece of this spec, it is going to surface that issue and force us to reconcile it there so that we don't get these sort of black swans or things that are just hidden now inside of our project that we don't realize we broke.

So again, it forces you to have this living set of specifications for all of the major features of your app. After all of that is done, we get this archive folder. If we were to click into this, anything now that we have worked on—for example, this design system migration—all of that information actually gets stored so that we can always go back and reference it if we need to. All of the tasks we worked on, the proposal, how we were going to make sure there was visual fidelity in place—all of that stuff is now saved for us so we can always go back and look at it later.

This is the base workflow, but there are three other workflows you can use that solve a lot of problems that you get with other tools. The first one up is actually two different workflows that you use—


### 15:35 — New & Continue Command

—together, and they are new and continue.

One of the paradigms of this tool that I think really make it stand out compared with others is that it takes an iterative approach to planning. You might have some idea, you start planning it out, but then information pops up along the way and you want to reintegrate that information into your plan moving forward. One of the ways that they solve that is through these two new commands, new and continue.

We're going to kick off this new command and basically we're going to say: now that we have this front-end change made, we need to build out the backend functionality so that the API routes are there, the data models are in place, and everything is good for us to be able to actually do this thing. So we're going to kick off with the new command to start moving in that direction.

What this does is it sets up a shell for us to move through a similar process that we moved through earlier. What we would do to continue through this process now is type in `opsx continue`, and then if there are any questions that we need to answer based on this, we can put our responses in here. In this case I have two options. One is I can do one huge change with everything in it. Number two is that I can slice these changes up into more focused changes and then take them piece by piece, where every single change gets its own proposal, specs, and tasks.

Since this is touching the backend logic, I really want to make sure that we don't miss anything important here. So I chose to go through and slice it that way, which means it's going to take more time, but it's probably going to be done better.

Now in this case, since we have all of these different slices that we're going to move through, we can run this new command again. But in this case we're saying: well, what do we want to kick off? In this specific instance, we're trying to work slice by slice. And so we're going to go through that entire process of creating the proposal, applying the changes, and archiving them for each of these individual pieces. Similar to how we had that scaffolding for this broader plan, we now have the same scaffolding for this very specific change.

Now if we were to come down and run this continue command, what it's going to do is draft the proposal. Similar to how earlier we ran that propose command, we're now doing that in this step-wise fashion. And instead of us having to call the specific command, we are just moving through the process using this continue command.

The difference that we can see now is when we go into this specific change instance for wiring the public profile reads, instead of having generated all of those things at once like we did last time, now we have just the proposal piece. We could go through, we can read this, we can make sure that we're on the same page. And then from here, if we move through and run the continue command, it's going to move on and generate the specs.

The reason that this is really valuable is that earlier on we looked at that explore command. If at any point we're in the middle of doing this and something crops up that we kind of don't know the best way to handle it, we can run the explore command. We can talk through the problem and then we can integrate that change into whatever stage we're at now. This library is really good at generating the context, storing it in a really intelligent way, and then letting you move through to the next stage really easily.

One of the things that's really nice is that if at any point we think we're already good enough with the plan and we just want it to run through the rest of the stages, we can run this fast forward command.


### 18:55 — Fast Forward Command

This is going to allow us to go a lot faster, but still remain on rails. It's still following the system, which is enforcing the best way of doing things and having your spec in place, and then developing from that spec and doing everything that you defined there.

This is very similar to what we were doing in that new-and-continue paradigm, except it's just going to continue to move through it automatically. So this is now complete, and that brings us to the final feature, which I think is one of the most valuable things about how this library works—and that is the sync command.


### 19:27 — Sync Command

Basically what this does is it helps you keep a running tab of the actual state of all of the different features of your app so that you don't need to worry about documentation going off the rails and quickly becoming out of date.

If we were to come back into that master specs folder and scroll down now to public profile, we can see that it has been updated based on this work. All of this extra information in here about the requirements and what the database needs to look like and all of those things—these are all based on the work that we just did in this change. We already had the public profile spec that existed, but now it's been updated with the work that just happened.

Anytime we make any change that touches something that already exists, we have this built-in step that's going to go back and actually update the documentation so that things never get lost and never fall out of touch with the reality of what is there. And that is a huge value add that you don't get with a lot of other tools natively.

This library is pretty great, and I think for having a daily-driver type of workflow—specifically one that calls these other plugins like OBRA or similar libraries in when you need them, for example with sub-agent execution or test-driven development—this is for sure a new daily driver, especially if you're working on an established project.

So if you like this video, I'm going to link to a playlist of other breakdowns of tools like this one that I have done. But that is it for this video.
