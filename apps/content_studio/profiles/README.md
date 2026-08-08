# Content Studio — consumer asset profiles

Tracked specifications for generating media that a **consumer app** will use. Each profile
describes what to make, in what format, with what prompts, and where approved files land.

Profiles live here (in git). Generated media lives under `apps/content_studio/_data/` (gitignored,
symlinked across worktrees via `_LOCAL_FILES` — see root `docs/worktrees-guide.md`).

## Layout

```text
apps/content_studio/profiles/<consumer-slug>.md   # this folder — tracked spec
apps/content_studio/_data/profiles/<consumer-slug>/
  reference/    # source stills (e.g. PDF export, concept art) — local only
  staging/      # generate→verify candidates — local only
  approved/     # ship-ready outputs — copy or symlink into the consumer app
```

## Workflow

1. Read the consumer profile (format, dimensions, prompts, delivery paths).
2. Put reference images in `_data/profiles/<slug>/reference/`.
3. Generate with the CLI; write staging outputs under `staging/` (use `--out`).
4. On verifier pass, move the winner to `approved/`.
5. Copy or symlink from `approved/` into the consumer app's asset folder (profile lists the
   exact paths). Consumer branches may not exist in every worktree — that is fine; assets in
   `_LOCAL_FILES` are shared once the consumer mount exists.

## Profiles

| Profile | Consumer | Branch (when present) |
|---------|----------|------------------------|
| `math-quiz-dragon-baby.md` | Dragon Fluency Game (`apps/math-quiz/dragon/`) | `feature/math-quiz-dragon-baby` |
