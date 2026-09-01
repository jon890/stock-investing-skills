#!/usr/bin/env python3
"""Compatibility entry point for WSAJ investing wiki lookup."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_DIR = ROOT / "wiki" / "experts" / "wsaj" / "evidence"

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import query_investing_wiki as investing_wiki

ALIASES = investing_wiki.ALIASES
UNSUPPORTED_PATTERNS = investing_wiki.UNSUPPORTED_PATTERNS
CURRENT_POSITION_PATTERNS = investing_wiki.CURRENT_POSITION_PATTERNS
load_evidence = investing_wiki.load_evidence
query_terms = investing_wiki.query_terms
needs_current_data = investing_wiki.needs_current_data
term_in_text = investing_wiki.term_in_text
score_evidence = investing_wiki.score_evidence
render_text = investing_wiki.render_text


def search(
    question: str,
    limit: int = 5,
    evidence_dir: Path = DEFAULT_EVIDENCE_DIR,
) -> dict[str, Any]:
    return investing_wiki.search(question, limit=limit, evidence_dir=evidence_dir, expert="wsaj")


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
