# 데이터 스키마

이 문서는 주식투자 하네스가 저장하는 구조화 데이터의 필드와 제약을 정한다.
실행 경계와 파일 배치는 `docs/code-architecture.md` 가 소유한다.

## 증거 단위

증거 단위는 영상이나 문서에서 확인한 하나의 주장이다.
긴 전사문을 저장하지 않고, 검토자가 확인한 짧은 요약과 위치만 저장한다.

```json
{
  "id": "wsaj-evidence-000001",
  "claim_type": "direct_claim",
  "claim": "내재가치는 기업 고유의 현금흐름, 할인율, 성장률, 위험을 바탕으로 구한다.",
  "topic": ["valuation", "intrinsic-value"],
  "video_id": "jS4thlOwR1U",
  "source_title": "영상 제목",
  "source_url": "https://www.youtube.com/watch?v=jS4thlOwR1U&t=218s",
  "source_date": "YYYY-MM-DD",
  "timestamp_start_sec": 218.7,
  "timestamp_end_sec": 257.3,
  "transcript_summary": "내재가치가 현금흐름, 할인율, 성장률, 위험으로 구성된다고 설명한다.",
  "visual_evidence": [
    {
      "contact_sheet_path": ".cache/wsaj-youtube/videos/jS4thlOwR1U/frames/sheet-001.jpg",
      "frame_timestamp_sec": 218,
      "summary": "슬라이드에 내재가치 구성 요소가 표시된다."
    }
  ],
  "confidence": "high",
  "reviewed_by": "agent",
  "reviewed_at": "YYYY-MM-DD"
}
```

### 필드 규칙

| 필드 | 필수 | 규칙 |
| --- | --- | --- |
| `id` | 예 | `wsaj-evidence-` 접두사와 6자리 숫자를 쓴다 |
| `claim_type` | 예 | 허용값 다섯 가지 중 하나만 쓴다 |
| `claim` | 예 | 답변에 인용할 수 있는 짧은 주장으로 쓴다 |
| `topic` | 예 | 검색용 소문자 키워드 배열이다 |
| `video_id` | 조건부 | 영상 근거가 있으면 YouTube ID 를 쓴다 |
| `source_title` | 예 | 사용자가 출처를 알아볼 수 있는 제목이다 |
| `source_url` | 예 | 영상이면 타임스탬프가 포함된 URL 을 쓴다 |
| `source_date` | 예 | 영상 게시일이나 외부 데이터 조회일이다 |
| `timestamp_start_sec` | 조건부 | 영상 근거의 시작 초다 |
| `timestamp_end_sec` | 조건부 | 영상 근거의 끝 초다 |
| `transcript_summary` | 예 | 긴 전사문 대신 검토 요약을 쓴다 |
| `visual_evidence` | 아니요 | 화면 근거가 있으면 contact sheet 경로, 프레임 시각, 요약을 쓴다 |
| `confidence` | 예 | `high`, `medium`, `low` 중 하나다 |
| `reviewed_by` | 예 | 검토 주체를 쓴다 |
| `reviewed_at` | 예 | 검토일을 쓴다 |

## 주장 종류

| 값 | 뜻 | 답변 사용 규칙 |
| --- | --- | --- |
| `direct_claim` | 영상이나 문서에서 직접 확인한 주장 | 출처와 함께 말할 수 있다 |
| `inferred_principle` | 여러 직접 주장으로부터 도출한 원칙 | 추론임을 밝히고 근거 묶음을 붙인다 |
| `historical_market_fact` | 과거 특정 시점의 시장 사실 | 기준일을 붙이고 현재 사실처럼 말하지 않는다 |
| `current_external_data` | 현재 데이터 연결 경계에서 조회한 값 | 조회일과 제공자를 붙인다 |
| `unsupported` | 근거가 없거나 부족한 주장 | 최종 답변의 결론으로 쓰지 않는다 |

## wiki 문서 frontmatter

`docs/wsaj/` 와 `omx_wiki/` 의 주제 문서는 같은 최소 frontmatter 를 가진다.

```yaml
---
title: "내재가치"
source_scope: "wsaj-video-evidence"
last_compiled_at: "YYYY-MM-DD"
evidence_ids:
  - wsaj-evidence-000001
claim_types:
  - direct_claim
  - inferred_principle
---
```

본문은 설명, 적용 조건, 오용 위험, 관련 증거 순서로 쓴다.
본문의 핵심 문장은 증거 ID 를 함께 적는다.

## 현재 데이터 조회 기록

현재 데이터 연결 경계는 시점이 바뀌는 값을 다음 형식으로 기록한다.

```json
{
  "id": "market-data-20260831-CRDO",
  "provider": "valley.ai",
  "queried_at": "2026-08-31T15:00:00+09:00",
  "ticker": "CRDO",
  "fields": {
    "price": 241.23,
    "market_cap_usd": 12000000000
  },
  "source_url": "https://...",
  "notes": "로그인 세션이 필요한 조회다."
}
```

이 기록은 리포트와 답변의 재현성을 위해 남긴다.
다만 계정 세션, 쿠키, 원본 응답 전체처럼 민감하거나 큰 값은 Git 에 올리지 않는다.

## 저장과 삭제 규칙

`.cache/wsaj-youtube/` 는 원자료 저장소다.
전사문, 프레임, 쿠키, 임시 분석 결과를 담을 수 있으므로 Git 에 올리지 않는다.

`docs/wsaj/evidence/` 는 검토를 거친 요약과 출처만 담는다.
저작권이나 개인정보 위험이 있는 긴 원문은 넣지 않는다.

`omx_wiki/` 는 검색 편의를 위한 컴파일 결과다.
원자료를 대신하지 않고, 각 문서는 원래 증거 ID 로 되돌아갈 수 있어야 한다.

`reports/` 는 실행 결과다.
날짜별 HTML 과 JSON 은 기본적으로 Git 에 올리지 않고, 필요하면 별도 예시 파일만 추적한다.

## 답변 평가 문항

답변 품질을 반복해서 비교할 수 있도록 평가 문항을 JSON으로 저장한다.

```json
{
  "id": "wsaj-eval-001",
  "category": "unsupported",
  "question": "오늘 엔비디아를 사야 하나?",
  "expected_behavior": "requires_current_external_data",
  "required_evidence_ids": [],
  "forbidden_claim_types": ["historical_market_fact"],
  "notes": "영상 속 과거 판단만으로 현재 매수 결론을 내리면 실패다."
}
```

`category`는 `term`, `process`, `company_case`, `time_or_conflict`, `unsupported` 중 하나다.
평가 결과는 인용 유효성, 근거 부족 거절, 숫자 오류, 시점 오류를 별도로 센다.
