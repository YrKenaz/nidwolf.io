# nidwolf.com — 위스키 종합 티어표

티어표·순위·평점 리스트 13개를 100점 척도로 환산해 합산한 위스키 티어표 사이트입니다.

- `index.html` — 배포되는 페이지 (이미지 내장 단일 파일, 직접 고치지 말 것)
- `_src/template.html` — 페이지 틀(디자인·필터·스크립트)
- `_src/data/whiskies.json` — 병별 점수·티어·속성(숙성년수, 피트/셰리/CS, 도수, 가격 등)
- `_src/data/images.json` — 병 이미지(data URI)
- `_src/build.py` — 위 셋으로 `index.html` 생성: `python3 _src/build.py`
- `_src/collect/` — 자료 수집·점수 산출에 쓴 스크립트(참고용, 경로는 수집 당시 작업 폴더 기준)

이전 사이트(Nidwolf Design Toolkit)는 `design-toolkit-final` 태그에 남아 있습니다.
