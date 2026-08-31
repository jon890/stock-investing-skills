#!/usr/bin/env python3
"""월가아재 유튜브 영상을 음성과 화면 기준으로 증분 분석한다.

유튜브 자막은 사용하지 않는다. 영상에서 음성을 직접 인식하고 일정 간격의
화면을 contact sheet로 만든다. 원본 영상은 한 편 처리가 끝날 때마다 삭제한다.

실행 예:
    uv run --with mlx-whisper scripts/wsaj_video_corpus.py index
    uv run --with mlx-whisper scripts/wsaj_video_corpus.py process --limit 1
    uv run --with mlx-whisper scripts/wsaj_video_corpus.py process
    uv run --with mlx-whisper scripts/wsaj_video_corpus.py status
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path


CHANNEL_URL = "https://www.youtube.com/@wsaj/videos"
DEFAULT_CACHE = Path(".cache/wsaj-youtube")
DEFAULT_MODEL = "mlx-community/whisper-large-v3-turbo"
VIDEO_FORMAT = "18/b[height<=360]/best[height<=360]"
COOKIE_FILE_NAME = "session-cookies.txt"
VALUATION_TERMS = {
    "valuation": ("가치평가", "가치 평가", "밸류에이션", "내재가치", "상대가치"),
    "cash_flow": ("현금흐름", "현금 흐름", "DCF", "디씨에프", "잉여현금"),
    "multiples": ("PER", "PBR", "EV/EBITDA", "피이알", "피비알", "배수"),
    "discount_rate": ("할인율", "자본비용", "WACC", "왁", "리스크 프리미엄", "베타"),
    "terminal_value": ("잔존가치", "영구가치", "영구 성장률", "터미널 밸류"),
    "financials": ("재무제표", "매출 성장", "영업이익률", "마진", "자본잠식"),
    "judgment": ("안전마진", "민감도", "적정주가", "목표주가", "다모다란"),
    "special_case": ("신생기업", "성장기업", "성숙기업", "쇠퇴기업", "금융서비스", "경기순환주"),
}


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def require_commands(*names: str) -> None:
    missing = [name for name in names if shutil.which(name) is None]
    if missing:
        raise SystemExit(f"필수 명령이 없습니다: {', '.join(missing)}")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".pending")
    pending.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    pending.replace(path)


def load_index(cache: Path) -> list[dict]:
    path = cache / "index.json"
    if not path.exists():
        raise SystemExit(f"영상 색인이 없습니다. 먼저 index를 실행하세요: {path}")
    return json.loads(path.read_text(encoding="utf-8"))["videos"]


def index_channel(cache: Path) -> None:
    require_commands("yt-dlp")
    result = run(
        [
            "yt-dlp",
            "--flat-playlist",
            "--dump-single-json",
            "--extractor-args",
            "youtube:lang=ko",
            CHANNEL_URL,
        ],
        capture=True,
    )
    playlist = json.loads(result.stdout)
    videos = []
    for entry in playlist.get("entries", []):
        videos.append(
            {
                "id": entry["id"],
                "title": entry.get("title"),
                "url": entry.get("url") or f"https://www.youtube.com/watch?v={entry['id']}",
                "duration": entry.get("duration"),
                "view_count": entry.get("view_count"),
            }
        )
    write_json(
        cache / "index.json",
        {
            "channel_id": playlist.get("channel_id") or playlist.get("id"),
            "channel": playlist.get("channel") or playlist.get("title"),
            "source_url": CHANNEL_URL,
            "indexed_at": datetime.now(UTC).isoformat(),
            "count": len(videos),
            "videos": videos,
        },
    )
    print(f"색인 완료: {len(videos)}편 -> {cache / 'index.json'}", flush=True)


def export_browser_cookies(cache: Path) -> None:
    require_commands("yt-dlp")
    cache.mkdir(parents=True, exist_ok=True)
    cookie_file = cache / COOKIE_FILE_NAME
    run(
        [
            "yt-dlp",
            "--cookies-from-browser",
            "chrome",
            "--cookies",
            str(cookie_file),
            "--skip-download",
            "--playlist-items",
            "1",
            CHANNEL_URL,
        ]
    )
    cookie_file.chmod(0o600)
    print(
        f"Chrome 세션을 한 번 저장했습니다: {cookie_file} "
        f"(권한 {oct(cookie_file.stat().st_mode & 0o777)})",
        flush=True,
    )


def download_commands(video_url: str, target: Path, cookie_file: Path | None) -> list[list[str]]:
    output = str(target / "source.%(ext)s")
    commands = [
        [
            "yt-dlp",
            "--extractor-args",
            "youtube:lang=ko;player_client=android",
            "--no-cookies",
            "--no-write-subs",
            "--no-write-auto-subs",
            "-f",
            VIDEO_FORMAT,
            "-o",
            output,
            video_url,
        ]
    ]
    if cookie_file is not None:
        commands.append(
            [
                "yt-dlp",
                "--cookies",
                str(cookie_file),
                "--extractor-args",
                "youtube:lang=ko;player_client=web",
                "--no-write-subs",
                "--no-write-auto-subs",
                "-f",
                VIDEO_FORMAT,
                "-o",
                output,
                video_url,
            ]
        )
    return commands


def download_video(video: dict, target: Path, cookie_file: Path | None) -> Path:
    last_error = None
    for command in download_commands(video["url"], target, cookie_file):
        for partial in target.glob("source.*"):
            partial.unlink()
        try:
            run(command)
            break
        except subprocess.CalledProcessError as error:
            last_error = error
    else:
        assert last_error is not None
        raise last_error

    matches = list(target.glob("source.*"))
    if len(matches) != 1:
        raise RuntimeError(f"다운로드한 영상 파일을 찾을 수 없습니다: {video['id']}")
    return matches[0]


def transcribe(video_path: Path, model: str) -> dict:
    try:
        import mlx_whisper
    except ImportError as error:
        raise SystemExit(
            "mlx-whisper가 필요합니다. "
            "uv run --with mlx-whisper scripts/wsaj_video_corpus.py process 로 실행하세요."
        ) from error
    return mlx_whisper.transcribe(
        str(video_path),
        path_or_hf_repo=model,
        language="ko",
        task="transcribe",
        verbose=False,
        condition_on_previous_text=False,
    )


def extract_contact_sheets(video_path: Path, output_dir: Path, interval: int) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = output_dir / "sheet-%03d.jpg"
    draw_time = "drawtext=text='%{pts\\:hms}':x=8:y=8:fontsize=20:fontcolor=white:box=1:boxcolor=black@0.65"
    video_filter = (
        f"fps=1/{interval},scale=480:-2,{draw_time},"
        "tile=4x4:padding=4:margin=4"
    )
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video_path),
            "-vf",
            video_filter,
            "-fps_mode",
            "vfr",
            "-q:v",
            "3",
            str(output_pattern),
        ]
    )
    return [path.name for path in sorted(output_dir.glob("sheet-*.jpg"))]


def compact_transcript(result: dict) -> dict:
    return {
        "language": result.get("language"),
        "text": result.get("text", "").strip(),
        "segments": [
            {
                "start": round(float(segment["start"]), 2),
                "end": round(float(segment["end"]), 2),
                "text": segment["text"].strip(),
            }
            for segment in result.get("segments", [])
        ],
    }


def process_one(
    video: dict,
    cache: Path,
    model: str,
    interval: int,
    cookie_file: Path | None,
) -> None:
    output_dir = cache / "videos" / video["id"]
    result_path = output_dir / "analysis.json"
    if result_path.exists():
        print(f"건너뜀 {video['id']} 이미 완료", flush=True)
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix=f"wsaj-{video['id']}-") as temp_name:
        video_path = download_video(video, Path(temp_name), cookie_file)
        transcript = compact_transcript(transcribe(video_path, model))
        sheets = extract_contact_sheets(video_path, output_dir / "frames", interval)

    write_json(
        result_path,
        {
            "video": video,
            "source": {
                "captions_used": False,
                "audio_source": "downloaded_video",
                "visual_source": f"{interval}-second interval frames",
                "transcription_model": model,
            },
            "processed_at": datetime.now(UTC).isoformat(),
            "elapsed_seconds": round(time.monotonic() - started, 2),
            "transcript": transcript,
            "contact_sheets": sheets,
        },
    )
    print(
        f"완료 {video['id']} {video.get('title', '')} "
        f"({time.monotonic() - started:.1f}초)",
        flush=True,
    )


def process_channel(
    cache: Path,
    model: str,
    interval: int,
    limit: int | None,
    selected_ids: set[str] | None,
) -> None:
    require_commands("yt-dlp", "ffmpeg")
    cookie_file = cache / COOKIE_FILE_NAME
    if cookie_file.exists():
        mode = cookie_file.stat().st_mode & 0o777
        if mode & 0o077:
            raise SystemExit(f"Chrome 세션 파일 권한이 안전하지 않습니다: {oct(mode)}")
    else:
        cookie_file = None
    videos = load_index(cache)
    if selected_ids:
        known_ids = {video["id"] for video in videos}
        unknown_ids = sorted(selected_ids - known_ids)
        if unknown_ids:
            raise SystemExit(f"색인에 없는 영상 ID입니다: {', '.join(unknown_ids)}")
        videos = [video for video in videos if video["id"] in selected_ids]
    pending = [v for v in videos if not (cache / "videos" / v["id"] / "analysis.json").exists()]
    if limit is not None:
        pending = pending[:limit]
    print(f"처리 대상: {len(pending)}편", flush=True)
    failures = 0
    for position, video in enumerate(pending, start=1):
        print(f"[{position}/{len(pending)}] 시작 {video['id']} {video.get('title', '')}", flush=True)
        try:
            process_one(video, cache, model, interval, cookie_file)
            failures = 0
        except Exception as error:
            failures += 1
            print(
                f"실패 {video['id']} ({type(error).__name__}): {error}",
                file=sys.stderr,
                flush=True,
            )
            if failures >= 3:
                raise SystemExit("연속 세 편이 실패해 처리를 중단했습니다. 원인을 확인한 뒤 재개하세요.")


def show_status(cache: Path) -> None:
    videos = load_index(cache)
    completed = [v for v in videos if (cache / "videos" / v["id"] / "analysis.json").exists()]
    elapsed = 0.0
    for video in completed:
        data = json.loads(
            (cache / "videos" / video["id"] / "analysis.json").read_text(encoding="utf-8")
        )
        elapsed += data.get("elapsed_seconds", 0.0)
    print(
        json.dumps(
            {
                "total": len(videos),
                "completed": len(completed),
                "remaining": len(videos) - len(completed),
                "processing_hours": round(elapsed / 3600, 2),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def relevance(video: dict, transcript: str) -> dict:
    title = video.get("title") or ""
    combined = f"{title}\n{transcript}"
    matches = {}
    score = 0
    for category, terms in VALUATION_TERMS.items():
        category_hits = {}
        for term in terms:
            title_count = len(re.findall(re.escape(term), title, re.IGNORECASE))
            body_count = len(re.findall(re.escape(term), combined, re.IGNORECASE)) - title_count
            if title_count or body_count:
                category_hits[term] = {"title": title_count, "transcript": body_count}
                score += title_count * 8 + min(body_count, 8)
        if category_hits:
            matches[category] = category_hits
    return {"score": score, "matches": matches}


def build_catalog(cache: Path) -> None:
    videos = load_index(cache)
    catalog = []
    for video in videos:
        result_path = cache / "videos" / video["id"] / "analysis.json"
        if not result_path.exists():
            continue
        result = json.loads(result_path.read_text(encoding="utf-8"))
        item = {"video": video, **relevance(video, result["transcript"]["text"])}
        catalog.append(item)
    catalog.sort(key=lambda item: (-item["score"], item["video"]["id"]))
    write_json(
        cache / "catalog.json",
        {
            "generated_at": datetime.now(UTC).isoformat(),
            "analyzed_count": len(catalog),
            "videos": catalog,
        },
    )
    print(f"분류 완료: {len(catalog)}편 -> {cache / 'catalog.json'}", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("auth", "index", "process", "status", "catalog"))
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--frame-interval", type=int, default=30)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--ids", help="쉼표로 구분한 영상 ID. 지정한 영상만 처리한다")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.action == "auth":
        export_browser_cookies(args.cache)
    elif args.action == "index":
        index_channel(args.cache)
    elif args.action == "process":
        selected_ids = set(args.ids.split(",")) if args.ids else None
        process_channel(args.cache, args.model, args.frame_interval, args.limit, selected_ids)
    elif args.action == "status":
        show_status(args.cache)
    else:
        build_catalog(args.cache)


if __name__ == "__main__":
    main()
