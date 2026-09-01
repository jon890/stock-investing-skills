# 코드 아키텍처

이 문서는 주식투자 하네스의 실행 경계와 파일 배치를 정한다.
사용자 가치와 범위는 `docs/prd.md` 가 소유하고, 데이터 형식은 `docs/data-schema.md` 가 소유한다.

## 핵심 경계

투자 거장 자료 기반 투자 연구 챗봇은 인물 흉내가 아니라 근거 기반 연구 보조 도구로 둔다.
답변은 영상과 문서에서 확인한 근거, 현재 시장 데이터, 사용자의 분석 요청을 분리해서 처리한다.

| 경계 | 책임 | 쓰기 위치 | 읽기 위치 |
| --- | --- | --- | --- |
| 영상 적재 | 영상 ID, 제목, URL, 음성 전사, 화면 요약을 로컬 원자료로 저장한다 | `.cache/wsaj-youtube/` | 증거 추출기 |
| 증거 저장소 | 원자료에서 짧은 주장 단위와 출처를 뽑아 expert 별로 구조화한다 | `wiki/experts/<expert_id>/evidence/` | wiki 컴파일러, 검색 스크립트 |
| wiki 컴파일 | 증거를 expert 별 주제 문서와 공통 개념 문서로 엮고 출처를 남긴다 | `wiki/experts/<expert_id>/pages/`, `wiki/concepts/` | 답변 스킬 |
| 검색과 답변 | 질문과 관련된 근거를 찾고, 근거가 부족하면 답하지 않는다 | `skills/investing-wiki/` | Codex, Claude Code |
| 호환 진입점 | 기존 월가아재 호출을 새 검색 스크립트로 위임한다 | `skills/wsaj-investing-brain/` | Codex, Claude Code |
| 현재 데이터 연결 | 주가, 배수, 실적 발표, 컨센서스처럼 시점이 바뀌는 값만 새로 조회한다 | `scripts/` 또는 별도 adapter | 답변 스킬 |
| 품질 평가 | 인용, 거절, 숫자와 시점 정확도를 고정 문항으로 검증한다 | `tests/fixtures/`, `tests/` | 배포 전 검증 |

현재 시장 사실은 영상 근거에서 가져오지 않는다.
주가, 시가총액, 실적, 컨센서스, 금리, 환율, 뉴스는 항상 현재 데이터 연결 경계를 통해 조회하고 조회일을 남긴다.

## 디렉터리 책임

| 경로 | 책임 |
| --- | --- |
| `AGENTS.md` | 프로젝트 작업 규칙의 실제 파일이다 |
| `CLAUDE.md` | `AGENTS.md` 를 가리키는 심볼릭 링크다 |
| `skills/` | Claude Code 와 Codex 가 함께 읽는 스킬 원본이다 |
| `.agents/skills` | `skills/` 를 가리키는 Codex 호환 경로다 |
| `.claude/skills` | `skills/` 를 가리키는 Claude Code 호환 경로다 |
| `.cache/wsaj-youtube/` | 영상 원자료, 전사 결과, 프레임, 임시 분석 결과를 둔다 |
| `wiki/index.md` | 투자 Wiki의 canonical entrypoint 와 expert 목록을 둔다 |
| `wiki/log.md` | 사람이 유지할 가치가 있는 Wiki 변경 기록을 둔다 |
| `wiki/experts/<expert_id>/profile.json` | expert 이름, 공개 자료 범위, 금지된 답변 범위를 둔다 |
| `wiki/experts/<expert_id>/index.md` | expert 별 주제 지도와 주요 문서를 둔다 |
| `wiki/experts/<expert_id>/evidence/` | 사람이 검토한 증거 단위를 둔다 |
| `wiki/experts/<expert_id>/pages/` | expert 별 철학, 원칙, 사례, 한계를 사람이 읽는 문서로 둔다 |
| `wiki/concepts/` | 여러 expert 를 연결하는 공통 개념 문서를 둔다 |
| `reports/` | 실행 결과 HTML 과 JSON 리포트를 둔다 |

스킬 원본은 `skills/` 하나만 둔다.
도구별 경로에는 복사본을 만들지 않고 심볼릭 링크만 둔다.
wiki 원본은 `wiki/` 하나만 둔다.
특정 도구 이름이 들어간 경로는 장기 저장 구조로 쓰지 않는다.
`wiki/concepts/` 는 둘 이상 expert 의 근거가 있을 때만 만든다.

## 처리 흐름

영상 분석은 원자료와 해석을 분리한다.
원자료는 `.cache/wsaj-youtube/` 에 두고 Git 에 올리지 않는다.
사람이 검토한 짧은 증거와 요약만 `wiki/experts/<expert_id>/evidence/` 로 승격한다.

답변 스킬은 다음 순서로 동작한다.

1. 질문이 가치관, 개념, 방법론, 종목 분석 중 어디에 속하는지 분류한다.
2. expert 지정이 없으면 검색하지 않고 `expert_required` 상태와 사용 가능한 expert 목록을 반환한다.
3. `wiki/experts/<expert_id>/evidence/` 와 `wiki/experts/<expert_id>/pages/` 에서 관련 근거를 찾는다.
4. 여러 expert 질문이면 expert 별 provenance 를 분리해 찾는다.
5. 공통 개념 문서가 있으면 `wiki/concepts/` 에서 출처별 연결만 보강한다.
6. 현재 시점 값이 필요하면 현재 데이터 연결 경계로 조회한다.
7. 각 문장을 `direct_claim`, `inferred_principle`, `historical_market_fact`, `current_external_data`, `unsupported` 중 하나로 표시한다.
8. `unsupported` 이거나 출처가 부족한 핵심 주장에는 답하지 않는다.

## 답변 규칙

답변 스킬은 “월가아재라면 이렇게 말한다” 같은 인물 대역 표현을 쓰지 않는다.
대신 “자료에서 확인되는 원칙을 적용하면”처럼 근거 적용임을 밝힌다.

근거가 충분한 답변은 자료 제목, URL이나 문헌 위치, `source_locator`, 증거 ID 를 함께 남긴다.
근거가 부족한 답변은 부족한 근거가 무엇인지 말하고, 필요한 추가 조회나 분석을 제안한다.

투자 판단은 주문 실행으로 이어지지 않는다.
하네스는 분석과 의사결정 기록까지만 담당한다.
