# Client and server discrepancies in multiplayer test
_Exported on 5/11/2026 at 20:34:40 PDT from Cursor (3.3.30)_

---

**User**

@mathquest/docs/2026-05-11_multiplayer-npc-test-script.md @mathquest/docs/2026-05-11_mathquest-server-conversion-plan.md @mathquest/docs/OVERVIEW.md @/Users/randytrue/.cursor/projects/Users-randytrue-Documents-Code-kid-games/terminals/15.txt:541-569  Okay, so I'm going through this test script, the testscript.md, and I'm on step six or section six, test six, section number 17, and the operation for me was Exponentiation, and it was an addition. And when I hit MathQuest status from the client, I see some differences. The interval is 10 minutes versus on the server it's two minutes. But here, I let you see what it is on the server. I'm just going to copy this in and then I'm going to say what's different. Okay. Yeah, and by the way, just review the plan document, review the overview document. The problems per quiz is 10 here on the client and on the server it's five. And then my character player name is RJComp, and for me, the operation is set to Exponentiation. And then what it is in the server, I don't appear in the server under a player preset. The other players are the same, but I don't show up there, which is strange. These have the same file. I copied the same file over and I don't think I changed or removed my player preset, so that's weird. I did designate myself as an OP, so I don't know if that changed, that removed me, my player preset. It is giving me 10 questions for Exponentiation, which is different from what the server is showing. So why is that different? But then here's what's strange, the NPC does seem to be the wandering nerd, does seem to be spawning every 15 seconds, not every 10 minutes. So what's going on here?

---

**Cursor**

I’ll trace what the test script and docs expect against what the server/client status outputs actually mean, then I’ll check the MathQuest config path/code if the docs don’t explain the mismatch.

I found the key split in the overview: in remote multiplayer, Wandering Nerd spawning/timing is server-side, but the quiz screen still builds questions from the client’s local `mathquest.json`. That explains why the spawn cadence can match the server while operation/problem count match your client.

What’s happening is a split-brain config issue, not OP status.

The server is controlling **world behavior**: enabled/disabled, NPC mode, and Wandering Nerd spawn timing. That’s why the nerds follow the server’s `15 seconds` interval. The `2 minutes` line in server status is the **NPC despawn time**, not the spawn interval.

But the quiz content is still controlled by the **client’s local config**. When you right-click the Wandering Nerd, the server only tells your client “open a quiz.” Your client then builds the quiz from its own `mathquest.json`, including:

- `problemsPerQuiz = 10`
- player preset for `rjcomp` / `RJComp`
- operation `exponentiation`

So `/mathquest operation addition` on the server did change the server’s default operation, but your client-side `RJComp` preset overrides that when the quiz starts. That’s why you still saw exponentiation.

Being OP did not remove your preset. If the server status does not show `rjcomp`, then the server’s `~/mathquest-server/config/mathquest.json` does not currently have that preset loaded. If you copied the file while the server was running, the server may still have had the old in-memory config and then saved over it later.

This is a real P1-6 finding: the current server-side command surface is only partly authoritative. It controls NPC spawning, but not remote-client quiz content yet. The test script’s section 17 expectation, “next quiz should show addition problems,” is too strong for the current implementation unless the client’s local config/preset is also changed.

My recommendation: treat this as a follow-up before marking P1-6 complete. The right fix is probably to make server-triggered quizzes carry server-resolved quiz settings to the client, so server `/mathquest operation`, `/mathquest range`, `/mathquest player ...`, and problem count actually govern remote players.

