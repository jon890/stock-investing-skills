#!/usr/bin/env python3
"""Validate the tool-independent investing wiki structure."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WIKI_ROOT = ROOT / "wiki"

ALLOWED_CLAIM_TYPES = {
    "direct_claim",
    "inferred_principle",
    "historical_market_fact",
    "current_external_data",
    "unsupported",
}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}
ALLOWED_SOURCE_KINDS = {
    "youtube_video",
    "book",
    "letter",
    "article",
    "interview",
    "filing",
    "other",
}
ALLOWED_DATE_STATUSES = {
    "verified_upload_date",
    "verified_publication_date",
    "verified_event_date",
    "unavailable",
}
YOUTUBE_RE = re.compile(r"^(https://www\.)?youtube\.com/watch\?[^ ]*v=([A-Za-z0-9_-]{8,})")
EXPERT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
EVIDENCE_ID_RE = re.compile(r"^([a-z0-9][a-z0-9-]*)-evidence-\d{6}$")


def load_json(path: Path) -> tuple[Any | None, list[str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"{path}: cannot read JSON: {exc}"]


def is_iso_date(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def frontmatter_evidence_ids(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return []
    end = text.find("\n---", 4)
    if end == -1:
        return []
    lines = text[4:end].splitlines()
    ids: list[str] = []
    in_evidence_ids = False
    for line in lines:
        if re.match(r"^[A-Za-z0-9_-]+:", line):
            in_evidence_ids = line.startswith("evidence_ids:")
            continue
        if in_evidence_ids:
            match = re.match(r"\s*-\s*([A-Za-z0-9_-]+)", line)
            if match:
                ids.append(match.group(1))
    return ids


def validate_profile(expert_dir: Path) -> tuple[dict[str, Any] | None, list[str]]:
    profile_path = expert_dir / "profile.json"
    if not profile_path.is_file():
        return None, [f"{expert_dir}: missing profile.json"]
    profile, failures = load_json(profile_path)
    if failures:
        return None, failures
    if not isinstance(profile, dict):
        return None, [f"{profile_path}: profile must be an object"]
    expert_id = profile.get("expert_id")
    if expert_id != expert_dir.name:
        failures.append(f"{profile_path}: expert_id must match directory name {expert_dir.name}")
    if not isinstance(expert_id, str) or not EXPERT_ID_RE.fullmatch(expert_id):
        failures.append(f"{profile_path}: expert_id must use lowercase letters, digits, and hyphens")
    for field in ("expert_name", "corpus_id", "source_scope", "language"):
        if not str(profile.get(field, "")).strip():
            failures.append(f"{profile_path}: missing {field}")
    paths = profile.get("paths", {})
    if "paths" in profile and not isinstance(paths, dict):
        failures.append(f"{profile_path}: paths must be an object")
    elif isinstance(paths, dict) and "glossary" in paths:
        glossary = paths.get("glossary")
        if not isinstance(glossary, str) or not glossary.strip():
            failures.append(f"{profile_path}: paths.glossary must be a relative path string")
        else:
            glossary_path = Path(glossary)
            if glossary_path.is_absolute():
                failures.append(f"{profile_path}: paths.glossary must be a relative path string")
            else:
                expert_root = expert_dir.resolve()
                resolved_glossary = (expert_dir / glossary_path).resolve()
                try:
                    resolved_glossary.relative_to(expert_root)
                except ValueError:
                    failures.append(f"{profile_path}: paths.glossary must stay inside {expert_dir}")
                else:
                    if not resolved_glossary.is_file():
                        failures.append(f"{profile_path}: paths.glossary file does not exist: {glossary}")
    return profile, failures


def validate_locator(path: Path, row: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    source_kind = row.get("source_kind")
    locator = row.get("source_locator")
    if not isinstance(locator, dict):
        return [f"{path}: {row.get('id')}: source_locator must be an object"]
    if locator.get("source_kind") != source_kind:
        failures.append(f"{path}: {row.get('id')}: source_locator.source_kind must match source_kind")

    if source_kind == "youtube_video":
        video_id = locator.get("video_id")
        start = locator.get("timestamp_start_sec")
        end = locator.get("timestamp_end_sec")
        url = str(locator.get("url", ""))
        if not isinstance(video_id, str) or not video_id:
            failures.append(f"{path}: {row.get('id')}: youtube locator missing video_id")
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or start >= end:
            failures.append(f"{path}: {row.get('id')}: youtube locator has invalid timestamp range")
        match = YOUTUBE_RE.match(url)
        if not match:
            failures.append(f"{path}: {row.get('id')}: youtube locator url must be a YouTube watch URL")
        elif video_id and match.group(2) != video_id:
            failures.append(f"{path}: {row.get('id')}: youtube locator url video id differs")
        return failures

    if "video_id" in locator:
        failures.append(f"{path}: {row.get('id')}: non-YouTube locator must not use video_id")
    required_by_kind = {
        "book": (("title",), ("page", "chapter")),
        "letter": (("author", "date"), ()),
        "article": (("title", "publication", "publication_date", "url"), ()),
        "interview": (("interviewee",), ("event_date", "publication_date")),
        "filing": (("issuer", "filing_type", "filing_date"), ()),
        "other": (("description",), ("date", "url")),
    }
    fixed, alternatives = required_by_kind.get(str(source_kind), ((), ()))
    for field in fixed:
        if not str(locator.get(field, "")).strip():
            failures.append(f"{path}: {row.get('id')}: {source_kind} locator missing {field}")
    if alternatives and not any(str(locator.get(field, "")).strip() for field in alternatives):
        failures.append(f"{path}: {row.get('id')}: {source_kind} locator needs one of {', '.join(alternatives)}")
    return failures


def validate_evidence_row(path: Path, row: dict[str, Any], expert_id: str) -> list[str]:
    failures: list[str] = []
    row_id = row.get("id")
    match = EVIDENCE_ID_RE.fullmatch(str(row_id))
    if not match:
        failures.append(f"{path}: {row_id}: id must look like <expert_id>-evidence-000001")
    elif match.group(1) != expert_id:
        failures.append(f"{path}: {row_id}: id prefix must match expert_id {expert_id}")
    if row.get("expert_id") != expert_id:
        failures.append(f"{path}: {row_id}: evidence expert_id must match {expert_id}")
    for field in ("expert_name", "corpus_id", "source_title", "source_url", "source_summary", "reviewed_by"):
        if not str(row.get(field, "")).strip():
            failures.append(f"{path}: {row_id}: missing {field}")
    if row.get("source_kind") not in ALLOWED_SOURCE_KINDS:
        failures.append(f"{path}: {row_id}: invalid source_kind {row.get('source_kind')}")
    if row.get("claim_type") not in ALLOWED_CLAIM_TYPES:
        failures.append(f"{path}: {row_id}: invalid claim_type {row.get('claim_type')}")
    if not str(row.get("claim", "")).strip():
        failures.append(f"{path}: {row_id}: missing claim")
    if not isinstance(row.get("topic"), list) or not row.get("topic"):
        failures.append(f"{path}: {row_id}: topic must be a non-empty list")
    if row.get("confidence") not in ALLOWED_CONFIDENCE:
        failures.append(f"{path}: {row_id}: invalid confidence {row.get('confidence')}")
    if row.get("source_date_status") not in ALLOWED_DATE_STATUSES:
        failures.append(f"{path}: {row_id}: invalid source_date_status {row.get('source_date_status')}")
    if not is_iso_date(row.get("source_date")):
        failures.append(f"{path}: {row_id}: source_date must be ISO yyyy-mm-dd")
    if row.get("source_date_status") == "unavailable" and not str(row.get("source_date_unavailable_reason", "")).strip():
        failures.append(f"{path}: {row_id}: unavailable source_date requires source_date_unavailable_reason")
    if not is_iso_date(row.get("source_observed_at")):
        failures.append(f"{path}: {row_id}: source_observed_at must be ISO yyyy-mm-dd")
    if not is_iso_date(row.get("reviewed_at")):
        failures.append(f"{path}: {row_id}: reviewed_at must be ISO yyyy-mm-dd")
    failures.extend(validate_locator(path, row))
    if row.get("source_kind") == "youtube_video":
        for field in ("video_id", "timestamp_start_sec", "timestamp_end_sec", "transcript_summary"):
            if field not in row:
                failures.append(f"{path}: {row_id}: youtube evidence missing compatibility field {field}")
        if row.get("transcript_summary") != row.get("source_summary"):
            failures.append(f"{path}: {row_id}: transcript_summary must match source_summary")
    if "supporting_evidence_ids" in row and not isinstance(row.get("supporting_evidence_ids"), list):
        failures.append(f"{path}: {row_id}: supporting_evidence_ids must be a list")
    return failures


def iter_evidence_rows(expert_dir: Path, expert_id: str) -> tuple[list[dict[str, Any]], list[str]]:
    evidence_dir = expert_dir / "evidence"
    failures: list[str] = []
    rows: list[dict[str, Any]] = []
    if not evidence_dir.is_dir():
        failures.append(f"{expert_dir}: missing evidence directory")
        return rows, failures
    for path in sorted(evidence_dir.glob("*.json")):
        payload, load_failures = load_json(path)
        failures.extend(load_failures)
        if load_failures:
            continue
        candidates = payload.get("evidence") if isinstance(payload, dict) else payload
        if not isinstance(candidates, list):
            failures.append(f"{path}: evidence file must contain an evidence array or list")
            continue
        for row in candidates:
            if not isinstance(row, dict):
                failures.append(f"{path}: evidence row must be an object")
                continue
            failures.extend(validate_evidence_row(path, row, expert_id))
            rows.append(row)
    return rows, failures


def lint(wiki_root: Path = DEFAULT_WIKI_ROOT) -> list[str]:
    failures: list[str] = []
    experts_dir = wiki_root / "experts"
    if not experts_dir.is_dir():
        return [f"{wiki_root}: missing experts directory"]
    root_index = wiki_root / "index.md"
    if not root_index.is_file():
        failures.append(f"{wiki_root}: missing root index.md")

    evidence_to_expert: dict[str, str] = {}
    evidence_rows: list[tuple[Path, dict[str, Any]]] = []
    for expert_dir in sorted(path for path in experts_dir.iterdir() if path.is_dir()):
        if not (expert_dir / "index.md").is_file():
            failures.append(f"{expert_dir}: missing expert index.md")
        profile, profile_failures = validate_profile(expert_dir)
        failures.extend(profile_failures)
        expert_id = expert_dir.name if profile is None else str(profile.get("expert_id", expert_dir.name))
        rows, evidence_failures = iter_evidence_rows(expert_dir, expert_id)
        failures.extend(evidence_failures)
        for row in rows:
            row_id = str(row.get("id"))
            if row_id in evidence_to_expert:
                failures.append(f"{expert_dir}: duplicate evidence id {row_id}")
            evidence_to_expert[row_id] = str(row.get("expert_id", expert_id))
            evidence_rows.append((expert_dir, row))

    for expert_dir, row in evidence_rows:
        row_id = str(row.get("id"))
        row_expert = str(row.get("expert_id", expert_dir.name))
        for support_id in row.get("supporting_evidence_ids", []):
            if support_id == row_id:
                failures.append(f"{expert_dir}: {row_id}: supporting_evidence_ids must not include itself")
                continue
            owner = evidence_to_expert.get(str(support_id))
            if owner is None:
                failures.append(f"{expert_dir}: {row_id}: broken supporting_evidence_id {support_id}")
            elif owner != row_expert:
                failures.append(
                    f"{expert_dir}: {row_id}: supporting_evidence_id {support_id} belongs to expert {owner}, not {row_expert}"
                )

    for expert_dir in sorted(path for path in experts_dir.iterdir() if path.is_dir()):
        expert_id = expert_dir.name
        for path in [expert_dir / "index.md", *sorted((expert_dir / "pages").glob("*.md"))]:
            if not path.is_file():
                continue
            try:
                refs = frontmatter_evidence_ids(path)
            except OSError as exc:
                failures.append(f"{path}: cannot read markdown: {exc}")
                continue
            for evidence_id in refs:
                owner = evidence_to_expert.get(evidence_id)
                if owner is None:
                    failures.append(f"{path}: broken evidence_id {evidence_id}")
                elif owner != expert_id:
                    failures.append(f"{path}: evidence_id {evidence_id} belongs to expert {owner}, not {expert_id}")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki-root", type=Path, default=DEFAULT_WIKI_ROOT)
    args = parser.parse_args(argv)

    failures = lint(args.wiki_root)
    if failures:
        print(json.dumps({"passed": False, "failures": failures}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"passed": True, "failures": []}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
