# Phase 02: 스킬, 문서, 검증 연결

**Execution profile**: standard

---

## 목표

범용 `investing-wiki` 스킬과 OMX 없는 Wiki 검증을 추가하고, 기존 월가아재 진입점을 새 구조에 맞춰 정리한다.

**범위 외**: 새 투자 거장 코퍼스 추가, 투자 판단 알고리즘 변경, 전체 월가아재 영상 처리 완료 보장은 이 phase 의 책임이 아니다.

---

## 작업 항목 (5)

### 1. `skills/investing-wiki/SKILL.md`: 범용 스킬 추가

`--expert` 로 expert 를 선택하는 답변 계약을 적는다.
답변은 결론, 직접 근거, 적용 추론, 반론과 한계, 링크와 타임스탬프 순서를 따른다.
여러 expert 를 함께 묻는 경우에는 출처별로 병렬 제시하고, 근거가 없으면 답하지 않는다.

### 2. `skills/wsaj-investing-brain/SKILL.md`: 호환 스킬 정리

기존 월가아재 전용 스킬은 삭제하지 않는다.
대신 `investing-wiki --expert wsaj` 로 위임하는 호환 진입점임을 명시한다.
인물 모사 금지와 최신 종목 직접 판정 금지 규칙은 유지한다.

### 3. `scripts/lint_investing_wiki.py`: 도구 비종속 검증 추가

검증기는 `wiki/experts/*/profile.json`, evidence 필수 필드와 `source_locator`·`source_summary`, evidence ID 중복, wiki 문서의 깨진 증거 참조, expert 간 provenance 혼합을 검사한다.
OMX 명령 없이 실행되어야 한다.
부정 테스트는 missing profile, duplicate ID, broken evidence_ids, mismatched expert_id, non-YouTube locator 를 포함한다.

### 4. 테스트와 평가: 새 경로에 맞춤

기존 `tests/test_wsaj_wiki.py`, `tests/test_wsaj_brain.py`, `tests/fixtures/wsaj-brain-eval.json`, `scripts/evaluate_wsaj_brain.py` 를 새 `wiki/` 구조에 맞춘다.
월가아재 호환 경로와 범용 검색 경로를 둘 다 검증한다.
WSAJ 평가는 YouTube 전용 회귀로 유지한다.
범용 `source_kind` 검증은 `lint_investing_wiki.py` 와 그 테스트가 맡는다.

### 5. 문서와 task 상태: 완료 표시

`docs/investing-wiki.md`, `docs/code-architecture.md`, `docs/data-schema.md`, `docs/flow.md`, `docs/prd.md` 가 실제 구현과 맞는지 확인한다.
마지막에 `tasks/plan005-multi-expert-wiki/index.json` 의 `status` 를 `completed` 로 바꾸고 `current_phases` 를 `2` 로 맞춘다.

## Critical Files

| 파일 | 변경 |
| --- | --- |
| `skills/investing-wiki/SKILL.md` | 신규 |
| `skills/wsaj-investing-brain/SKILL.md` | 수정 |
| `scripts/lint_investing_wiki.py` | 신규 |
| `scripts/evaluate_wsaj_brain.py` | 수정 |
| `tests/test_wsaj_wiki.py` | 수정 |
| `tests/test_wsaj_brain.py` | 수정 |
| `tests/test_investing_wiki_lint.py` | 신규 |
| `tests/fixtures/wsaj-brain-eval.json` | 수정 |
| `docs/investing-wiki.md` | 수정 |
| `docs/wsaj-corpus.md` | 수정 |
| `docs/handoff.md` | 수정 |
| `tasks/plan005-multi-expert-wiki/index.json` | 수정 |

## 검증

```bash
# cwd: /Users/nhn/personal/finance-skills
python3 scripts/lint_investing_wiki.py
python3 scripts/evaluate_wsaj_brain.py
python3 -m unittest -v tests/test_wsaj_wiki.py tests/test_wsaj_brain.py tests/test_investing_wiki_lint.py tests/test_youtube_publish_dates.py
python3 /Users/nhn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/investing-wiki
python3 /Users/nhn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/wsaj-investing-brain
for file in docs/prd.md docs/flow.md docs/code-architecture.md docs/data-schema.md docs/investing-wiki.md docs/wsaj-corpus.md docs/handoff.md docs/adr/0001-evidence-backed-wsaj-wiki.md docs/adr/0002-split-investment-skills.md docs/adr/0003-tool-independent-multi-expert-wiki.md skills/investing-wiki/SKILL.md skills/wsaj-investing-brain/SKILL.md; do
  ~/.claude/scripts/korean-style-check.sh "$file"
  python3 ~/.claude/scripts/check-readability.py "$file"
done
python3 scripts/query_investing_wiki.py --json "안전마진은 어떻게 조절해?" | python3 -c 'import json,sys; data=json.load(sys.stdin); assert data["status"] == "expert_required"; assert "wsaj" in data["experts"]'
! rg -n "omx_wiki|docs/wsaj/" docs scripts skills tests \
  -g '!docs/adr/**' \
  -g '!docs/retrospectives/**'
rg -n "omx_wiki|docs/wsaj/" docs/adr tasks || true
git status --ignored --short reports .cache
```

## 의도 메모

- 새 검증기는 OMX 없이 돌아가야 한다.
- 기존 WSAJ 평가 기준은 유지하되, 기본 데이터 위치만 `wiki/experts/wsaj/` 로 바꾼다.
- WSAJ 평가는 YouTube 전용 회귀이고, 책과 글 같은 범용 출처 계약은 linter 테스트가 책임진다.
- 운영 참조에서는 옛 경로 이름이 남지 않아야 한다. ADR과 task는 의사결정과 마이그레이션 기록이므로 별도 allowlist 로 확인한다.
- 완료 표시 지시는 마지막 phase 에만 둔다.
