# 02 — Design Toolkit 메인 (design-toolkit.html)

← [[🏠 Home]] | [[01 - 파일 구조]]

---

## 개요

`design-toolkit.html` — 246KB, 약 3150줄의 단일 파일 앱.
모든 JS/CSS가 인라인으로 포함된 완전한 SPA(Single Page App).

---

## 사이드바 구조

```
Wizard
  └── Design Wizard (P1)
        ├── 🌐 Web
        └── 📱 App

Fun Zone
  ├── 💡 오늘의 팁 (Daily Tip)
  ├── 📅 오늘의 과제 (Challenge)
  ├── 🎯 색상 맞히기 (Color Game)
  ├── 🧠 감각 퀴즈 (Taste Quiz)
  └── 📚 디자인 역사 (Timeline)
  └── 🏅 디자이너 뱃지 (Badges)

Contents
  └── (아티클 링크)

Output
  └── (내보내기 패널)

Settings
  ├── 🌙 Dark Mode
  ├── 🌐 KR / EN 전환
  └── ◀ Collapse
```

---

## 핵심 기능 목록

### Design Wizard
- 5가지 기준(환경, 목적, 사용자, 톤, 규모)으로 UI 방향 선택
- Web / App 환경 분기
- 카테고리 탭 필터링 (`.wz-cat-tab`)
- 라이브 프리뷰 프레임 (`.wz-live-frame`)
- 요약 패널 (`.wz-summary`)

### Color Palette
- 팔레트 생성 및 4가지 포맷 내보내기
- `.export-tabs` → CSS / Tailwind / JSON / Figma

### Fun Zone
- **오늘의 팁**: 날짜 기반 랜덤 디자인 팁
- **오늘의 과제**: 날짜 기반 디자인 챌린지
- **색상 맞히기**: 색상값→이름 맞히기 게임
- **감각 퀴즈**: 디자인 감각 테스트
- **디자인 역사 타임라인**: 주요 디자인 운동 시각화
- **뱃지 시스템**: 활동 기반 디자이너 뱃지 획득

---

## i18n (이중언어) 패턴

```css
/* CSS */
html[lang="ko"] .en { display: none; }
html[lang="en"] .ko { display: none; }
```

```javascript
// JS 초기화 (head 인라인)
var lang = localStorage.getItem('nw-lang') || 'ko';
document.documentElement.lang = lang;
```

```html
<!-- HTML 마크업 -->
<span class="ko">한국어 텍스트</span>
<span class="en">English text</span>
```

localStorage 키: `nw-lang` (`'ko'` | `'en'`)

---

## 대형 파일 수정 시 주의사항

> ⚠️ **Edit 도구는 246KB 파일에서 묵시적으로 잘릴 수 있음**

수정 방법: Python `str.replace()` 패치 스크립트 사용

```python
BUILD = '/sessions/.../NoNameProject/design-toolkit.html'
src = open(BUILD, encoding='utf-8').read()
src = src.replace('OLD', 'NEW', 1)
assert 'marker' in src  # 검증
open(BUILD, 'w', encoding='utf-8').write(src)
```

→ 관련: [[03 - 아티클 생성 시스템]] (동일 패턴 build.py 적용)
