# 데이터 스키마

이 문서는 주식투자 하네스가 저장하는 구조화 데이터의 필드와 제약을 정한다.
실행 경계와 파일 배치는 `docs/code-architecture.md` 가 소유한다.

## 증거 단위

증거 단위는 영상이나 문서에서 확인한 하나의 주장이다.
긴 전사문을 저장하지 않고, 검토자가 확인한 짧은 요약과 위치만 저장한다.

```json
{
  "id": "wsaj-evidence-000001",
  "expert_id": "wsaj",
  "expert_name": "월가아재",
  "corpus_id": "wsaj-youtube-public",
  "source_kind": "youtube_video",
  "claim_type": "direct_claim",
  "claim": "내재가치는 기업 고유의 현금흐름, 할인율, 성장률, 위험을 바탕으로 구한다.",
  "topic": ["valuation", "intrinsic-value"],
  "video_id": "jS4thlOwR1U",
  "source_title": "영상 제목",
  "source_url": "https://www.youtube.com/watch?v=jS4thlOwR1U&t=218s",
  "source_locator": {
    "source_kind": "youtube_video",
    "video_id": "jS4thlOwR1U",
    "timestamp_start_sec": 218.7,
    "timestamp_end_sec": 257.3,
    "url": "https://www.youtube.com/watch?v=jS4thlOwR1U&t=218s"
  },
  "source_date": "YYYY-MM-DD",
  "source_date_status": "verified_upload_date",
  "source_observed_at": "YYYY-MM-DD",
  "timestamp_start_sec": 218.7,
  "timestamp_end_sec": 257.3,
  "source_summary": "내재가치가 현금흐름, 할인율, 성장률, 위험으로 구성된다고 설명한다.",
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
| `id` | 예 | `<expert_id>-evidence-` 접두사와 6자리 숫자를 쓴다 |
| `expert_id` | 예 | 소문자와 숫자, 하이픈만 쓰는 expert 식별자다 |
| `expert_name` | 예 | 사용자가 출처를 알아볼 수 있는 이름이다 |
| `corpus_id` | 예 | 같은 expert 안에서 원자료 묶음을 구분한다 |
| `source_kind` | 예 | `youtube_video`, `book`, `letter`, `article`, `interview`, `filing`, `other` 중 하나다 |
| `claim_type` | 예 | 허용값 다섯 가지 중 하나만 쓴다 |
| `claim` | 예 | 답변에 인용할 수 있는 짧은 주장으로 쓴다 |
| `topic` | 예 | 검색용 소문자 키워드 배열이다 |
| `video_id` | 조건부 | 영상 근거가 있으면 YouTube ID 를 쓴다 |
| `source_title` | 예 | 사용자가 출처를 알아볼 수 있는 제목이다 |
| `source_url` | 예 | 원자료 위치를 확인할 수 있는 URL 이다 |
| `source_locator` | 예 | 원자료 안에서 해당 주장을 다시 찾는 위치 객체다 |
| `source_date` | 예 | 검증한 게시일, 발행일, 사건일, 외부 데이터 조회일이다 |
| `source_date_status` | 예 | `verified_upload_date`, `verified_publication_date`, `verified_event_date`, `unavailable` 중 하나다 |
| `source_observed_at` | 예 | 원자료를 확인하거나 분석한 날짜다 |
| `timestamp_start_sec` | 조건부 | 영상 근거의 시작 초다 |
| `timestamp_end_sec` | 조건부 | 영상 근거의 끝 초다 |
| `source_summary` | 예 | 원자료 종류와 관계없이 긴 원문 대신 검토 요약을 쓴다 |
| `transcript_summary` | 조건부 | 기존 WSAJ 영상 평가와 호환할 때 `source_summary` 와 같은 요약을 쓴다 |
| `visual_evidence` | 아니요 | 화면 근거가 있으면 contact sheet 경로, 프레임 시각, 요약을 쓴다 |
| `confidence` | 예 | `high`, `medium`, `low` 중 하나다 |
| `reviewed_by` | 예 | 검토 주체를 쓴다 |
| `reviewed_at` | 예 | 검토일을 쓴다 |

`video_id`, `timestamp_start_sec`, `timestamp_end_sec`, `transcript_summary` 는 기존 WSAJ 평가와 호환을 위해 유지할 수 있다.
새 구현은 `source_locator` 와 `source_summary` 를 기준으로 검증하고, 호환 필드는 두 공통 필드와 같은 값을 가져야 한다.

### source locator

`source_locator` 는 원자료 안에서 해당 주장을 다시 찾는 공통 위치 객체다.
모든 locator 는 `source_kind` 를 가진다.
`source_kind` 값은 증거 단위의 최상위 `source_kind` 와 같아야 한다.

| `source_kind` | 필수 locator 필드 | 선택 locator 필드 |
| --- | --- | --- |
| `youtube_video` | `video_id`, `timestamp_start_sec`, `timestamp_end_sec`, `url` | `channel_id`, `playlist_id`, `frame_timestamp_sec` |
| `book` | `title`, `page` 또는 `chapter` | `edition`, `isbn`, `publisher`, `url` |
| `letter` | `author`, `date` | `page`, `section`, `recipient`, `url` |
| `article` | `title`, `publication`, `publication_date`, `url` | `section`, `author` |
| `interview` | `interviewee`, `event_date` 또는 `publication_date` | `timestamp_start_sec`, `timestamp_end_sec`, `url`, `host` |
| `filing` | `issuer`, `filing_type`, `filing_date` | `accession_number`, `section`, `page`, `url` |
| `other` | `description`, `date` 또는 `url` | `section`, `page`, `note` |

`youtube_video` 는 `timestamp_start_sec` 가 `timestamp_end_sec` 보다 작아야 한다.
URL 이 있으면 YouTube 영상 ID와 타임스탬프를 함께 확인할 수 있어야 한다.
YouTube가 아닌 자료는 `video_id` 를 쓰지 않는다.

`source_date_status` 의 의미는 다음과 같다.

| 값 | 의미 | 사용 규칙 |
| --- | --- | --- |
| `verified_upload_date` | 영상 게시일을 확인했다 | `youtube_video` 에 쓴다 |
| `verified_publication_date` | 책, 글, 인터뷰 공개일을 확인했다 | `book`, `article`, `interview`, `other` 에 쓴다 |
| `verified_event_date` | 편지, 인터뷰, 공시 같은 사건 날짜를 확인했다 | `letter`, `interview`, `filing`, `other` 에 쓴다 |
| `unavailable` | 공개 날짜를 확인하지 못했다 | `source_date_unavailable_reason` 을 함께 쓴다 |

분석일을 게시일, 발행일, 사건일 대신 넣지 않는다.

## 주장 종류

| 값 | 뜻 | 답변 사용 규칙 |
| --- | --- | --- |
| `direct_claim` | 영상이나 문서에서 직접 확인한 주장 | 출처와 함께 말할 수 있다 |
| `inferred_principle` | 여러 직접 주장으로부터 도출한 원칙 | 추론임을 밝히고 근거 묶음을 붙인다 |
| `historical_market_fact` | 과거 특정 시점의 시장 사실 | 기준일을 붙이고 현재 사실처럼 말하지 않는다 |
| `current_external_data` | 현재 데이터 연결 경계에서 조회한 값 | 조회일과 제공자를 붙인다 |
| `unsupported` | 근거가 없거나 부족한 주장 | 최종 답변의 결론으로 쓰지 않는다 |

## expert 프로필

각 expert 는 `wiki/experts/<expert_id>/profile.json` 을 가진다.

```json
{
  "expert_id": "wsaj",
  "expert_name": "월가아재",
  "default_corpus_id": "wsaj-youtube-public",
  "source_scope": "public-youtube",
  "language": "ko",
  "persona_policy": "no_impersonation",
  "current_data_policy": "external_lookup_required",
  "created_at": "YYYY-MM-DD",
  "updated_at": "YYYY-MM-DD"
}
```

`profile.json` 은 인물의 성격을 재현하기 위한 파일이 아니다.
검색 범위, 출처 범위, 답변 금지 조건을 고정하는 설정 파일이다.

## wiki 문서 frontmatter

`wiki/experts/<expert_id>/index.md`, `wiki/experts/<expert_id>/pages/*.md`, `wiki/concepts/*.md` 의 주제 문서는 같은 최소 frontmatter 를 가진다.

```yaml
---
title: "내재가치"
expert_id: "wsaj"
source_scope: "public-youtube"
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
`wiki/concepts/` 문서는 여러 expert 의 `evidence_ids` 를 함께 가질 수 있다.
이때 본문은 출처별 견해를 병렬로 제시하고, 한 expert 의 판단을 다른 expert 의 판단처럼 합치지 않는다.

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

`wiki/experts/<expert_id>/evidence/` 는 검토를 거친 요약과 출처만 담는다.
저작권이나 개인정보 위험이 있는 긴 원문은 넣지 않는다.

`wiki/` 는 도구와 무관한 관리 원본이다.
OMX, Codex, Claude Code 중 어느 도구를 쓰더라도 같은 `wiki/` 를 읽는다.
특정 도구 이름이 들어간 별도 wiki 경로는 원본으로 쓰지 않는다.

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
