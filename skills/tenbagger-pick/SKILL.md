---
name: tenbagger-pick
description: >
  검증된 병목 산업 그룹에서 3년 안에 10배 여지가 남은 종목을 추리고,
  DCF, 역DCF, 상대가치, 손익비, 데이터 출처와 특수 상황 점검으로
  후보 또는 참고 가치평가 판정을 낸다.
  "텐베거", "10배", "종목 발굴", "병목 섹터에서 종목", "이 종목 사도 되나",
  "밸류에이션", "적정주가", "목표주가", "DCF", "상대가치", "tenbagger",
  "valuation report"를 언급하면 이 스킬을 쓴다.
  섹터나 산업만 묻고 종목 판단을 원하지 않으면 sector-bottleneck이 먼저 담당한다.
---

# 텐베거 후보 선정

이 스킬은 검증된 병목 안에서 **무엇을 후보로 볼지** 답한다.
병목을 아직 정하지 않았으면 `sector-bottleneck`을 먼저 실행한다.

목표와 판정 기준은 `docs/prd.md`, 전체 흐름은 `docs/flow.md`,
입력과 출력 형식은 `docs/data-schema.md`가 소유한다.
실행 진입점은 `scripts/tenbagger_pick.py`다.

매매 주문은 넣지 않는다.
분석과 로컬 리포트까지만 만든다.

## 입력을 확인한다

필수 입력은 다음과 같다.

- 미국 시장 유니버스 JSON
- `sector-bottleneck`이 확정한 `bottleneck_context` JSON
- 그룹 코드 또는 티커
- 티커 가치평가를 할 때는 `scripts/inputs/<TICKER>.json`

병목 근거의 `group_code`가 실제 산업 그룹과 다르거나 `duration_years`가 3 이하면
`reference_only`로 끝낸다.

## 병목 그룹에서 후보를 발굴한다

```bash
cd ~/personal/finance-skills
today=$(date +%Y%m%d)
python3 scripts/tenbagger_pick.py "reports/universe-USA-$today.json" \
  --group <GROUP> --context "reports/bottleneck-context-<GROUP>-$today.json" \
  --json --output "reports/candidates-<GROUP>-$today.json"
```

`candidate_pool_status=screenable`일 때만 후보 목록을 다음 단계로 넘긴다.
기본 선별 조건은 다음과 같다.

| 조건 | 판정 |
| --- | --- |
| 시가총액 100억 달러 이하 | 3년 10배 후보로 우선 검토한다 |
| 시가총액 100억 달러 초과, 500억 달러 이하 | 성장과 배수 확대 근거를 더 강하게 본다 |
| 시가총액 500억 달러 초과 | 텐베거 후보에서 제외한다 |
| 매출 성장률 10% 미만 | 병목 수혜 후보에서 제외한다 |
| 마진 확대 없음 | 가격결정력 근거가 약하므로 제외한다 |

그룹 후보 출력은 1차 선별이다.
아직 가치평가 입력과 현재 데이터가 없는 종목을 최종 후보로 부르지 않는다.

## 티커를 역방향으로 검증한다

사용자가 티커를 바로 주면 산업 그룹과 병목 문맥부터 확인한다.

```bash
python3 scripts/tenbagger_pick.py "reports/universe-USA-$today.json" \
  --ticker <TICKER> --context "reports/bottleneck-context-<GROUP>-$today.json" \
  --json --output "reports/tenbagger-<TICKER>-$today.json"
```

다음 중 하나라도 실패하면 `candidate_status=reference_only`로 둔다.

- 산업 그룹이 정량 병목 상위권이 아니다.
- 병목 근거가 다른 그룹을 가리키거나 검증되지 않았다.
- 티커가 시총, 성장률, 마진 확대 조건을 통과하지 못했다.
- 가치평가의 데이터 출처, 상대가치, 특수 상황 또는 텐베거 안전장치가 보류다.

## 가치평가 입력을 준비한다

새 종목은 `scripts/inputs/<TICKER>.json`을 만든다.
기존 종목도 시점이 바뀌는 값은 다시 조회한다.

`data_provenance`에는 다음 값을 둔다.

- `provider`
- timezone을 포함한 `queried_at`
- 비어 있지 않은 `source_urls`
- 조회한 필드 목록 `fields`
- `status=current`

과거 입력에 출처가 남아 있지 않으면 `status=legacy_unavailable`과 보류 사유를 남긴다.
이 상태에서는 계산 결과가 나와도 후보로 승격하지 않는다.

## 가치평가 안전장치를 적용한다

- 절대가치와 상대가치를 평균 내지 않는다.
- 대상 성장률이 동종군 범위 밖이면 해당 상대가치 배수를 버린다.
- 모든 상대가치 배수가 외삽이면 상대가치를 보류한다.
- DCF와 현재가가 크게 다르면 역DCF로 시장 가정을 확인한다.
- 3년 텐베거 판정이 `가능` 또는 `최선 시나리오만`이 아니면 후보로 올리지 않는다.
- 손익비가 약하거나 현재 데이터 출처가 부족하면 보류한다.

## 특수 상황을 먼저 분기한다

IPO, M&A, 은행과 보험, 실적발표 직후, 브랜드 소비재는
[특수 상황](references/special-situations.md)을 먼저 읽는다.

`special_situation.active=true`이면 `type`, `review_status`, `decision`,
`evidence`, `source_urls`를 입력에 둔다.
`review_status=completed`이고 `decision=continue`일 때만 일반 가치평가를 후보 판정에 쓴다.

## HTML 리포트를 만든다

```bash
python3 scripts/render_report.py company "reports/tenbagger-<TICKER>-$today.json" \
  -o "reports/company-<TICKER>-$today.html"
```

리포트 첫 부분에서 다음 내용을 확인한다.

- `candidate`인지 `reference_only`인지
- 산업 그룹, 병목 순위와 근거 검증 상태
- 보류 사유
- 현재 데이터 제공자, 조회 시점과 출처
- 특수 상황 검토 상태

로컬 HTML을 실제로 열어 제목과 오류를 확인한다.

```bash
B=~/.claude/scripts/browser-driver
REPORT_PAGE=$($B open "file://$PWD/reports/company-<TICKER>-$today.html")
$B snap "$REPORT_PAGE"
$B errors "$REPORT_PAGE"
$B close "$REPORT_PAGE"
```

## 결론 형식

1. 병목 안 후보인지, 병목 밖 참고 가치평가인지 적는다.
2. 3년 텐베거 판정과 핵심 가정을 적는다.
3. 절대가치, 상대가치와 손익비를 분리해 적는다.
4. 출처, 특수 상황 또는 계산이 보류라면 부족한 데이터를 적는다.

## 내기 전에 점검할 것

- [ ] 병목 근거가 티커의 실제 산업 그룹과 일치한다
- [ ] 티커가 시총, 성장률과 마진 확대 조건을 통과했다
- [ ] 모든 현재 데이터에 조회 시점과 출처가 있다
- [ ] 상대가치 외삽을 후보 판정에 쓰지 않았다
- [ ] 특수 상황의 완료 상태를 확인했다
- [ ] 3년 텐베거와 손익비가 모두 후보 기준을 통과했다
- [ ] HTML을 실제로 열고 오류를 확인했다
