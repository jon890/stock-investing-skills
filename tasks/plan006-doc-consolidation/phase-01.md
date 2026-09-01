# Phase 01: 용어집 경계와 핵심 문서 정합성 확립

**Execution profile**: standard

---

## 목표

투자 공통 용어와 월가아재 용례를 분리하고, 핵심 문서와 실제 profile·Wiki·가치평가 구조를 일치시킨다.

**범위 외**: 새 expert 자료 수집, 월가아재 증거 추가, 투자 계산식 변경, 외부 데이터 조회 방식 변경은 이 phase의 책임이 아니다.

---

## 작업 항목 (5)

### 1. `docs/glossary.md`: 투자 공통 용어집으로 재작성

특정 인물의 영상 ID와 해석을 제거한다.
용어, 일반 정의, 계산이나 지표, 적용 범위, 오용 주의를 설명한다.
`tenbagger-pick` 같은 일반 스킬이 특정 expert 자료에 의존하지 않고 읽을 수 있어야 한다.

### 2. `wiki/experts/wsaj/glossary.md`: 월가아재 용어집 생성

기존 용어집의 월가아재 표현과 영상에서 강조한 일반 금융 용어를 옮긴다.
각 항목은 자료에서 확인한 의미, 적용 맥락, 오용 위험, evidence ID나 영상 위치를 가진다.
같은 용어가 공통 용어집에 있더라도 일반 정의를 복제하지 않고 월가아재 자료의 강조점만 설명한다.

`wiki/experts/wsaj/profile.json` 의 `paths.glossary` 와 expert 인덱스를 새 경로에 연결한다.

### 3. 스킬 읽기 경로 정리

`tenbagger-pick` 은 공통 용어집만 일반 정의의 원본으로 읽는다.
`investing-wiki` 는 일반 뜻과 expert 별 용례를 구분해 읽는다.
`wsaj-investing-brain` 은 `wiki/experts/wsaj/glossary.md` 와 증거 저장소를 월가아재 용례의 원본으로 읽고, 제거 예정인 `docs/investing-wiki.md` 에 의존하지 않는다.

스킬 변경 뒤 세 스킬을 `quick_validate.py` 로 검증한다.

### 4. Wiki 구조 검증 보강

`profile.json` 에 `paths.glossary` 가 있으면 해당 파일이 실제 expert 디렉터리 안에 존재하는지 `lint_investing_wiki.py` 가 검사한다.
경로가 없거나 expert 디렉터리 밖을 가리키는 부정 테스트를 추가한다.
expert 용어집이 선택 사항이라는 계약은 유지한다.

### 5. 핵심 문서와 ADR 정합성 확인

`docs/prd.md`, `docs/flow.md`, `docs/code-architecture.md`, `docs/data-schema.md` 가 다음 실제 상태를 설명해야 한다.

- DCF 명시 예측 기본값은 5년이다.
- `profile.json` 은 실제 `answer_policy`, `paths` 구조를 쓴다.
- expert 인덱스와 용어집에는 frontmatter를 강제하지 않는다.
- 유니버스, 병목 결과, 가치평가 입력과 결과의 소유 위치가 드러난다.
- Wiki 문서는 자동 컴파일 결과가 아니라 검토자가 편집하는 관리 원본이다.

용어집 분리 결정은 `docs/adr/0004-separate-common-and-expert-glossaries.md` 에 남긴다.

## Critical Files

| 파일 | 변경 |
| --- | --- |
| `docs/glossary.md` | 공통 용어집으로 재작성 |
| `wiki/experts/wsaj/glossary.md` | 신규 |
| `wiki/experts/wsaj/profile.json` | `paths.glossary` 추가 |
| `wiki/experts/wsaj/index.md` | 용어집 링크 추가 |
| `skills/tenbagger-pick/SKILL.md` | 공통 용어집 책임 명시 |
| `skills/investing-wiki/SKILL.md` | 공통·expert 용어 조회 경계 추가 |
| `skills/wsaj-investing-brain/SKILL.md` | 새 월가아재 용어집 경로 적용 |
| `scripts/lint_investing_wiki.py` | 선택 glossary 경로 검증 추가 |
| `tests/test_investing_wiki_lint.py` | glossary 경로 회귀 추가 |
| `docs/prd.md` | 제품 원칙 보완 |
| `docs/flow.md` | 용어 조회 흐름 보완 |
| `docs/code-architecture.md` | 실제 편집·경로 책임 반영 |
| `docs/data-schema.md` | 실제 스키마와 구조화 산출물 반영 |
| `docs/adr/0004-separate-common-and-expert-glossaries.md` | 결정 기록 신규 |

## 검증

```bash
# cwd: /Users/nhn/personal/finance-skills
python3 scripts/lint_investing_wiki.py
python3 -m unittest -v tests/test_investing_wiki_lint.py tests/test_wsaj_wiki.py tests/test_wsaj_brain.py
python3 /Users/nhn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/tenbagger-pick
python3 /Users/nhn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/investing-wiki
python3 /Users/nhn/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/wsaj-investing-brain
for file in docs/prd.md docs/flow.md docs/code-architecture.md docs/data-schema.md docs/glossary.md docs/adr/0004-separate-common-and-expert-glossaries.md wiki/experts/wsaj/glossary.md wiki/experts/wsaj/index.md skills/tenbagger-pick/SKILL.md skills/investing-wiki/SKILL.md skills/wsaj-investing-brain/SKILL.md; do
  ~/.claude/scripts/korean-style-check.sh "$file"
  python3 ~/.claude/scripts/check-readability.py "$file"
done
```

## 의도 메모

- 공통 용어집과 expert 용어집은 같은 단어를 담을 수 있지만 책임이 다르다.
- profile 의 glossary 경로는 선택 사항이므로 고유 용어가 없는 expert 에 빈 파일을 강요하지 않는다.
- 기존 문서를 지우기 전에 새 경로와 스킬 참조를 먼저 검증한다.
