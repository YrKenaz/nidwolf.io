# Nidwolf Design Toolkit — 개발 문서

> **도메인**: `https://nidwolf.com`
> **워크스페이스**: `H:\Dev\html\NoNameProject\`
> **최종 업데이트**: 2026-06-20

---

## 프로젝트 목적

업무 중 디자이너 및 기획자가 실시간으로 활용할 수 있는 **통합 디자인 도구 사이트**.
Google AdSense 수익화를 목표로 SEO 고품질 사이트 기준을 충족시키는 방향으로 개발.

---

## 빠른 탐색

| 문서 | 설명 |
|------|------|
| [[01 - 파일 구조]] | 폴더 레이아웃, 각 파일 역할 |
| [[02 - Design Toolkit 메인]] | design-toolkit.html 기능 목록 |
| [[03 - 아티클 생성 시스템]] | build.py, 정적 페이지 파이프라인 |
| [[04 - SEO & 수익화]] | sitemap, robots, JSON-LD, canonical |
| [[05 - 사다리타기 게임]] | ladder.html 아키텍처 & 기술 명세 |
| [[06 - ALM & 작업 이력]] | 이슈 트래커 / 스프린트 로그 / 백로그 |
| [[07 - AdSense 신청 평가표]] | AdSense 준비도 평가 / 체크리스트 / 로드맵 |

---

## 현재 상태 요약

### 사이트 공통
- [x] 폴더 구조 정리 (사이트 파일 / `_dev/` 개발 파일 분리)
- [x] KR/EN 이중언어 전체 지원 (`localStorage: nw-lang`)
- [x] 다크/라이트 모드 전체 지원 (`localStorage: nw-dark`)
- [x] 전체 페이지 통합 네비게이션 (사다리 게임 링크 포함)
- [x] SEO: sitemap.xml, robots.txt, JSON-LD, canonical, og:image

### 아티클
- [x] 아티클 40편 생성 (디자인 팁 30 + 역사 10)
- [x] 핵심 포인트 박스 + 인라인 관련 아티클 자동 삽입
- [x] build.py 이중언어 지원

### 사다리타기 게임 (ladder.html)
- [x] Canvas 기반 경로 사전계산 엔진
- [x] 바 동적 시스템 (normal / hidden / trap)
- [x] 포탈 텔레포트 시스템
- [x] 2초 맵 생성 리빌 애니메이션
- [x] 기본 속도 2× 상향 (420 px/s)
- [x] 포탈 이동 후 위치 점프 버그 수정
- [x] 함정/숨김 바 트리거 버그 수정 (대각선 바 양끝 체크)

---

## 기술 스택

```
Frontend   HTML5 / CSS3 (CSS Variables) / Vanilla JS (ES6+)
Generator  Python 3 — f-string 기반 정적 HTML 생성
Canvas     HTML5 Canvas API (사다리 게임)
SEO        JSON-LD / Open Graph / Twitter Card
Storage    localStorage (언어·다크모드 설정 영속화)
```

---

## 주요 상수 / 키

| 키 | 위치 | 값 |
|----|------|----|
| `nw-lang` | localStorage | `'ko'` \| `'en'` |
| `nw-dark` | localStorage | 존재 여부로 판단 |
| `BASE_URL` | build.py | `https://nidwolf.com` |
| `TRIGGER_PX` | ladder.html | `72` px (바 트리거 윈도우 반경) |
| `_vspd` | ladder.html | `420 * speed` px/s (×1 기본) |
