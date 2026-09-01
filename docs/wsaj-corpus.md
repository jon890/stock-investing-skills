# 월가아재 영상 코퍼스

이 문서는 월가아재 공개 영상 코퍼스를 어떻게 만들고, 어디까지 처리했는지 기록한다.
원자료는 `.cache/wsaj-youtube/` 에 두며 Git 에 올리지 않는다.

## 진행 상태 확인

| 항목 | 값 |
| --- | --- |
| 채널 | `https://www.youtube.com/@wsaj/videos` |
| 색인한 영상 수 | 아래 `status` 명령의 `total` 값 |
| 처리 상태 | 증분 처리 중 |
| 최신 진행률 | 아래 `status` 명령의 출력이 기준 |

처리 수, 남은 수, 누적 처리 시간은 작업 중 계속 바뀐다.
Git 문서에 시점별 숫자를 고정하지 않고 다음 명령으로 확인한다.

```bash
python3 scripts/wsaj_video_corpus.py status
```

## 처리 방식

유튜브 자막은 쓰지 않는다.
각 영상은 공개 no-cookie 경로로 내려받고, 로컬에서 음성과 화면을 따로 처리한다.

| 자료 | 만드는 방식 | 저장 위치 |
| --- | --- | --- |
| 음성 전사 | `mlx-whisper` 로 영상 음성을 직접 전사한다 | `.cache/wsaj-youtube/videos/<video_id>/analysis.json` |
| 화면 근거 | 30초 간격 프레임을 contact sheet 로 만든다 | `.cache/wsaj-youtube/videos/<video_id>/frames/` |
| 분류 카탈로그 | 제목과 전사문에서 가치평가 관련 용어를 센다 | `.cache/wsaj-youtube/catalog.json` |

원본 영상 파일은 한 편 처리가 끝나면 삭제한다.
`analysis.json` 과 contact sheet 만 남긴다.

## 실행 명령

처리 전에는 색인이 있어야 한다.

```bash
uv run --with mlx-whisper scripts/wsaj_video_corpus.py index
```

남은 영상을 순서대로 처리하려면 다음 명령을 쓴다.

```bash
uv run --with mlx-whisper scripts/wsaj_video_corpus.py process
```

병렬 처리를 할 때는 서로 겹치지 않는 영상 ID 묶음을 나누어 실행한다.
한 묶음은 20개 안팎이 적당하다.

```bash
uv run --with mlx-whisper scripts/wsaj_video_corpus.py process --ids '<쉼표로 구분한 영상 ID 목록>'
```

처리가 끝나면 카탈로그를 다시 만든다.

```bash
python3 scripts/wsaj_video_corpus.py catalog
```

## 중단 조건

스크립트는 연속 세 편이 실패하면 처리를 멈춘다.
이 중단은 YouTube 요청 제한, 다운로드 실패, 로컬 전사 실패를 같은 방식으로 다룬다.

Mac 비밀번호 입력을 피하기 위해 기본 경로에서는 쿠키와 브라우저 세션을 쓰지 않는다.
`.cache/wsaj-youtube/session-cookies.txt` 가 있으면 스크립트가 fallback 으로 쓸 수 있으므로, 현재 공개 처리에서는 이 파일을 만들지 않는다.

## 승격 기준

`.cache` 의 전사문은 원자료다.
답변 근거로 바로 쓰지 않는다.

영상에서 투자 원칙, 가치평가 절차, 회사 사례, 특수 상황 규칙이 확인되면 짧은 증거 단위로 요약해 `wiki/experts/wsaj/evidence/core.json` 에 승격한다.
승격할 때는 다음 조건을 확인한다.

- 영상 ID, 제목, URL, 타임스탬프가 있어야 한다.
- 게시일은 `scripts/fetch_youtube_publish_dates.py` 로 확인한다.
- 긴 전사문을 복사하지 않고, 검토자가 확인한 요약만 넣는다.
- 화면 근거가 있으면 contact sheet 경로와 프레임 시각을 함께 남긴다.
- 승격 뒤 `scripts/evaluate_wsaj_brain.py` 를 다시 실행한다.

승격된 증거 수는 다음 명령으로 확인한다.

```bash
jq '.evidence | length' wiki/experts/wsaj/evidence/core.json
```

처리 완료된 영상 전체가 답변 근거로 승격된 것은 아니다.
