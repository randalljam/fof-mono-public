# Test data files

This directory contains small, synthetic fixtures used by the automated test suite.
The text and structured data were written specifically for this repository and do
not reproduce podcast, interview, or other third-party transcripts.

Tests should treat these files as read-only. When a test needs to modify a fixture
or create a sibling output file, it should first copy the fixture into a temporary
directory.

- `fileops/` contains generic documents for manual file-operation checks.
- `llm/` contains synthetic dialogue used for block splitting and QA generation.
- `rag/` and `vectordb/` contain minimal synthetic retrieval examples.
- `transcribe/` contains synthetic YouTube, number-conversion, and Deepgram data.
- `transcription/` contains a longer generated alignment-evaluation source.
- `manual_output/` is the ignored destination for disposable manual-test outputs.

`tests/test_manual_files/` remains a legacy reference corpus and is not used by the
automated unit tests.
