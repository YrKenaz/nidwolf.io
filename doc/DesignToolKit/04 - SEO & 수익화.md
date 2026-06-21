# 04 — SEO & 수익화

← [[🏠 Home]]

---

## 적용된 SEO 항목

### sitemap.xml

경로: `sitemap.xml` (루트)
44개 URL 포함.

| 페이지 | priority | changefreq |
|--------|----------|------------|
| design-toolkit.html | 1.0 | monthly |
| articles/index.html | 0.9 | monthly |
| articles/tip-*.html × 30 | 0.8 | yearly |
| articles/history-*.html × 10 | 0.8 | yearly |
| about.html | 0.5 | yearly |
| privacy.html | 0.3 | yearly |

### robots.txt

```
User-agent: *
Allow: /
Sitemap: https://nidwolf.com/sitemap.xml
```

### JSON-LD (Schema.org Article)

모든 아티클 페이지에 삽입. `build.py`의 `jsonld_article()` 함수로 자동 생성.

```json
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "...",
  "description": "...",
  "url": "https://nidwolf.com/articles/slug.html",
  "inLanguage": "ko",
  "publisher": {
    "@type": "Organization",
    "name": "Nidwolf Design Toolkit",
    "url": "https://nidwolf.com"
  },
  "datePublished": "2026-01-01",
  "dateModified": "2026-06-13"
}
```

### Canonical Tag

```html
<link rel="canonical" href="https://nidwolf.com/articles/{slug}.html"/>
```

`head()` 함수에서 `page_url` 인자가 있을 때만 출력.

### Open Graph / Twitter Card

```html
<meta property="og:title"       content="{title}"/>
<meta property="og:description" content="{desc}"/>
<meta property="og:type"        content="article"/>
<meta property="og:url"         content="{page_url}"/>
<meta property="og:image"       content="https://nidwolf.com/nidwolf-logo.png"/>
<meta name="twitter:card"       content="summary"/>
<meta name="twitter:image"      content="https://nidwolf.com/nidwolf-logo.png"/>
```

---

## AdSense 고품질 기준 체크리스트

Google AdSense 고품질 사이트 가이드라인 기준으로 적용.

| 항목 | 상태 | 비고 |
|------|------|------|
| 독창적 콘텐츠 (1,500자+) | ✅ | 40편 아티클, 본문 검증 |
| 명확한 내비게이션 | ✅ | 공통 header/footer, breadcrumb |
| about 페이지 | ✅ | about.html |
| 개인정보처리방침 | ✅ | privacy.html |
| 빠른 로딩 (단일 파일) | ✅ | 외부 CDN 의존 없음 |
| 모바일 대응 | ✅ | `viewport` 메타 태그 |
| sitemap.xml | ✅ | 44 URLs |
| robots.txt | ✅ | |
| Canonical | ✅ | 아티클 전체 |
| JSON-LD 구조화 데이터 | ✅ | Article 타입 |
| OG / Twitter 태그 | ✅ | |
| 핵심 포인트 박스 | ✅ | UX 품질 향상 |
| 인라인 관련 아티클 | ✅ | 페이지뷰 증가 유도 |
| 영문 번역 | ✅ | 전체 아티클 KR/EN |

---

## 향후 수익화 개선 포인트

1. **OG Image 개인화** — 현재 단일 로고 이미지. 아티클별 카드 이미지 생성 고려
2. **dateModified 자동화** — 현재 하드코딩(`2026-06-13`). 빌드 시 자동 날짜 삽입 검토
3. **아티클 수 확장** — 40편 → 100편 이상 목표 (AdSense 승인 가속)
4. **내부 링크 강화** — 현재 2번째 `</p>` 이후 1개. 본문 밀도 기반 추가 삽입 검토
5. **Contact 폼** — about.html에 실제 문의 폼 추가 (신뢰도 향상)
