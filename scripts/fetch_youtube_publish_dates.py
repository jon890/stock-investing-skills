#!/usr/bin/env python3
"""YouTube 영상 페이지에서 게시일을 읽어 증거 JSON을 보강한다."""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


UPLOAD_DATE_RE = re.compile(
    r'<meta\s+itemprop="uploadDate"\s+content="([^"T]+)(?:T[^"]*)?"'
)


def parse_upload_date(html: str) -> str:
    match = UPLOAD_DATE_RE.search(html)
    if not match:
        raise ValueError("YouTube 페이지에서 uploadDate를 찾지 못했다.")
    return match.group(1)


def fetch_upload_date(video_id: str, timeout: int = 20) -> str:
    url = f"https://www.youtube.com/watch?v={video_id}&hl=en"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        html = response.read().decode("utf-8", errors="replace")
    return parse_upload_date(html)


def enrich(payload: dict, fetcher=fetch_upload_date) -> dict:
    rows = payload.get("evidence", [])
    dates = {video_id: fetcher(video_id) for video_id in sorted({row["video_id"] for row in rows})}
    observed_at = datetime.now(UTC).date().isoformat()
    for row in rows:
        row["source_date"] = dates[row["video_id"]]
        row["source_date_status"] = "verified_upload_date"
        row["source_observed_at"] = observed_at
    payload.pop("source_date_note", None)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence_json", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.evidence_json.read_text(encoding="utf-8"))
    enriched = enrich(payload)
    args.evidence_json.write_text(
        json.dumps(enriched, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"게시일 보강 완료: {args.evidence_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
