# plan003-wsaj-wiki-mvp

## 목적

월가아재 공개 영상 근거로만 답하는 비공식 연구 보조자 MVP를 만든다.
이 plan 의 판정은 Conditional Go 다.
근거 추적과 거절 규칙을 지킬 수 있을 때만 진행한다.

## 의존 관계

- `plan001-sector-bottleneck`

이 plan 은 `docs/prd.md` 의 세 진입점 정의를 전제한다.
`plan001` 이 아직 병합되지 않았으면 최신 base 를 확인하고 멈춘다.

## 소유 파일

- `docs/prd.md`
- `docs/flow.md`
- `docs/glossary.md`
- `docs/wsaj-wiki.md`
- `skills/wsaj-investing-brain/SKILL.md`
- `scripts/wsaj_video_corpus.py`
- `scripts/evaluate_wsaj_brain.py`
- `tests/fixtures/wsaj-brain-eval.json`
- `tests/test_wsaj_brain.py`

## 범위

- `wsaj-investing-brain` 스킬을 만든다.
- 공개 영상 ID, 제목, 게시일, 타임스탬프, 음성 근거, 화면 근거를 답변 근거로 쓰는 규칙을 둔다.
- `docs/wsaj-wiki.md` 에 위키 구조와 답변 계약을 적는다.
- `docs/glossary.md` 는 용어 뜻과 오용 주의만 담고, 위키는 주장과 판단 흐름을 담게 분리한다.
- 근거 부족, 영상 사이 충돌, 현재 데이터 필요 상황에서는 답변을 보류한다.
- 50문항 평가 세트와 자동 평가 스크립트를 만든다.

## 범위 밖

- 월가아재 본인의 인격이나 말투를 흉내 내는 프롬프트.
- 최신 종목에 대한 직접 매수와 매도 판단.
- 비공개 자료나 개인 메시지 수집.
- 전체 공개 영상의 완전 수집 보장.

## 완료 기준

- 모든 답변 예시는 영상 ID와 타임스탬프를 가진다.
- 근거가 없는 질문에는 "근거 부족" 으로 답한다.
- 답변은 영상에서 확인한 내용과 하네스의 해석을 분리한다.
- 최신 시장 데이터가 필요한 질문은 영상 근거만으로 단정하지 않는다.
- `docs/glossary.md` 와 `docs/wsaj-wiki.md` 의 책임이 겹치지 않는다.
- 인용 유효성 90% 이상, 근거 부족 질문 거절률 95% 이상을 만족한다.
- 숫자와 시점 오류는 한 건도 허용하지 않는다.

## 검증 명령

```bash
for file in docs/prd.md docs/flow.md docs/glossary.md docs/wsaj-wiki.md skills/wsaj-investing-brain/SKILL.md; do
  ~/.claude/scripts/korean-style-check.sh "$file"
  python3 ~/.claude/scripts/check-readability.py "$file"
done
python3 scripts/wsaj_video_corpus.py --help
python3 -m unittest -v tests/test_wsaj_brain.py
```

답변 예시는 실제 코퍼스 근거가 있을 때만 추가한다.
근거가 아직 부족하면 예시 대신 거절 규칙만 검증한다.

## 원자 커밋 기준

이 plan 은 research brain MVP만 하나의 커밋과 PR로 묶는다.
전체 영상 수집 파이프라인 확장이나 종목 가치평가 변경이 섞이면 중단한다.
