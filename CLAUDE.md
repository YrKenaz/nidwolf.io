# Nidwolf Design Toolkit — Claude 작업 지침

> 이 파일은 Claude가 이 프로젝트에서 작업할 때 반드시 읽고 따라야 할 규칙과 워크플로우를 담고 있다.

---

## 프로젝트 개요

- **도메인**: `https://nidwolf.com`
- **워크스페이스**: `H:\Dev\html\NoNameProject\`
- **목적**: 디자이너·기획자를 위한 무료 통합 도구 사이트 (AdSense 수익화 목표)
- **상세 문서**: `doc/DesignToolKit/🏠 Home.md` (Obsidian 볼트)

---

## 이슈 등록 규칙 (필수)

**버그를 발견하거나 수정했을 때, 또는 기능 요청이 생겼을 때 반드시 아래 절차를 따른다.**

### 1. 이슈 파일 생성

`doc/DesignToolKit/Issues/` 폴더에 개별 마크다운 파일을 생성한다.

```
파일명 규칙:
  BUG-XXX.md   ← 버그 / 예상치 못한 동작
  FEAT-XXX.md  ← 기능 요청 / 개선 제안
  TD-XXX.md    ← 기술 부채
```

다음 번 ID는 `doc/DesignToolKit/Issues/_Index.md`의 "이슈 ID 채번 규칙" 표를 확인한다.

### 2. 이슈 파일 내용 (템플릿: `_TEMPLATE.md`)

```markdown
---
id: BUG-XXX
type: BUG
status: open          # open | closed
severity: High        # Critical | High | Medium | Low
created: YYYY-MM-DD
resolved:             # 해결 후 날짜 기입
file: 파일명.html
---

# [BUG-XXX] 이슈 제목

## 요약
> 한 줄 설명

## 증상
(사용자가 경험한 현상)

## 원인 분석
(코드 레벨 원인)

## 수정 내용
(before/after 코드 포함)

## 검증
- [ ] 확인 항목
```

### 3. `_Index.md` 업데이트

`doc/DesignToolKit/Issues/_Index.md`를 열어:
- **오픈 이슈**: 신규 이슈를 테이블에 추가
- **클로즈 이슈**: 해결 후 오픈→클로즈 테이블로 이동, `resolved` 날짜 기입
- **채번 규칙 표**의 "다음 번호" 업데이트

### 4. `06 - ALM & 작업 이력.md` 업데이트

이슈 트래커 테이블에 위키링크로 한 줄 추가:
```markdown
| [[Issues/BUG-XXX\|BUG-XXX]] | 🔴 open | High | 이슈 제목 |
```

---

## 파일 수정 규칙

> ⚠️ **대형 파일(ladder.html ~1280줄, design-toolkit.html ~246KB, build.py)은 Edit 도구로 직접 수정하면 파일이 잘릴 수 있다.**

항상 Python `str.replace()` 패치 스크립트를 사용한다:

```python
path = '/sessions/.../NoNameProject/ladder.html'
txt = open(path, encoding='utf-8').read()
assert 'OLD_PATTERN' in txt, '패턴 없음 — 확인 필요'
txt = txt.replace('OLD_PATTERN', 'NEW_PATTERN', 1)
open(path, 'w', encoding='utf-8').write(txt)
```

> ⚠️ **`</body>` 교체 시 주의**: `str.replace('</body>', ...)` 는 파일 내 **첫 번째** 매칭을 교체한다.  
> template literal(백틱 문자열) 안에 `</body>`가 있는 파일(예: design-toolkit.html의 WPF 미리보기 srcdoc)은  
> `rfind`로 **마지막** 위치를 찾아 슬라이싱으로 삽입해야 한다:
> ```python
> last = txt.rfind('</body>')
> txt = txt[:last] + SNIPPET + txt[last:]
> ```

---

## 프로젝트 구조 요약

```
NoNameProject/
├── index.html              ← 메인 랜딩 페이지
├── design-toolkit.html     ← 디자인 도구 앱 (~246KB)
├── ladder.html             ← 사다리 게임 (~1280줄)
├── about.html / privacy.html
├── articles/               ← 정적 아티클 40편 (build.py 생성)
│   ├── index.html
│   └── style.css
├── _dev/_gen/
│   └── build.py            ← 아티클 생성기 (python build.py)
└── doc/DesignToolKit/      ← Obsidian 볼트
    ├── 🏠 Home.md
    ├── Issues/             ← 이슈 관리 폴더
    │   ├── _Index.md       ← 이슈 목록 인덱스
    │   ├── _TEMPLATE.md    ← 새 이슈 템플릿
    │   └── BUG-XXX.md
    └── 06 - ALM & 작업 이력.md
```

---

## 주요 기술 상수

| 항목 | 값 |
|------|----|
| `nw-lang` localStorage | `'ko'` \| `'en'` |
| `nw-dark` localStorage | 존재 여부로 판단 |
| `TRIGGER_PX` (ladder) | `72` px |
| `_vspd` (ladder 기본) | `420 * speed` px/s |
| `BASE_URL` (build.py) | `https://nidwolf.com` |

---

## CSS 다크모드 패턴

```html
<!-- head 최상단 인라인 스크립트 -->
<script>(function(){
  var l=localStorage.getItem('nw-lang')||'ko';
  document.documentElement.lang=l;
  if(localStorage.getItem('nw-dark'))
    document.documentElement.setAttribute('data-dark','');
})();</script>
```

```css
:root { --bg:#f5f6fa; --t1:#1a1d2e; }
html[data-dark] { --bg:#0E1117; --t1:#E8EAF0; }
html[lang="ko"] .en { display:none; }
html[lang="en"] .ko { display:none; }
```
