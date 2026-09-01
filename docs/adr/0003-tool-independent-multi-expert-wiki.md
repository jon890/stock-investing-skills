# ADR: 투자 Wiki를 도구와 독립된 다중 expert 구조로 둔다

## 상태

채택.

## 배경

기존 월가아재 Wiki는 `omx_wiki/` 를 검색용 저장 위치로 썼다.
이 이름은 OMX를 쓰지 않는 상황에서도 유지해야 할 지식 원본에 특정 도구 이름을 새긴다.
또 사용자는 월가아재뿐 아니라 다른 투자 거장도 같은 방식으로 분석해 Wiki로 관리하고 싶어한다.

[ADR-0001](0001-evidence-backed-wsaj-wiki.md) 은 인물 모사가 아니라 근거형 연구 보조 도구를 만든다고 결정했다.
이번 결정은 그 원칙을 유지하면서 저장 범위를 월가아재 전용 구조에서 다중 expert 구조로 확장한다.

## 결정

Wiki의 관리 원본은 `wiki/` 로 둔다.
각 expert 는 `wiki/experts/<expert_id>/` 아래에 프로필, 인덱스, 주제 문서, 증거를 가진다.
월가아재는 `expert_id=wsaj` 로 이전한다.

공통 개념은 선택적으로 `wiki/concepts/` 에 둔다.
공통 개념 문서는 여러 expert 의 증거를 연결할 수 있지만, provenance 를 섞지 않고 출처별 판단을 병렬로 제시한다.

검색 진입점은 범용 `investing-wiki` 로 둔다.
기존 `wsaj-investing-brain` 과 `query_wsaj_wiki.py` 는 월가아재 호환 진입점으로 남기고, 내부에서는 `expert_id=wsaj` 를 지정한 범용 검색으로 위임한다.

## 대안

| 대안 | 판단 |
| --- | --- |
| `omx_wiki/` 를 계속 관리 원본으로 사용 | 기각. 특정 도구를 쓰지 않을 때도 장기 지식 구조가 도구 이름에 묶인다 |
| expert 별로 전혀 다른 디렉터리와 검색기를 둠 | 기각. 인물마다 검증 기준이 갈라지고 공통 개념을 연결하기 어렵다 |
| `wiki/experts/` 와 `wiki/concepts/` 로 분리 | 채택. 인물별 출처를 분리하면서 공통 개념을 확장할 수 있다 |

## 결과

새로운 Wiki 구조는 OMX 없이도 유지된다.
Codex, Claude Code, OMX는 같은 `wiki/` 원본을 읽는다.
`omx_wiki/` 는 더 이상 장기 저장 구조가 아니며, 필요하면 일시적인 도구 산출물로만 취급한다.

증거 단위에는 `expert_id`, `expert_name`, `corpus_id`, `source_kind` 를 추가한다.
이 필드는 나중에 다른 투자 거장을 추가할 때 출처가 섞이는 문제를 막는다.

## 검증 조건

1. `wiki/experts/wsaj/` 아래에서 기존 월가아재 증거와 주제 문서를 찾을 수 있다.
2. `omx_wiki/` 를 읽지 않아도 검색과 답변 평가가 동작한다.
3. `investing-wiki` 는 `--expert wsaj` 로 월가아재 근거를 검색한다.
4. `wsaj-investing-brain` 과 `query_wsaj_wiki.py` 는 호환 진입점으로 유지된다.
5. `lint_investing_wiki.py` 는 expert 프로필, evidence 필드, 깨진 증거 참조, provenance 혼합을 검사한다.
