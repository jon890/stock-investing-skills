# 투자 거장 Wiki

이 Wiki는 투자 거장 공개 자료에서 확인한 원칙을 expert 별 증거 ID와 함께 관리하는 저장소다.
특정 도구의 산출물이 아니라 Codex, Claude Code, 일반 스크립트가 함께 읽는 원본이다.

## expert 목록

| expert | 범위 | 진입점 |
| --- | --- | --- |
| [월가아재](experts/wsaj/index.md) | 공개 YouTube 영상에서 검토한 투자 철학, 용어, 가치평가 흐름, 사례. [그래프 보기](experts/wsaj/graph.md), [용어집](experts/wsaj/glossary.md) | `expert_id=wsaj` |

## 구조

| 경로 | 역할 |
| --- | --- |
| `experts/<expert_id>/profile.json` | expert 이름, 자료 범위, 답변 정책 |
| `experts/<expert_id>/index.md` | expert 별 주제 지도 |
| `experts/<expert_id>/glossary.md` | expert 별 용어 사용과 강조점 |
| `experts/<expert_id>/pages/*.md` | expert 별 주제 문서 |
| `experts/<expert_id>/evidence/*.json` | 답변에 쓸 수 있는 검토 증거 |
| `concepts/*.md` | 둘 이상 expert 의 근거가 모였을 때만 만드는 공통 개념 |

## 새 expert 추가 최소 계약

새 투자 거장을 추가할 때는 최소한 다음 파일을 만든다.

1. `experts/<expert_id>/profile.json`
2. `experts/<expert_id>/index.md`
3. `experts/<expert_id>/evidence/*.json`

`expert_id` 는 소문자, 숫자, 하이픈만 쓴다.
증거 ID는 `<expert_id>-evidence-000001` 형식을 쓴다.
모든 증거는 `source_kind`, `source_locator`, `source_summary`, `source_date_status`, `source_observed_at` 을 가진다.

`concepts/` 문서는 둘 이상 expert 의 직접 근거가 있을 때만 만든다.
한 expert 의 원칙을 공통 개념처럼 먼저 만들지 않는다.

## 검증

구조를 바꾼 뒤에는 다음 명령으로 Wiki 자체를 검증한다.

```bash
python3 scripts/lint_investing_wiki.py
```
