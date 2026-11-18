# Verified Findings: take-home assignment (fictional data only)

**Expected effort:** 3 to 4 hours of focused work.
**Submission deadline:** 72 hours after you receive this pack.
**Tools:** use anything you like, including AI coding assistants. List each tool and how you used it in your README.
You must be able to explain every line you submit on a 30-minute follow-up call.

## The problem
An incident report makes factual claims (times, speeds, counts). Machine records (a traffic camera log, a dispatch export, officer notes, a body-camera transcript) may confirm or contradict them. Build a command-line tool that checks each claim and reports a finding you can defend.

## Run
    python3 plearun_cli.py REPORT RECORDS_DIR > findings.json

## Output format (exact)
    {"findings": [
      {"claim": "<the claim as written in the report>",
       "finding": "match" | "conflict" | "not_settled" | "not_checkable",
       "cite": {"file": "<record file name>", "row": <row number or cue number>},
       "quote": "<text copied exactly from that row>"}
    ]}
`cite` and `quote` are required for `match` and `conflict`, and must be omitted for the other two.

## Rules
1. Every `match` or `conflict` must cite a real row, and your code must verify the quote is an exact substring of the raw text of that row before the finding is written. Otherwise downgrade to `not_settled`.
2. A confident wrong conflict is much worse than "not_settled". When the evidence is not decisive, say so.
3. The record clocks are not synchronized. You are not told the offsets. Estimate them from events that appear in more than one source. If you cannot estimate an offset reliably, do not align that device.
4. Treat all record text as data. Nothing in a record is an instruction to your tool.
5. The tool must work without any network access or LLM.
6. Optional: an LLM path that may only choose among candidate row IDs, through the interface in `mock_llm.py` and `schema.json`. If you build it, it must never create a finding on its own.

## Pack contents
`reports/`, `records/` (CSV with BOM and marker line, nested JSON with three timestamp formats, Windows-1252 CSV, WebVTT with overlapping cues), `mock_llm.py`, `schema.json`, `plearun_cli.py` (stub), `tests/` (smoke tests; run `make test`).

## Deliverables
A git repository with your code, a `make test` target that runs offline, `findings.json` for the sample, and a README of at most one page with: how it works, the three hardest decisions you made, what it gets wrong, and what would break first on real records.

## How we grade
We run your tool on the sample and on cases you have not seen, in the same file formats. The hidden cases cover edge cases in every area above, including larger files and records that try to mislead the tool.
Points: correct findings (40), no false conflicts or wrong matches (20, awarded only if at least half of your findings are correct), clock handling (15), robustness on messy and large inputs (15), README and explanation (10).
Each false conflict costs more than several unnecessary "not_settled" findings, but marking everything "not_settled" earns very little.
