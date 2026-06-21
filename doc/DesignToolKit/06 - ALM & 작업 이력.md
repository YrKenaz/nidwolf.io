# 06 — ALM & 작업 이력

← [[🏠 Home]] | [[05 - 사다리타기 게임]]

> ALM (Application Lifecycle Management) 스타일로 스프린트·백로그를 관리한다.  
> **이슈 상세는 → [[Issues/_Index|Issues 폴더]]에서 개별 파일로 관리한다.**

---

## 이슈 트래커

→ **[[Issues/_Index]]** 에서 등록·조회·클로즈 처리

| ID | 상태 | 심각도 | 제목 |
|----|------|--------|------|
| [[Issues/BUG-001\|BUG-001]] | 🟢 closed | Medium | build.py f-string 절단 |
| [[Issues/BUG-002\|BUG-002]] | 🟢 closed | High | 포탈 이동 후 마커 순간이동 |
| [[Issues/BUG-003\|BUG-003]] | 🟢 closed | High | 함정/숨김 바 트리거 불가 |
| [[Issues/BUG-004\|BUG-004]] | 🟢 closed | Low | build.py 한국어 인코딩 깨짐 |

---

## 스프린트 로그

### Sprint 4 — 도메인 전환 + 이중언어 완성 (2026-06-21)

**목표**: nidwolf.com 도메인 연결 / Cloudflare Pages 배포 / design-toolkit 전체 이중언어화

| # | 작업 | 결과 |
|---|------|------|
| 1 | 전체 파일 nidwolf.io → nidwolf.com 일괄 치환 | ✅ |
| 2 | Cloudflare Pages 프로젝트 생성 + GitHub 연동 | ✅ |
| 3 | Gabia 네임서버 → Cloudflare 이전 | ✅ |
| 4 | nidwolf.com 커스텀 도메인 Active 확인 | ✅ |
| 5 | Google Search Console 등록 + sitemap 제출 | ✅ |
| 6 | CHALLENGES `cat_en` 필드 추가 (14개) | ✅ |
| 7 | renderChallenge 3곳 한/영 cat 표시 전환 | ✅ |
| 8 | `_showBadgeUnlock` 토스트 이중언어화 | ✅ |

---

### Sprint 3 — 사다리 게임 고도화 + 메인 페이지 (2026-06-20)

**목표**: 사다리 게임 완성도 향상 / 전체 사이트 통합 / 메인 페이지 신설

| # | 작업 | 결과 |
|---|------|------|
| 1 | 전체 페이지 네비게이션에 사다리 게임 링크 추가 | ✅ |
| 2 | 맵 생성 2초 리빌 애니메이션 구현 | ✅ |
| 3 | 기본 속도 2× 상향 (210→420 px/s) | ✅ |
| 4 | [[Issues/BUG-002\|BUG-002]] 포탈 점프 버그 수정 | ✅ |
| 5 | [[Issues/BUG-003\|BUG-003]] 함정/숨김 바 트리거 버그 수정 | ✅ |
| 6 | `index.html` 메인 랜딩 페이지 신설 | ✅ |
| 7 | 볼트 Issues 폴더 + ALM 구조 정비 | ✅ |
| 8 | [[07 - AdSense 신청 평가표]] 작성 (100점 평가표 + 로드맵) | ✅ |

---

### Sprint 2 — SEO & 콘텐츠 확장 (2026-06)

| # | 작업 | 결과 |
|---|------|------|
| 1 | 아티클 40편 생성 파이프라인 구축 | ✅ |
| 2 | KR/EN 이중언어 전환 시스템 | ✅ |
| 3 | 다크/라이트 모드 전체 적용 | ✅ |
| 4 | sitemap.xml + robots.txt | ✅ |
| 5 | JSON-LD + canonical + OG 태그 | ✅ |
| 6 | 핵심 포인트 박스 + 인라인 관련글 | ✅ |

---

### Sprint 1 — 사다리 게임 v1 (2026-06)

| # | 작업 | 결과 |
|---|------|------|
| 1 | SkinBase + DefaultSkin + SkinManager | ✅ |
| 2 | LadderEngine (경로 사전계산 bijection) | ✅ |
| 3 | 바 동적 시스템 (hidden/trap) | ✅ |
| 4 | AnimationController (타이밍 엔진) | ✅ |
| 5 | 포탈 시스템 구현 | ✅ |
| 6 | LadderUI + 참가자 패널 + 속도 컨트롤 | ✅ |

---

## 백로그 (Backlog)

### 사다리 게임

| ID | 우선순위 | 제목 | 설명 |
|----|---------|------|------|
| BL-001 | ⭐⭐⭐ | RPG 도트 스킨 | `class RPGSkin extends SkinBase` 구현 |
| BL-002 | ⭐⭐⭐ | 사이버펑크 스킨 | 네온 글로우 강화 버전 |
| BL-003 | ⭐⭐ | 배경음악 / 효과음 | Web Audio API 연동 |
| BL-004 | ⭐⭐ | 결과 공유 QR | 결과 화면 QR 코드 (qrcode.js) |
| BL-005 | ⭐⭐ | 인원 수 프리셋 | 2/4/6/8인 빠른 선택 |
| BL-006 | ⭐ | 히스토리 저장 | 이전 추첨 결과 localStorage |
| BL-007 | ⭐ | 타이틀 입력 | 게임 제목 표시 |

### 사이트 공통

| ID | 우선순위 | 제목 | 설명 |
|----|---------|------|------|
| BL-010 | ⭐⭐⭐ | Google AdSense 연동 | 심사 통과 후 광고 스크립트 삽입 |
| BL-011 | ✅ 완료 | design-toolkit 영문 데이터 완성 | TIPS/CHALLENGES/BADGES/HISTORY 영문 필드 + 렌더 전환 완료 |
| BL-012 | ⭐⭐ | 아티클 검색 기능 | articles/index.html 클라이언트 검색 |
| BL-013 | ⭐ | 뉴스레터 구독 폼 | 이메일 수집 |

---

## 기술 부채 (Tech Debt)

| ID | 상태 | 내용 |
|----|------|------|
| TD-001 | 🟡 보류 | design-toolkit.html 246KB 단일 파일 → 모듈 분리 검토 (3140줄, 구조 변경 부담 큼) |
| TD-002 | 🟢 완료 | ladder.html Edit 도구 절단 → Python 패치 스크립트 규칙화 (CLAUDE.md 문서화 완료) |
| TD-003 | ⬜ 미착수 | build.py 테스트 커버리지 (본문 길이 검증 자동화) |
| TD-004 | ⬜ 미착수 | 