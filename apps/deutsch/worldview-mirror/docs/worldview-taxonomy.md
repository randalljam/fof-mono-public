file: apps/deutsch/worldview-mirror/docs/worldview-taxonomy.md
title: Worldview taxonomy — research survey, axis design, and seed profiles
last-updated: 2026-07-11_1120
ai: Claude Code (Fable 5, local)
session: `Build worldview-mirror + atlas`

The Worldview Atlas taxonomy (`taxonomy/axes.jsonl`, `taxonomy/profiles/*.json`) was designed from a survey of published worldview-classification frameworks (web research, 2026-07-11) rather than invented ad hoc. This doc records what was surveyed, the axis design decisions, and the seeding rules for named profiles. The taxonomy is explicitly a **start** — revisable, and expected to be curated the same way the deutsch-graph topics are.


## Surveyed frameworks

### Philosophical worldview theory
- **Apostel/Aerts worldview components** (Worldviews group, VUB Brussels, 1994) — a worldview answers a fixed set of sub-questions: ontology, explanation, axiology, futurology, epistemology, praxeology. https://pespmc1.vub.ac.be/CLEA/Reports/WorldviewsBook.html
- **Clément Vidal, "What is a worldview?" (2008)** — formalizes six first-order worldview questions (What is? Where from? Where to? What is good? How act? What is true?). https://philpapers.org/rec/VIDWIA
- **James Sire, The Universe Next Door** — eight diagnostic worldview questions used to compare theism, naturalism, existentialism, postmodernism, etc. https://www.ivpress.com/the-universe-next-door
- **David Naugle, Worldview: The History of a Concept (2002)** — worldviews as narrative sign-systems operating from the "heart"; informs the Mirror's framing (worldviews are stories people live inside, not just propositions). https://archive.org/details/worldview00davi
- **Wilhelm Dilthey** — three recurring worldview types: naturalism, idealism of freedom, objective idealism. https://plato.stanford.edu/entries/dilthey/
- **Stephen Pepper, World Hypotheses (1942)** — four root-metaphor world hypotheses (formism, mechanism, contextualism, organicism). https://en.wikipedia.org/wiki/World_Hypotheses

### Psychology of belief and values
- **Koltko-Rivera, "The Psychology of Worldviews" (Review of General Psychology, 2004)** — the anchor academic survey; collates prior models into 7 groups / 26 dimensions (human nature, will, cognition, behavior, interpersonal, truth, world-and-life). Many of our axes map directly onto its dimensions. https://journals.sagepub.com/doi/10.1037/1089-2680.8.1.3
- **Moral Foundations Theory** (Haidt/Graham) — care, fairness, loyalty, authority, sanctity (+liberty); individualizing vs binding foundations. https://moralfoundations.org/
- **Schwartz Theory of Basic Values** — ten values on two bipolar axes: openness-to-change↔conservation, self-enhancement↔self-transcendence. https://scholarworks.gvsu.edu/orpc/vol2/iss1/11/
- **Grid-group Cultural Theory / cultural cognition** (Douglas, Wildavsky; Kahan) — hierarchy↔egalitarianism and individualism↔communitarianism predict risk perception. https://en.wikipedia.org/wiki/Cultural_theory_of_risk
- **Inglehart–Welzel World Values Survey map** — traditional↔secular-rational and survival↔self-expression. https://en.wikipedia.org/wiki/Inglehart%E2%80%93Welzel_cultural_map_of_the_world
- **Scale to Assess World Views (SAWV)** (Ibrahim & Kahn 1987) and the **Worldview Assessment Instrument** (Koltko-Rivera 2000) — existence proofs that worldview positions can be elicited by instrument; their item wording patterns are usable for future profile-elicitation prompts. https://journals.sagepub.com/doi/10.2466/pr0.1987.60.1.163

### Epistemology- and progress-relevant sources
- **Critical rationalism / fallibilism vs justificationism, inductivism, Bayesianism** (Popper; Deutsch). https://en.wikipedia.org/wiki/Critical_rationalism
- **Proactionary vs precautionary principle** (More 2004; Wingspread 1998). https://en.wikipedia.org/wiki/Proactionary_principle
- **Progress studies / techno-optimism vs degrowth / doomerism** — the modern progress-optimism debate. https://en.wikipedia.org/wiki/Progress_studies


## Axis design decisions

**14 axes** (`taxonomy/axes.jsonl`), inside the 8–15 target from `deutsch-graph/docs/use-cases.md` §2. Axes 1–8 are Deutsch-diagnostic (epistemology, reach, authority, realism, progress, risk, agency, significance); 9–14 buy breadth so worldviews far from Deutsch's (religious traditionalism, postmodernism, deep ecology) are representable without caricature (morality, metaphysics, change, nature, meaning, social).

- **Scale**: every position is a float in **[-2.0, +2.0]**; -2 = fully at `pole_neg`, +2 = fully at `pole_pos`. **Omission = no position** (orthogonal or low-salience) — per Koltko-Rivera's warning that worldview dimensions are not all bipolar, profiles simply omit axes they have no stance on (e.g. Stoicism omits progress and risk).
- **Orientation convention**: the pole assignments are arbitrary and carry **no valence** — "+" is not "better". As it happens the critical-rationalist pole is usually `pole_pos`, which makes Deutsch's profile read mostly positive; that is a readability convention, not a scoring.
- Every axis carries `frameworks` (which surveyed models support it) and `sources` (URLs).

### Trade-offs and alternatives considered
- **14 bipolar axes vs Koltko-Rivera's 26 multipolar dimensions.** Chose fewer, bipolar-ish axes: tractable UI (sliders/tracks), tractable LLM classification, and the use-cases doc's own 8–15 guidance. Cost: some nuance is flattened (e.g. "authority: linear/lateral" and "knowledge sources: 9 options" collapse into two axes). Revisit if profile claims start feeling forced.
- **Dropped candidates** (documented for future addition): egalitarianism↔hierarchism (grid axis), reductive-mechanist↔holistic-contextual explanatory style (Pepper; interesting because Deutsch is a marked both/neither case), time orientation (past/present/future, SAWV). Add as new JSONL rows when needed — the loader takes any axis count.
- **Numeric positions vs qualitative stances.** Numbers make the Mirror's diff computable and displayable (the whole point of the app); the `summary` string on every position carries the qualitative nuance the number loses. Alternative — stance enums per axis — was rejected as harder to compare and not obviously more honest.
- **Single scale for user and profiles.** The user profile aggregates observation positions on the same [-2, +2] scale (confidence-weighted mean, explicit override wins), so user-vs-profile comparison is a structured diff, exactly as `use-cases.md` §1 prescribes.


## Seed profiles

Nine profiles in `taxonomy/profiles/`, chosen to span the axes and to include the worldviews Randy's notes name (deep optimism; the Bayesian-rationalist and precautionary stances Deutsch most often argues against; plus major live traditions):

| Profile | Cited from graph? | Role in the atlas |
|---|---|---|
| Deep Optimism (Deutschian critical rationalism) | **yes — every position carries deutsch-graph node ids** | the reference lens; IS the L5 layer seed |
| Bayesian Rationalism (LessWrong) | no (URL-sourced) | nearest neighbor with sharp epistemology/risk contrast |
| Precautionary Environmentalism / Degrowth | no | the risk/nature/progress opposite |
| Religious Traditionalism (classical Christian theism) | no | the authority/metaphysics/meaning opposite |
| Secular Humanism | no | moderate naturalist baseline |
| Stoicism | no | inner-agency worldview; tests axis omission |
| Buddhism (secular reading) | no | non-Western; tests axis omission and variants |
| Scientific Materialism / Naturalism | no | naturalist near-neighbor differing on significance/morality |
| Postmodern Relativism / Social Constructionism | no | the realism/progress opposite |

Seeding rules:
- **Deutsch's profile cites the graph**: every position's `evidence` lists real `qa:`/`concept:` node ids, validated at build/test time against `apps/deutsch/deutsch-graph/graph/` (so a graph rebuild that removes a cited node fails the taxonomy test). This makes the atlas format concrete before any other worldview is added — per use-cases.md §2, it is the first fully-cited entry of the L5 layer.
- **Other profiles cite public sources** (SEP, primary manifestos, Wikipedia) and carry `cited_from_graph: false` plus a `variants` field flagging internal diversity — the anti-caricature guard the use-cases doc calls for. Their numeric positions are curated seeds derived from the research summaries; treat them as revisable first passes, reviewed like overlay files.
- Position values were assigned by reading each tradition's self-descriptions/scholarly summaries against the axis definitions; deltas between profiles matter more than absolute values.

### Known gaps / future work
- Wiki-style review discipline (a review log like deutsch-graph's topics review) once anyone else edits the taxonomy.
- Elicitation instrument: SAWV/WAI-style question batteries for users who want to fill their profile directly instead of chatting.
- Additional profiles worth adding: effective altruism, Confucianism, existentialism, Islam (classical), indigenous relational worldviews, Marxist historical materialism, transhumanism/e-acc as a distinct entry.
- Exporting Deutsch's cited positions back into deutsch-graph as proper L5 overlay files once that layer's node/edge format is finalized (`deutsch-graph/docs/graph-spec.md`).
