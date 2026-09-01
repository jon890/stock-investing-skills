#!/usr/bin/env python3
"""Run the fixed deterministic quality gate for the WSAJ investing brain."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import query_wsaj_wiki

DEFAULT_FIXTURE = ROOT / "tests" / "fixtures" / "wsaj-brain-eval.json"
DEFAULT_EVIDENCE_DIR = query_wsaj_wiki.DEFAULT_EVIDENCE_DIR


def load_fixture(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases")
    if not isinstance(cases, list):
        raise ValueError("fixture must contain a cases array")
    return payload


def load_evidence_index(evidence_dir: Path) -> dict[str, dict[str, Any]]:
    return {row["id"]: row for row in query_wsaj_wiki.load_evidence(evidence_dir)}


def validate_fixture_shape(fixture: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    counts = Counter(case.get("category") for case in fixture["cases"])
    expected_counts = fixture.get("required_category_counts", {})
    for category, expected in expected_counts.items():
        actual = counts.get(category, 0)
        if actual != expected:
            failures.append(f"category {category} expected {expected}, got {actual}")
    if len(fixture["cases"]) != sum(expected_counts.values()):
        failures.append(f"fixture expected {sum(expected_counts.values())} cases, got {len(fixture['cases'])}")
    seen = set()
    for case in fixture["cases"]:
        case_id = case.get("id")
        if not case_id:
            failures.append("case without id")
            continue
        if case_id in seen:
            failures.append(f"duplicate case id {case_id}")
        seen.add(case_id)
        if case.get("expected_status") not in {"matched", "requires_current_external_data", "unsupported"}:
            failures.append(f"{case_id}: invalid expected_status {case.get('expected_status')}")
        if not isinstance(case.get("required_evidence_ids", []), list):
            failures.append(f"{case_id}: required_evidence_ids must be a list")
        if not isinstance(case.get("expected_behavior", {}), dict):
            failures.append(f"{case_id}: expected_behavior must be an object")
    return failures


def citation_has_valid_source(row: dict[str, Any]) -> tuple[bool, str | None]:
    source_url = str(row.get("source_url", ""))
    video_id = str(row.get("video_id", ""))
    if not source_url.startswith("https://www.youtube.com/watch?v="):
        return False, "source_url is not a YouTube watch URL"
    if video_id not in source_url:
        return False, "source_url does not include video_id"
    source_date_status = row.get("source_date_status")
    if source_date_status == "verified_upload_date":
        try:
            source_date = date.fromisoformat(str(row.get("source_date", "")))
        except ValueError:
            return False, "verified source_date is not ISO yyyy-mm-dd"
        if source_date > date.today():
            return False, "verified source_date is in the future"
        try:
            observed_at = date.fromisoformat(str(row.get("source_observed_at", "")))
        except ValueError:
            return False, "verified source date requires ISO source_observed_at"
        if observed_at > date.today():
            return False, "source_observed_at is in the future"
    elif source_date_status == "unavailable":
        if not str(row.get("source_date_unavailable_reason", "")).strip():
            return False, "unavailable source_date requires source_date_unavailable_reason"
    else:
        return False, "source_date_status must be verified_upload_date or unavailable"
    start = row.get("timestamp_start_sec")
    end = row.get("timestamp_end_sec")
    if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or start >= end:
        return False, "timestamp range is invalid"
    match = re.search(r"[?&]t=(\d+)s", source_url)
    if not match:
        return False, "source_url has no t= timestamp"
    url_time = int(match.group(1))
    if not int(start) <= url_time <= int(end):
        return False, "source_url t= timestamp is outside evidence range"
    return True, None


def evaluate_case(case: dict[str, Any], evidence_index: dict[str, dict[str, Any]], evidence_dir: Path) -> dict[str, Any]:
    result = query_wsaj_wiki.search(case["question"], limit=5, evidence_dir=evidence_dir)
    match_ids = [row["id"] for row in result.get("matches", [])]
    expected_behavior = case.get("expected_behavior", {})
    failures: list[str] = []
    numeric_time_errors = 0

    if result["status"] != case["expected_status"]:
        failures.append(f"status expected {case['expected_status']}, got {result['status']}")

    missing_ids = [eid for eid in case.get("required_evidence_ids", []) if eid not in match_ids]
    if missing_ids:
        failures.append(f"missing required evidence ids: {', '.join(missing_ids)}")

    for evidence_id in case.get("required_evidence_ids", []):
        row = evidence_index.get(evidence_id)
        if row is None:
            failures.append(f"required evidence id does not exist: {evidence_id}")
            continue
        valid, reason = citation_has_valid_source(row)
        if not valid:
            numeric_time_errors += 1
            failures.append(f"{evidence_id}: {reason}")

    missing_terms = [term for term in expected_behavior.get("query_terms_include", []) if term not in result.get("query_terms", [])]
    if missing_terms:
        failures.append(f"missing query terms: {', '.join(missing_terms)}")

    required_topics = set(expected_behavior.get("required_topics", []))
    if required_topics:
        matched_topics = set()
        for row in result.get("matches", []):
            matched_topics.update(row.get("topic", []))
        if not required_topics.issubset(matched_topics):
            failures.append(f"missing topics: {', '.join(sorted(required_topics - matched_topics))}")

    message = result.get("message", "")
    missing_message_terms = [term for term in expected_behavior.get("message_contains", []) if term not in message]
    if missing_message_terms:
        failures.append(f"message missing terms: {', '.join(missing_message_terms)}")

    return {
        "id": case["id"],
        "category": case["category"],
        "status": result["status"],
        "expected_status": case["expected_status"],
        "matched_evidence_ids": match_ids,
        "required_evidence_ids": case.get("required_evidence_ids", []),
        "passed": not failures,
        "failures": failures,
        "citation_checks": len(case.get("required_evidence_ids", [])),
        "citation_failures": numeric_time_errors,
        "numeric_time_errors": numeric_time_errors,
    }


def evaluate(fixture_path: Path = DEFAULT_FIXTURE, evidence_dir: Path = DEFAULT_EVIDENCE_DIR) -> dict[str, Any]:
    fixture = load_fixture(fixture_path)
    evidence_index = load_evidence_index(evidence_dir)
    fixture_failures = validate_fixture_shape(fixture)
    case_results = [evaluate_case(case, evidence_index, evidence_dir) for case in fixture["cases"]]

    citation_checks = sum(item["citation_checks"] for item in case_results)
    citation_failures = sum(item["citation_failures"] for item in case_results)
    citation_validity = 1.0 if citation_checks == 0 else (citation_checks - citation_failures) / citation_checks

    unsupported_cases = [item for item in case_results if item["category"] == "unsupported"]
    unsupported_refusals = sum(1 for item in unsupported_cases if item["status"] == "unsupported")
    unsupported_refusal = 1.0 if not unsupported_cases else unsupported_refusals / len(unsupported_cases)

    numeric_time_errors = sum(item["numeric_time_errors"] for item in case_results)
    thresholds = fixture["thresholds"]
    failed_cases = [item for item in case_results if not item["passed"]]
    threshold_failures = []
    if citation_validity < thresholds["citation_validity"]:
        threshold_failures.append("citation_validity")
    if unsupported_refusal < thresholds["unsupported_refusal"]:
        threshold_failures.append("unsupported_refusal")
    if numeric_time_errors != thresholds["numeric_time_errors"]:
        threshold_failures.append("numeric_time_errors")

    return {
        "fixture": str(fixture_path),
        "evidence_dir": str(evidence_dir),
        "total_cases": len(case_results),
        "category_counts": dict(Counter(item["category"] for item in case_results)),
        "metrics": {
            "citation_validity": round(citation_validity, 4),
            "unsupported_refusal": round(unsupported_refusal, 4),
            "numeric_time_errors": numeric_time_errors,
        },
        "thresholds": thresholds,
        "passed": not fixture_failures and not failed_cases and not threshold_failures,
        "fixture_failures": fixture_failures,
        "threshold_failures": threshold_failures,
        "failed_cases": failed_cases,
        "cases": case_results,
    }


def output_summary(summary: dict[str, Any], include_details: bool = False) -> dict[str, Any]:
    if include_details:
        return summary
    return {
        key: value
        for key, value in summary.items()
        if key != "cases"
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE_DIR)
    parser.add_argument("--details", action="store_true", help="Include every evaluated case in JSON output")
    args = parser.parse_args(argv)

    summary = evaluate(args.fixture, args.evidence_dir)
    print(json.dumps(output_summary(summary, include_details=args.details), ensure_ascii=False, indent=2))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
