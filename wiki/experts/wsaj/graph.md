# 월가아재 투자 Wiki 그래프

이 문서는 현재 Wiki의 정보 구조와 월가아재 자료에서 확인한 투자 원칙의 연결 관계를 보여준다.
그래프의 화살표는 원문의 발언 순서가 아니라, 검토된 증거를 Wiki에서 탐색하기 위한 연결이다.

## 정보 구조

```mermaid
flowchart LR
    ROOT["투자 거장 Wiki"] --> PROFILE["월가아재 프로필<br/>범위·답변 정책"]
    ROOT --> INDEX["월가아재 주제 지도"]
    ROOT --> QUERY["근거 검색<br/>expert_id=wsaj"]

    INDEX --> VALUES["투자 가치관<br/>문서 참조 증거 4개"]
    INDEX --> VALUATION["가치평가 흐름<br/>문서 참조 증거 18개"]
    INDEX --> CASES["기업 사례<br/>문서 참조 증거 6개"]
    INDEX --> SPECIAL["특수 상황<br/>문서 참조 증거 4개"]

    VALUES --> EVIDENCE[("검토 증거 29개")]
    VALUATION --> EVIDENCE
    CASES --> EVIDENCE
    SPECIAL --> EVIDENCE
    QUERY --> EVIDENCE

    EVIDENCE --> SOURCE["YouTube 원문 위치<br/>영상 ID·타임스탬프·URL"]
    EVIDENCE --> LIMIT["적용 한계<br/>현재 데이터 필요·근거 부족"]

    classDef root fill:#172554,color:#fff,stroke:#172554;
    classDef page fill:#dbeafe,color:#172554,stroke:#2563eb;
    classDef evidence fill:#fef3c7,color:#713f12,stroke:#d97706;
    classDef policy fill:#f3e8ff,color:#581c87,stroke:#9333ea;
    class ROOT root;
    class INDEX,VALUES,VALUATION,CASES,SPECIAL page;
    class EVIDENCE,SOURCE evidence;
    class PROFILE,QUERY,LIMIT policy;
```

현재 구조는 `주제 문서 → 증거 ID → 원문 위치`로 내려간다.
주제 문서는 설명과 오용 위험을 제공하고, 증거 JSON은 claim 종류와 출처 위치를 보존한다.

## 현재 존재하는 층과 비어 있는 층

```mermaid
flowchart LR
    EXPERT["expert 근거층<br/>현재 있음"] --> VALUES["월가아재 원칙 요약<br/>현재 있음"]
    VALUES -. "둘 이상 expert 필요" .-> CONCEPTS["공통 개념·차이 비교<br/>설계만 있고 아직 비어 있음"]
    CONCEPTS -. "사용자 선택 필요" .-> PERSONAL["나의 투자 가치관<br/>채택·보류·거부·제약<br/>현재 없음"]
    PERSONAL -. "반복 검증" .-> JOURNAL["판단 기록과 회고<br/>현재 Wiki 범위 밖"]

    classDef ready fill:#dcfce7,color:#14532d,stroke:#16a34a;
    classDef planned fill:#fef3c7,color:#713f12,stroke:#d97706,stroke-dasharray: 5 5;
    classDef missing fill:#fee2e2,color:#7f1d1d,stroke:#dc2626,stroke-dasharray: 5 5;
    class EXPERT,VALUES ready;
    class CONCEPTS planned;
    class PERSONAL,JOURNAL missing;
```

따라서 현재 Wiki는 월가아재의 공개 자료를 공부하고 검증하는 데 적합하다.
하지만 사용자의 위험 감수 수준, 투자 기간, 손실 허용도와 원칙 채택 여부를 기록하지 않으므로, 아직 개인 투자자의 자기 탐색 도구는 아니다.

## 투자 가치관과 가치평가의 연결

```mermaid
flowchart TD
    QUESTION["투자 질문"] --> BEHAVIOR["행동부터 점검"]

    BEHAVIOR --> PROB["확률적 우위"]
    BEHAVIOR --> DISC["절제 우위"]
    BEHAVIOR --> RR["손익비"]
    LEV["물타기·과한 레버리지"] -. "훼손" .-> RR
    PROB --> EXPECTED["장기 기대값을 지키는 판단"]
    DISC --> EXPECTED
    RR --> EXPECTED

    EXPECTED --> FS["재무제표 흐름 확인"]
    FS --> VAL["적정가치 평가"]
    VAL --> INTRINSIC["내재가치"]
    VAL --> RELATIVE["상대가치"]

    INTRINSIC --> DCF["DCF<br/>현금흐름·성장률·할인율·위험"]
    INTRINSIC --> REVERSE["Reverse DCF<br/>현재 가격의 성장 가정 역산"]
    INTRINSIC --> INDEXDCF["인덱스 DCF<br/>시장 기대수익률 점검"]

    RELATIVE --> PEER["유사기업 선정"]
    PEER --> MULTIPLE["PER·PBR·제한적 PSR"]
    MULTIPLE --> DIST["분포·아웃라이어·회계 품질"]
    DIST --> MARKETRISK["비교군 전체 고평가 위험"]

    DCF --> SCENARIO["시나리오·민감도 분석"]
    REVERSE --> SCENARIO
    INDEXDCF --> SCENARIO
    MARKETRISK --> SCENARIO
    SCENARIO --> MOS["불확실성에 맞춘 안전마진"]
    MOS --> DECISION["후보·보류·재평가"]

    classDef value fill:#ffedd5,color:#7c2d12,stroke:#ea580c;
    classDef process fill:#dbeafe,color:#172554,stroke:#2563eb;
    classDef tool fill:#dcfce7,color:#14532d,stroke:#16a34a;
    classDef risk fill:#fee2e2,color:#7f1d1d,stroke:#dc2626;
    classDef result fill:#ede9fe,color:#4c1d95,stroke:#7c3aed;
    class BEHAVIOR,PROB,DISC,RR,EXPECTED value;
    class QUESTION,FS,VAL,INTRINSIC,RELATIVE,PEER,SCENARIO,MOS process;
    class DCF,REVERSE,INDEXDCF,MULTIPLE,DIST tool;
    class LEV,MARKETRISK risk;
    class DECISION result;
```

이 연결의 중심은 가격 예측이 아니라 `기대값과 행동 점검 → 가치평가 → 불확실성 조정`이다.
다만 `확률적 우위`, `절제 우위`, `손익비`를 뒷받침하는 현재 증거는 가치평가 증거보다 적다.
따라서 이 부분은 월가아재의 완결된 투자 철학이 아니라, 현재까지 승격된 근거가 보여주는 잠정 지도다.

## 사례와 예외 경로

```mermaid
flowchart LR
    CORE["일반 가치평가"] --> GROWTH["성장주"]
    CORE --> MODEL["사업모델 중심 기업"]
    CORE --> EVENT["특수 상황"]

    GROWTH --> NVIDIA["엔비디아<br/>DCF·Reverse DCF·민감도"]
    GROWTH --> TESLA["테슬라<br/>희망·절망 시나리오"]
    MODEL --> MCD["맥도날드<br/>프랜차이즈·부동산·자본환원"]

    EVENT --> EARNINGS["실적 발표<br/>컨센서스·가이던스"]
    EVENT --> IPO["IPO<br/>공모 구조·락업"]
    EVENT --> MNA["M&A<br/>성사확률·규제"]
    EVENT --> BANK["은행<br/>예금·유동성·자본비율"]

    NVIDIA --> CURRENT["현재 데이터로 다시 계산"]
    TESLA --> CURRENT
    MCD --> CURRENT
    EARNINGS --> CURRENT
    IPO --> CURRENT
    MNA --> CURRENT
    BANK --> CURRENT

    classDef branch fill:#dbeafe,color:#172554,stroke:#2563eb;
    classDef case fill:#f3e8ff,color:#581c87,stroke:#9333ea;
    classDef boundary fill:#fee2e2,color:#7f1d1d,stroke:#dc2626;
    class CORE,GROWTH,MODEL,EVENT branch;
    class NVIDIA,TESLA,MCD,EARNINGS,IPO,MNA,BANK case;
    class CURRENT boundary;
```

## 근거 묶음

| 탐색 영역 | 증거 ID | 현재 읽을 문서 |
| --- | --- | --- |
| 투자 행동과 가치관 | `wsaj-evidence-000012`, `000013`, `000024`, `000026` | [투자 가치관](pages/investing-values.md) |
| 가치평가 원리와 절차 | `wsaj-evidence-000001`부터 `000014`, `000025`, `000027`부터 `000029` | [가치평가 흐름](pages/valuation-process.md) |
| 실제 기업 적용 | `wsaj-evidence-000015`부터 `000019`, `000029` | [기업 사례](pages/company-cases.md) |
| 사건별 예외 처리 | `wsaj-evidence-000020`부터 `000023` | [특수 상황](pages/special-situations.md) |

증거의 상세 claim과 원문 URL은 [evidence/core.json](evidence/core.json)에서 확인한다.
현재 종목에 적용할 때는 이 그래프만으로 매수와 매도 결론을 내리지 않고, 최신 시장 데이터와 가정 검증을 별도로 붙인다.
