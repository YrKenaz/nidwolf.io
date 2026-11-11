# nidwolf.com — 위스키 종합 티어표

티어표·순위·평점 리스트를 100점 척도로 환산해 합산한 위스키 티어표 사이트입니다.

- 데이터: `data/sources.json`(출처), `data/bottles.json`(병), `data/observations.json`(병 × 출처 점수)
- 이미지: `img/<병 id>.webp`
- 빌드: `python3 tools/build.py` → `index.html` 생성 (`--single 경로`로 이미지 내장 단일 파일도 생성)
- 수집·갱신 절차와 필드 설명: [CLAUDE.md](CLAUDE.md)

이전 사이트(Nidwolf Design Toolkit)는 `design-toolkit-final` 태그에 남아 있습니다.
