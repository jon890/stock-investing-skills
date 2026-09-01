---
name: sector-bottleneck
description: >
  시장 전 종목의 기간별 등락과 밸류에이션 배수를 받아
  어느 산업 그룹이 가치사슬의 병목인지 다섯 팩터로 점수화하고,
  공급 제약과 지속 기간을 출처로 확인해 로컬 HTML 리포트를 만든다.
  "병목", "어느 섹터", "어느 산업", "섹터 히트맵", "히트맵", "섹터 선정",
  "오늘 장", "시황", "시장 훑어줘", "어디가 좋나", "산업 그룹 점수",
  "bottleneck", "sector heatmap"을 언급하면 이 스킬을 쓴다.
  종목 후보 선별과 가치평가는 tenbagger-pick이 담당한다.
  매매 주문은 넣지 않는다.
---

# 병목 섹터 선정

이 스킬은 **어디를 볼지**까지만 답한다.
개별 종목 후보를 출력하지 않고 검증된 `bottleneck_context`를 다음 스킬에 넘긴다.

목표와 팩터 기준은 `docs/prd.md`, 전체 흐름은 `docs/flow.md`가 소유한다.
valley 수집을 실행할 때는 [valley 데이터 수집](references/valley-data.md)을 읽는다.

## 준비

```bash
B=~/.claude/scripts/browser-driver
PAGE=$($B open "https://www.valley.town/markets/sector-heatmap" 30000)
$B url "$PAGE"
```

주소가 로그인 화면이면 중단하고 사용자에게 로그인을 요청한다.

## 유니버스를 수집한다

```bash
cd ~/personal/finance-skills
today=$(date +%Y%m%d)
scripts/fetch_universe.sh "$PAGE" USA "reports/universe-USA-$today.json"
scripts/fetch_universe.sh "$PAGE" KOR "reports/universe-KOR-$today.json"
```

같은 날 파일이 있으면 기본적으로 다시 받지 않는다.
수집 결과의 종목 수와 기간 수익률, 배수 결측 개수를 확인한다.

## 정량 병목을 계산한다

```bash
python3 scripts/bottleneck.py "reports/universe-USA-$today.json" \
  --json --output "reports/bottleneck-USA-$today.json"
python3 scripts/bottleneck.py "reports/universe-USA-$today.json"
```

상위 세 그룹만 질적 검증 대상으로 삼는다.
다음 조건을 하나라도 통과하지 못하면 다음 순위로 내려간다.

- 수요 수준과 가격결정력 표준점수가 모두 양수다.
- 팩터별 관측률이 70% 이상이다.
- 기간 수익률 커버리지가 98% 이상이다.
- 최근 흐름이 병목 해소 신호를 보이지 않는다.
- 대표 종목이 한 가지 공급 제약으로 설명된다.

## 병목의 실체를 확인한다

상위 그룹의 대표 종목과 가치사슬을 현재 공개 자료로 검색한다.
다음 질문에 모두 답한다.

- 무엇이 공급을 제약하는가.
- 제약이 3년을 넘겨 유지되는가.
- 누가 제약을 통제하고 가격결정력을 갖는가.

병목 근거 파일은 템플릿에서 만든다.

```bash
cp skills/sector-bottleneck/assets/bottleneck-basis.template.json \
  "reports/bottleneck-basis-<GROUP>-$today.json"
```

`group_code`는 점수를 낸 그룹과 같아야 한다.
`reviewed_at`과 각 출처의 `observed_at`은 실제 확인일을 쓴다.
`duration_years`는 3보다 커야 한다.
모든 조건을 확인했을 때만 `verdict`를 `pass`로 바꾼다.

## 전달 문맥을 확정한다

```bash
python3 scripts/bottleneck.py "reports/universe-USA-$today.json" \
  --group <GROUP> --basis "reports/bottleneck-basis-<GROUP>-$today.json" \
  --json --output "reports/bottleneck-context-<GROUP>-$today.json"
```

출력의 `candidate_pool_passed`가 `true`일 때만 `tenbagger-pick`으로 넘긴다.
`false`이면 누락 필드와 실패 조건을 리포트에 남기고 종목 후보를 만들지 않는다.

## 한국 시장을 선택적으로 계산한다

```bash
python3 scripts/bottleneck.py "reports/universe-KOR-$today.json" \
  --json --output "reports/bottleneck-KOR-$today.json"
```

데이터 품질 검사에서 실패하면 한국 결과를 억지로 만들지 않는다.
미국 종목 선별은 계속할 수 있으며 HTML에서 한국 시장을 생략한다.

## HTML 리포트를 만든다

한국 결과가 없으면 다음 명령을 쓴다.

```bash
python3 scripts/render_report.py bottleneck "reports/bottleneck-USA-$today.json" \
  --context "reports/bottleneck-context-<GROUP>-$today.json" \
  --asof "$(date +%Y-%m-%d)" -o "reports/bottleneck-$today.html"
```

한국 결과가 유효하면 `--kor "reports/bottleneck-KOR-$today.json"`을 추가한다.

리포트에는 정량 순위, 데이터 품질, 공급 제약, 지속 기간, 통제 주체와 출처를 표시한다.
종목 후보 목록은 표시하지 않는다.

로컬 HTML을 실제로 열어 제목과 오류를 확인한다.

```bash
REPORT_PAGE=$($B open "file://$PWD/reports/bottleneck-$today.html")
$B snap "$REPORT_PAGE"
$B errors "$REPORT_PAGE"
$B close "$REPORT_PAGE"
```

## 다음 단계로 넘긴다

다음 값만 `tenbagger-pick`에 넘긴다.

- 유니버스 JSON 경로
- 그룹 코드
- `bottleneck_context` JSON 경로

병목 리포트는 사용자가 근거를 확인하는 산출물이며 다음 스킬의 입력은 아니다.

## 내기 전에 점검할 것

- [ ] 기간 수익률과 팩터 관측률 기준을 통과했다
- [ ] 수요 수준과 가격결정력이 모두 양수다
- [ ] 병목 근거가 점수를 낸 그룹과 묶여 있다
- [ ] 제약이 3년을 넘겨 유지된다
- [ ] 모든 출처에 제목, 위치와 확인일이 있다
- [ ] 종목 후보를 이 스킬에서 출력하지 않았다
- [ ] HTML을 실제로 열고 오류를 확인했다
