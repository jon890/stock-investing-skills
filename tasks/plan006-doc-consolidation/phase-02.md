# Phase 02: 중복 문서 제거와 공개 탐색 경로 정리

**Execution profile**: standard

---

## 목표

관리 책임이 겹치는 문서를 제거하고 공개 저장소의 진입점을 핵심 문서와 Wiki로 직접 연결한다.

**범위 외**: 과거 task 본문의 마이그레이션 명령 재작성, 새 투자 기능 구현, report·cache 추적 정책 변경은 이 phase의 책임이 아니다.

---

## 작업 항목 (5)

### 1. `docs/handoff.md`: 안정 사실을 흡수하고 제거

DCF 5년 기본값은 PRD와 데이터 스키마가 소유한다.
현재 진행률은 `docs/wsaj-corpus.md` 의 status 명령이 소유한다.
구조와 결정은 핵심 문서와 ADR이 소유하므로 인계 문서를 별도 원본으로 남기지 않는다.

### 2. `docs/investing-wiki.md`: 중복 책임을 제거

제품 경계는 PRD, 호출 흐름은 flow, 파일 배치는 code architecture, 데이터 형식은 data schema, 사용자 탐색은 `wiki/index.md`, 실행 계약은 skills가 소유한다.
스킬과 운영 문서에 이 파일을 가리키는 활성 참조가 없는지 확인한 뒤 파일을 제거한다.

### 3. `wiki/log.md`: Git과 중복되는 수동 로그 제거

정적인 증거 개수와 마이그레이션 내역은 Git과 ADR에서 찾는다.
`wiki/index.md` 와 핵심 문서의 log 링크를 제거하고, 향후 진행률은 실행 명령으로 확인한다.

### 4. 공개 저장소 진입점과 역사 기록 정리

짧은 `README.md` 를 만들고 프로젝트 목표, 세 스킬, `docs/prd.md`, `docs/flow.md`, `wiki/index.md` 로 연결한다.
핵심 정의를 README에 복제하지 않는다.

`tasks/plan003-wsaj-wiki-mvp.md` 는 당시 경로를 바꾸지 않고 plan005와 ADR-0003으로 대체됐다는 표시만 추가한다.
`tasks/index.json` 의 plan003에도 `superseded_by`를 추가해 역사 기록과 현재 운영 경로를 구분한다.

### 5. 통합 결과 검증과 완료 표시

삭제한 문서와 `wiki/log.md` 를 활성 문서·스킬·스크립트·테스트가 참조하지 않아야 한다.
과거 ADR과 task는 역사 기록이므로 참조 검색에서 별도로 허용한다.

검증이 모두 통과하면 `tasks/plan006-doc-consolidation/index.json` 의 `status` 를 `completed`, `current_phases` 를 `2` 로 바꾼다.

## Critical Files

| 파일 | 변경 |
| --- | --- |
| `README.md` | 공개 진입점 신규 |
| `docs/handoff.md` | 삭제 |
| `docs/investing-wiki.md` | 삭제 |
| `wiki/log.md` | 삭제 |
| `wiki/index.md` | 용어집 구조와 현재 탐색 경로 반영 |
| `tasks/plan003-wsaj-wiki-mvp.md` | 대체 표시 추가 |
| `tasks/index.json` | plan003 대체 정보와 plan006 등록 |
| `tasks/plan006-doc-consolidation/index.json` | 완료 상태 반영 |

## 검증

```bash
# cwd: /Users/nhn/personal/finance-skills
python3 scripts/lint_investing_wiki.py
python3 scripts/evaluate_wsaj_brain.py
python3 -m unittest discover -s tests
python3 /Users/nhn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/tenbagger-pick
python3 /Users/nhn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/investing-wiki
python3 /Users/nhn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/wsaj-investing-brain
for file in README.md docs/prd.md docs/flow.md docs/code-architecture.md docs/data-schema.md docs/glossary.md docs/wsaj-corpus.md docs/adr/0004-separate-common-and-expert-glossaries.md wiki/index.md wiki/experts/wsaj/index.md wiki/experts/wsaj/glossary.md tasks/plan003-wsaj-wiki-mvp.md tasks/plan006-doc-consolidation/phase-01.md tasks/plan006-doc-consolidation/phase-02.md; do
  ~/.claude/scripts/korean-style-check.sh "$file"
  python3 ~/.claude/scripts/check-readability.py "$file"
done
! rg -n "docs/(handoff|investing-wiki)\.md|wiki/log\.md" README.md docs scripts skills tests wiki
git diff --check
```

## 의도 메모

- 인계 메모와 수동 Wiki 로그는 Git·task·status 명령과 같은 사실을 다시 적어 부패하기 쉬웠다.
- 과거 task의 경로는 당시 결정을 보여 주므로 삭제하거나 현재 경로로 위장하지 않는다.
- README는 탐색용이며 정책 원본이 아니다.
