#!/usr/bin/env python3
"""Deterministic lookup over curated investing expert evidence JSON files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WIKI_ROOT = ROOT / "wiki"

ALIASES = {
    "가치평가": ["valuation", "process"],
    "밸류에이션": ["valuation"],
    "내재가치": ["intrinsic-value"],
    "상대가치평가": ["relative-valuation", "process"],
    "상대가치": ["relative-valuation"],
    "유사기업": ["peer-group"],
    "비교군": ["peer-group"],
    "고평가": ["valuation-risk", "market-efficiency"],
    "왜곡": ["valuation-risk", "market-efficiency"],
    "약점": ["valuation-risk"],
    "배수": ["multiples"],
    "멀티플": ["multiples"],
    "per": ["per"],
    "pbr": ["pbr"],
    "psr": ["psr"],
    "dcf": ["dcf"],
    "인덱스 dcf": ["index-dcf", "market-valuation", "equity-risk-premium"],
    "index dcf": ["index-dcf", "market-valuation", "equity-risk-premium"],
    "reverse dcf": ["reverse-dcf", "growth-expectation", "free-cash-flow"],
    "리버스 dcf": ["reverse-dcf", "growth-expectation", "free-cash-flow"],
    "역dcf": ["reverse-dcf", "growth-expectation", "free-cash-flow"],
    "할인율": ["discount-rate", "cost-of-capital"],
    "리스크 프리미엄": ["equity-risk-premium"],
    "현금흐름": ["cash-flow"],
    "잉여현금흐름": ["free-cash-flow"],
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


def expert_root(expert_id: str, wiki_root: Path = DEFAULT_WIKI_ROOT) -> Path:
    return wiki_root / "experts" / expert_id


def evidence_dir_for_expert(expert_id: str, wiki_root: Path = DEFAULT_WIKI_ROOT) -> Path:
    return expert_root(expert_id, wiki_root) / "evidence"


def list_experts(wiki_root: Path = DEFAULT_WIKI_ROOT) -> list[dict[str, str]]:
    experts_dir = wiki_root / "experts"
    if not experts_dir.exists():
        return []
    experts = []
    for path in sorted(experts_dir.iterdir()):
        profile_path = path / "profile.json"
        if not profile_path.is_file():
            continue
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        experts.append(
            {
                "expert_id": str(profile.get("expert_id", path.name)),
                "expert_name": str(profile.get("expert_name", profile.get("display_name", path.name))),
                "corpus_id": str(profile.get("corpus_id", "")),
            }
        )
    return experts


def load_evidence(evidence_dir: Path) -> list[dict[str, Any]]:
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
    matched_keys = [key for key in ALIASES if key.lower() in lowered]
    for key in matched_keys:
        normalized_key = key.lower()
        if any(
            normalized_key != other.lower() and normalized_key in other.lower()
            for other in matched_keys
        ):
            continue
        terms.add(normalized_key)
        terms.update(ALIASES[key])
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
        for field in ("claim", "source_summary", "transcript_summary", "source_title", "video_id")
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


def expert_required_result(question: str, wiki_root: Path = DEFAULT_WIKI_ROOT) -> dict[str, Any]:
    return {
        "status": "expert_required",
        "question": question,
        "experts": [expert["expert_id"] for expert in list_experts(wiki_root)],
        "supported_experts": list_experts(wiki_root),
        "matches": [],
        "message": "검색할 expert를 --expert로 지정해야 한다.",
    }


def expert_not_found_result(question: str, expert_id: str, wiki_root: Path = DEFAULT_WIKI_ROOT) -> dict[str, Any]:
    return {
        "status": "expert_not_found",
        "question": question,
        "expert": expert_id,
        "experts": [expert["expert_id"] for expert in list_experts(wiki_root)],
        "supported_experts": list_experts(wiki_root),
        "matches": [],
        "message": f"지원하지 않는 expert다: {expert_id}",
    }


def evidence_dir_mismatch_result(
    question: str,
    expert_id: str,
    requested_dir: Path,
    expected_dir: Path,
) -> dict[str, Any]:
    return {
        "status": "evidence_dir_mismatch",
        "question": question,
        "expert": expert_id,
        "requested_evidence_dir": str(requested_dir),
        "expected_evidence_dir": str(expected_dir),
        "matches": [],
        "message": "--evidence-dir must match wiki_root/experts/<expert>/evidence for the requested expert.",
    }


def evidence_expert_mismatch_result(
    question: str,
    expert_id: str,
    mismatched_ids: list[str],
) -> dict[str, Any]:
    return {
        "status": "evidence_expert_mismatch",
        "question": question,
        "expert": expert_id,
        "mismatched_evidence_ids": mismatched_ids,
        "matches": [],
        "message": "Loaded evidence contains rows whose expert_id differs from the requested expert.",
    }


def evidence_label(expert: str | None) -> str:
    if expert:
        return f"{expert} Wiki 근거"
    return "투자 Wiki 근거"


def render_locator(row: dict[str, Any]) -> str:
    locator = row.get("source_locator")
    if not isinstance(locator, dict):
        return "locator: unavailable"
    source_kind = str(row.get("source_kind", locator.get("source_kind", "unknown")))
    if source_kind == "youtube_video":
        start = locator.get("timestamp_start_sec", row.get("timestamp_start_sec", "?"))
        end = locator.get("timestamp_end_sec", row.get("timestamp_end_sec", "?"))
        return f"youtube: {locator.get('video_id', row.get('video_id', '?'))} {start}-{end}s"
    if source_kind == "book":
        parts = [str(locator.get("title", row.get("source_title", "")))]
        if locator.get("page"):
            parts.append(f"p.{locator['page']}")
        elif locator.get("chapter"):
            parts.append(f"chapter {locator['chapter']}")
        return "book: " + ", ".join(part for part in parts if part)
    if source_kind == "letter":
        return f"letter: {locator.get('author', '?')}, {locator.get('date', '?')}"
    if source_kind == "article":
        return f"article: {locator.get('publication', '?')}, {locator.get('publication_date', '?')}"
    if source_kind == "interview":
        date_value = locator.get("event_date", locator.get("publication_date", "?"))
        return f"interview: {locator.get('interviewee', '?')}, {date_value}"
    if source_kind == "filing":
        return f"filing: {locator.get('issuer', '?')} {locator.get('filing_type', '?')} {locator.get('filing_date', '?')}"
    if source_kind == "other":
        return f"other: {locator.get('description', row.get('source_title', '?'))}"
    return f"{source_kind}: {row.get('source_title', 'unknown source')}"


def search(
    question: str,
    limit: int = 5,
    evidence_dir: Path | None = None,
    expert: str | None = None,
    wiki_root: Path = DEFAULT_WIKI_ROOT,
) -> dict[str, Any]:
    if expert is None:
        return expert_required_result(question, wiki_root)

    candidate = evidence_dir_for_expert(expert, wiki_root)
    if not candidate.is_dir():
        return expert_not_found_result(question, expert, wiki_root)
    if evidence_dir is None:
        evidence_dir = candidate
    elif evidence_dir.resolve() != candidate.resolve():
        return evidence_dir_mismatch_result(question, expert, evidence_dir, candidate)

    terms = query_terms(question)
    rows = load_evidence(evidence_dir)
    mismatched_ids = [
        str(row.get("id"))
        for row in rows
        if row.get("expert_id") != expert
    ]
    if mismatched_ids:
        return evidence_expert_mismatch_result(question, expert, mismatched_ids)
    current_data_needed = needs_current_data(question)
    if not terms:
        status = "requires_current_external_data" if current_data_needed else "unsupported"
        message = (
            f"현재 주가, 최신 실적, 매수·매도 판단은 {evidence_label(expert)}만으로 결론을 낼 수 없다."
            if current_data_needed
            else f"검토된 {evidence_label(expert)}에서 관련 근거를 찾지 못했다."
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
            "message": f"현재 주가, 최신 실적, 매수·매도 판단은 {evidence_label(expert)}만으로 결론을 낼 수 없다.",
        }
    if not matches:
        return {
            "status": "unsupported",
            "question": question,
            "query_terms": sorted(terms),
            "matches": [],
            "message": f"검토된 {evidence_label(expert)}에서 관련 근거를 찾지 못했다.",
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
    if result["status"] in {"expert_required", "expert_not_found"}:
        experts = result.get("supported_experts", [])
        if experts:
            lines.append("experts:")
            for expert in experts:
                lines.append(f"  - {expert['expert_id']}: {expert['expert_name']}")
    for row in result.get("matches", []):
        lines.extend(
            [
                "",
                f"- {row['id']} ({row['claim_type']}, {row['confidence']})",
                f"  claim: {row['claim']}",
                f"  source: {row['source_title']}",
                f"  url: {row['source_url']}",
                f"  locator: {render_locator(row)}",
            ]
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="+", help="Question to search")
    parser.add_argument("--expert", help="Expert id to search, for example wsaj")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--wiki-root", type=Path, default=DEFAULT_WIKI_ROOT)
    args = parser.parse_args(argv)

    result = search(
        " ".join(args.question),
        limit=args.limit,
        evidence_dir=args.evidence_dir,
        expert=args.expert,
        wiki_root=args.wiki_root,
    )
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))
    if result["status"] in {"evidence_dir_mismatch", "evidence_expert_mismatch"}:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
