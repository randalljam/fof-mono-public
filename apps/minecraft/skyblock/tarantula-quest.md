# The Web Ledger Questline v2

## Earn the Tarantula Companion (and learn calm, cooperation, and negotiation)

This is a refreshed **five-step** Skyblock-style progression that keeps all the original spreadsheet learning (ledger → rates → craft vs buy → pet XP → dashboard), but now bakes in:

* **“Calm → Plan → Act”** as the family co-op protocol
* A **no-pressure negotiation** pathway (asking well earns more yeses)
* A **Luck Lab** (so “unfair RNG” becomes science instead of a meltdown trigger)
* A **borrow/checkout system** (trust ritual instead of constant bargaining)

You can read the dialogue, then do the bite-sized spreadsheet tasks while you play side-by-side.

---

## Pre-Quest Setup (2 minutes)

### How the Seals work (doubling progression)

She earns **Silk Seals** each mission: **1 → 2 → 4 → 8 → 16**.
They’re story currency. At the end, the Spider Bank approves the Tarantula “adoption” (your gift/trade).

Optional: give **1 Bonus Seal** anytime she uses the calm protocol *without you prompting*.

### Google Sheet tabs (unlocked as you go)

1. **Code+Ledger**
2. **Rates**
3. **Craft vs Buy**
4. **Pet XP + Luck Lab**
5. **Dashboard + Checkout Log**

---

# Prologue Script (read aloud)

> **Narrator (you):** “There’s a secret Spider Bank in Skyblock. Spiders don’t care about coins… they care about *how you play*.”
> **Spider Clerk:** “Rare drops cause rare emotions. We don’t punish emotions. We build better plans.”
> **Spider Clerk:** “To earn a Tarantula companion, you must become a **Keeper of the Web Ledger**—calm, clever, and cooperative.”

> **You (to Kid1):** “You can want it a lot. That’s allowed. The quest is about learning the best way to go after what you want.”

---

# Mission 1 — The Spider Bank Code + First Strand

## Earn **1 Silk Seal**

**Skills:** simple entries, addition, timestamps, *“formulas vs values”*, emotional protocol (“Calm → Plan → Act”)
**Theme:** feelings are allowed; pressure isn’t the way we decide

## Story (read aloud)

> **Spider Clerk:** “First rule: the Code. Second rule: the Ledger. Without the Code, the Ledger becomes a weapon. With the Code, it becomes power.”

## The Code (you and Kid1 agree out loud)

Keep it short and repeatable:

1. **Feelings are allowed.**
2. **No deals under pressure** (we pause, then plan).
3. **Ask like a teammate** (no demanding).
4. **Always have two plans** (Plan A and Plan B).

Give it a “magic phrase” she chooses: **“Spider Pause!”**

### Tiny practice (30 seconds)

You say: “Spider Pause.”
She does: one deep breath + relax shoulders + “Okay, calm brain.”

That’s it. No lecture.

---

## Spreadsheet task: Code + Ledger tab

### A) Write the Code (kid-owned)

In the top-left, have her type:

* **A1:** `Spider Bank Code`
* **A2–A5:** the 4 rules above
* **A6:** `My Spider Pause phrase is:`
* **B6:** (she types it)

### B) Money snapshot (first strand)

Make columns:

* **A:** Snapshot
* **B:** Time Stamp
* **C:** Purse
* **D:** Bank
* **E:** Total

Fill row 2:

* **A2:** `1`
* **B2:** `=NOW()`
* Copy **B2** → **Paste special → Values only** (freeze time)
* **C2:** Purse (number)
* **D2:** Bank (number)
* **E2:** `=C2+D2`

**Mini-lesson line (short):**

> “A formula is like a spell that keeps calculating. A value is like a number carved in stone.”

### “Doubling” for Mission 1

Do **two snapshots** today (row 2 now, row 3 later).

## Win condition

* She can point to E2 and say: “This cell calculates.”

## Reward

> **Spider Clerk:** “A calm Code and a real Ledger. You earn **1 Silk Seal**.”

---

# Mission 2 — The Measuring Web

## Earn **2 Silk Seals**

**Skills:** division, multiplication, rates per minute → per hour, cell references
**Theme:** we don’t argue about progress; we measure it

## Story (read aloud)

> **Spider Scientist:** “Spiders don’t guess. We measure. Bring me a rate.”

## Focus Sprint rule (this is your attention tool)

> “We do **10 minutes of focus**. When the timer ends, you choose what we do next.”

Optional “Parking Lot”: a cell where she can park random thoughts:

* “Stuffies idea / random thought” goes into the parking lot cell, not your face mid-sentence.

---

## Game task

Harvest **Acacia** (or any steady activity) for **5 minutes** with a timer.

---

## Spreadsheet task: Rates tab

Headers:

* **A:** Test
* **B:** Minutes
* **C:** Amount Collected
* **D:** Per Minute
* **E:** Per Hour
* **F:** Coins Each (optional)
* **G:** Coins per Hour (optional)

Row 2:

* **A2:** `Acacia Test 1`
* **B2:** `5`
* **C2:** (amount collected)
* **D2:** `=C2/B2`
* **E2:** `=D2*60`

Optional money math:

* **F2:** (bazaar price per log, or an estimated value)
* **G2:** `=E2*F2`

### “Doubling” for Mission 2

Do a second test that doubles time:

* Row 3: **10 minutes** (double 5)
  Compare E2 vs E3 (are they close?).

## Win condition

* She can explain why we multiply by 60.

## Reward

> **Spider Scientist:** “You measured reality. You earn **2 Silk Seals**.”

---

# Mission 3 — The Bazaar Mirror + The Negotiator’s Web

## Earn **4 Silk Seals**

**Skills:** multi-row multiplication, SUM, comparisons, structured negotiation
**Theme:** asking well beats demanding; deals are made calmly

## Story (read aloud)

> **Spider Merchant:** “The Bazaar shows prices. The Web Ledger shows *truth.*”
> **Spider Merchant:** “And the Spider Bank has a rule: *No deals under pressure.* Ask like a negotiator.”

---

## Part A: Craft vs Buy (spreadsheet)

Pick an item you both care about today (can be Tarantula-related, minion upgrade, anything).

### Craft vs Buy tab layout

Row 1 headers:

* **A:** Ingredient
* **B:** Quantity
* **C:** Price Each
* **D:** Cost

Rows 2–6 ingredients:

* **D2:** `=B2*C2` (copy down)

Craft total (example **D8**):

* `=SUM(D2:D6)` (adjust range)

Bazaar price:

* **F1:** `Bazaar Price`
* **F2:** (number)

Difference:

* **F3:** `Craft - Bazaar`
* **F4:** `=D8-F2`

**Kid version meaning:**

* Positive = crafting costs more
* Negative = crafting costs less

---

## Part B: Negotiation mini-quest (the key emotional upgrade)

Add a small table beneath it:

### “Negotiator Offers” table

Headers:

* **A:** Offer
* **B:** Time Cost
* **C:** Why it helps Team Web
* **D:** My Offer Score (1–5)

Example offers she can choose from (you can customize):

* “Garden clear for 10 minutes”
* “Minion collection helper (one round)”
* “Spreadsheet focus sprint (10 minutes, no interruptions)”
* “Arachne fights together (30 minutes)”
* “Organize chest: spider drops”

This is not punishment. It’s **tradeable value**.

---

## Negotiator Script (she practices once)

She says (you can prompt lightly):

1. “I feel ___.”
2. “I want ___.”
3. “Because ___.”
4. “Can we make a plan?”

You respond (calmly):

> “Yes. We only plan while calm. Which offer do you want to try?”

### “Doubling” for Mission 3

She makes **two offers** (two rows).
That’s her doubling: one idea → two possible deals.

## Win condition

* She completes Craft vs Buy *and* makes at least one calm offer.

## Reward

> **Spider Merchant:** “You used truth and teamwork. You earn **4 Silk Seals**.”

---

# Mission 4 — The Spider Lab: Pet XP + Luck Lab

## Earn **8 Silk Seals**

**Skills:** differences, rates, time-to-goal, using Wiki/AI responsibly, probability thinking
**Theme:** when RNG feels unfair, we do science instead of spirals

## Story (read aloud)

> **Spider Trainer:** “To keep a Tarantula, you must understand training. Training is measured progress.”
> **Spider Mathematician:** “And when luck hurts your feelings… we calculate.”

---

## Part A: Pet XP session (10 minutes)

### Game task

Grind spiders for **10 minutes**. Record pet XP start and end.

### Pet XP + Luck Lab tab layout

Headers:

* **A:** Session
* **B:** Minutes
* **C:** Start XP
* **D:** End XP
* **E:** XP Gained
* **F:** XP/Minute
* **G:** XP/Hour
* **H:** Target XP (Level goal)
* **I:** XP Remaining
* **J:** Hours to Goal

Row 2 formulas:

* **E2:** `=D2-C2`
* **F2:** `=E2/B2`
* **G2:** `=F2*60`
* **I2:** `=H2-D2`
* **J2:** `=I2/G2`

### Wiki + AI milestone (required)

* iPad Wiki: find the **total XP needed** for her chosen level goal (level 50? 100? you choose) and enter into **H2**.
* AI: ask “What does total XP mean vs XP to next level?” and “How do we estimate time from a 10-minute sample?”

**Rule of thumb you say out loud:**

> “Wiki gives facts. AI gives explanations. Spreadsheet does the math.”

---

## Part B: Luck Lab (turn “unfair” into “random”)

Make a tiny section to model Arachne’s pet drop chance.

### Luck Lab cells

* **L1:** `Drop chance per fight (p)`
* **L2:** (enter the drop chance as a decimal; if the wiki says ~2%, enter `0.02`)
* **M1:** `Number of fights (N)`
* **M2:** (enter your planned fights today)
* **N1:** `Chance of at least one drop`
* **N2:** `=1-(1-L2)^M2`

**Kid explanation line:**

> “Even if we do everything right, the game can still say ‘not this time.’ That’s not unfair—it’s random.”

### “Doubling” for Mission 4

Do two sessions or two Ns:

* Session row 3 with **20 minutes** (double 10), OR
* Compare N = 25 vs N = 50 (double fights) and see how probability grows.

## Win condition

* She can say: “We’re not owed drops. We’re increasing chances.”

## Reward

> **Spider Mathematician:** “You turned feelings into science. You earn **8 Silk Seals**.”

---

# Mission 5 — The Adoption Contract + Checkout Log

## Earn **16 Silk Seals** (and the Tarantula)

**Skills:** linking tabs, summary dashboard, planning, trust rituals (borrowing schedule)
**Theme:** teamwork + calm negotiation = big rewards

## Story (read aloud)

> **Spider Queen of Accounts:** “You have measured. You have planned. You have asked well.”
> “The Tarantula does not belong to tantrums. It belongs to Keepers.”

---

## Part A: Dashboard (make the plan visible)

### Dashboard tab: 4 power boxes

**Box 1: Coins per Hour**

* Label cell: `Coins/hour (best method)`
* Formula: link from Rates tab (example)

  * `=Rates!G2`  (or wherever your coins/hour is)

**Box 2: Goal Cost**

* Label: `Adoption Fee / Target Cost`
* Enter a number (story fee) OR a real bazaar price for something meaningful.

**Box 3: Hours to Earn**

* `= (Goal Cost) / (Coins per Hour)`

**Box 4: Training Time**

* Label: `Hours to Pet Goal`
* Link from Pet XP tab:

  * `='Pet XP + Luck Lab'!J2` (adjust tab name)

**One-line interpretation (she writes it):**

> “If we do ___ hours of ___, we can reach the goal.”

---

## Part B: Checkout Log (trust ritual for borrowing)

This solves the “loan it to me right now forever” loop by making borrowing calm and structured.

### Checkout Log section (same Dashboard tab, or its own area)

Headers:

* Date
* Start Time
* End Time
* What I’m doing (spiders / bestiary / etc.)
* Did I ask with the Negotiator Script? (Y/N)
* Notes (one sentence)

**Rule (Spider Bank style):**

* Borrowing only happens **after** “Spider Pause” + negotiator ask.
* If emotions spike, you pause and the pet “returns to the bank” until calm again.

This makes it about **fair process**, not who is “winning.”

---

## The final ceremony (read aloud)

> **Spider Queen:** “Guardian Randy, present the companion.”
> **You:** “Kid1, you earned this by learning the Web Ledger and asking like a teammate.”
> **Spider Queen:** “Welcome, Keeper of the Web Ledger.”

Then you do the trade/gift.

### “Doubling” for Mission 5 (choose one)

Let her pick:

* Add a **second money method** to compare (two rates), OR
* Add a **Combat 22 plan board** (two boosters/methods and one test), OR
* Run one more spider lab session and update the dashboard.

## Win condition

* Dashboard links work
* Checkout Log exists
* She can explain one cross-tab reference (“this box pulls from Rates”)

## Reward

> **Spider Queen:** “You earn **16 Silk Seals**… and the Tarantula chooses you.”

---

# A tiny “morning script” you can use immediately

If she asks for the pet right away:

> “I hear you—you want it a lot.”
> “Are you calm brain, medium brain, or storm brain?”
> “If storm brain: Spider Pause first. No deals under pressure.”
> “If calm/medium: pick one—Plan A fight together, Plan B checkout schedule, Plan C build your Combat plan.”

---

If you want, I can also provide a **copy-paste sheet blueprint** (exact cell placements and formulas) so you can build this in 5 minutes—while still leaving the key “typing moments” for Kid1.
