# stock-investing-skills

금융 투자를 위한 개인 의사결정 하네스다.
제품 목표와 범위는 `docs/prd.md`, 실행 순서는 `docs/flow.md`,
코드 책임은 `docs/code-architecture.md`, 데이터 계약은 `docs/data-schema.md`가 소유한다.

## 두 투자 스킬의 경계

- `sector-bottleneck`은 산업 그룹과 병목 근거까지만 판정한다.
- `tenbagger-pick`은 검증된 `bottleneck_context` 안에서 종목 후보와 가치평가를 다룬다.
- 병목 밖 종목과 출처가 불완전한 평가는 `reference_only`로 남긴다.
- `daily-market-decision` 같은 통합 진입점은 다시 만들지 않는다.

## 데이터와 계산

- 리포트 숫자는 `scripts/` 계산 결과에서 가져온다.
- 주가, 시가총액, 실적, 컨센서스와 뉴스에는 제공자, 조회 시점, 출처와 필드 목록을 남긴다.
- 대상 성장률이 동종군 범위 밖이면 상대가치에 외삽하지 않는다.
- 특수 상황 검토가 끝나지 않으면 일반 가치평가로 후보 판정을 내리지 않는다.
- 실행 스킬은 `.cache/` 임시 원자료를 직접 읽지 않는다.
- 실행 중 만든 `reports/` 전달 파일과 검토된 Wiki, 문서, 계산 입력은 읽을 수 있다.
- valley 데이터 수집 절차는 `skills/sector-bottleneck/references/valley-data.md`가 소유한다.

## 산출물

`reports/`와 `.cache/`는 Git에 올리지 않는다.
HTML 리포트는 실제로 열어 제목, 링크와 페이지 오류를 확인한다.

## 검증

스킬을 수정한 뒤 다음 검증을 실행한다.

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/sector-bottleneck
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/tenbagger-pick
python3 -m unittest discover -s tests
```

마크다운을 수정한 뒤 전역 한국어와 가독성 검사기를 실행한다.
