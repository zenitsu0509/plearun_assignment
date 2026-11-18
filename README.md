# PLEARUN Offline Evidence Checker

An offline, deterministic Python command-line tool that checks report claims
against machine records and emits citation-verified JSON findings. It uses only
the Python standard library; no network or LLM is required.

## Usage

```bash
python3 plearun_cli.py reports/report_fictional_02.txt records/ > findings.json
make test
```

## How it works

The CLI splits report sentences and separates the explicit speed clause while
preserving the claim wording. It loads the UTF-8-with-BOM camera CSV, Windows-
1252 notes CSV, nested dispatch JSON, and WebVTT cues into evidence rows. It
normalizes timestamps as UTC, naive wall time, or relative cue time. Citations
use physical CSV lines, numbered VTT cues, and 1-based JSON event indexes;
quotes must occur verbatim in the source document before a `match` or `conflict`
is emitted. Clock offsets require at least two explicit shared anchor IDs with
absolute timestamps. The sample has no such anchors, so cross-source timing
claims remain unresolved.

## Three hardest decisions

1. **Clock alignment:** A single approximate or minute-level event is not enough
   to align unsynchronized devices. The `21:10:19` dispatch time versus `21:11`
   report time is unresolved rather than assumed to match or conflict.
2. **Claim scope:** The camera and bodycam support the 58 mph in a 45 zone
   assertion, but do not establish vehicle color, identity, or location. The
   speed clause is evaluated separately from the observation claim.
3. **Citation units:** CSV lines and VTT cues have natural row numbers; JSON
   events do not, so an event index and its exact source substring are used.

## Limitations and likely failure points

The claim grammar is narrow; paraphrases, complex references, or transcription
errors may be missed. Matching a speed reading does not prove it belongs to the
reported car. The evaluator favors `not_settled` over unsupported conflicts.
Real records with schema drift, malformed encodings, multi-line CSV fields, or
unclear clock behavior would fail parsing or leave more claims unresolved.

Tooling: Python standard library and an AI coding assistant for implementation
and review.
