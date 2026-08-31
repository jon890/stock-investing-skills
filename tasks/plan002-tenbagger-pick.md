# plan002-tenbagger-pick

## 목적

병목 섹터 안에서 텐베거 후보를 고르고 가치평가로 연결하는 스킬을 만든다.
이 plan 은 `tenbagger-pick` 이 "무엇을 살 후보로 볼 것인가"와 "어떤 값이면 보류할 것인가"를 답하도록 한다.

## 의존 관계

- `plan001-sector-bottleneck`

이 plan 은 `plan001` 이 만드는 병목 진입점과 문서 용어를 전제한다.
`plan001` 이 아직 병합되지 않았으면 최신 base 를 확인하고 멈춘다.

## 소유 파일

- `docs/flow.md`
- `skills/tenbagger-pick/SKILL.md`
- `skills/daily-market-decision/SKILL.md`
- `scripts/bottleneck.py`
- `scripts/valuation.py`
- `scripts/render_report.py`
- `scripts/inputs/*.json`

## 범위

- `tenbagger-pick` 스킬을 새로 만든다.
- 병목 그룹에서 후보를 고르는 조건을 문서와 스킬에 맞춘다.
- 티커 직행 흐름을 `tenbagger-pick` 안에 둔다.
- DCF, 역DCF, 상대가치, 손익비, 3년 텐베거 판정을 하나의 종목 리포트로 연결한다.
- IPO, M&A, 은행, 실적발표 직후를 일반 가치평가와 분리한다.
- `daily-market-decision` 은 deprecated 상태로 돌리거나 얇은 안내 파일로 줄인다.

## 범위 밖

- 섹터 병목 점수 공식 재설계.
- 월가아재 영상 분석과 지식 베이스 구축.
- 자동 매매 주문.

## 완료 기준

- `tenbagger-pick` 은 병목 그룹 입력과 티커 입력을 모두 처리한다.
- 병목 밖 티커는 텐베거 후보가 아니라 참고 가치평가로 표시한다.
- 시총, 성장률, 마진 확대, 기대 분산 기준이 후보 선별에 반영된다.
- 절대가치와 상대가치는 가중평균하지 않는다.
- 손익비가 1 미만이면 상승 여력이 있어도 보류한다.
- 특수 상황은 별도 분기나 보류로 끝난다.

## 검증 명령

```bash
for file in docs/flow.md skills/tenbagger-pick/SKILL.md; do
  ~/.claude/scripts/korean-style-check.sh "$file"
  python3 ~/.claude/scripts/check-readability.py "$file"
done
python3 scripts/valuation.py <TICKER> --json > /tmp/valuation.json
python3 scripts/render_report.py company /tmp/valuation.json -o /tmp/company.html
```

`<TICKER>` 는 `scripts/inputs/` 에 입력 가정이 있는 종목을 사용한다.
실제 입력 파일이 없으면 실행자는 먼저 입력 예시를 추가하고 검증한다.

## 원자 커밋 기준

이 plan 은 종목 선별과 가치평가 연결만 하나의 커밋과 PR로 묶는다.
전체 유튜브 코퍼스나 brain 답변 로직이 섞이면 중단한다.
