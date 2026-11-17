# Verified Findings

## How to run

This is an offline, standard-library-only Python CLI. Run
`python3 plearun_cli.py REPORT RECORDS_DIR`; `make sample` writes the supplied
case to `findings.json`, and `make test` runs the offline smoke tests. No LLM or
network connection is used.

The tool splits report text into sentences and separates the explicit speed
clause without changing its wording. It loads the supplied CSV, JSON, and
WebVTT formats into evidence rows and normalizes timestamps as UTC, naive wall
time, or relative cue time. CSV lines and WebVTT cue blocks are preserved for
citation. JSON events use their 1-based `events` array index and exact source
substring. Quotes are checked against the original source document. Clock
offsets are estimated only when at least two explicit shared anchor IDs have
absolute timestamps; this pack has no such anchors, so its cross-source timing
claims remain unresolved.

## Three hardest decisions

1. **Clock alignment:** The pack does not provide two explicit, precise shared
   anchors. The implementation does not infer offsets from coincidental times.
   `21:10:19` versus `21:11` is therefore unresolved rather than assumed to
   match or conflict.
2. **Claim scope:** A camera speed reading cannot establish car color, identity,
   or location. Multi-facet assertions are not marked as fully supported by a
   partial metric match.
3. **Citation units:** CSV line numbers and VTT cue numbers are stable. Nested
   JSON has no physical rows, so event index and compact event serialization
   define its citation unit.

## Limitations and likely failure points

Claim extraction is intentionally narrow and tailored to the report patterns;
novel phrasing can be missed or conservatively unresolved. It does not estimate
clock offsets without defensible anchors, and it cannot establish vehicle
identity from these records. Real records with malformed encodings, different
schemas, ambiguous duplicate events, or undocumented clock behavior would
break parsing or make findings unresolved first. Tooling used: Python standard
library and an AI coding assistant for implementation and review.
