# App Specification

## ADDED Requirements
### Requirement: Corpus Inventory Catalog
The system SHALL build a corpus inventory catalog from committed S3 manifest rows for the `deutsch`, `pv`, and `sovereign-child` corpora.

#### Scenario: Known transcript suffixes are cataloged
- **WHEN** the inventory builder reads `.md` and `.json` manifest rows whose filenames end in known raw, reference, or stage suffixes
- **THEN** it groups rows by episode stem and records raw suffixes, reference suffixes, stage suffixes, JSON suffixes, pair status, and semicolon-separated S3 keys.

#### Scenario: Non-candidate files are excluded
- **WHEN** a manifest row has an unsupported extension, no known suffix, or only stage/supporting suffixes
- **THEN** it is excluded from the eval-pair catalog.

#### Scenario: Inventory run completes
- **WHEN** the inventory script finishes processing all configured corpora
- **THEN** it writes `references/corpus-inventory-catalog.csv` and prints per-corpus counts for episodes, raw+reference pairs, raw-only episodes, and reference-only episodes.

### Requirement: Evaluation Pair Fetching
The system SHALL fetch paired transcript markdown files and required support files from `s3://[S3-FILES-BUCKET]` into their repo-relative local paths.

#### Scenario: Paired keys are fetched
- **WHEN** the fetch script runs with an initialized S3 client
- **THEN** it loads `has_pair=yes` catalog rows, adds the configured support file list, downloads missing or mismatched files, skips already-present matching files, and prints downloaded, skipped, and failed counts.

#### Scenario: Scoped S3 credentials are present
- **WHEN** `FOF_FILES_DATA_S3_ACCESS_KEY_ID` and `FOF_FILES_DATA_S3_SECRET_ACCESS_KEY` are set
- **THEN** the fetch script uses those credentials for the S3 client instead of the default AWS credential chain.

#### Scenario: S3 client initialization fails
- **WHEN** boto3 or S3 credentials cannot initialize a client
- **THEN** the fetch script prints an error telling the operator to configure AWS credentials and exits with failure.

### Requirement: Corpus Evaluation Profiles
The system SHALL load corpus-specific evaluation profiles and normalization policies from `config/eval-corpora.json`.

#### Scenario: A corpus profile is requested
- **WHEN** evaluation code requests a configured corpus such as `deutsch`, `pv`, or `sovereign-child`
- **THEN** it receives that corpus' reference suffix priority, eval suffixes, search folders, policy id, proper-name method, and score weights.

#### Scenario: A normalization policy is requested
- **WHEN** evaluation code requests a configured policy id
- **THEN** it receives the configured filler, repeat, partial-word, numeral, and contraction normalization settings.

#### Scenario: An unknown policy is requested
- **WHEN** evaluation code requests an unknown policy id
- **THEN** it falls back to the `keep-all` policy.

### Requirement: Baseline Transcript Evaluation
The system SHALL evaluate local raw transcript markdown files against the highest-priority available local reference for each paired catalog row.

#### Scenario: Local eval and reference transcripts exist
- **WHEN** the baseline runner finds a paired catalog row with a local reference containing `### transcript` and local eval transcripts for configured suffixes
- **THEN** it runs `evaluate_transcript` non-interactively with the corpus profile's normalization policy, weights, policy id, and proper-name method.

#### Scenario: Evaluation outputs are written
- **WHEN** a baseline eval run succeeds
- **THEN** it writes per-segment CSVs, `eval_metrics.csv`, and `eval_log.md` under `data/stellar-eval/<corpus>/<run-timestamp>/` and updates `references/baseline-eval-results.md` with per-corpus model summaries.

#### Scenario: No local transcript files are available
- **WHEN** the baseline runner skips missing files and records zero scored runs
- **THEN** it prints an error instructing the operator to run `fetch_eval_pairs.py` first and exits with failure.

### Requirement: Transcript Scoring Metrics
The system SHALL compute version-stamped transcript quality metrics, subscores, and a weighted overall score for evaluated transcripts.

#### Scenario: Alignment error counts are available
- **WHEN** metrics include `seg_error_count` and `total_ref_segments`
- **THEN** the alignment subscore is computed as `100 * (1 - seg_error_count / total_ref_segments)` clamped to 0 through 100.

#### Scenario: Word accuracy is a fraction
- **WHEN** `word_accuracy` is stored as a value from 0 through 1
- **THEN** the word-accuracy subscore scales it to the 0 through 100 score range.

#### Scenario: Composite scores are computed
- **WHEN** transcript metrics and corpus weights are available
- **THEN** the system writes alignment, word accuracy, quotation, proper-name, speaker, and overall score fields along with `policy_id` and `eval_code_version`.

### Requirement: Draft Build CLI
The system SHALL expose a command-line entry point for building draft transcripts from local raw transcript markdown.

#### Scenario: Single mode is requested
- **WHEN** `build_draft_transcript.py` runs in `single` mode with `--raw`
- **THEN** it builds either a deterministic or LLM single-transcript draft and prints the output path.

#### Scenario: Dual mode is requested
- **WHEN** `build_draft_transcript.py` runs in `dual` mode with `--raw-a` and `--raw-b`
- **THEN** it builds either a deterministic or LLM dual-transcript draft and prints the output path.

#### Scenario: Required raw inputs are missing
- **WHEN** the draft CLI is missing `--raw` for single mode or either `--raw-a` or `--raw-b` for dual mode
- **THEN** argument parsing rejects the command with an error.

### Requirement: Deterministic Draft Cleanup
The system SHALL create deterministic single-transcript draft files by applying conservative speaker-boundary cleanup to parsed transcript segments.

#### Scenario: Deterministic single draft is created
- **WHEN** deterministic cleanup runs on a raw transcript
- **THEN** it writes a `_draftds` markdown file with denovo pipeline version, method, mode, and repair-count metadata.

#### Scenario: Boundary repairs are applied
- **WHEN** the cleanup pass detects supported boundary issues such as dangling question tails, short speaker blips, or broken-sentence transitions
- **THEN** it moves or merges only the affected segment text and records repair logs used for the repair count.

#### Scenario: Evaluation normalization policy is supplied
- **WHEN** deterministic cleanup receives a normalization policy
- **THEN** it uses the policy for comparison-compatible behavior but does not persist lowercased or punctuation-stripped normalized dialogue into the draft transcript.

### Requirement: LLM Draft Processing
The system SHALL create LLM single-transcript drafts by running a deterministic pre-pass and then chunked LLM segmentation repair.

#### Scenario: LLM single draft is created
- **WHEN** LLM cleanup runs on a raw transcript
- **THEN** it first creates a deterministic draft, chunks the prepped segments with adjacent context, calls the configured provider/model, and writes a `_draftls` markdown file.

#### Scenario: LLM returns read-only context segments
- **WHEN** an LLM chunk result echoes leading or trailing context segments
- **THEN** the system strips those echoed context segments before reassembling the draft.

#### Scenario: LLM chunk correction fails
- **WHEN** a chunk returns no usable LLM result
- **THEN** the system falls back to the original chunk segments for that portion of the draft.

### Requirement: Dual Transcript Merging
The system SHALL merge two raw transcript variants into deterministic or LLM dual draft outputs using anchor and island detection.

#### Scenario: Deterministic dual merge runs
- **WHEN** deterministic dual merge receives two raw transcript paths
- **THEN** it applies deterministic cleanup to both, finds matching anchors, builds islands between anchors, arbitrates island text by deterministic rules, and writes a `_draftdd` markdown file.

#### Scenario: LLM dual merge runs
- **WHEN** LLM dual merge receives two raw transcript paths
- **THEN** it applies deterministic cleanup to both, sends island pairs to the configured LLM, falls back to deterministic arbitration for unusable LLM island results, and writes a `_draftld` markdown file.

#### Scenario: Dual LLM metadata is written
- **WHEN** an LLM dual merge completes
- **THEN** the draft metadata includes method, mode, model, prompts version, sources, anchor count, island count, API call count, token counts, and estimated USD cost.

### Requirement: Alignment Ladder Evaluation
The system SHALL score a per-episode alignment ladder for raw and draft transcript variants using absolute segment-error counts and word accuracy as a guard metric.

#### Scenario: Fixture mode is requested
- **WHEN** the alignment runner is called with `--fixture`
- **THEN** it builds a synthetic reference and two defect-injected raw transcripts before running the ladder against that fixture.

#### Scenario: Real transcript paths are supplied
- **WHEN** the alignment runner is called with `--raw-a`, `--raw-b`, and `--ref`
- **THEN** it scores raw A, raw B, deterministic single drafts, optional LLM single drafts, and optional dual LLM variants against the reference.

#### Scenario: Alignment report is written
- **WHEN** an alignment ladder run completes
- **THEN** it writes a markdown report under `data/stellar-eval/alignment-runs/` with missing, spurious, boundary, misplaced, total error, reduction, and word-accuracy columns.

### Requirement: Alignment Fixture Generation
The system SHALL generate deterministic synthetic alignment fixtures with known defect logs and expected segment-error counts.

#### Scenario: Fixture set is built
- **WHEN** `make_alignment_fixture.py` runs
- **THEN** it writes one reference transcript and two raw transcripts under the requested output directory.

#### Scenario: Defects are injected
- **WHEN** fixture generation creates raw A and raw B
- **THEN** it injects boundary shifts, segment merges, segment splits, and wrong-speaker changes using deterministic seeds.

#### Scenario: Expected counts are reported
- **WHEN** fixture generation completes
- **THEN** it reports the injected defects and expected missing, spurious, boundary, and total segment-error counts for each raw transcript.

### Requirement: Alignment Report Aggregation
The system SHALL aggregate per-episode alignment ladder markdown reports into a combined results markdown file.

#### Scenario: Matching reports exist
- **WHEN** the aggregator finds reports matching the requested run suffix
- **THEN** it keeps the newest report per episode stem, writes corpus totals by variant, and includes per-episode tables in the requested output file.

#### Scenario: Reduction totals are computed
- **WHEN** corpus totals are written for a non-raw variant
- **THEN** reduction percentages are computed against that variant's raw baseline or the better raw baseline for dual variants.

#### Scenario: No reports match
- **WHEN** the aggregator finds no reports for the requested run suffix
- **THEN** it prints the unmatched glob pattern and exits with failure.

### Requirement: M3B Dual-LLM Scoring Runner
The system SHALL run M3B dual-LLM scoring phases for selected deutsch and pv transcript sets.

#### Scenario: Selection phase is requested
- **WHEN** the M3B runner is called with `--phase selection`
- **THEN** it writes a markdown episode-selection report from locally resolvable deutsch catalog rows.

#### Scenario: Scoring phase is requested
- **WHEN** the M3B runner is called with `--phase single`, `five`, `deutsch`, or `pv`
- **THEN** it resolves local raw A, raw B, and reference paths, scores raw baselines and draft variants, writes a phase results markdown report, and includes LLM usage cost when LLM scoring is enabled.

#### Scenario: LLM scoring is skipped
- **WHEN** the M3B runner is called with `--skip-llm`
- **THEN** it scores baselines and deterministic dual output without running the LLM dual merge.

### Requirement: M3B Review Bundle Archiving
The system SHALL build an M3B five-file review bundle from local inputs, reports, draft outputs, eval artifacts, and a bundle index.

#### Scenario: Review bundle build runs
- **WHEN** the archive script runs after model-comparison outputs exist
- **THEN** it creates `data/stellar-eval/m3b-five-model-review/` with copied inputs, reports, model draft folders, eval artifacts, and `bundle-index.json`.

#### Scenario: Missing model drafts may be regenerated
- **WHEN** the archive script runs with `--regenerate-missing`
- **THEN** it may rerun the configured dual LLM merge for models marked for regeneration before copying drafts into the bundle.

#### Scenario: Upload is requested
- **WHEN** the archive script runs with `--upload`
- **THEN** it invokes the S3 archive build and upload flow for the `stellar-eval_m3b-five-review` manifest area.
