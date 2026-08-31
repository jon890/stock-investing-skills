# plan001-sector-bottleneck

## 목적

섹터 히트맵에서 가치사슬 병목을 찾는 진입점을 독립된 스킬로 고정한다.
이 plan 은 `sector-bottleneck` 이 "어느 섹터나 산업 그룹이 병목인가"만 답하도록 정리한다.

## 배경

현재 제품 기준은 3년 안에 10배가 될 수 있는 종목 발굴이다.
병목 판정은 현재 `scripts/bottleneck.py` 의 다섯 팩터를 따른다.

| 팩터 | 가중치 |
| --- | --- |
| 수요 수준 | 28% |
| 가격결정력 | 22% |
| 미반영 여지 | 30% |
| 기대 분산 | 12% |
| 자금 집중 | 8% |

## 의존 관계

없다.
현재 `origin/main` 기준으로 실행할 수 있어야 한다.

## 소유 파일

- `docs/prd.md`
- `docs/flow.md`
- `skills/sector-bottleneck/SKILL.md`
- `scripts/bottleneck.py`
- `scripts/fetch_universe.sh`
- `scripts/render_report.py`

## 범위

- `sector-bottleneck` 스킬 설명을 병목 판정 전용으로 맞춘다.
- 스킬, 문서, 리포트 문구가 모두 다섯 팩터를 말하게 한다.
- 섹터 히트맵 수집, 결측 진단, 로그인 만료, 빈 데이터 흐름을 문서와 출력에 맞춘다.
- 병목 그룹을 `tenbagger-pick` 으로 넘길 때 필요한 값인 그룹 코드, 유니버스 파일, 병목 실체, 결측 진단을 명시한다.

## 범위 밖

- 종목 단위 가치평가 구현.
- 월가아재 연구 보조자 구현.
- `daily-market-decision` 삭제.

## 완료 기준

- `sector-bottleneck` 은 개별 종목 매수 판단을 하지 않는다.
- 문서와 스킬에 2년 텐베거 기준이 남아 있지 않다.
- 문서와 스킬이 현재 병목 다섯 팩터와 충돌하지 않는다.
- 리포트는 상위 병목 그룹, 팩터별 근거, 결측 진단, 다음 실행 경로를 보여 준다.
- 데이터 실패 시 점수를 억지로 만들지 않고 중단 사유를 남긴다.

## 검증 명령

```bash
for file in docs/prd.md docs/flow.md skills/sector-bottleneck/SKILL.md; do
  ~/.claude/scripts/korean-style-check.sh "$file"
  python3 ~/.claude/scripts/check-readability.py "$file"
done
python3 scripts/bottleneck.py reports/universe-USA-<YYYYMMDD>.json --json > /tmp/bottleneck-USA.json
python3 scripts/bottleneck.py reports/universe-KOR-<YYYYMMDD>.json --json > /tmp/bottleneck-KOR.json
python3 scripts/render_report.py bottleneck /tmp/bottleneck-USA.json /tmp/bottleneck-KOR.json \
  <YYYY-MM-DD> -o /tmp/bottleneck.html
```

유니버스 JSON 은 실제 valley 수집 결과를 사용한다.
로그인 세션이 없으면 실행자는 수집 검증을 보류하고 그 사유를 커밋 메시지나 PR 본문에 적는다.

## 원자 커밋 기준

이 plan 은 섹터 병목 진입점만 하나의 커밋과 PR로 묶는다.
종목 선별이나 월가아재 코퍼스 변경이 섞이면 중단한다.
