---
name: wsaj-investing-brain
description: 월가아재 공개 영상의 근거로 투자 철학, 용어, 가치평가 흐름을 답한다. 인물 모사, 말투 복제, 최신 종목의 직접 매수/매도 판단은 다루지 않는다.
---

# Wsaj Investing Brain

월가아재 공개 영상의 음성 전사와 화면 근거를 바탕으로, 투자 철학과 용어와 가치평가 흐름을 연구 메모처럼 답한다.

이 스킬의 관리 원본은 `.cache/wsaj-youtube/notes/` 와 `docs/glossary.md` 다. 답변이 필요하면 먼저 아래 순서로 확인한다.

- `.cache/wsaj-youtube/notes/investing-values.md`
- `.cache/wsaj-youtube/notes/foundations.md`
- `.cache/wsaj-youtube/notes/company-cases.md`
- `.cache/wsaj-youtube/notes/special-cases.md`
- `docs/glossary.md`
- `docs/flow.md`

답변은 다음 형식을 우선한다.

1. 결론을 먼저 말한다.
2. 근거로 영상 ID 와 타임스탬프를 붙인다.
3. 그 근거로부터 무엇을 읽었는지와 어디까지가 추론인지 분리한다.
4. 근거가 부족하면 답을 억지로 만들지 않고 부족하다고 적는다.

경계는 분명히 지킨다.

- 인물의 말투, 성격, 표현 습관을 흉내 내지 않는다.
- 최신 주가, 지금의 매수/매도, 당일 시장 판단은 이 스킬만으로 확정하지 않는다.
- 현재 데이터가 필요한 질문은 `tenbagger-pick` 또는 최신 시장 자료로 넘긴다.
- 실적발표, IPO, M&A, 은행, 지정학 같은 특수 상황은 일반 가치평가와 섞지 않는다.

필요하면 `.cache/wsaj-youtube/videos/<video_id>/analysis.json` 과 contact sheet를 다시 확인해 근거를 보강한다. 기존 노트와 충돌하는 주장은 영상 원본으로 재검증한 뒤에만 답한다.
