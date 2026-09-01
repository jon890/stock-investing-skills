# 월가아재 근거형 Wiki

이 문서는 월가아재 공개 영상 기반 연구 보조 도구의 사용 경계와 자료 구조를 정리한다.
목표는 실제 인물의 대역을 만드는 것이 아니라, 공개 영상에서 확인한 원칙을 증거 ID와 함께 되찾는 것이다.

## 범위

현재 Wiki는 `docs/wsaj/evidence/core.json` 에 검토된 29개 증거를 단일 소스로 삼는다.
이 증거는 YouTube 자막이 아니라 로컬에서 처리한 음성 전사와 contact sheet 검토에서 승격한 요약이다.
영상 코퍼스 처리 현황과 재개 절차는 `docs/wsaj-corpus.md` 에 둔다.
`source_date_status` 가 `verified_upload_date` 인 증거는 `source_date` 를 영상 게시일로 쓸 수 있다.
그 외 상태의 `source_date` 는 게시일처럼 인용하지 않는다.
`source_observed_at` 은 원자료 분석일이나 확인일로만 쓴다.

| 자료 | 용도 |
| --- | --- |
| `docs/wsaj/evidence/core.json` | 답변의 증거 단위 |
| `docs/wsaj/*.md` | 사람이 읽는 주제별 설명 |
| `omx_wiki/*.md` | 키워드 검색용 Wiki 페이지 |
| `docs/glossary.md` | 용어 정의와 오용 주의 |
| `docs/flow.md` | 전체 투자 하네스 흐름 |

`.cache/wsaj-youtube/` 는 원자료 저장소다.
Git에 올리는 답변 근거는 검토된 짧은 claim과 위치 정보로 제한한다.

## 답변 원칙

답변은 결론, 직접 근거, 적용 추론, 반론과 한계, 영상 링크와 타임스탬프 순서로 쓴다.
핵심 문장은 `direct_claim`, `inferred_principle`, `historical_market_fact`, `current_external_data`, `unsupported` 중 하나로 구분한다.

`unsupported` 는 결론으로 쓰지 않는다.
현재 주가, 최신 실적, 지금의 매수와 매도 판단은 영상 근거만으로 답하지 않는다.
이런 질문은 현재 데이터 연결 경계로 넘기고 조회일과 제공자를 남겨야 한다.

## 주제 지도

| 문서 | 다루는 질문 | 핵심 증거 |
| --- | --- | --- |
| `docs/wsaj/investing-values.md` | 투자 가치관, 절제 우위, 손익비 | `wsaj-evidence-000024`, `wsaj-evidence-000026` |
| `docs/wsaj/valuation-process.md` | 재무제표, 내재가치, 상대가치, 안전마진, Reverse DCF | `wsaj-evidence-000001` 부터 `wsaj-evidence-000014`, `wsaj-evidence-000025`, `wsaj-evidence-000027` 부터 `wsaj-evidence-000029` |
| `docs/wsaj/company-cases.md` | 엔비디아, 테슬라, 맥도날드 사례 | `wsaj-evidence-000015` 부터 `wsaj-evidence-000019`, `wsaj-evidence-000029` |
| `docs/wsaj/special-situations.md` | 실적 발표, IPO, M&A, 은행 | `wsaj-evidence-000020` 부터 `wsaj-evidence-000023` |

## 한계

현재 코퍼스는 전체 495개 영상 중 처리된 일부에서 승격한 증거만 포함한다.
따라서 Wiki가 말할 수 있는 범위는 검토된 증거가 닿는 곳까지다.

월가아재의 현재 생각, 비공개 판단, 최신 포트폴리오 변화는 이 Wiki가 알 수 없다.
사용자가 최신 종목 판단을 묻는 경우에는 이 Wiki가 원칙을 제공하고, 현재 데이터는 별도 조회로 보강해야 한다.

## 품질 검증

다음 명령은 50개 고정 질문으로 증거 검색과 거절 정책을 검사한다.

```bash
python3 scripts/evaluate_wsaj_brain.py
```

평가 범위는 필수 증거 검색, 영상 링크와 타임스탬프 정합성, 게시일 상태, 현재 데이터 질문 보류, 근거 부족 질문 거절이다.
이 검사는 자유형 LLM 답변의 문장 품질이나 새로운 투자 판단의 정확도를 보증하지 않는다.
실제 답변 품질은 별도 전방 테스트로 확인한다.
