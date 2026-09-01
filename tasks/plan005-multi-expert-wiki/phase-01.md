# Phase 01: 저장 구조와 검색 스크립트 마이그레이션

**Execution profile**: standard

---

## 목표

`omx_wiki/` 와 `docs/wsaj/` 에 묶인 월가아재 Wiki 원본을 `wiki/experts/wsaj/` 로 옮기고, 범용 expert 검색 진입점을 만든다.

**범위 외**: 스킬 문구 정리, 최종 평가 문항 확장, 전체 영상 추가 분석은 phase 02와 plan004의 책임이다.

---

## 작업 항목 (5)

### 1. `wiki/experts/wsaj/`: 월가아재 expert 구조 생성

`wiki/experts/wsaj/profile.json`, `wiki/experts/wsaj/index.md`, `wiki/experts/wsaj/pages/`, `wiki/experts/wsaj/evidence/` 를 만든다.
기존 `docs/wsaj/evidence/core.json` 은 `wiki/experts/wsaj/evidence/core.json` 로 옮긴다.
기존 `docs/wsaj/*.md` 주제 문서는 `wiki/experts/wsaj/pages/` 로 옮긴다.
파일을 옮기기 전에 기존 evidence 개수, evidence ID 집합, `sha256` 값을 기록한다.
새 경로 생성, 파일 이동이나 복사, 원본과 복사본의 `sha256` 일치 검증을 먼저 끝낸다.
그 다음 스키마를 확장하고 evidence 개수와 ID 집합이 유지되는지 검증한다.
이 검증이 실패하면 `docs/wsaj/` 와 `omx_wiki/` 를 삭제하지 않는다.

### 2. evidence 스키마: expert 필드 추가

모든 월가아재 evidence row 에 `expert_id`, `expert_name`, `corpus_id`, `source_kind`, `source_locator`, `source_summary` 를 추가한다.
값은 각각 `wsaj`, `월가아재`, `wsaj-youtube-public`, `youtube_video` 로 둔다.
기존 `video_id`, 타임스탬프, `transcript_summary` 는 WSAJ 회귀 호환 필드로 유지하고 공통 필드와 같은 값을 가져야 한다.
모든 row 에 `source_locator` 를 추가하고, YouTube 위치 정보는 `source_locator.video_id`, `source_locator.timestamp_start_sec`, `source_locator.timestamp_end_sec`, `source_locator.url` 에 둔다.

### 3. `scripts/query_investing_wiki.py`: 범용 검색기 추가

새 스크립트는 `--expert <expert_id>` 를 받는다.
기본 evidence 위치는 `wiki/experts/<expert_id>/evidence/` 다.
기존 `query_wsaj_wiki.py` 의 검색, 현재 데이터 판정, 텍스트 출력 계약은 유지하되 expert 범위를 인자로 분리한다.
`--expert` 가 없으면 검색하지 않는다.
대신 지원 expert 목록과 `expert_required` 상태를 반환한다.

### 4. `scripts/query_wsaj_wiki.py`: 호환 진입점 유지

기존 CLI와 import 계약을 깨지 않는다.
내부 구현은 `query_investing_wiki.py` 를 호출하거나 위임하고, 기본 expert 는 `wsaj` 로 고정한다.
따라서 WSAJ wrapper 는 `--expert` 없이도 월가아재 근거를 검색해야 한다.

### 5. `omx_wiki/` 와 옛 docs 경로: 원본 역할 제거

검색과 테스트가 `omx_wiki/` 를 읽지 않게 한다.
마이그레이션 뒤 `omx_wiki/` 는 제거한다.
`docs/wsaj/` 는 관리 원본이 아니므로 제거하거나, 필요한 경우 `docs/investing-wiki.md` 로 안내를 합친다.
삭제는 새 경로의 개수, ID 집합, 원본과 복사본의 `sha256`, 범용 검색, 호환 검색, 테스트가 모두 통과한 뒤에만 수행한다.

## Critical Files

| 파일 | 변경 |
| --- | --- |
| `wiki/experts/wsaj/profile.json` | 신규 |
| `wiki/experts/wsaj/index.md` | 신규 |
| `wiki/experts/wsaj/pages/*.md` | 신규 |
| `wiki/experts/wsaj/evidence/core.json` | 신규 |
| `scripts/query_investing_wiki.py` | 신규 |
| `scripts/query_wsaj_wiki.py` | 수정 |
| `docs/wsaj-corpus.md` | 수정 |
| `docs/handoff.md` | 수정 |
| `docs/wsaj/evidence/core.json` | 삭제 또는 이동 |
| `docs/wsaj/*.md` | 삭제 또는 이동 |
| `omx_wiki/*.md` | 삭제 |

## 검증

```bash
# cwd: /Users/nhn/personal/finance-skills
python3 scripts/query_investing_wiki.py --expert wsaj --json "안전마진은 어떻게 조절해?"
python3 scripts/query_wsaj_wiki.py --json "안전마진은 어떻게 조절해?"
python3 scripts/query_investing_wiki.py --json "안전마진은 어떻게 조절해?" | python3 -c 'import json,sys; data=json.load(sys.stdin); assert data["status"] == "expert_required"; assert "wsaj" in data["experts"]'
python3 -m unittest -v tests/test_wsaj_wiki.py tests/test_wsaj_brain.py
python3 - <<'PY'
import hashlib
import json
from pathlib import Path

old = json.loads(Path("/tmp/wsaj-core-before.json").read_text(encoding="utf-8"))
new = json.loads(Path("wiki/experts/wsaj/evidence/core.json").read_text(encoding="utf-8"))
old_ids = {row["id"] for row in old["evidence"]}
new_ids = {row["id"] for row in new["evidence"]}
assert len(old["evidence"]) == len(new["evidence"])
assert old_ids == new_ids
before_hash = Path("/tmp/wsaj-core-before.sha256").read_text(encoding="utf-8").split()[0]
copied_hash = Path("/tmp/wsaj-core-copied.sha256").read_text(encoding="utf-8").split()[0]
assert before_hash == copied_hash
for row in new["evidence"]:
    assert row["expert_id"] == "wsaj"
    assert row["source_kind"] == "youtube_video"
    assert row["source_locator"]["source_kind"] == "youtube_video"
PY
test ! -d omx_wiki
test ! -d docs/wsaj
```

## 의도 메모

- `wiki/` 는 도구와 무관한 관리 원본이다.
- 월가아재 호환 진입점은 기존 사용자의 호출을 깨지 않기 위해 남긴다.
- provenance 필드는 다른 expert 를 추가할 때 출처가 섞이는 문제를 막는다.
- `query_investing_wiki.py` 의 `expert_required` 는 사용자가 범위를 모르는 질문을 던졌을 때 추측 검색을 막는 장치다.
