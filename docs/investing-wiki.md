# 투자 거장 근거형 Wiki

이 문서는 투자 거장 공개 자료 기반 연구 보조 도구의 사용 경계와 자료 구조를 정리한다.
목표는 실제 인물의 대역을 만드는 것이 아니라, 공개 자료에서 확인한 원칙을 증거 ID와 함께 되찾는 것이다.

## 범위

Wiki의 관리 원본은 `wiki/` 다.
첫 번째 expert 는 월가아재이며 `expert_id` 는 `wsaj` 다.
월가아재 증거는 YouTube 자막이 아니라 로컬에서 처리한 음성 전사와 contact sheet 검토에서 승격한 요약을 쓴다.
영상 코퍼스 처리 현황과 재개 절차는 `docs/wsaj-corpus.md` 에 둔다.

`source_date_status` 는 자료 종류에 맞는 날짜 상태만 쓴다.
영상은 `verified_upload_date`, 책과 글은 `verified_publication_date`, 편지와 공시는 `verified_event_date` 를 쓴다.
그 외 상태의 `source_date` 는 게시일이나 발행일처럼 인용하지 않는다.
`source_observed_at` 은 원자료 분석일이나 확인일로만 쓴다.

| 자료 | 용도 |
| --- | --- |
| `wiki/index.md` | Wiki의 canonical entrypoint 와 expert 목록 |
| `wiki/log.md` | 사람이 유지할 가치가 있는 Wiki 변경 기록 |
| `wiki/experts/<expert_id>/profile.json` | expert 이름, 출처 범위, 답변 금지 조건 |
| `wiki/experts/<expert_id>/index.md` | expert 별 주제 지도 |
| `wiki/experts/<expert_id>/evidence/*.json` | 답변의 증거 단위 |
| `wiki/experts/<expert_id>/pages/*.md` | expert 별 주제 설명 |
| `wiki/concepts/*.md` | 여러 expert 를 연결하는 공통 개념 |
| `docs/glossary.md` | 용어 정의와 오용 주의 |
| `docs/flow.md` | 전체 투자 하네스 흐름 |

`.cache/wsaj-youtube/` 는 원자료 저장소다.
Git에 올리는 답변 근거는 검토된 짧은 claim과 위치 정보로 제한한다.

## 답변 원칙

답변은 결론, 직접 근거, 적용 추론, 반론과 한계, URL이나 문헌 위치 순서로 쓴다.
직접 근거에는 `source_kind` 에 맞는 `source_locator` 를 붙인다.
핵심 문장은 `direct_claim`, `inferred_principle`, `historical_market_fact`, `current_external_data`, `unsupported` 중 하나로 구분한다.

`unsupported` 는 결론으로 쓰지 않는다.
현재 주가, 최신 실적, 지금의 매수와 매도 판단은 공개 자료 근거만으로 답하지 않는다.
이런 질문은 현재 데이터 연결 경계로 넘기고 조회일과 제공자를 남겨야 한다.

인물의 말투를 흉내 내지 않는다.
답변은 “자료에서 확인되는 원칙”과 “하네스가 적용한 추론”을 나눠 쓴다.

## expert 구조

| 경로 | 책임 |
| --- | --- |
| `wiki/experts/wsaj/profile.json` | 월가아재 출처 범위와 답변 정책 |
| `wiki/experts/wsaj/index.md` | 월가아재 Wiki의 주제 지도 |
| `wiki/experts/wsaj/pages/` | 투자 가치관, 가치평가, 기업 사례, 특수 상황 |
| `wiki/experts/wsaj/evidence/` | 검토된 월가아재 증거 JSON |

다른 투자 거장을 추가할 때는 새 `expert_id` 아래 같은 구조를 만든다.
공통 개념은 `wiki/concepts/` 에 둘 수 있지만, 본문은 expert 별 근거를 섞지 않고 출처별로 나눠 쓴다.
`wiki/concepts/` 는 둘 이상 expert 의 직접 근거가 있을 때만 만든다.

## 월가아재 주제 지도

| 문서 | 다루는 질문 | 핵심 증거 |
| --- | --- | --- |
| `wiki/experts/wsaj/pages/investing-values.md` | 투자 가치관, 절제 우위, 손익비 | `wsaj-evidence-000024`, `wsaj-evidence-000026` |
| `wiki/experts/wsaj/pages/valuation-process.md` | 재무제표, 내재가치, 상대가치, 안전마진, Reverse DCF | `wsaj-evidence-000001` 부터 `wsaj-evidence-000014`, `wsaj-evidence-000025`, `wsaj-evidence-000027` 부터 `wsaj-evidence-000029` |
| `wiki/experts/wsaj/pages/company-cases.md` | 엔비디아, 테슬라, 맥도날드 사례 | `wsaj-evidence-000015` 부터 `wsaj-evidence-000019`, `wsaj-evidence-000029` |
| `wiki/experts/wsaj/pages/special-situations.md` | 실적 발표, IPO, M&A, 은행 | `wsaj-evidence-000020` 부터 `wsaj-evidence-000023` |

## 한계

현재 월가아재 코퍼스는 전체 공개 영상 중 처리된 일부에서 승격한 증거만 포함한다.
따라서 Wiki가 말할 수 있는 범위는 검토된 증거가 닿는 곳까지다.

월가아재의 현재 생각, 비공개 판단, 최신 포트폴리오 변화는 이 Wiki가 알 수 없다.
사용자가 최신 종목 판단을 묻는 경우에는 이 Wiki가 원칙을 제공하고, 현재 데이터는 별도 조회로 보강해야 한다.

## 품질 검증

품질 검증은 두 층으로 나눈다.

| 검증 | 확인하는 것 |
| --- | --- |
| `lint_investing_wiki.py` | root/expert index, evidence 필드, 깨진 증거 참조, expert 간 provenance 혼합 |
| 평가 문항 | 필수 증거 검색, 링크와 타임스탬프 정합성, 게시일 상태, 현재 데이터 질문 보류, 근거 부족 질문 거절 |

이 검사는 자유형 LLM 답변의 문장 품질이나 새로운 투자 판단의 정확도를 보증하지 않는다.
실제 답변 품질은 별도 전방 테스트로 확인한다.
