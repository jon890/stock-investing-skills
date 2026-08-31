#!/usr/bin/env python3
"""Deterministic lookup over curated WSAJ evidence JSON files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_DIR = ROOT / "docs" / "wsaj" / "evidence"

ALIASES = {
    "가치평가": ["valuation", "process"],
    "밸류에이션": ["valuation"],
    "내재가치": ["intrinsic-value"],
    "상대가치": ["relative-valuation"],
    "유사기업": ["peer-group"],
    "비교군": ["peer-group"],
    "배수": ["multiples"],
    "멀티플": ["multiples"],
    "per": ["per"],
    "pbr": ["pbr"],
    "psr": ["psr"],
    "dcf": ["dcf"],
    "할인율": ["discount-rate", "cost-of-capital"],
    "현금흐름": ["cash-flow"],
    "성장률": ["growth"],
    "안전마진": ["margin-of-safety"],
    "손익비": ["risk-reward"],
    "확률적 우위": ["investing-values", "probabilistic-edge"],
    "절제 우위": ["investing-values", "discipline"],
    "기대값": ["investing-values", "probabilistic-edge", "risk-reward"],
    "레버리지": ["leverage"],
    "물타기": ["averaging-down"],
    "절제": ["discipline"],
    "재무제표": ["financial-statements"],
    "실적발표": ["earnings"],
    "컨센서스": ["consensus"],
    "가이던스": ["guidance"],
    "ipo": ["ipo"],
    "공모": ["ipo"],
    "락업": ["lock-up"],
    "m&a": ["mna"],
    "인수합병": ["mna"],
    "합병": ["mna"],
    "은행": ["bank", "deposit", "liquidity", "tier-1", "rwa"],
    "예금": ["deposit"],
    "유동성": ["liquidity"],
    "엔비디아": ["nvidia"],
    "nvidia": ["nvidia"],
    "테슬라": ["tesla"],
    "tesla": ["tesla"],
    "맥도날드": ["mcdonalds"],
    "mcdonald": ["mcdonalds"],
}

UNSUPPORTED_PATTERNS = [
    "오늘",
    "지금",
    "현재",
    "사야",
    "팔아",
    "매수",
    "매도",
    "목표가",
    "최신",
    "주가",
]

CURRENT_POSITION_PATTERNS = [
    re.compile(pattern)
    for pattern in (
        r"포트폴리오",
        r"내\s*계좌",
        r"비중\s*(을|를)?\s*(늘|줄|높|낮|확대|축소)",
        r"추매",
        r"손절",
        r"익절",
        r"편입",
        r"계속\s*보유",
        r"보유\s*해야",
    )
]


def load_evidence(evidence_dir: Path = DEFAULT_EVIDENCE_DIR) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(evidence_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("evidence"), list):
            rows.extend(payload["evidence"])
        elif isinstance(payload, list):
            rows.extend(payload)
    return rows


def query_terms(question: str) -> set[str]:
    lowered = question.lower()
    terms = set(re.findall(r"[a-z0-9][a-z0-9\-]+", lowered))
    for key, aliases in ALIASES.items():
        if key.lower() in lowered:
            terms.add(key.lower())
            terms.update(aliases)
    return terms


def needs_current_data(question: str) -> bool:
    lowered = question.lower()
    if any(pattern.lower() in lowered for pattern in UNSUPPORTED_PATTERNS):
        return True
    return any(pattern.search(question) for pattern in CURRENT_POSITION_PATTERNS)


def term_in_text(term: str, text: str) -> bool:
    if re.fullmatch(r"[a-z0-9][a-z0-9\-]+", term):
        return re.search(rf"(?<![a-z0-9\-]){re.escape(term)}(?![a-z0-9\-])", text) is not None
    return term in text


def score_evidence(row: dict[str, Any], terms: set[str], question: str) -> int:
    topics = set(row.get("topic", []))
    score = len(topics & terms) * 4
    haystack = " ".join(
        str(row.get(field, ""))
        for field in ("claim", "transcript_summary", "source_title", "video_id")
    ).lower()
    for term in terms:
        if term_in_text(term, haystack):
            score += 1
    for token in re.findall(r"[a-z0-9][a-z0-9\-]+", question.lower()):
        if term_in_text(token, haystack):
            score += 1
    if score > 0 and row.get("claim_type") == "direct_claim":
        score += 1
    return score


def search(question: str, limit: int = 5, evidence_dir: Path = DEFAULT_EVIDENCE_DIR) -> dict[str, Any]:
    terms = query_terms(question)
    rows = load_evidence(evidence_dir)
    current_data_needed = needs_current_data(question)
    if not terms:
        status = "requires_current_external_data" if current_data_needed else "unsupported"
        message = (
            "현재 주가, 최신 실적, 매수·매도 판단은 영상 근거만으로 결론을 낼 수 없다."
            if current_data_needed
            else "검토된 월가아재 증거 저장소에서 관련 근거를 찾지 못했다."
        )
        return {
            "status": status,
            "question": question,
            "query_terms": [],
            "matches": [],
            "message": message,
        }
    scored = [
        (score_evidence(row, terms, question), row)
        for row in rows
    ]
    matches = [
        row
        for score, row in sorted(scored, key=lambda item: (-item[0], item[1]["id"]))
        if score > 0
    ][:limit]

    if current_data_needed:
        return {
            "status": "requires_current_external_data",
            "question": question,
            "query_terms": sorted(terms),
            "matches": matches,
            "message": "현재 주가, 최신 실적, 매수·매도 판단은 영상 근거만으로 결론을 낼 수 없다.",
        }
    if not matches:
        return {
            "status": "unsupported",
            "question": question,
            "query_terms": sorted(terms),
            "matches": [],
            "message": "검토된 월가아재 증거 저장소에서 관련 근거를 찾지 못했다.",
        }
    return {
        "status": "matched",
        "question": question,
        "query_terms": sorted(terms),
        "matches": matches,
    }


def render_text(result: dict[str, Any]) -> str:
    lines = [
        f"status: {result['status']}",
        f"question: {result['question']}",
    ]
    if result.get("message"):
        lines.append(f"message: {result['message']}")
    for row in result.get("matches", []):
        lines.extend(
            [
                "",
                f"- {row['id']} ({row['claim_type']}, {row['confidence']})",
                f"  claim: {row['claim']}",
                f"  source: {row['source_title']}",
                f"  url: {row['source_url']}",
                f"  time: {row['timestamp_start_sec']}-{row['timestamp_end_sec']}s",
            ]
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="+", help="Question to search")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE_DIR)
    args = parser.parse_args(argv)

    result = search(" ".join(args.question), limit=args.limit, evidence_dir=args.evidence_dir)
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
