#!/usr/bin/env python3
# Extract structured lesson fields from a natural-language transcript using
# OpenAI function calling (structured output).  Standalone — does not import
# core/llm.py, so it works without the full project .env / heavy deps.
#
# Usage:
#   echo "Kid1 did 30 min of math" | python3 extract_lesson.py
#   python3 extract_lesson.py --in transcript.txt
#   python3 extract_lesson.py --transcript "40 min reading"
#   python3 extract_lesson.py --model gpt-4o-mini --transcript "..."
#
# Env: OPENAI_API_KEY (required).
# Output: JSON object with extracted fields on stdout.
import argparse
import json
import os
import sys
from openai import OpenAI

DEFAULT_MODEL = "gpt-4.1-mini"
EXTRACTOR_VERSION = "1.0.0"
KNOWN_SUBJECTS = ["Math", "Reading", "Writing", "Art", "Science", "Music"]

### Tool schema — OpenAI function-calling format with strict mode
TOOL_EXTRACT_LESSON = {
    "type": "function",
    "function": {
        "name": "extract_lesson",
        "description": "Extract structured lesson fields from a homeschool lesson description.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "students": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": 'List of student names mentioned. If none are named, use ["Kid1"].',
                },
                "teachers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "List of teacher/facilitator names. Three possible outputs:\n"
                        '1. Named teacher(s): ["TL"], ["Mrs. Chen"] — when the transcript names them.\n'
                        '2. ["self"] — ONLY when the transcript contains an explicit independence marker: '
                        '"on her own", "by herself", "independently", or student using a software '
                        "platform (Khan Academy, Duolingo, etc.) with no adult mentioned.\n"
                        '3. ["not specified"] — when the transcript does not mention a teacher and '
                        "there is no explicit independence marker. This is the default for ambiguous cases "
                        'like "Kid1 did 30 min of math" — the save pipeline will resolve it.'
                    ),
                },
                "subject": {
                    "type": "string",
                    "description": (
                        f"The lesson subject. Map to one of {KNOWN_SUBJECTS} when it clearly fits "
                        '(e.g. "times tables" → "Math", "piano" → "Music"). '
                        "Otherwise keep the stated subject as-is (e.g. \"History\")."
                    ),
                },
                "curricula": {
                    "type": "string",
                    "description": (
                        "The book, curriculum, or software program used, if mentioned "
                        '(e.g. "Charlotte\'s Web", "Khan Academy", "Singapore Math 4A"). '
                        'Empty string if not mentioned.'
                    ),
                },
                "duration": {
                    "type": "integer",
                    "description": (
                        "Lesson duration in minutes. Normalize spoken forms: "
                        '"half an hour" → 30, "an hour and a half" → 90, '
                        '"a quarter of an hour" → 15, "two hours" → 120. No cap.'
                    ),
                },
                "location": {
                    "type": "string",
                    "description": 'Where the lesson happened, if mentioned (e.g. "kitchen table", "co-op"). Empty string if not mentioned.',
                },
                "date": {
                    "type": "string",
                    "description": (
                        'The lesson date. "today" unless a day is stated; '
                        '"yesterday" for yesterday; otherwise YYYY-MM-DD.'
                    ),
                },
                "time": {
                    "type": "string",
                    "description": (
                        'The time of day the lesson happened, if mentioned '
                        '(e.g. "2:30 PM", "10:15 AM", "morning"). '
                        'Empty string if not mentioned — do not guess or fill with the current time.'
                    ),
                },
                "notes": {
                    "type": "string",
                    "description": 'Descriptive detail about the lesson, lightly cleaned. Empty string if none.',
                },
            },
            "required": ["students", "teachers", "subject", "curricula", "duration", "location", "date", "time", "notes"],
            "additionalProperties": False,
        },
    },
}

SYSTEM_PROMPT = (
    "You extract a single homeschool lesson record from a short message. "
    "Call the extract_lesson function with the structured fields. "
    "Rules:\n"
    f"- subject: map to one of {KNOWN_SUBJECTS} when it clearly fits; otherwise keep the stated subject.\n"
    '- students: list the kids named. If none are named, use ["Kid1"].\n'
    '- teachers: named person(s) when stated; ["self"] with explicit independence markers '
    '("on her own", "by herself", "independently", or solo software use like Khan Academy); '
    '["not specified"] for everything else where no teacher is mentioned.\n'
    '- duration: integer minutes; normalize spoken forms ("half an hour"→30, "an hour and a half"→90, "a quarter of an hour"→15). No cap.\n'
    '- date: "today" unless a day is stated; "yesterday" for yesterday; else YYYY-MM-DD.\n'
    '- time: the time of day if mentioned (e.g. "2:30 PM", "this morning"); "" if not mentioned — do not guess.\n'
    '- curricula: the book, curriculum, or program if mentioned; "" if not.\n'
    '- location: where the lesson happened if mentioned; "" if not.\n'
    '- notes: the descriptive detail, lightly cleaned; "" if none.\n'
)

### Extraction
def extract_lesson(transcript, model=DEFAULT_MODEL, api_key=None, verbose=False):
    """Call OpenAI with function calling to extract lesson fields from a transcript.

    Returns a dict with the extracted fields, or raises on failure.
    """
    client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": transcript.strip()},
    ]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=[TOOL_EXTRACT_LESSON],
        tool_choice={"type": "function", "function": {"name": "extract_lesson"}},
    )
    choice = response.choices[0]
    if verbose:
        print(f"[extract] model={response.model} finish={choice.finish_reason}", file=sys.stderr)
    if not choice.message.tool_calls:
        raise RuntimeError(f"No tool call in response: {choice.message.content}")
    args_json = choice.message.tool_calls[0].function.arguments
    return json.loads(args_json)

### CLI
def main():
    ap = argparse.ArgumentParser(description="Extract lesson fields from a transcript via OpenAI structured output.")
    ap.add_argument("--transcript", "-t", help="Transcript text (else read from --in or stdin).")
    ap.add_argument("--in", dest="infile", help="File containing the transcript.")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"OpenAI model (default: {DEFAULT_MODEL}).")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args()
    if args.transcript:
        text = args.transcript
    elif args.infile:
        with open(args.infile) as f:
            text = f.read()
    else:
        text = sys.stdin.read()
    if not text.strip():
        print("No transcript provided.", file=sys.stderr)
        sys.exit(1)
    result = extract_lesson(text, model=args.model, verbose=args.verbose)
    print(json.dumps(result, indent=2, ensure_ascii=False))
if __name__ == "__main__":
    main()
