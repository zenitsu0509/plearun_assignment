#!/usr/bin/env python3
"""Offline, conservative fact checks for the fictional PLEARUN evidence pack."""
from __future__ import annotations

import csv
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ParsedTimestamp:
    kind: str
    value: float
    precision: str


def parse_timestamp(raw: Any) -> ParsedTimestamp | None:
    """Normalize supported timestamps while retaining whether their clocks compare."""
    if raw is None:
        return None
    value = str(raw).strip()
    if re.fullmatch(r"\d{13}", value):
        return ParsedTimestamp("utc", int(value) / 1000.0, "millisecond")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            return ParsedTimestamp("utc", dt.timestamp(), "second")
    except ValueError:
        pass
    vtt = re.fullmatch(r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})", value)
    if vtt:
        h, m, s, ms = (int(part) for part in vtt.groups())
        return ParsedTimestamp("relative", h * 3600 + m * 60 + s + ms / 1000, "millisecond")
    clock = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", value)
    if clock:
        h, m, s = int(clock[1]), int(clock[2]), int(clock[3] or 0)
        return ParsedTimestamp("naive", h * 3600 + m * 60 + s, "minute" if clock[3] is None else "second")
    # Handle a naive date-time without assigning an invented timezone.
    naive = re.fullmatch(r"\d{4}-\d{2}-\d{2}[ T](\d{2}):(\d{2}):(\d{2})", value)
    if naive:
        h, m, s = (int(naive[i]) for i in range(1, 4))
        return ParsedTimestamp("naive", h * 3600 + m * 60 + s, "second")
    return None


@dataclass
class EvidenceRow:
    source_file: str
    row_id: int
    raw_text: str
    fields: dict[str, Any]
    clock_source: str
    source_document: str = ""
    timestamp: ParsedTimestamp | None = None


def estimate_clock_offsets(rows: list[EvidenceRow], min_anchors: int = 2) -> dict[tuple[str, str], dict[str, Any]]:
    """Estimate pairwise offsets only from explicit shared anchor IDs with absolute timestamps."""
    anchors: dict[str, list[EvidenceRow]] = {}
    for row in rows:
        key = row.fields.get("anchor_id")
        if key and row.timestamp and row.timestamp.kind == "utc":
            anchors.setdefault(str(key), []).append(row)
    pairs: dict[tuple[str, str], list[float]] = {}
    for sightings in anchors.values():
        for i, left in enumerate(sightings):
            for right in sightings[i + 1:]:
                if left.clock_source == right.clock_source:
                    continue
                pair = tuple(sorted((left.clock_source, right.clock_source)))
                delta = (left.timestamp.value - right.timestamp.value
                         if left.clock_source == pair[0] else right.timestamp.value - left.timestamp.value)
                pairs.setdefault(pair, []).append(delta)
    result = {}
    for pair, deltas in pairs.items():
        if len(deltas) >= min_anchors:
            result[pair] = {"aligned": True, "offset_seconds": sum(deltas) / len(deltas), "anchors": len(deltas)}
        else:
            result[pair] = {"aligned": False, "anchors": len(deltas)}
    return result


def clocks_aligned(rows: list[EvidenceRow], source_a: str, source_b: str) -> bool:
    if source_a == source_b:
        return True
    pair = tuple(sorted((source_a, source_b)))
    return estimate_clock_offsets(rows).get(pair, {}).get("aligned", False)


def load_camera(path: Path) -> list[EvidenceRow]:
    rows: list[EvidenceRow] = []
    document = path.read_text(encoding="utf-8-sig")
    raw_lines = document.splitlines()
    # Line 1 is the export marker; line 2 is the CSV header.
    for line_no, raw in enumerate(raw_lines[2:], start=3):
        if not raw.strip():
            continue
        try:
            values = next(csv.reader([raw]))
            if len(values) != 4:
                continue
            timestamp, device, speed, limit = values
            rows.append(EvidenceRow(path.name, line_no, raw,
                                    {"timestamp": timestamp, "device": device,
                                     "speed_mph": int(speed), "zone_mph": int(limit)}, "camera", document,
                                    parse_timestamp(timestamp)))
        except (ValueError, csv.Error):
            continue
    return rows


def load_notes(path: Path) -> list[EvidenceRow]:
    rows: list[EvidenceRow] = []
    document = path.read_bytes().decode("cp1252").replace("\r\n", "\n").replace("\r", "\n")
    with path.open(encoding="cp1252", newline="") as f:
        for line_no, raw in enumerate(f, start=1):
            raw = raw.rstrip("\r\n")
            if line_no == 1 or not raw:
                continue
            try:
                fields = next(csv.reader([raw]))
                rows.append(EvidenceRow(path.name, line_no, raw,
                                        {"id": fields[0], "author": fields[1],
                                         "note": fields[2], "time": fields[3]}, "notes", document,
                                        parse_timestamp(fields[3])))
            except (IndexError, csv.Error):
                continue
    return rows


def load_dispatch(path: Path) -> list[EvidenceRow]:
    document = path.read_text(encoding="utf-8")
    data = json.loads(document)
    rows = []
    events_key = re.search(r'"events"\s*:\s*\[', document)
    if not events_key:
        return rows
    decoder = json.JSONDecoder()
    pos = events_key.end()
    index = 1
    while pos < len(document):
        while pos < len(document) and (document[pos].isspace() or document[pos] == ","):
            pos += 1
        if pos >= len(document) or document[pos] == "]":
            break
        event, end = decoder.raw_decode(document, pos)
        raw = document[pos:end]
        rows.append(EvidenceRow(path.name, index, raw, event, "dispatch", document,
                                parse_timestamp(event.get("logged"))))
        index += 1
        pos = end
    return rows


def load_vtt(path: Path) -> list[EvidenceRow]:
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    rows: list[EvidenceRow] = []
    i = 0
    while i < len(lines):
        if "-->" not in lines[i]:
            i += 1
            continue
        cue_line = i
        block = [lines[i]]
        i += 1
        while i < len(lines) and lines[i].strip():
            block.append(lines[i]); i += 1
        rows.append(EvidenceRow(path.name, len(rows) + 1, "\n".join(block),
                                {"text": " ".join(block[1:]), "cue_time": lines[cue_line].split(" --> ")[0]}, "bodycam", text,
                                parse_timestamp(lines[cue_line].split(" --> ")[0].strip())))
    return rows


def load_records(directory: Path) -> list[EvidenceRow]:
    loaders = {"camera_log.csv": load_camera, "notes_cp1252.csv": load_notes,
               "dispatch.json": load_dispatch, "bodycam_transcript.vtt": load_vtt}
    rows: list[EvidenceRow] = []
    for name, loader in loaders.items():
        path = directory / name
        if path.exists():
            rows.extend(loader(path))
    return rows


def report_claims(text: str) -> list[str]:
    # Split at the comma without changing either claim's original words.
    text = re.sub(r"(?i)SYNTHETIC\s*-\s*FICTIONAL CASE\.\s*", "", text)
    pieces = re.split(r"(?<=[.!?])\s+|,\s*(?=(?:travelling|traveling)\s+\d+\s*mph\b)", text.strip(), flags=re.I)
    return [part.strip() for part in pieces if part.strip()]


def verified(finding: str, claim: str, row: EvidenceRow | None = None) -> dict[str, Any]:
    if finding in ("match", "conflict"):
        if row is None:
            finding = "not_settled"
        else:
            quote = row.raw_text
            if not quote or quote not in row.source_document:
                finding = "not_settled"
            else:
                return {"claim": claim, "finding": finding,
                        "cite": {"file": row.source_file, "row": row.row_id}, "quote": quote}
    return {"claim": claim, "finding": finding}


def evaluate(claim: str, rows: list[EvidenceRow]) -> dict[str, Any]:
    lower = claim.lower()
    # Full-claim support requires identity/context in addition to a matching metric.
    if "only car" in lower or "only vehicle" in lower:
        return verified("not_checkable", claim)

    if "911 call" in lower:
        matches = [r for r in rows if r.clock_source == "dispatch" and r.fields.get("type") == "911_call"]
        claim_time = re.search(r"\b(?:at\s+)?(\d{1,2}):(\d{2})\b", lower)
        if matches and claim_time:
            logged = re.search(r"(\d{1,2}):(\d{2}):(\d{2})", str(matches[0].fields.get("logged", "")))
            if logged:
                reported_minute = int(claim_time.group(1)) * 60 + int(claim_time.group(2))
                logged_minute = int(logged.group(1)) * 60 + int(logged.group(2))
                # Minute-level report precision is ambiguous at a minute boundary;
                # do not claim a match or conflict without a documented rounding rule.
                if reported_minute == logged_minute:
                    return verified("match", claim, matches[0])
        return verified("not_settled", claim)

    if "mph" in lower and ("zone" in lower or "travelling" in lower or "traveling" in lower):
        speed_match = re.search(r"(\d+)\s*mph", lower)
        limit_match = re.search(r"(?:posted\s+)?(\d+)\s*(?:mph\s+)?zone", lower)
        if speed_match and limit_match:
            speed, limit = int(speed_match.group(1)), int(limit_match.group(1))
            # Camera rows cannot identify vehicle/color/location; transcript can corroborate
            # the spoken measurement but does not independently identify the car.
            candidates = [r for r in rows if r.clock_source == "camera" and
                          r.fields.get("speed_mph") == speed and r.fields.get("zone_mph") == limit]
            spoken = [r for r in rows if r.clock_source == "bodycam" and
                      re.search(rf"\b{speed}\s+in\s+a\s+{limit}\b", r.fields.get("text", ""), re.I)]
            if candidates and spoken:
                return verified("match", claim, candidates[0])
            return verified("not_settled", claim)

    if "stopped" in lower or "pull" in lower and "lot" in lower:
        note = next((r for r in rows if r.clock_source == "notes" and "stopped at lot" in r.fields.get("note", "").lower()), None)
        cue = next((r for r in rows if r.clock_source == "bodycam" and "pulling in at the lot" in r.fields.get("text", "").lower()), None)
        if note and cue and "harbor gas" not in lower:
            return verified("match", claim, note)
        if note or cue:
            return verified("not_settled", claim)

    if "on scene" in lower or "after the stop" in lower:
        if not clocks_aligned(rows, "dispatch", "notes"):
            return verified("not_settled", claim)
        # Aligned source clocks still need explicit event matching before a delta
        # can be used; this pack has no shared stop/arrival anchor IDs.
        return verified("not_settled", claim)

    # Observation/identity/location assertions are only partly represented by these records.
    if any(term in lower for term in ("observed", "mile marker", "blue sedan", "harbor gas")):
        return verified("not_settled", claim)
    return verified("not_checkable", claim)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: python3 plearun_cli.py REPORT RECORDS_DIR", file=sys.stderr)
        return 2
    report = Path(argv[1]); records_dir = Path(argv[2])
    try:
        claims = report_claims(report.read_text(encoding="utf-8-sig"))
        rows = load_records(records_dir)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"plearun: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"findings": [evaluate(claim, rows) for claim in claims]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
