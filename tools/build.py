#!/usr/bin/env python3
"""사이트 생성기. 저장소 루트에서:  python3 tools/build.py
    data/sources.json       출처 대장
    data/bottles.json       병 마스터(이름·종류·속성·가격·이미지 경로)
    data/observations.json  관측값(병 × 출처, 100점 척도 환산값 + 원문 표기)
  → 점수·티어를 계산해 index.html 을 만든다. 표준 라이브러리만 쓴다.
옵션:
    --single 경로     이미지를 내장한 단일 HTML 파일도 함께 만든다(오프라인 보관용)
    --fragment 경로   <head> 없는 조각 HTML(이미지 내장)을 만든다
    --check           index.html 을 쓰지 않고 검증·요약만 한다
"""
import json, os, sys, re, base64, datetime, collections, math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 사진 공개 기준(사용자 결정 2026-11-12): 사진이 있는 병이 전체 병 수의 이 비율 이상일 때만 화면에 사진을 싣는다.
# 미만이면 사진·출처 표시를 내보내지 않고 글자 카드로 운영한다(사진 데이터는 쌓아 두고 검증만 한다)
PHOTO_MIN_COVERAGE = 0.85
K = 1.0                                   # 종합 = (매체 그룹별 점수 합 + 종류별 사전 평균*K) / (독립 출처 수 + K)
SHARE = [("S", 0.05), ("A", 0.15), ("B", 0.25), ("C", 0.25), ("D", 0.20), ("E", 0.10)]   # 티어별 비율(점수 상위부터). 경계 점수는 빌드 때 계산
TIERS = []
TYPES = {"SM", "BL", "BB", "RY", "IR", "JP", "WD"}
# 허용 사진 라이선스(허용 목록). "CC BY-NC…"처럼 접두어만 같은 값이 통과하지 않도록 전체 형식을 맞춘다.
# 버전 뒤의 관할 표기(예: "CC BY 2.5 DE", "CC BY-SA 3.0 IGO")는 허용한다
LICENSE_OK = re.compile(r"^(CC0( 1\.0)?|Public domain|CC BY(-SA)?( \d\.\d( (?!N[CD]$)[A-Za-z]{2,3})?)?)$", re.I)
STYLE, CASK, SPEC = {"peat", "sherry", "cs"}, {"bourbon", "wine", "rum", "mizunara"}, {"SiB", "SmB", "BiB", "BP", "Wh"}

def load(name):
    with open(os.path.join(ROOT, "data", name), encoding="utf-8") as f:
        return json.load(f)

def tier(s):
    return next(t for t, lo in TIERS if s >= lo)

def set_tiers(scores):
    """점수 분포의 백분위로 티어 경계를 정한다."""
    s = sorted(scores, reverse=True); n = len(s); cum = 0; TIERS.clear()
    for name, share in SHARE[:-1]:
        cum += share; TIERS.append((name, s[min(n - 1, max(0, round(cum * n) - 1))]))
    TIERS.append((SHARE[-1][0], -1))

def photo_coverage(bottles):
    return sum(1 for b in bottles if b.get("img")) / len(bottles) if bottles else 0.0

def photos_on(bottles):
    return round(photo_coverage(bottles), 9) >= PHOTO_MIN_COVERAGE

def compute():
    """규칙(docs/research 02의 1단계):
    1) 같은 매체(group)의 리스트는 먼저 평균해 한 표로 센다.
    2) 순서 없는 추천 목록(in_score=false)은 점수에 넣지 않고 추천 횟수로만 센다.
    3) 사전 평균은 종류(type)별 평균을 쓴다.
    4) 독립 출처 1곳이면 '잠정', 점수 ± 표준오차가 티어 경계를 넘으면 '경계'로 표시한다."""
    sources, bottles, obs = load("sources.json"), load("bottles.json"), load("observations.json")
    errs, ids = [], [b["id"] for b in bottles]
    idset = set(ids)
    for i, c in collections.Counter(ids).items():
        if c > 1: errs.append(f"병 id 중복: {i}")
    by, seen = collections.defaultdict(list), set()
    for o in obs:
        if o["bottle"] not in idset: errs.append(f"관측값의 병 id 없음: {o['bottle']}"); continue
        if o["source"] not in sources: errs.append(f"관측값의 출처 id 없음: {o['source']}"); continue
        if (o["bottle"], o["source"]) in seen: errs.append(f"관측값 중복: {o['bottle']} × {o['source']}")
        seen.add((o["bottle"], o["source"]))
        s = sources[o["source"]]
        if s["in_score"]:
            if o["value"] is None or not (50 <= o["value"] <= 100): errs.append(f"환산 점수 없음/범위 밖: {o}")
        elif o["value"] is not None: errs.append(f"추천 목록 출처에 점수가 있음: {o}")
        by[o["bottle"]].append(o)
    rows = []
    for b in bottles:
        if b["type"] not in TYPES: errs.append(f"{b['id']}: 알 수 없는 type {b['type']}")
        for key, allowed in (("style", STYLE), ("cask", CASK), ("spec", SPEC)):
            bad = set(b[key]) - allowed
            if bad: errs.append(f"{b['id']}: {key} 값 오류 {bad}")
        # 사진 파일 검사: 사진을 싣는 경우에는 늘 한다. 싣지 않는 동안에는 img/ 가 배포 저장소에서 빠져 있을 수 있으므로 폴더가 있을 때만 한다
        if b.get("img") and (photos_on(bottles) or os.path.isdir(os.path.join(ROOT, "img"))) and not os.path.exists(os.path.join(ROOT, b["img"])):
            errs.append(f"{b['id']}: 이미지 파일 없음 {b['img']}")
        # 사진 보기 링크(상세 창): 데일리샷 상품 페이지, 위키미디어 공용 파일 페이지. https 주소만 받는다
        for k in ("ds_url", "img_page"):
            if b.get(k) and not str(b[k]).startswith("https://"): errs.append(f"{b['id']}: {k} 가 https:// 주소가 아님 ({b[k]!r})")
        if b.get("img"):
            # 사진은 위키미디어 공용의 자유 이용 사진만 쓴다. 저작자·라이선스·원본 페이지 표시가 빠지면 라이선스 위반이므로 빌드를 멈춘다
            for k in ("img_license", "img_page"):
                if not b.get(k): errs.append(f"{b['id']}: 사진이 있는데 {k} 가 없음")
            lic = b.get("img_license") or ""
            if lic and not LICENSE_OK.match(lic):
                errs.append(f"{b['id']}: 허용하지 않는 사진 라이선스 {lic!r} (CC0·Public domain·CC BY·CC BY-SA만. NC·ND·GFDL·FAL 등은 쓰지 않는다)")
            if b.get("img_source") != "Wikimedia Commons":
                errs.append(f"{b['id']}: 사진 출처가 Wikimedia Commons 가 아님 ({b.get('img_source')!r})")
            if lic.upper().startswith("CC BY") and not b.get("img_author"):
                errs.append(f"{b['id']}: {lic} 사진인데 img_author 가 없음")
        # 관측값이 0건인 병(출처 제외·평가 출처 없이 등록된 병)은 지우지 않고 '미평가'로 둔다.
        # gm 이 비어 있으므로 사전 평균·병 내 표준편차·티어 백분위 모수에 들어가지 않는다(점수형 출처 없는 병과 같은 경로)
        if "vintage" in b and not isinstance(b["vintage"], bool): errs.append(f"{b['id']}: vintage 는 true/false 만 허용 ({b['vintage']!r})")
        # 증류소 라인업(N3): distillery(영문 묶음 키)·distillery_ko·brand·bottler 는 문자열 또는 null
        for k in ("distillery", "distillery_ko", "brand", "bottler"):
            if b.get(k) is not None and (not isinstance(b[k], str) or not b[k].strip()): errs.append(f"{b['id']}: {k} 는 빈 아닌 문자열 또는 null ({b[k]!r})")
        if b.get("distillery") and not b.get("distillery_ko"): errs.append(f"{b['id']}: distillery 가 있는데 distillery_ko 가 없음")
        o = by.get(b["id"], [])
        g = collections.defaultdict(list)
        for x in o:
            if x["value"] is not None: g[sources[x["source"]]["group"]].append(x["value"])
        rows.append((b, o, [sum(v) / len(v) for v in g.values()]))
    dko = collections.defaultdict(set)
    for b in bottles:
        if isinstance(b.get("distillery"), str) and b.get("distillery_ko"): dko[b["distillery"]].add(b["distillery_ko"])
    for d, v in dko.items():
        if len(v) > 1: errs.append(f"증류소 {d}: distillery_ko 가 병마다 다름 {sorted(v)}")
    if errs: return [], {}, bottles, errs, {}
    # 종류별 사전 평균, 병 내 표준편차(독립 출처 2곳 이상인 병으로 추정)
    # 옛 병(vintage: true, 지금은 구하기 어려운 수집가용 병)은 사전 평균·병 내 표준편차·티어 경계 모수에서 모두 뺀다(사용자 결정 2026-11-21).
    # 옛 병이 있든 없든 다른 병의 점수·티어·경계가 같아야 한다. 옛 병 자신은 같은 수식으로 점수를 내고, 나머지 병으로 정한 경계에 대어 티어를 정한다
    tm = collections.defaultdict(list); ss = df = 0
    for b, o, gm in rows:
        if gm and not b.get("vintage"):
            m = sum(gm) / len(gm); tm[b["type"]].append(m)
            if len(gm) > 1: ss += sum((x - m) ** 2 for x in gm); df += len(gm) - 1
    prior = {t: sum(v) / len(v) for t, v in tm.items()}
    allm = [x for v in tm.values() for x in v]
    for b, o, gm in rows:   # 옛 병만 있는 종류: 옛 병이 아닌 병 전체 평균을 사전 평균으로 쓴다
        if gm and b["type"] not in prior: prior[b["type"]] = sum(allm) / len(allm) if allm else sum(gm) / len(gm)
    sd = (ss / df) ** 0.5 if df else 2.0
    set_tiers([round((sum(gm) + prior[b["type"]] * K) / (len(gm) + K), 1) for b, o, gm in rows if gm and not b.get("vintage")])
    out = []
    for b, o, gm in rows:
        n = len(gm)
        w = {"id": b["id"], "ko": b["ko"], "en": b["en"], "type": b["type"], "region": b["region"], "n": n,
             "obs": [{"s": x["source"], "v": x["value"], "raw": x.get("raw", "")} for x in o],
             "rec": sum(1 for x in o if x["value"] is None),
             "age": b["age"], "abv": b["abv"], "style": b["style"], "cask": b["cask"], "spec": b["spec"],
             "beg": b["beginner"], "price": b["price"], "pname": b["price_product"], "pdate": b.get("price_date"), "pml": b.get("price_ml"),
             "dsu": b.get("ds_url"), "wp": b.get("img_page"),   # 사진 보기 링크용. 사진 공개 기준과 무관하게 내보낸다(사진 자체는 싣지 않음)
             "ds": [b["ds_rating"], b["ds_reviews"]] if b.get("ds_rating") else None,
             "vin": bool(b.get("vintage"))}
        # 증류소 라인업용(값이 있을 때만 내보내 용량을 아낀다): di 증류소 키, dk 한글 이름, br 브랜드, bo 독립병입 회사
        w.update({k: b[f] for k, f in (("di", "distillery"), ("br", "brand"), ("bo", "bottler")) if b.get(f)})   # 한글 증류소 이름은 stats["dk"] 표 하나로(병마다 반복하지 않음)
        if n == 0:
            w.update(score=None, tier="N", flag="none", lo=None, hi=None, bt=None)
        else:
            sc = (sum(gm) + prior[b["type"]] * K) / (n + K); se = sd / (n + K) ** 0.5
            lo, hi = sc - se, sc + se; t1, t2 = tier(hi), tier(lo)
            w.update(score=round(sc, 1), tier=tier(round(sc, 1)), lo=round(lo, 1), hi=round(hi, 1),
                     flag="prov" if n == 1 else ("border" if t1 != t2 else "firm"), bt=f"{t1}~{t2}" if t1 != t2 else None)
        out.append(w)
    out.sort(key=lambda w: (-(w["score"] if w["score"] is not None else 0), w["ko"]))
    meta = {k: [s["name"], s["lang"], s["kind"], s["url"], s["rule"], s["group_name"], s["in_score"]] for k, s in sources.items()}
    stats = {"dk": {d: sorted(v)[0] for d, v in sorted(dko.items())},
             "prior": {t: round(v, 1) for t, v in prior.items()}, "sd": round(sd, 2), "k": K, "tiers": [[t, lo] for t, lo in TIERS]}
    return out, meta, bottles, errs, stats

def render(ws, meta, bottles, embed, stats):
    img, src, cr = {}, {}, {}
    for b in (bottles if photos_on(bottles) else []):   # 기준 미만이면 사진 경로·저작자 정보를 페이지에 한 글자도 넣지 않는다
        if not b.get("img"): continue
        if embed:
            with open(os.path.join(ROOT, b["img"]), "rb") as f:
                img[b["id"]] = "data:image/webp;base64," + base64.b64encode(f.read()).decode()
        else:
            img[b["id"]] = b["img"]
        if b.get("img_source"): src[b["id"]] = b["img_source"]
        # 사진 출처 표시용: 저작자 a, 라이선스 l, 라이선스 주소 lu, 원본 페이지 p, 변경 내용 c, 출처 이름 s
        cr[b["id"]] = {k: b.get(f) for k, f in (("a", "img_author"), ("l", "img_license"), ("lu", "img_license_url"), ("p", "img_page"), ("c", "img_changes"), ("s", "img_source")) if b.get(f)}
    updated = datetime.date.today().isoformat()
    data = json.dumps({"whiskies": ws, "meta": meta, "updated": updated, "stats": stats}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    with open(os.path.join(ROOT, "tools", "template.html"), encoding="utf-8") as f:
        t = f.read()
    t = t.replace("__ART_METHOD__", method_fig("score", "tier")).replace("__ART_TREND__", method_fig("trend"))
    return t.replace("__DATA__", data).replace("__IMAGES__", json.dumps({"img": img, "src": src, "cr": cr}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))

SITE_ART = os.path.join("art", "site")   # 티어표 하단 '점수 산출 방식'·'트렌드지수' 옆 도해(이미지 담당 산출물). 없으면 그 칸을 비운다
def method_svg(name):
    p = os.path.join(ROOT, SITE_ART, f"{name}.svg")
    if not os.path.exists(p): return ""
    with open(p, encoding="utf-8") as f: s = f.read().strip()
    return s[s.find("<svg"):] if "<svg" in s else ""

def method_fig(*names):
    s = "".join(method_svg(n) for n in names)
    return f'<figure class="mart">{s}</figure>' if s else ""

def check_method_art():
    """도해 속 숫자가 실제 값과 맞는지 본다. trend.svg 의 재료 비중(큰 숫자 3개·'합 N')은 data/trends.json weights 와,
    tier.svg 의 비율(5%·15%…)은 SHARE 와 비교한다. 어긋나면 메시지 목록을 돌려준다(그림은 tools/cocktail-art/method_art.py 로 다시 만든다)."""
    out = []
    tr = method_svg("trend"); tp = os.path.join(ROOT, "data", "trends.json")
    if tr and os.path.exists(tp):
        try:
            with open(tp, encoding="utf-8") as f: wt = json.load(f).get("weights") or {}
        except Exception: wt = {}
        got = [int(x) for x in re.findall(r'font-size:16px">(\d+)</text>', tr)]
        sm = re.search(r">합 (\d+)</text>", tr)
        want = [int(v) for v in wt.values()]
        if wt and (got != want or (sm and int(sm.group(1)) != sum(want))):
            out.append(f"art/site/trend.svg 의 비중 {'/'.join(map(str, got))}(합 {sm.group(1) if sm else '?'})이 trends.json weights {'/'.join(map(str, want))}(합 {sum(want)})와 다름 — python3 -B tools/cocktail-art/method_art.py 로 다시 만들 것")
    ti = method_svg("tier")
    if ti:
        got = [int(x) for x in re.findall(r'>(\d+)%</text>', ti)]
        want = [round(s * 100) for _, s in SHARE]
        if got != want:
            out.append(f"art/site/tier.svg 의 티어 비율 {'·'.join(map(str, got))}%가 build.py SHARE {'·'.join(map(str, want))}%와 다름 — 그림을 다시 만들 것")
    return out

DESC = "한국·영어권 위스키 티어표와 순위·평점 리스트를 100점 척도로 합산한 위스키 티어표. 종류·숙성년수·피트·셰리·CS·가격대별로 골라 볼 수 있습니다."
CK_DESC = "버번·라이·스카치 등 위스키로 만드는 칵테일 제조법. 투명한 잔에 재료를 넣는 순서대로 양에 비례해 층층이 쌓은 그림으로 따라 하기 쉽게 보여 줍니다."

def head(title, desc, url):
    return ('<!doctype html>\n<html lang="ko"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            f'<meta name="description" content="{desc}">'
            f'<link rel="canonical" href="{url}"><link rel="icon" href="/Nidwolf-ico.ico">'
            f'<meta property="og:title" content="{title}"><meta property="og:description" content="{desc}">'
            f'<meta property="og:type" content="website"><meta property="og:url" content="{url}">'
            '<style>body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n')

HEAD = head("위스키 종합 티어표", DESC, "https://nidwolf.com/")
GL_DESC = "싱글몰트·버번·캐스크 스트렝스·보틀드 인 본드·피트·NAS 등 위스키 라벨과 티어표에 나오는 용어를 법령·공식 자료 근거와 함께 풀이한 용어 사전."
LN_DESC = "위스키 종류, 만드는 과정, 통 숙성과 숙성년수 표기를 그림 세 장으로 정리했습니다. 스코틀랜드·미국 법령 등 근거 자료를 함께 답니다."
LN_HEAD = head("그림으로 배우는 위스키", LN_DESC, "https://nidwolf.com/learn")
GL_HEAD = head("위스키 용어 사전", GL_DESC, "https://nidwolf.com/glossary")
CK_HEAD = head("위스키 칵테일 제조법", CK_DESC, "https://nidwolf.com/cocktails")   # 호스팅이 cocktails.html → /cocktails 로 308 리다이렉트하므로 표기를 /cocktails 로 통일

# 사이트 페이지 목록(메뉴 순서). 새 페이지는 여기에만 더한다: (키, 정적 href, 메뉴 이름, 배포 주소)
# 정적 href 는 로컬 서버에서도 열리는 파일 이름, 배포 주소는 호스팅(Cloudflare)이 .html 을 308 로 돌리는 짧은 주소
PAGES = [("index", "./", "위스키 티어표", "/"), ("cocktails", "cocktails.html", "칵테일 제조법", "/cocktails"), ("glossary", "glossary.html", "용어 사전", "/glossary"),
         ("learn", "learn.html", "그림으로 배우기", "/learn"), ("changes", "changes.html", "바뀐 것", "/changes")]

def nav_html(cur, built):
    """두 페이지 이상 만들어질 때만 메뉴를 넣는다(없는 페이지로 가는 죽은 링크 방지). 주소 보정 스크립트는 늘 넣는다"""
    ps = [x for x in PAGES if x[0] in built]
    links = "".join(f'<a href="{h}"' + (' aria-current="page"' if k == cur else "") + f'>{n}</a>' for k, h, n, _ in ps) if len(ps) > 1 else ""
    pretty = {h: u for k, h, n, u in PAGES if h != "./"}
    js = ('<script>/* 주소 보정(build.py 의 PAGES 로 생성). 배포 주소(nidwolf.com)에서는 *.html 링크를 짧은 주소로(308 리다이렉트를 건너뜀), '
          '로컬 파일(file://)에서는 ./ 링크를 index.html 로(./ 는 폴더 목록이 열림) 바꾼다. 스크립트로 나중에 만드는 링크는 siteHref() 를 거친다 */\n'
          f'(()=>{{const P={json.dumps(pretty)},live=/(^|\\.)nidwolf\\.com$/.test(location.hostname),file=location.protocol==="file:";'
          'const f=h=>{if(live){const m=h.match(/^([a-z0-9-]+\\.html)(.*)$/);if(m&&P[m[1]])return P[m[1]]+m[2]}else if(file&&h.startsWith("./"))return "index.html"+h.slice(2);return h};'
          'window.siteHref=f;const run=()=>document.querySelectorAll("a[href]").forEach(a=>{const h=a.getAttribute("href"),g=f(h);if(g!==h)a.setAttribute("href",g)});'
          'document.readyState==="loading"?document.addEventListener("DOMContentLoaded",run):run()})()</script>')
    return (f'<nav class="site" aria-label="사이트 메뉴">{links}</nav>\n  ' if links else "") + js

def site_nav(t, cur, built):
    return t.replace("__NAV__", nav_html(cur, built), 1)

def full(t, hd=HEAD):
    t = t.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "")
    return hd + t.replace('<div class="wrap">', '</head><body>\n<div class="wrap">', 1) + "\n</body></html>\n"

# ── 가격 변동(S3)·바뀐 것(S4). 자료는 트렌드 담당(NAS 일꾼)이 만든다. 파일이 없으면 관련 화면을 만들지 않는다
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PH_MAX = 104   # price_history.json 의 병당 최대 점 수(주 1회 × 2년)
PH_KEEP = 12   # index.html 에는 병마다 최근 12점만 싣는다
CHG_TYPES = ("new", "tier", "price", "trend", "removed")   # 화면에 보이는 순서
TIER_ORDER = "SABCDEN"

def _date_ok(s):
    if not isinstance(s, str) or not DATE_RE.match(s): return False
    try: datetime.date.fromisoformat(s); return True
    except ValueError: return False

def load_price_history(ids):
    """data/price_history.json: {"<병 id>": [["YYYY-MM-DD", 원], …]} 측정일 오름차순. 없으면 (None, [])"""
    p = os.path.join(ROOT, "data", "price_history.json")
    if not os.path.exists(p): return None, []
    try:
        with open(p, encoding="utf-8") as f: ph = json.load(f)
    except Exception as e: return None, [f"price_history.json 읽기 실패({e.__class__.__name__})"]
    if not isinstance(ph, dict): return None, ["price_history.json: 최상위가 {병 id: [[날짜, 가격], …]} 객체가 아님"]
    errs = []
    for k, pts in ph.items():
        if k not in ids: errs.append(f"price_history.json: bottles.json 에 없는 병 id {k}"); continue
        if not isinstance(pts, list) or not pts: errs.append(f"price_history.json {k}: 점 목록이 비었거나 목록이 아님"); continue
        if len(pts) > PH_MAX: errs.append(f"price_history.json {k}: 점 {len(pts)}개(최대 {PH_MAX})")
        prev = ""
        for x in pts:
            if not (isinstance(x, list) and len(x) == 2 and _date_ok(x[0]) and isinstance(x[1], int) and not isinstance(x[1], bool) and x[1] > 0):
                errs.append(f"price_history.json {k}: 형식이 [\"YYYY-MM-DD\", 양의 정수 원]이 아닌 점 {x!r}"); break
            if x[0] <= prev: errs.append(f"price_history.json {k}: 측정일이 오름차순이 아님({prev} 다음 {x[0]})"); break
            prev = x[0]
    return ph, errs

def ph_stats(ph, order):
    """index.html 용 압축: 점이 2개 이상인 병만, 최근 PH_KEEP 점.
    d = 공통 날짜 축(오름차순), u = 값 단위(모든 가격이 100원 단위면 100, 아니면 1).
    v = 병 목록(DATA.whiskies) 순서와 같은 배열. 이력이 없는 병은 0, 있는 병은 [첫 점의 날짜 번호, 첫 값, 다음 날짜 값−직전 값, …]
    — 날짜 축을 한 칸씩 따라가며 그 병의 측정이 없는 날은 null. 병 id 를 다시 싣지 않아 용량이 작다"""
    keep = {k: v[-PH_KEEP:] for k, v in ph.items() if len(v) >= 2}
    d = sorted({x[0] for v in keep.values() for x in v}); ix = {s: i for i, s in enumerate(d)}
    u = 100 if all(x[1] % 100 == 0 for v in keep.values() for x in v) else 1
    out = {}
    for k, v in keep.items():
        m = {ix[x[0]]: x[1] // u for x in v}; i0, i1 = ix[v[0][0]], ix[v[-1][0]]
        row, prev = [i0, m[i0]], m[i0]
        for i in range(i0 + 1, i1 + 1):
            if i in m: row.append(m[i] - prev); prev = m[i]
            else: row.append(None)
        out[k] = row
    return {"d": d, "u": u, "v": [out.get(k, 0) for k in order]} if out else None

def load_changes(ids):
    """data/changes.json: [{"date","type","id","from","to"}, …] 최근 12주치. 없으면 (None, [])"""
    p = os.path.join(ROOT, "data", "changes.json")
    if not os.path.exists(p): return None, []
    try:
        with open(p, encoding="utf-8") as f: cs = json.load(f)
    except Exception as e: return None, [f"changes.json 읽기 실패({e.__class__.__name__})"]
    if not isinstance(cs, list): return None, ["changes.json: 최상위가 목록이 아님"]
    errs, num = [], (lambda v: isinstance(v, (int, float)) and not isinstance(v, bool))
    for i, c in enumerate(cs):
        w = f"changes.json [{i}]"
        if not isinstance(c, dict): errs.append(f"{w}: 객체가 아님"); continue
        if not _date_ok(c.get("date")): errs.append(f"{w}: date 가 YYYY-MM-DD 가 아님({c.get('date')!r})")
        ty = c.get("type")
        if ty not in CHG_TYPES: errs.append(f"{w}: type {ty!r} 은 {'/'.join(CHG_TYPES)} 가운데 하나여야 함"); continue
        if not isinstance(c.get("id"), str) or not c["id"]: errs.append(f"{w}: id 없음"); continue
        if ty != "removed" and c["id"] not in ids: errs.append(f"{w}: bottles.json 에 없는 병 id {c['id']}(removed 만 허용)")
        fr, to = c.get("from"), c.get("to")
        if ty == "tier" and not (fr in list(TIER_ORDER) and to in list(TIER_ORDER) and fr != to): errs.append(f"{w}: tier 의 from/to 는 서로 다른 티어 글자(S~E, N)여야 함")
        if ty == "price" and not (isinstance(fr, int) and isinstance(to, int) and fr > 0 and to > 0 and fr != to): errs.append(f"{w}: price 의 from/to 는 서로 다른 양의 정수(원)여야 함")
        if ty == "trend" and not (num(fr) and num(to) and fr != to): errs.append(f"{w}: trend 의 from/to 는 서로 다른 숫자여야 함")
    return cs, errs

def chg_latest(cs):
    """가장 최근 측정일과 그날의 건수(티어표 머리말 링크용)"""
    if not cs: return None
    d = max(c["date"] for c in cs)
    return {"d": d, "n": sum(1 for c in cs if c["date"] == d)}

# ── 많이 본 병(S7). 집계는 Cloudflare Pages Functions(functions/api/v.js·top.js)+D1, 빌드는 tools/fetch_views.py 가 받은 data/views.json 만 읽는다.
# 티어·종합 점수·트렌드지수 계산에는 넣지 않는다. 횟수는 화면에 싣지 않고 순위만 보인다
VW_MIN, VW_TOP, VW_SHOW_MIN = 5, 10, 5   # 이 횟수 미만인 병은 제외 / 상위 몇 개 / 순위에 든 병이 이보다 적으면 구역 없음
IDS_JS = os.path.join("functions", "api", "_ids.js")

def load_views():
    """data/views.json: {"week": "YYYY-MM-DD" 또는 null, "to": 선택, "top": [[병 id, 횟수], …]}. 없으면 (None, [])"""
    p = os.path.join(ROOT, "data", "views.json")
    if not os.path.exists(p): return None, []
    try:
        with open(p, encoding="utf-8") as f: v = json.load(f)
    except Exception as e: return None, [f"views.json 읽기 실패({e.__class__.__name__})"]
    errs = []
    if not isinstance(v, dict) or not isinstance(v.get("top"), list): return None, ["views.json: {\"week\", \"top\": [[id, 횟수], …]} 형식이 아님"]
    if v.get("week") is not None and not _date_ok(v.get("week")): errs.append(f"views.json: week 가 YYYY-MM-DD 나 null 이 아님({v.get('week')!r})")
    if v.get("to") is not None and not _date_ok(v.get("to")): errs.append(f"views.json: to 가 YYYY-MM-DD 가 아님({v.get('to')!r})")
    for x in v["top"]:
        if not (isinstance(x, list) and len(x) == 2 and isinstance(x[0], str) and isinstance(x[1], int) and not isinstance(x[1], bool) and x[1] >= 0):
            errs.append(f"views.json: top 의 항목 {x!r} 이 [병 id, 0 이상 정수]가 아님"); break
    return v, errs

def views_block(v, ws):
    """changes.html 맨 위 "이번 주 많이 본 병": 횟수 VW_MIN 이상·지금 목록에 있는 병만, 순위만(숫자 없음). VW_SHOW_MIN 개 미만이면 빈 문자열"""
    if not v or not v.get("week"): return ""
    by = {w["id"]: w for w in ws}
    xs = [by[i] for i, n in v["top"] if n >= VW_MIN and i in by][:VW_TOP]
    if len(xs) < VW_SHOW_MIN: return ""
    li = "".join(f'<li><a class="nm" href="./#b={esc_attr(w["id"])}">{esc_attr(w["ko"])}</a></li>' for w in xs)
    rng = f'{v["week"]} ~ {v["to"]}' if v.get("to") else f'{v["week"]}부터 7일'
    return (f'<section class="views" aria-labelledby="vh"><h2 id="vh">이번 주 많이 본 병 <small>{rng}</small></h2><ol>{li}</ol>'
            '<p class="vnote">티어표에서 병 상세를 연 횟수의 순위입니다. 평가가 아니며 티어·종합 점수·트렌드지수 계산에 넣지 않습니다.</p></section>')

def write_ids_js(bottles):
    """functions/api/v.js 가 대조할 유효 병 id 목록(옛 병·미평가 병 포함). functions/api 폴더가 있을 때만 쓴다"""
    d = os.path.join(ROOT, "functions", "api")
    if not os.path.isdir(d): return None
    ids = sorted(b["id"] for b in bottles)
    s = ("// build.py 가 data/bottles.json 으로 만드는 파일 — 손으로 고치지 않는다. functions/api/v.js 가 병 id 를 대조한다\n"
         f"export const IDS = new Set({json.dumps(ids, separators=(',', ':'))});\n")
    p = os.path.join(ROOT, IDS_JS)
    old = open(p, encoding="utf-8").read() if os.path.exists(p) else None
    if old != s:
        with open(p, "w", encoding="utf-8") as f: f.write(s)
    return len(ids)

CHG_DESC = "위스키 종합 티어표에서 측정일마다 새로 들어온 병, 티어가 바뀐 병, 데일리샷 가격과 트렌드지수가 바뀐 병을 모아 보여 줍니다."
CH_HEAD = head("위스키 티어표 — 최근 바뀐 것", CHG_DESC, "https://nidwolf.com/changes")
CHG_TITLE = {"new": "새로 들어온 병", "tier": "티어가 바뀐 병", "price": "가격이 바뀐 병", "trend": "트렌드지수가 바뀐 병", "removed": "목록에서 빠진 병"}

def _fmt_num(v):
    return f"{v:,.1f}".rstrip("0").rstrip(".") if isinstance(v, float) else f"{v:,}"

def render_changes(cs, ws, gl, views=None):
    """changes.html: 측정일(최근 먼저)마다 종류별 목록. 병 이름은 티어표 상세 ./#b=<id> 로 잇는다(빠진 병은 링크 없음)"""
    by = {w["id"]: w for w in ws}
    def name(c):
        w = by.get(c["id"])
        if not w: return f'<span class="nm">{esc_attr(c.get("ko") or c.get("name") or c["id"])}</span>'
        return f'<a class="nm" href="./#b={esc_attr(w["id"])}">{esc_attr(w["ko"])}</a>'
    def tag(w):
        return f'<span class="tt t-{w["tier"]}">{"미평가" if w["tier"] == "N" else w["tier"]}</span>' if w else ""
    def line(c):
        w, ty, fr, to = by.get(c["id"]), c["type"], c.get("from"), c.get("to")
        if ty == "new": d = f'{tag(w)}<span class="dv">{"" if not w or w["score"] is None else str(w["score"]) + "점"}</span>'
        elif ty == "tier":
            up = TIER_ORDER.index(to) < TIER_ORDER.index(fr)
            d = f'<span class="dv {"up" if up else "dn"}"><span aria-hidden="true">{"▲" if up else "▼"}</span><span class="sr">{"오름" if up else "내림"}</span> {fr} → {to}</span>'
        elif ty == "price":
            df = to - fr; pc = df / fr * 100
            d = f'<span class="dv">{fr:,}원 → {to:,}원 <b>{"+" if df > 0 else "−"}{abs(df):,}원</b> ({"+" if df > 0 else "−"}{abs(pc):.1f}%)</span>'
        elif ty == "trend":
            df = round(to - fr, 1)
            d = f'<span class="dv">{_fmt_num(fr)} → {_fmt_num(to)} <b>{"+" if df > 0 else "−"}{_fmt_num(abs(df))}</b></span>'
        else: d = ""
        return f"<li>{name(c)}{d}</li>"
    def key(c):
        ty, fr, to = c["type"], c.get("from"), c.get("to")
        if ty == "price": return -abs((to - fr) / fr)
        if ty == "trend": return -abs(to - fr)
        if ty == "tier": return (TIER_ORDER.index(to) - TIER_ORDER.index(fr), TIER_ORDER.index(to))
        return 0
    days = sorted({c["date"] for c in cs}, reverse=True)
    secs = []
    for d in days:
        g = [c for c in cs if c["date"] == d]
        parts = []
        for ty in CHG_TYPES:
            xs = sorted((c for c in g if c["type"] == ty), key=lambda c: (key(c), by[c["id"]]["ko"] if c["id"] in by else c["id"]))
            if not xs: continue
            parts.append(f'<section class="cg"><h3>{CHG_TITLE[ty]} <small>{len(xs)}</small></h3><ul>{"".join(line(c) for c in xs)}</ul></section>')
        secs.append(f'<section class="day" id="d-{d}" aria-labelledby="h-{d}"><h2 id="h-{d}">{d} 측정 <small>{len(g)}건</small></h2>{"".join(parts)}</section>')
    body = "".join(secs) or '<p class="empty">아직 기록된 변동이 없습니다.</p>'
    tl = '<a href="glossary.html#g-tier">티어</a>' if gl else "티어"
    with open(os.path.join(ROOT, "tools", "changes_template.html"), encoding="utf-8") as f: t = f.read()
    return (t.replace("__TOKENS__", tokens_css()).replace("__DAYS__", body).replace("__TIERLINK__", tl)
             .replace("__WEEKS__", str(len(days))).replace("__VIEWS__", views_block(views, ws)))

# 트렌드지수 원자료: 재료 key → trends.json raw 의 대표 값. trends.json 에 "raw_keys" 가 있으면 그것을 쓴다
RAW_KEYS = {"ds": "ds_reviews", "wiki": "wiki_en", "src": "src_en"}
TREND_FLAGS = {"ds_no_product", "wiki_no_article", "wiki_unsure", "no_brand"}   # 화면에서 쓰는 점검 표시

def add_trends(ws):
    """data/trends.json(트렌드 담당 산출물)을 읽어 병마다 트렌드지수를 붙인다. 티어 점수 계산(compute)과 무관하다.
    파일이 없거나 형식이 어긋나도 빌드는 계속한다. bottles.json 에 없는 id(등록 대기 병)는 건너뛴다."""
    p = os.path.join(ROOT, "data", "trends.json")
    if not os.path.exists(p): return None, "trends.json 없음"
    try:
        with open(p, encoding="utf-8") as f: t = json.load(f)
        tb = t.get("bottles") or {}
        weights = t.get("weights") or {}
    except Exception as e:
        return None, f"trends.json 읽기 실패({e.__class__.__name__}) — 지수 없이 빌드"
    rk = {**RAW_KEYS, **(t.get("raw_keys") or {})}
    n = nods = 0
    for w in ws:
        x = tb.get(w["id"])
        if not isinstance(x, dict) or not isinstance(x.get("index"), (int, float)): continue
        raw, parts = x.get("raw") or {}, x.get("parts") or {}
        flags = [f for f in (x.get("flags") or []) if f in TREND_FLAGS]
        w["tr"] = {"i": round(x["index"]), "d": x.get("domestic"), "o": x.get("overseas"), "brand": x.get("brand"),
                   "p": {k: [parts.get(k), raw.get(rk.get(k, ""))] for k in weights},
                   "wt": raw.get("wiki_title"), "dsp": raw.get("ds_products"), "f": flags, "m": x.get("measured")}
        n += 1; nods += "ds_no_product" in flags
    keep = ("measured", "formula", "formula_note", "weights", "scales", "materials", "domestic_parts")
    info = {k: t.get(k) for k in keep}
    info.update(n=n, nods=nods, pending=sum(1 for k in tb if k not in {w["id"] for w in ws}))
    return info, f"트렌드지수 {n}병(국내 판매 자료 없음 {nods}) · 미등록 {info['pending']}병 건너뜀 · 측정 {t.get('measured')} · 산식 {t.get('formula')}"

# ───────────── 칵테일 제조법 페이지(cocktails.html) ─────────────
# data/cocktails.json(레시피)과 tools/cocktails_template.html 이 있을 때만 만든다. 잔 그림은 여기서 정적 SVG로 그린다(JS 없이도 보이게)
GLASS_KO = {"rocks": "록스 잔", "highball": "하이볼 잔", "coupe": "쿠페 잔", "martini": "마티니 잔", "mug": "머그", "julep": "줄렙 컵", "wine": "와인 잔", "shot": "샷 잔"}
METHOD_KO = {"build": "빌드(잔에 바로)", "stir": "스터(저어서)", "shake": "셰이크(흔들어서)", "hot": "따뜻하게"}
ICE_KO = {"none": "얼음 없음", "cube": "각얼음", "large": "큰 얼음", "crushed": "간 얼음"}
DIFF_KO = {1: "쉬움", 2: "보통", 3: "어려움"}
TYPE_KO = {"SM": "싱글몰트 스카치", "BL": "블렌디드 스카치", "BB": "버번", "RY": "라이·아메리칸", "IR": "아이리시", "JP": "재패니즈", "WD": "월드"}
ING_KINDS = {"whiskey", "liqueur", "vermouth", "juice", "syrup", "sugar", "soda", "bitters", "egg", "dairy", "coffee", "water", "other"}
HEX6 = re.compile(r"^#[0-9a-fA-F]{6}$")
CK_SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

CK_GROUP_KINDS = ["술", "리큐어", "주스·과일", "시럽·설탕", "탄산·음료", "기타"]   # "가진 재료로 찾기" 칩 줄 순서
# 위스키 재료 묶음 → 티어표 종류(빠진 위스키에서 티어표로 가는 링크). 테네시는 라이·아메리칸, 아일라는 싱글몰트
CK_GROUP_TYPE = {"bourbon": "BB", "rye": "RY", "tennessee": "RY", "scotch-blended": "BL", "scotch-malt": "SM", "scotch-islay": "SM", "irish": "IR", "japanese": "JP"}

def load_cocktail_groups():
    p = os.path.join(ROOT, "data", "cocktail_groups.json")
    if not os.path.exists(p): return None, []
    try:
        with open(p, encoding="utf-8") as f: gs = json.load(f)
    except Exception as e:
        return None, [f"cocktail_groups.json 읽기 실패: {e}"]
    errs = []
    if not isinstance(gs, list): return None, ["cocktail_groups.json 은 배열이어야 함"]
    for i, n in collections.Counter(g.get("id") for g in gs if isinstance(g, dict)).items():
        if n > 1: errs.append(f"재료 묶음 id 중복: {i}")
    for g in gs:
        if not isinstance(g, dict) or not all(k in g for k in ("id", "ko", "kind", "common")): errs.append(f"재료 묶음 필드 없음: {g!r}"); continue
        if not isinstance(g["id"], str) or not CK_SLUG.match(g["id"]): errs.append(f"재료 묶음 {g['id']!r}: id 는 영문 소문자·숫자·하이픈만")
        if g["kind"] not in CK_GROUP_KINDS: errs.append(f"재료 묶음 {g['id']}: kind 값 오류 {g['kind']!r} (허용 {CK_GROUP_KINDS})")
        if not isinstance(g["common"], bool): errs.append(f"재료 묶음 {g['id']}: common 은 true/false")
        if not isinstance(g["ko"], str) or not g["ko"].strip(): errs.append(f"재료 묶음 {g['id']}: ko 가 빈 값")
    return gs, errs

def check_cocktail_groups(cs, gs):
    """재료의 groups(그중 하나만 있어도 됨)·optional 검사. 묶음 파일이 없는데 groups 를 쓰면 오류"""
    errs, ids = [], {g["id"] for g in (gs or []) if isinstance(g, dict) and "id" in g}
    for c in cs if isinstance(cs, list) else []:
        for j, x in enumerate(c.get("ingredients") or [], 1):
            if not isinstance(x, dict): continue
            nm = f"칵테일 {c.get('id')}: 재료 {j}({x.get('ko')})"
            if "groups" in x:
                if gs is None: errs.append(f"{nm}: groups 가 있는데 data/cocktail_groups.json 이 없음"); continue
                if not isinstance(x["groups"], list) or not x["groups"]: errs.append(f"{nm}: groups 는 묶음 id 배열(1개 이상)")
                else:
                    bad = [g for g in x["groups"] if g not in ids]
                    if bad: errs.append(f"{nm}: cocktail_groups.json 에 없는 묶음 {bad}")
            if "optional" in x and not isinstance(x["optional"], bool): errs.append(f"{nm}: optional 은 true/false ({x['optional']!r})")
            if ("groups" in x) != ("optional" in x): errs.append(f"{nm}: groups 와 optional 은 함께 넣는다")
    return errs

def check_step_adds(c):
    """만드는 법 단계-재료 대응(스크롤 연출용). 없으면 검사하지 않는다(임시로 모든 재료를 첫 단계에 둔다)"""
    errs, e = [], None
    if not any(k in c for k in ("step_adds", "ice_step", "garnish_step")): return errs
    cid = c.get("id"); m = len(c.get("steps") or []); n = len(c.get("ingredients") or [])
    sa = c.get("step_adds")
    if not isinstance(sa, list) or len(sa) != m: errs.append(f"칵테일 {cid}: step_adds 는 steps 와 같은 길이({m})의 배열이어야 함")
    else:
        flat = [i for x in sa if isinstance(x, list) for i in x]
        if any(not isinstance(x, list) for x in sa) or any(type(i) is not int for i in flat): errs.append(f"칵테일 {cid}: step_adds 의 각 칸은 재료 순번(정수) 배열")
        elif sorted(flat) != list(range(n)): errs.append(f"칵테일 {cid}: step_adds 에 재료 순번 0~{n - 1} 이 빠짐없이 한 번씩 있어야 함 ({flat})")
        elif flat != sorted(flat): errs.append(f"칵테일 {cid}: step_adds 의 재료 순번은 단계 순서대로 줄어들지 않아야 함 ({flat})")
    ist = c.get("ice_step", -1)
    if type(ist) is not int or not (-1 <= ist < m): errs.append(f"칵테일 {cid}: ice_step 은 -1(얼음 없는 잔) 또는 0~{m - 1} ({ist!r})")
    elif (c.get("ice") == "none") != (ist == -1): errs.append(f"칵테일 {cid}: ice 가 none 이면 ice_step 은 -1, 얼음이 있으면 0~{m - 1} 이어야 함 (ice={c.get('ice')!r}, ice_step={ist})")
    gst = c.get("garnish_step")
    if gst is not None and (type(gst) is not int or not (0 <= gst < m)): errs.append(f"칵테일 {cid}: garnish_step 은 null 또는 0~{m - 1} ({gst!r})")
    return errs

def check_cocktails(cs):
    """cocktails.json 검증. 오류 문장 목록을 돌려준다"""
    if not isinstance(cs, list): return ["cocktails.json 은 배열이어야 함"]
    errs = []
    for i, n in collections.Counter(c.get("id") for c in cs if isinstance(c, dict)).items():
        if n > 1: errs.append(f"칵테일 id 중복: {i}")
    for c in cs:
        if not isinstance(c, dict): errs.append(f"칵테일 항목이 객체가 아님: {c!r}"); continue
        cid = c.get("id") or "?"; e = lambda m: errs.append(f"칵테일 {cid}: {m}")
        miss = [k for k in ("id", "ko", "en", "base", "glass", "method", "ice", "difficulty", "taste", "ingredients", "garnish", "steps", "sources") if k not in c]
        if miss: e(f"필수 필드 없음 {miss}"); continue
        if not isinstance(c["id"], str) or not CK_SLUG.match(c["id"]): e("id 는 영문 소문자·숫자·하이픈만")
        for k in ("ko", "en"):
            if not isinstance(c[k], str) or not c[k].strip(): e(f"{k} 가 빈 문자열")
        if not isinstance(c["base"], list) or not c["base"] or set(c["base"]) - TYPES: e(f"base 값 오류 {c['base']!r} (허용 {sorted(TYPES)})")
        if c["glass"] not in GLASS_KO: e(f"glass 값 오류 {c['glass']!r}")
        if c["method"] not in METHOD_KO: e(f"method 값 오류 {c['method']!r}")
        if c["ice"] not in ICE_KO: e(f"ice 값 오류 {c['ice']!r}")
        if type(c["difficulty"]) is not int or c["difficulty"] not in DIFF_KO: e(f"difficulty 는 1~3 정수 ({c['difficulty']!r})")
        for k in ("taste", "garnish", "steps"):
            if not isinstance(c[k], list) or not all(isinstance(x, str) and x.strip() for x in c[k]): e(f"{k} 는 문자열 배열")
        if isinstance(c["steps"], list) and not c["steps"]: e("steps 가 비어 있음")
        if "tip" in c and c["tip"] is not None and not isinstance(c["tip"], str): e("tip 은 문자열")
        ing = c["ingredients"]
        if not isinstance(ing, list) or not ing: e("ingredients 가 비어 있음"); ing = []
        for j, x in enumerate(ing, 1):
            if not isinstance(x, dict): e(f"재료 {j}: 객체가 아님"); continue
            m = [k for k in ("ko", "en", "ml", "amount", "kind", "color") if k not in x]
            if m: e(f"재료 {j}: 필드 없음 {m}"); continue
            if x["ml"] is not None and (isinstance(x["ml"], bool) or not isinstance(x["ml"], (int, float)) or x["ml"] <= 0): e(f"재료 {j}({x['ko']}): ml 은 양수 또는 null ({x['ml']!r})")
            if x["kind"] not in ING_KINDS: e(f"재료 {j}({x['ko']}): kind 값 오류 {x['kind']!r}")
            if not isinstance(x["color"], str) or not HEX6.match(x["color"]): e(f"재료 {j}({x['ko']}): color 는 #rrggbb ({x['color']!r})")
            if not isinstance(x["amount"], str) or not x["amount"].strip(): e(f"재료 {j}({x['ko']}): amount 가 빈 값")
        if isinstance(c["steps"], list) and isinstance(c["ingredients"], list): errs.extend(check_step_adds(c))
        if not isinstance(c["sources"], list): e("sources 는 배열")
        else:
            for s in c["sources"]:
                if not isinstance(s, dict) or not s.get("name") or not str(s.get("url", "")).startswith("https://"): e(f"출처는 name 과 https:// url 이 있어야 함 ({s!r})")
    return errs

# 잔 안쪽 단면: y(바닥에서 높이) → 반지름 r. 회전체로 보고 층 경계를 부피로 나눈다
#   H 안쪽 높이, wall 벽 두께, base 바닥 두께(텀블러형), stem 다리 길이(다리 있는 잔), foot 받침 반폭
GLASS_SHAPES = {
    "rocks":    dict(H=104, r=lambda t: 44 + 8 * t, wall=5, base=16),
    "highball": dict(H=176, r=lambda t: 30 + 4 * t, wall=4, base=14),
    "shot":     dict(H=72,  r=lambda t: 21 + 6 * t, wall=5, base=20),
    "mug":      dict(H=118, r=lambda t: 42.0, wall=5, base=10, handle=True),
    "julep":    dict(H=128, r=lambda t: 36 + 6 * t, wall=4, base=10, ridge=True),
    "coupe":    dict(H=46,  r=lambda t: 64 * max(0.0, 2 * t - t * t) ** 0.5, wall=4, stem=82, foot=46),
    "martini":  dict(H=76,  r=lambda t: 3 + 64 * t, wall=4, stem=86, foot=44),
    "wine":     dict(H=92,  r=lambda t: 56 * t ** 0.5 * (1 - 0.32 * t * t), wall=4, stem=66, foot=42),
}
CK_FILL = 0.82          # 잔 부피 중 채우는 비율(모든 잔 공통). 층 비율은 이 안에서 재료 양에 비례
CK_N = 400              # 단면 표본 수
CK_GROUND, CK_CX, CK_W = 236, 100, 360

def glass_geom(g):
    s = GLASS_SHAPES[g]; H = s["H"]
    ys = [H * i / CK_N for i in range(CK_N + 1)]
    rs = [s["r"](y / H) for y in ys]
    cum = [0.0]
    for i in range(CK_N):   # 원뿔대 부피
        h, a, b = ys[i + 1] - ys[i], rs[i], rs[i + 1]
        cum.append(cum[-1] + math.pi * h * (a * a + a * b + b * b) / 3)
    y0 = CK_GROUND - (s.get("base") or 0) - ((s["stem"] + 6) if s.get("stem") else 0)   # 안쪽 바닥의 SVG y
    return dict(s=s, H=H, ys=ys, rs=rs, cum=cum, Y0=y0)

def _r_at(G, y):
    i = min(CK_N - 1, max(0, int(y / G["H"] * CK_N))); y1, y2 = G["ys"][i], G["ys"][i + 1]
    return G["rs"][i] + (G["rs"][i + 1] - G["rs"][i]) * ((y - y1) / (y2 - y1) if y2 > y1 else 0)

def _h_for_volume(G, v):
    """안쪽 바닥부터 부피 v 가 차는 높이(표본 구간 안에서 선형 보간)"""
    cum = G["cum"]
    if v <= 0: return 0.0
    if v >= cum[-1]: return G["H"]
    lo, hi = 0, CK_N
    while hi - lo > 1:
        m = (lo + hi) // 2
        (lo, hi) = (m, hi) if cum[m] <= v else (lo, m)
    return G["ys"][lo] + (G["ys"][hi] - G["ys"][lo]) * (v - cum[lo]) / (cum[hi] - cum[lo])

def volume_between(G, a, b):
    """높이 a~b 사이 부피(검증용, 원뿔대 합)"""
    n = 2000; tot = 0.0
    for i in range(n):
        y1, y2 = a + (b - a) * i / n, a + (b - a) * (i + 1) / n; r1, r2 = _r_at(G, y1), _r_at(G, y2)
        tot += math.pi * (y2 - y1) * (r1 * r1 + r1 * r2 + r2 * r2) / 3
    return tot

def layer_bounds(G, mls):
    """재료 양(ml) 목록 → 각 층의 (아래 높이, 위 높이). 경계는 부피 기준"""
    tot = sum(mls); cap = G["cum"][-1] * CK_FILL; out, acc = [], 0.0
    for m in mls:
        a = _h_for_volume(G, cap * acc / tot); acc += m; b = _h_for_volume(G, cap * acc / tot)
        out.append((a, b))
    return out

def _f(v): return f"{v:.1f}".rstrip("0").rstrip(".")

def _side(G, a, b, sign, off=0.0):
    """높이 a→b 를 따라가는 한쪽 벽의 점들(sign -1 왼쪽, +1 오른쪽)"""
    pts, ys = [], [a] + [y for k, y in enumerate(G["ys"]) if k % 10 == 0 and a < y < b] + [b]   # 그릴 때는 40구간이면 충분(부피 계산은 400구간)
    for y in ys: pts.append((CK_CX + sign * (_r_at(G, y) + off), G["Y0"] - y))
    return pts

def _poly(pts): return "M" + " L".join(f"{_f(x)},{_f(y)}" for x, y in pts) + "Z"

def _rgb(h): return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))

def _textw(t, fs=12):
    return sum(fs * (1.0 if ord(ch) > 0x1100 else 0.58) for ch in t)

def _garnish_svg(G, garnish):
    if not garnish: return ""
    g = " ".join(garnish); x = CK_CX + _r_at(G, G["H"]) + G["s"]["wall"] - 6; y = G["Y0"] - G["H"]; out = []
    citrus = next(((c, k) for k, c in (("레몬", "#f4d53c"), ("라임", "#8cc63f"), ("오렌지", "#f39a2b"), ("자몽", "#f07b5a")) if k in g), None)
    if citrus:
        c = citrus[0]
        if "껍질" in g.split(citrus[1], 1)[1][:4]:   # 껍질: 잔 가장자리에 걸친 꼬인 띠
            out.append(f'<path d="M{_f(x-14)},{_f(y+8)} q8,-22 18,-6 q8,12 16,-8" fill="none" stroke="{c}" stroke-width="6" stroke-linecap="round"/>'
                       f'<path d="M{_f(x-14)},{_f(y+8)} q8,-22 18,-6 q8,12 16,-8" fill="none" stroke="currentColor" stroke-opacity=".55" stroke-width="1.2" stroke-linecap="round"/>')
        else:                                       # 조각·슬라이스: 잔에 꽂힌 둥근 단면
            out.append(f'<g transform="translate({_f(x+2)},{_f(y-2)})"><circle r="13" fill="{c}" stroke="currentColor" stroke-width="2.4"/><circle r="9" fill="#fff8df" fill-opacity=".75"/>'
                       + "".join(f'<line x1="0" y1="0" x2="{_f(9*math.cos(a))}" y2="{_f(9*math.sin(a))}" stroke="{c}" stroke-width="1.6"/>' for a in [k * math.pi / 3 for k in range(6)]) + "</g>")
    if "체리" in g:
        cx, cy = CK_CX - _r_at(G, G["H"]) * 0.35, y - 6
        out.append(f'<path d="M{_f(cx)},{_f(cy-6)} q4,-16 14,-20" fill="none" stroke="#3d6b2a" stroke-width="2.4" stroke-linecap="round"/><circle cx="{_f(cx)}" cy="{_f(cy)}" r="7" fill="#b3122e" stroke="currentColor" stroke-width="2.2"/><circle cx="{_f(cx-2.5)}" cy="{_f(cy-2.5)}" r="1.8" fill="#fff" fill-opacity=".8"/>')
    if "민트" in g:
        cx, cy = CK_CX + 6, y - 8
        out.append(f'<path d="M{_f(cx)},{_f(cy+10)} c-14,-4 -16,-18 -6,-24 c6,8 10,16 6,24z M{_f(cx)},{_f(cy+10)} c12,-6 18,-16 10,-24 c-8,6 -12,14 -10,24z" fill="#4caf50" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>')
    return "".join(out)

def _ice_svg(G, ice, htop):
    if ice == "none" or htop <= 0: return ""
    out, rnd = [], 0
    def cube(cx, cy, s, rot):
        return (f'<rect x="{_f(cx-s/2)}" y="{_f(cy-s/2)}" width="{_f(s)}" height="{_f(s)}" rx="{_f(s*0.22)}" transform="rotate({rot} {_f(cx)} {_f(cy)})" '
                f'fill="#ffffff" fill-opacity=".16" stroke="#ffffff" stroke-opacity=".9" stroke-width="1.8"/>'
                f'<rect x="{_f(cx-s/2-1.2)}" y="{_f(cy-s/2-1.2)}" width="{_f(s+2.4)}" height="{_f(s+2.4)}" rx="{_f(s*0.24)}" transform="rotate({rot} {_f(cx)} {_f(cy)})" fill="none" stroke="#000" stroke-opacity=".22" stroke-width="1"/>')
    if ice == "large":
        r = _r_at(G, htop); s = min(46, r * 1.25, htop * 0.9)
        out.append(cube(CK_CX, G["Y0"] - htop + s * 0.42, s, -6))
    elif ice == "cube":
        s = 22 if G["H"] > 60 else 16; rots = [-12, 8, -4, 14]
        rows = [htop - s * 0.35, htop - s * 1.35] if G["H"] > 120 else [htop - s * 0.35]
        for k, hy in enumerate(rows):
            if hy - s / 2 < 4: continue
            r = _r_at(G, hy) - 4; n = max(1, min(3, int((2 * r) // (s + 5))))
            for j in range(n):
                cx = CK_CX - (n - 1) * (s + 5) / 2 + j * (s + 5) + (k % 2) * 5
                out.append(cube(cx, G["Y0"] - hy, s, rots[(j + k) % 4]))
    else:  # crushed
        import random
        rg = random.Random(7)
        for _ in range(int(G["H"] * 0.5)):
            hy = htop - rg.random() * min(htop, G["H"] * 0.55); r = max(2, _r_at(G, hy) - 6)
            out.append(cube(CK_CX + (rg.random() * 2 - 1) * r, G["Y0"] - hy, 6 + rg.random() * 4, rg.randint(-30, 30)))
    return "".join(out)

def glass_svg(c, labels=True):
    """칵테일 하나의 잔 그림 SVG. labels=False 면 목록 카드용 작은 그림(라벨·칩 없음)"""
    G = glass_geom(c["glass"]); s = G["s"]; H, Y0, w = G["H"], G["Y0"], s["wall"]
    ings = c["ingredients"]; num = lambda i: chr(0x2460 + i) if i < 20 else f"({i+1})"
    lay = [(i, x) for i, x in enumerate(ings) if x["ml"] is not None]
    chips = [(i, x) for i, x in enumerate(ings) if x["ml"] is None]
    tot = sum(x["ml"] for _, x in lay) or 1
    bounds = layer_bounds(G, [x["ml"] for _, x in lay]) if lay else []
    htop = bounds[-1][1] if bounds else 0
    o = []
    # 잔 몸통(유리 바탕): 바깥선 안쪽을 옅게 칠한다
    if s.get("stem"):
        L = _side(G, 0, H, -1, w)[::-1]; R = _side(G, 0, H, 1, w)
        sw = 4.5; fy = CK_GROUND; ft = fy - 6; f = s["foot"]
        body = L + [(CK_CX - sw, Y0 + w), (CK_CX - sw, ft), (CK_CX - f, ft + 1), (CK_CX - f, fy), (CK_CX + f, fy), (CK_CX + f, ft + 1), (CK_CX + sw, ft), (CK_CX + sw, Y0 + w)] + R
    else:
        L = _side(G, 0, H, -1, w)[::-1]; R = _side(G, 0, H, 1, w); b = s["base"]
        body = L + [(CK_CX - _r_at(G, 0) - w, Y0 + b)] + [(CK_CX + _r_at(G, 0) + w, Y0 + b)] + R
    if s.get("handle"):
        # 손잡이는 왼쪽에 둔다(오른쪽은 라벨 지시선이 지나가는 자리)
        xl = CK_CX - _r_at(G, 0) - w; ya, yb = Y0 - H * 0.82, Y0 - H * 0.2
        hp = f"M{_f(xl+2)},{_f(ya)} C{_f(xl-34)},{_f(ya-4)} {_f(xl-34)},{_f(yb+4)} {_f(xl+2)},{_f(yb)}"
        o.append(f'<path d="{hp}" fill="none" stroke="currentColor" stroke-width="13" stroke-linecap="round"/><path d="{hp}" fill="none" stroke="var(--bg)" stroke-width="6.5" stroke-linecap="round"/>'
                 f'<path d="{hp}" fill="none" stroke="currentColor" stroke-opacity=".08" stroke-width="6.5" stroke-linecap="round"/>')
    bodyd = "M" + " L".join(f"{_f(x)},{_f(y)}" for x, y in body)
    o.append(f'<path d="{bodyd}Z" fill="currentColor" fill-opacity=".07" stroke="none"/>')
    # 층: 넣는 순서대로 아래에서 위로, 부피 비례
    for k, ((i, x), (a, bb)) in enumerate(zip(lay, bounds)):
        o.append(f'<path d="{_poly(_side(G, a, bb, -1)[::-1] + _side(G, a, bb, 1))}" fill="{x["color"]}"/>')
        if x["kind"] == "soda" and bb - a > 14:   # 탄산 거품
            for j in range(int((bb - a) // 16)):
                yy = a + 8 + j * 16; rr = _r_at(G, yy) * 0.55
                for dx in ((-0.6, 0.15, 0.7) if j % 2 else (-0.25, 0.45)):
                    o.append(f'<circle cx="{_f(CK_CX + dx * rr)}" cy="{_f(Y0 - yy)}" r="2.2" fill="none" stroke="#ffffff" stroke-opacity=".95" stroke-width="1.2"/>')
    for k in range(1, len(lay)):   # 층 경계선: 색이 비슷하면 더 진하게(점선)
        y = bounds[k][0]; r = _r_at(G, y)
        c1, c2 = _rgb(lay[k - 1][1]["color"]), _rgb(lay[k][1]["color"]); near = sum((p - q) ** 2 for p, q in zip(c1, c2)) ** 0.5 < 70
        o.append(f'<line x1="{_f(CK_CX - r)}" y1="{_f(Y0 - y)}" x2="{_f(CK_CX + r)}" y2="{_f(Y0 - y)}" stroke="currentColor" stroke-opacity="{".75" if near else ".3"}" stroke-width="{1.6 if near else 1.1}"{" stroke-dasharray=\"5 3\"" if near else ""}/>')
    if lay:   # 맨 위 액면
        r = _r_at(G, htop); o.append(f'<line x1="{_f(CK_CX - r)}" y1="{_f(Y0 - htop)}" x2="{_f(CK_CX + r)}" y2="{_f(Y0 - htop)}" stroke="currentColor" stroke-opacity=".55" stroke-width="1.4"/>')
    o.append(_ice_svg(G, c["ice"], htop))
    # 안쪽 선(가늘게), 바깥선(굵게), 유리 하이라이트
    inner = _side(G, 0, H, -1)[::-1] + _side(G, 0, H, 1)
    o.append(f'<path d="M{" L".join(f"{_f(x)},{_f(y)}" for x, y in inner)}" fill="none" stroke="currentColor" stroke-opacity=".45" stroke-width="1.3" stroke-linejoin="round"/>')
    o.append(f'<path d="{bodyd}" fill="none" stroke="currentColor" stroke-width="3.4" stroke-linejoin="round" stroke-linecap="round"/>')
    if s.get("ridge"):
        for yy in (H - 10, 12):
            r = _r_at(G, yy) + w; o.append(f'<line x1="{_f(CK_CX - r)}" y1="{_f(Y0 - yy)}" x2="{_f(CK_CX + r)}" y2="{_f(Y0 - yy)}" stroke="currentColor" stroke-opacity=".5" stroke-width="1.6"/>')
    hl = [(CK_CX - _r_at(G, y) * 0.74, Y0 - y) for y in [H * (0.22 + 0.5 * k / 12) for k in range(13)] if _r_at(G, y) > 8]
    if len(hl) > 2:
        o.append(f'<path d="M{" L".join(f"{_f(x)},{_f(y)}" for x, y in hl)}" fill="none" stroke="#ffffff" stroke-opacity=".75" stroke-width="4" stroke-linecap="round"/>')
        y = H * 0.82; o.append(f'<line x1="{_f(CK_CX - _r_at(G, y) * 0.74)}" y1="{_f(Y0 - y)}" x2="{_f(CK_CX - _r_at(G, y) * 0.74)}" y2="{_f(Y0 - y + 5)}" stroke="#ffffff" stroke-opacity=".75" stroke-width="4" stroke-linecap="round"/>')
    o.append(_garnish_svg(G, c["garnish"]))
    summ = "아래부터 " + ", ".join(f"{num(i)} {x['ko']} {x['amount']}({round(x['ml'] / tot * 100)}%)" for i, x in lay) if lay else "층으로 쌓는 재료 없음"
    if chips: summ += ". 그 밖에 " + ", ".join(f"{num(i)} {x['ko']} {x['amount']}" for i, x in chips)
    if not labels:
        return f'<svg class="gl sm" viewBox="0 {_f(min(Y0 - H - 34, 40))} 200 {_f(CK_GROUND + 6 - min(Y0 - H - 34, 40))}" role="img" aria-label="{esc_attr(c["ko"])} 잔 그림. {esc_attr(summ)}"><title>{esc_html(summ)}</title>{"".join(o)}</svg>'
    # 라벨: 층 가운데 높이를 목표로, 위에서부터 겹치지 않게 내려 배치하고 아래로 넘치면 다시 올린다
    xedge = max(CK_CX + _r_at(G, y) + w for y in G["ys"])
    LX = max(xedge + 26, 204); GAP = 32
    tg = [Y0 - (a + bb) / 2 for a, bb in bounds][::-1]; items = lay[::-1]; bd = bounds[::-1]; ys = []
    for t in tg: ys.append(max(t, (ys[-1] + GAP) if ys else 24))
    for k in range(len(ys) - 1, -1, -1):
        ys[k] = min(ys[k], (ys[k + 1] - GAP) if k + 1 < len(ys) else CK_GROUND - 14)
    for (i, x), (a, bb), yl in zip(items, bd, ys):
        ym = Y0 - (a + bb) / 2; xe = CK_CX + _r_at(G, (a + bb) / 2)
        o.append(f'<path d="M{_f(xe)},{_f(ym)} L{_f(LX - 22)},{_f(ym)} L{_f(LX - 8)},{_f(yl)}" fill="none" stroke="currentColor" stroke-opacity=".6" stroke-width="1.2"/><circle cx="{_f(xe)}" cy="{_f(ym)}" r="2.6" fill="currentColor"/>')
        # 라벨 칸을 넘는 긴 이름·양은 괄호 설명을 빼거나 ml 값으로 줄인다(재료 표에는 원문 그대로 나온다)
        avail = CK_W - LX - 4; nm_, am = x["ko"], x["amount"]; pct = f" · {round(x['ml'] / tot * 100)}%"
        if _textw(f"{num(i)} {nm_}", 13) > avail: nm_ = re.sub(r"\s*\(.*?\)", "", nm_).strip() or nm_
        if _textw(am + pct, 12) > avail: am = f"{_f(x['ml'])}ml"
        o.append(f'<text x="{_f(LX)}" y="{_f(yl - 2)}" class="lb">{num(i)} {esc_html(nm_)}</text><text x="{_f(LX)}" y="{_f(yl + 13)}" class="la">{esc_html(am)}{pct}</text>')
    # ml 이 없는 재료: 잔 아래 칩(순서 번호 + 색 점 + 이름·양)
    yb = CK_GROUND + 14; x0 = 12; cy = yb; rows = 0
    if chips: rows = 1
    for i, x in chips:
        t = f"{num(i)} {x['ko']} {x['amount']}"; cw = _textw(t, 12) + 30
        if x0 + cw > CK_W - 8 and x0 > 12: x0 = 12; cy += 30; rows += 1
        o.append(f'<g class="chip"><rect x="{_f(x0)}" y="{_f(cy)}" width="{_f(cw)}" height="24" rx="12" fill="currentColor" fill-opacity=".06" stroke="currentColor" stroke-opacity=".45" stroke-width="1.2"/>'
                 f'<circle cx="{_f(x0 + 13)}" cy="{_f(cy + 12)}" r="5" fill="{x["color"]}" stroke="currentColor" stroke-width="1.2"/><text x="{_f(x0 + 23)}" y="{_f(cy + 16.5)}" class="lc">{esc_html(t)}</text></g>')
        x0 += cw + 8
    top = min([Y0 - H - 36] + ([ys[0] - 18] if ys else [])); hgt = (cy + 30 if rows else CK_GROUND + 8) - top
    return f'<svg class="gl" viewBox="0 {_f(top)} {CK_W} {_f(hgt)}" role="img" aria-label="{esc_attr(c["ko"])} 잔 그림. {esc_attr(summ)}"><title>{esc_html(summ)}</title>{"".join(o)}</svg>'

def esc_html(t): return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
def esc_attr(t): return esc_html(t).replace('"', "&quot;")

CK_NOTE = "그림은 넣는 순서(아래부터)와 양의 비율을 보여 줍니다. 실제로는 섞여서 색이 달라집니다."
CK_WARN = "이 페이지는 만 19세 이상을 위한 정보입니다. 지나친 음주는 건강을 해칩니다. 임신 중에는 마시지 말고, 술을 마신 뒤에는 운전하지 마세요."   # 기획 제안 문구

ART_DIR = os.path.join("art", "cocktails")   # 전담 그림: art/cocktails/<id>.svg(상세), <id>-s.svg(목록). 없으면 glass_svg 임시 그림

def cocktail_art(c, small=False):
    """잔 그림을 넣는 유일한 자리. 전담 그림 파일이 있으면 인라인으로 넣고(색 변수·title 이 살도록), 없으면 데이터로 그린 임시 그림을 쓴다"""
    p = os.path.join(ROOT, ART_DIR, f"{c['id']}{'-s' if small else ''}.svg")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f: t = f.read()
        t = re.sub(r"<\?xml[^>]*\?>|<!DOCTYPE[^>]*>|<!--.*?-->", "", t, flags=re.S).strip()
        if not t.startswith("<svg"): raise SystemExit(f"오류: {p} 가 <svg> 로 시작하지 않음")
        return t
    return glass_svg(c, not small)

def cocktail_cards(cs):
    out = []
    for c in cs:
        req = ";".join("|".join(x["groups"]) for x in c["ingredients"] if x.get("groups") and not x.get("optional"))   # 가진 재료로 찾기: 꼭 필요한 재료(| 는 그중 하나)
        out.append(f'<li data-base="{" ".join(c["base"])}" data-diff="{c["difficulty"]}" data-method="{c["method"]}"' + (f' data-req="{req}"' if req else "") + f'><a class="ccard" href="#c-{c["id"]}" data-id="{c["id"]}">'
                   f'<span class="cfig">{cocktail_art(c, True)}</span><span class="cbody"><span class="cn">{esc_html(c["ko"])}</span><span class="ce">{esc_html(c["en"])}</span>'
                   f'<span class="cm"><span class="df" title="난이도">{"●" * c["difficulty"]}{"○" * (3 - c["difficulty"])} {DIFF_KO[c["difficulty"]]}</span> · {esc_html(", ".join(TYPE_KO[b] for b in c["base"]))}</span>'
                   f'<span class="tg">{"".join(f"<span>{esc_html(t)}</span>" for t in c["taste"])}</span></span></a></li>')
    return "".join(out)

CK_PRICE_MAX = 100000   # "이 칵테일에 쓰는 종류의 병": 데일리샷 가격 상한(원). 칵테일 재료로 고가 병이 앞에 나오는 어색함을 막는다
CK_BOTTLES = 5          # 종류마다 보여 줄 병 수
CK_BOTTLE_RULE = (f"티어표에서 같은 종류 병 중 데일리샷 가격 {CK_PRICE_MAX // 10000}만 원 이하(700·750ml)인 병을 점수순으로 {CK_BOTTLES}병까지 보여 줍니다. "
                  "옛 병과 미평가 병은 뺐습니다. 티어 점수는 주로 그대로 마셨을 때의 평가를 모은 것으로, 칵테일용 평가가 아닙니다.")

def cocktail_bottles(ws, t):
    """종류 t 의 병 중 칵테일 상세에 보여 줄 병(빌드 때 계산). 화면 규칙은 CK_BOTTLE_RULE 에 그대로 적는다"""
    xs = [w for w in ws if w["type"] == t and not w["vin"] and w["tier"] != "N" and w["price"] and w["price"] <= CK_PRICE_MAX and w["pml"] in (None, 700, 750)]
    return sorted(xs, key=lambda w: (-w["score"], w["ko"]))[:CK_BOTTLES]

def bottle_block(c, ws):
    g = []
    for t in c["base"]:
        li = "".join(f'<li><a href="./#b={w["id"]}"><span class="bt" data-t="{w["tier"]}">{w["tier"]}</span><span class="bn">{esc_html(w["ko"])}</span><span class="bp">{w["price"]:,}원</span></a></li>' for w in cocktail_bottles(ws, t))
        g.append(f'<div class="bgrp"><p class="bgh">{TYPE_KO[t]}</p>' + (f'<ul class="bl">{li}</ul>' if li else "") + f'<a class="ball" href="./#type={t}">{TYPE_KO[t]} 전체 보기 →</a></div>')
    return f'<h4>이 칵테일에 쓰는 종류의 병</h4><p class="bnote">{CK_BOTTLE_RULE}</p>{"".join(g)}'

def step_plan(c):
    """스크롤 연출 계획: 단계 s(0 = 시작, k+1 = 만드는 법 k번째, m+1 = 꼬리). 재료마다 나타나는 단계, 얼음·가니시·김의 단계.
    step_adds 가 없으면 임시로 모든 재료를 첫 단계, 얼음은 첫 단계, 가니시는 마지막 단계에 둔다"""
    m, n = len(c["steps"]), len(c["ingredients"])
    sa = c.get("step_adds") or ([list(range(n))] + [[] for _ in range(m - 1)] if m else [])
    ist = [0] * n
    for k, xs in enumerate(sa):
        for i in xs: ist[i] = k + 1
    ice = c.get("ice_step", -1); ice = 0 if ice is None or ice < 0 else ice + 1   # -1 은 얼음 없는 잔(그림에 얼음 묶음 없음), n 은 n번째 단계에서 등장
    gst = c.get("garnish_step", (m - 1) if (c["garnish"] and "step_adds" not in c) else None)
    garn = "" if gst is None else gst + 1
    steam = ""
    if c["method"] == "hot":   # 김은 뜨거운 재료(뜨거운·끓는·커피)가 들어간 단계부터, 없으면 마지막 재료가 들어간 단계부터
        hot = [ist[i] for i, x in enumerate(c["ingredients"]) if re.search(r"뜨거운|끓는|커피", x["ko"]) or x["kind"] == "coffee"]
        steam = min(hot) if hot else max(ist or [0])
    return sa, ist, ice, garn, steam

def cocktail_articles(cs, ws):
    """레시피 본문(정적 HTML, JS 없이 전부 읽힘). 스크롤 연출은 만드는 법 중심: 단계 data-s = k+1 이 만드는 법 k번째이고,
    그 단계에서 넣는 재료 줄(.adds, 연출 중에만 보임)과 그림의 재료 묶음(data-i)이 함께 나타난다. 마지막 data-s 는 가니시·팁·병·출처"""
    out = []
    for c in cs:
        num = lambda i: chr(0x2460 + i) if i < 20 else f"({i+1})"
        sa, ist, ice, garn, steam = step_plan(c); m = len(c["steps"]); last = m + 1
        rows = "".join(f'<tr><td class="no">{num(i)}</td><td><i class="sw" style="background:{x["color"]}"></i>{esc_html(x["ko"])} <small>{esc_html(x["en"])}</small></td><td class="amt">{esc_html(x["amount"])}</td></tr>' for i, x in enumerate(c["ingredients"]))
        src = "".join(f'<li><a href="{esc_attr(s["url"])}" target="_blank" rel="noopener">{esc_html(s["name"])}<span aria-hidden="true"> ↗</span></a></li>' for s in c["sources"])
        def adds(k):
            xs = sa[k] if k < len(sa) else []
            return (f'<ul class="adds">' + "".join(f'<li><i class="sw" style="background:{c["ingredients"][i]["color"]}"></i>{num(i)} {esc_html(c["ingredients"][i]["ko"])} <b>{esc_html(c["ingredients"][i]["amount"])}</b></li>' for i in xs) + "</ul>") if xs else ""
        out.append(f'<article class="recipe" id="c-{c["id"]}" aria-labelledby="h-{c["id"]}" data-ist="{",".join(map(str, ist))}" data-ice="{ice}" data-garn="{garn}" data-steam="{steam}" data-last="{last}">'
                   f'<figure class="big">{cocktail_art(c)}<figcaption>{CK_NOTE}</figcaption></figure>'
                   f'<div class="rtext"><h3 id="h-{c["id"]}" tabindex="-1">{esc_html(c["ko"])} <small>{esc_html(c["en"])}</small></h3>'
                   f'<p class="rmeta"><span>{GLASS_KO[c["glass"]]}</span><span>{METHOD_KO[c["method"]]}</span><span>{ICE_KO[c["ice"]]}</span><span>난이도 {DIFF_KO[c["difficulty"]]}</span>{"".join(f"<span>{esc_html(t)}</span>" for t in c["taste"])}</p>'
                   f'<details class="ingall" open><summary><h4>재료 <small>넣는 순서</small></h4></summary><table class="ing"><tbody>{rows}</tbody></table></details>'
                   f'<h4 class="sth">만드는 법</h4><ol class="steps">{"".join(f"<li data-s=\"{k + 1}\"><p class=\"stx\">{esc_html(t)}</p>{adds(k)}</li>" for k, t in enumerate(c["steps"]))}</ol>'
                   + f'<div class="rtail" data-s="{last}">'
                   + (f'<div class="rgarn"><h4>가니시</h4><p>{esc_html(", ".join(c["garnish"]))}</p></div>' if c["garnish"] else "")   # 연출 중 garnish_step 에서 또렷해진다
                   + (f'<p class="tip"><b>팁</b> {esc_html(c["tip"])}</p>' if c.get("tip") else "")
                   + bottle_block(c, ws)
                   + (f'<h4>출처</h4><ul class="srcl">{src}</ul>' if src else "")
                   + '</div></div></article>')
    return "".join(out)

def cocktail_filters(cs):
    def grp(key, label, vals):
        return (f'<div class="cg" role="group" aria-label="{label}"><span class="cgl">{label}</span>'
                + "".join(f'<button type="button" class="chip" data-k="{key}" data-v="{v}" aria-pressed="false">{esc_html(t)}</button>' for v, t in vals) + "</div>")
    bases = [b for b in ("BB", "RY", "SM", "BL", "IR", "JP", "WD") if any(b in c["base"] for c in cs)]
    diffs = sorted({c["difficulty"] for c in cs}); meths = [m for m in METHOD_KO if any(c["method"] == m for c in cs)]
    return (grp("base", "베이스", [(b, TYPE_KO[b]) for b in bases]) + grp("diff", "난이도", [(str(d), DIFF_KO[d]) for d in diffs])
            + grp("method", "만드는 방식", [(m, METHOD_KO[m]) for m in meths]))

def tokens_css():
    """티어표 template.html 의 색 토큰(:root 와 다크 테마 정의)을 그대로 가져와 두 페이지가 같은 색을 쓰게 한다"""
    with open(os.path.join(ROOT, "tools", "template.html"), encoding="utf-8") as f: t = f.read()
    m = re.search(r"(:root\{.*?\n\}\n@media \(prefers-color-scheme: dark\)\{.*?\} \}\n:root\[data-theme=\"dark\"\]\{.*?\})", t, re.S)
    if not m: raise SystemExit("오류: template.html 에서 색 토큰을 찾지 못함")
    return m.group(1)

def bar_block(gs):
    """가진 재료로 찾기(JS 가 있을 때만 보임). 묶음 칩을 kind 줄로, 위스키 칩 옆에는 티어표 같은 종류 링크"""
    if not gs: return ""
    rows = []
    for k in CK_GROUP_KINDS:
        xs = [g for g in gs if g["kind"] == k]
        if not xs: continue
        rows.append(f'<div class="bgr" role="group" aria-label="{k}"><span class="cgl">{k}</span>' + "".join(
            f'<span class="bwrap"><button type="button" class="chip bchip" data-g="{g["id"]}" aria-pressed="false">{esc_html(g["ko"])}</button>'
            + (f'<a class="btier" href="./#type={CK_GROUP_TYPE[g["id"]]}" title="티어표에서 {TYPE_KO[CK_GROUP_TYPE[g["id"]]]} 보기">티어 →</a>' if g["id"] in CK_GROUP_TYPE else "") + "</span>" for g in xs) + "</div>")
    data = json.dumps({g["id"]: [g["ko"], g["kind"], g["common"], CK_GROUP_TYPE.get(g["id"])] for g in gs}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return (f'<details class="kbar" id="kbar" hidden><summary>가진 재료로 찾기 <span class="bon" id="bon"></span></summary>'
            '<p class="bnote2">가진 술과 재료를 켜면, 지금 바로 만들 수 있는 칵테일과 재료가 하나만 더 있으면 되는 칵테일을 앞으로 모아 보여 줍니다. 물·정향처럼 없어도 되는 재료는 따지지 않습니다. 고른 재료는 이 브라우저에만 저장되고 공유 주소에는 들어가지 않습니다.</p>'
            '<p class="bbtn"><button type="button" class="chip" id="bcommon">흔한 것 모두 켜기</button><button type="button" class="chip" id="bnone">모두 끄기</button><span class="bmsg" id="bmsg" role="status"></span></p>'
            f'{"".join(rows)}</details><script type="application/json" id="bgdata">{data}</script>')

def render_cocktails(cs, ws, gs=None):
    with open(os.path.join(ROOT, "tools", "cocktails_template.html"), encoding="utf-8") as f: t = f.read()
    return (t.replace("__TOKENS__", tokens_css()).replace("__FILTERS__", cocktail_filters(cs)).replace("__BAR__", bar_block(gs)).replace("__CARDS__", cocktail_cards(cs))
             .replace("__RECIPES__", cocktail_articles(cs, ws)).replace("__COUNT__", str(len(cs))).replace("__WARN__", CK_WARN))

def load_cocktails():
    """(레시피 목록 또는 None, 오류 목록). 파일이 없으면 칵테일 페이지를 만들지 않는다"""
    p = os.path.join(ROOT, "data", "cocktails.json")
    if not os.path.exists(p): return None, []
    try:
        with open(p, encoding="utf-8") as f: cs = json.load(f)
    except Exception as e:
        return None, [f"cocktails.json 읽기 실패: {e}"]
    return cs, check_cocktails(cs)

# ───────────── 용어 사전(glossary.html, N4) ─────────────
# data/glossary.json + tools/glossary_template.html 이 둘 다 있을 때만 만든다. 티어표 필터·상세 배지의 ? 도움말도 이때만 켠다
GL_SLUG = CK_SLUG
GL_FILTER_VALUES = {"age": {"nas", "a10", "a12", "a15", "a18"}, "style": STYLE, "cask": CASK, "spec": SPEC,
                    "abv": {"v1", "v2", "v3", "none"}, "price": {"p1", "p2", "p3", "p4", "none"}}   # template.html 의 GROUPS 값과 같게 둔다
# 용어 사전 페이지의 묶음(자료에 묶음 필드가 없어 여기서 정한다). 목록에 없는 id 는 "그 밖의 용어"로
GL_GROUPS = [("위스키 종류", ["single-malt", "blended", "blended-malt", "bourbon", "rye", "tennessee", "irish", "japanese"]),
             ("라벨 표기", ["age-statement", "cask-strength", "single-barrel", "small-batch", "bottled-in-bond", "abv-proof", "ncf-natural-colour"]),
             ("맛과 숙성", ["peat", "cask", "finish"]),
             ("이 사이트의 표시", ["tier", "trend-vintage"])]

def check_glossary(gs, bottles):
    if not isinstance(gs, list): return ["glossary.json 은 배열이어야 함"]
    errs, regions = [], {b.get("region") for b in bottles if b.get("region")}
    for i, n in collections.Counter(g.get("id") for g in gs if isinstance(g, dict)).items():
        if n > 1: errs.append(f"용어 id 중복: {i}")
    for g in gs:
        if not isinstance(g, dict): errs.append(f"용어 항목이 객체가 아님: {g!r}"); continue
        gid = g.get("id") or "?"; e = lambda m: errs.append(f"용어 {gid}: {m}")
        miss = [k for k in ("id", "ko", "en", "short", "body", "filter", "sources") if k not in g]
        if miss: e(f"필수 필드 없음 {miss}"); continue
        if not isinstance(g["id"], str) or not GL_SLUG.match(g["id"]): e("id 는 영문 소문자·숫자·하이픈만")
        for k in ("ko", "en", "short", "body"):
            if not isinstance(g[k], str) or not g[k].strip(): e(f"{k} 가 빈 문자열")
        if isinstance(g["short"], str) and len(g["short"]) > 70: e(f"short 가 70자 초과({len(g['short'])}자)")
        f = g["filter"]
        if f is not None:
            m = re.match(r"^(type)=(\w+)$|^f=(\w+):(.+)$|^view=(map|price)$", f) if isinstance(f, str) else None
            if not m: e(f"filter 형식 오류 {f!r} (type=XX, f=묶음:값, view=map|price 또는 null)")
            elif m.group(1) and m.group(2) not in TYPES: e(f"filter 의 종류 코드 오류 {f!r}")
            elif m.group(3):
                grp, val = m.group(3), m.group(4)
                ok = (val in regions) if grp == "region" else (val in GL_FILTER_VALUES.get(grp, ()))
                if not ok: e(f"filter 값이 티어표 필터에 없음 {f!r}")
        if not isinstance(g["sources"], list) or not g["sources"]: e("sources 가 비어 있음")
        else:
            for x in g["sources"]:
                if not isinstance(x, dict) or not x.get("name"): e(f"출처에 name 이 없음 ({x!r})")
                elif x.get("url") is not None and not str(x["url"]).startswith("https://"): e(f"출처 url 은 https:// 또는 null ({x['url']!r})")
    return errs

def load_glossary(bottles):
    p = os.path.join(ROOT, "data", "glossary.json")
    if not os.path.exists(p): return None, []
    try:
        with open(p, encoding="utf-8") as f: gs = json.load(f)
    except Exception as e:
        return None, [f"glossary.json 읽기 실패: {e}"]
    return gs, check_glossary(gs, bottles)

def render_glossary(gs, learn=None):
    by = {g["id"]: g for g in gs}; used = set(); secs = []; toc = []
    pic = {gid: (l["id"], l["title"]) for l in (learn or []) for gid in l.get("glossary", [])}   # 용어 → 그림으로 배우기 장
    groups = [(n, [i for i in ids if i in by]) for n, ids in GL_GROUPS]
    rest = [g["id"] for g in gs if g["id"] not in {i for _, ids in GL_GROUPS for i in ids}]
    if rest: groups.append(("그 밖의 용어", rest))
    for k, (name, ids) in enumerate(groups):
        if not ids: continue
        toc.append(f'<li><span class="tg">{esc_html(name)}</span>' + "".join(f'<a href="#g-{i}">{esc_html(by[i]["ko"])}</a>' for i in ids) + "</li>")
        items = []
        for i in ids:
            g = by[i]
            src = "".join(f'<li>{"<a href=\"" + esc_attr(x["url"]) + "\" target=\"_blank\" rel=\"noopener\">" + esc_html(x["name"]) + "<span aria-hidden=\"true\"> ↗</span></a>" if x.get("url") else esc_html(x["name"])}</li>' for x in g["sources"])
            items.append(f'<article class="term" id="g-{i}" aria-labelledby="gh-{i}"><h3 id="gh-{i}">{esc_html(g["ko"])} <small lang="en">{esc_html(g["en"])}</small></h3>'
                         f'<p class="short">{esc_html(g["short"])}</p><p class="body">{esc_html(g["body"])}</p>'
                         + ((f'<p class="go">' + (f'<a href="./#{esc_attr(g["filter"])}">티어표에서 보기 →</a>' if g["filter"] else "")
                             + (f'<a href="learn.html#l-{pic[i][0]}">그림으로 보기({esc_html(pic[i][1])}) →</a>' if i in pic else "") + '</p>') if (g["filter"] or i in pic) else "")
                         + f'<details class="src"><summary>근거 자료 {len(g["sources"])}건</summary><ul>{src}</ul></details></article>')
        secs.append(f'<section class="gsec" aria-labelledby="gs-{k}"><h2 id="gs-{k}">{esc_html(name)}</h2>{"".join(items)}</section>')
    with open(os.path.join(ROOT, "tools", "glossary_template.html"), encoding="utf-8") as f: t = f.read()
    return t.replace("__TOKENS__", tokens_css()).replace("__TOC__", "".join(toc)).replace("__TERMS__", "".join(secs)).replace("__COUNT__", str(len(gs)))

# ───────────── 그림으로 배우는 위스키(learn.html, N2) ─────────────
# data/learn.json + tools/learn_template.html 이 있을 때만 만든다. 그림은 art/learn/<art>.svg(PC 720×460)와 <art>-m.svg(휴대폰 360×880)를 둘 다 인라인으로 넣고 CSS 로 하나만 보인다
LEARN_ART = os.path.join("art", "learn")
LN_LINK = re.compile(r"^(\./#[\w=:%.,&가-힣-]*|#l-[a-z0-9-]+)$")

def check_learn(ls, gl_ids):
    if not isinstance(ls, list): return ["learn.json 은 배열이어야 함"]
    errs, ids = [], [l.get("id") for l in ls if isinstance(l, dict)]
    for i, n in collections.Counter(ids).items():
        if n > 1: errs.append(f"그림 장 id 중복: {i}")
    for l in ls:
        if not isinstance(l, dict): errs.append(f"그림 장이 객체가 아님: {l!r}"); continue
        lid = l.get("id") or "?"; e = lambda m: errs.append(f"그림 장 {lid}: {m}")
        miss = [k for k in ("id", "title", "lead", "art", "paras", "evidence", "links", "glossary") if k not in l]
        if miss: e(f"필수 필드 없음 {miss}"); continue
        if not isinstance(l["id"], str) or not CK_SLUG.match(l["id"]): e("id 는 영문 소문자·숫자·하이픈만")
        for k in ("title", "lead"):
            if not isinstance(l[k], str) or not l[k].strip(): e(f"{k} 가 빈 값")
        for suf in ("", "-m"):
            if not os.path.exists(os.path.join(ROOT, LEARN_ART, f"{l['art']}{suf}.svg")): e(f"그림 파일 없음 {LEARN_ART}/{l['art']}{suf}.svg")
        if not isinstance(l["paras"], list) or not l["paras"] or not all(isinstance(x, str) and x.strip() for x in l["paras"]): e("paras 는 문자열 배열(1개 이상)")
        for x in l["evidence"] if isinstance(l["evidence"], list) else [None]:
            if not isinstance(x, dict) or not x.get("what") or not x.get("src"): e(f"evidence 항목에 what·src 가 없음 ({x!r})")
            elif x.get("url") is not None and not str(x["url"]).startswith("https://"): e(f"evidence url 은 https:// 또는 null ({x['url']!r})")
        for x in l["links"] if isinstance(l["links"], list) else [None]:
            if not isinstance(x, dict) or not x.get("text") or not LN_LINK.match(str(x.get("href", ""))): e(f"links 항목 오류(href 는 ./#… 또는 #l-…) ({x!r})")
            elif x["href"].startswith("#l-") and x["href"][3:] not in ids: e(f"links 가 없는 장을 가리킴 {x['href']}")
        bad = [g for g in l["glossary"] if gl_ids is not None and g not in gl_ids] if isinstance(l["glossary"], list) else ["(배열 아님)"]
        if bad: e(f"glossary 에 용어 사전에 없는 id {bad}")
    return errs

def load_learn(gl_ids):
    p = os.path.join(ROOT, "data", "learn.json")
    if not os.path.exists(p): return None, []
    try:
        with open(p, encoding="utf-8") as f: ls = json.load(f)
    except Exception as e:
        return None, [f"learn.json 읽기 실패: {e}"]
    return ls, check_learn(ls, gl_ids)

def learn_svg(name):
    with open(os.path.join(ROOT, LEARN_ART, name + ".svg"), encoding="utf-8") as f: t = f.read()
    t = re.sub(r"<\?xml[^>]*\?>|<!DOCTYPE[^>]*>|<!--.*?-->", "", t, flags=re.S).strip()
    if not t.startswith("<svg"): raise SystemExit(f"오류: {LEARN_ART}/{name}.svg 가 <svg> 로 시작하지 않음")
    return t

def render_learn(ls, gs, gl_on):
    gk = {g["id"]: g["ko"] for g in (gs or [])}; toc, secs = [], []
    for k, l in enumerate(ls, 1):
        toc.append(f'<li><a href="#l-{l["id"]}"><b>{k}</b> {esc_html(l["title"])}</a></li>')
        ev = "".join(f'<tr><td>{esc_html(x["what"])}</td><td>' + (f'<a href="{esc_attr(x["url"])}" target="_blank" rel="noopener">{esc_html(x["src"])}<span aria-hidden="true"> ↗</span></a>' if x.get("url") else esc_html(x["src"])) + "</td></tr>" for x in l["evidence"])
        lk = "".join(f'<a href="{esc_attr(x["href"])}">{esc_html(x["text"])}{"" if x["href"].startswith("#l-") else " 티어 보기"} →</a>' for x in l["links"])
        gls = "".join(f'<a href="glossary.html#g-{g}">{esc_html(gk.get(g, g))}</a>' for g in l["glossary"]) if gl_on else ""
        secs.append(f'<section class="ch" id="l-{l["id"]}" aria-labelledby="lh-{l["id"]}"><p class="chn">그림 {k}</p><h2 id="lh-{l["id"]}">{esc_html(l["title"])}</h2><p class="lead">{esc_html(l["lead"])}</p>'
                    f'<figure class="lart"><div class="pc">{learn_svg(l["art"])}</div><div class="mo">{learn_svg(l["art"] + "-m")}</div></figure>'
                    + "".join(f"<p>{esc_html(x)}</p>" for x in l["paras"])
                    + (f'<p class="to"><span>티어표에서 보기</span>{lk}</p>' if lk else "")
                    + (f'<p class="to gl"><span>용어 사전</span>{gls}</p>' if gls else "")
                    + f'<details class="ev"><summary>근거 자료 {len(l["evidence"])}건</summary><table><thead><tr><th scope="col">그림·설명의 내용</th><th scope="col">근거</th></tr></thead><tbody>{ev}</tbody></table></details></section>')
    with open(os.path.join(ROOT, "tools", "learn_template.html"), encoding="utf-8") as f: t = f.read()
    return t.replace("__TOKENS__", tokens_css()).replace("__TOC__", "".join(toc)).replace("__CHAPTERS__", "".join(secs)).replace("__WARN__", CK_WARN)

def main():
    a = sys.argv[1:]
    ws, meta, bottles, errs, stats = compute()
    cs, cerrs = load_cocktails(); errs = errs + cerrs
    cg, cgerrs = load_cocktail_groups(); errs = errs + cgerrs + (check_cocktail_groups(cs, cg) if cs is not None else [])
    ck_tpl = os.path.exists(os.path.join(ROOT, "tools", "cocktails_template.html"))
    gs, gerrs = load_glossary(bottles); errs = errs + gerrs
    gl_tpl = os.path.exists(os.path.join(ROOT, "tools", "glossary_template.html"))
    ls, lerrs = load_learn({g["id"] for g in gs} if gs else None); errs = errs + lerrs
    ln_tpl = os.path.exists(os.path.join(ROOT, "tools", "learn_template.html"))
    bids = {b["id"] for b in bottles}
    ph, perrs = load_price_history(bids); errs = errs + perrs
    chs, cherrs = load_changes(bids); errs = errs + cherrs
    ch_tpl = os.path.exists(os.path.join(ROOT, "tools", "changes_template.html"))
    vw, vwerrs = load_views(); errs = errs + vwerrs
    aw = check_method_art()
    if "--check" in a: errs = errs + aw   # 점검에서는 도해 숫자 어긋남도 오류로 친다. 일반 빌드는 경고만 하고 계속한다
    else:
        for e in aw: print("경고:", e)
    for e in errs: print("오류:", e)
    if errs: sys.exit(1)
    stats["trend"], tmsg = add_trends(ws)
    c = collections.Counter(w["tier"] for w in ws)
    print(f"{len(ws)}병 · 출처 {len(meta)}개 · " + " ".join(f"{t}{c[t]}" for t, _ in TIERS) + f" 미평가{c['N']}" + f" · 잠정 {sum(1 for w in ws if w['flag']=='prov')} 경계 {sum(1 for w in ws if w['flag']=='border')} 확정 {sum(1 for w in ws if w['flag']=='firm')} · 경계 {stats['tiers']} · 병 내 sd {stats['sd']} · 사전 평균 {stats['prior']}" + f" · 이미지 {sum(1 for b in bottles if b.get('img'))}장({photo_coverage(bottles) * 100:.1f}%, " + (f"기준 {PHOTO_MIN_COVERAGE * 100:g}% 이상이라 화면에 실음" if photos_on(bottles) else f"기준 {PHOTO_MIN_COVERAGE * 100:g}% 미만이라 화면에 싣지 않음") + "".join(f", {k} {v}" for k, v in collections.Counter(b.get("img_license") or "라이선스 없음" for b in bottles if b.get("img")).most_common()) + ")")
    print(tmsg)
    dd = collections.Counter(w["di"] for w in ws if w.get("di"))
    print(f"증류소 {len(dd)}곳(2병 이상 {sum(1 for n in dd.values() if n > 1)}곳) · 증류소 표기 {sum(dd.values())}병 · 증류소 없이 브랜드만 {sum(1 for w in ws if not w.get('di') and w.get('br'))}병 · 둘 다 없음 {sum(1 for w in ws if not w.get('di') and not w.get('br'))}병 · 독립병입 {sum(1 for w in ws if w.get('bo'))}병")
    v = [w["id"] for w in ws if w["vin"]]
    print(f"옛 병 {len(v)}병(경계 계산 제외)" + (f": {', '.join(v)}" if v else ""))
    z = [w["id"] for w in ws if not w["obs"]]
    print(f"관측값 0건 {len(z)}병" + (f" (미평가 줄에 표시. 의도한 것이 아니면 관측값 누락을 확인할 것): {', '.join(z[:20])}{' …' if len(z) > 20 else ''}" if z else ""))
    if cs is None: print("칵테일: data/cocktails.json 없음 — cocktails.html 을 만들지 않음")
    else:
        print(f"칵테일 {len(cs)}종 · 잔 {dict(collections.Counter(c['glass'] for c in cs))} · 출처 없는 레시피 {sum(1 for c in cs if not c['sources'])}종"
              + (f" · 재료 묶음 {len(cg)}개(흔한 것 {sum(1 for g in cg if g['common'])})" if cg else "")
              + ("" if ck_tpl else " · tools/cocktails_template.html 없음 — cocktails.html 을 만들지 않음"))
    if gs is None: print("용어 사전: data/glossary.json 없음 — glossary.html 을 만들지 않음")
    else: print(f"용어 사전 {len(gs)}항목 · 필터 연결 {sum(1 for g in gs if g['filter'])}항목" + ("" if gl_tpl else " · tools/glossary_template.html 없음 — glossary.html 을 만들지 않음"))
    if ls is None: print("그림으로 배우기: data/learn.json 없음 — learn.html 을 만들지 않음")
    else: print(f"그림으로 배우기 {len(ls)}장 · 근거 {sum(len(l['evidence']) for l in ls)}건" + ("" if ln_tpl else " · tools/learn_template.html 없음 — learn.html 을 만들지 않음"))
    if ph is None: print("가격 이력: data/price_history.json 없음 — 병 상세에 가격 변동을 넣지 않음")
    else:
        np = collections.Counter(min(len(v), 3) for v in ph.values())
        print(f"가격 이력 {len(ph)}병 · 점 1개 {np[1]}병 · 2개 {np[2]}병 · 3개 이상 {np[3]}병 · 측정일 {len({x[0] for v in ph.values() for x in v})}개")
    if chs is None: print("바뀐 것: data/changes.json 없음 — changes.html 을 만들지 않음")
    else:
        cc = collections.Counter(c["type"] for c in chs)
        print(f"바뀐 것 {len(chs)}건 · 측정일 {len({c['date'] for c in chs})}개 · " + " ".join(f"{CHG_TITLE[k]} {cc[k]}" for k in CHG_TYPES) + ("" if ch_tpl else " · tools/changes_template.html 없음 — changes.html 을 만들지 않음"))
    if vw is None: print("많이 본 병: data/views.json 없음 — 순위 구역 없음")
    else: print(f"많이 본 병 {vw.get('week')} · 상위 {len(vw['top'])}병 · {VW_MIN}회 이상 {sum(1 for x in vw['top'] if x[1] >= VW_MIN)}병" + ("" if chs is not None and ch_tpl else " · changes.html 을 만들지 않아 표시 안 함"))
    if "--check" in a: return
    ck = cs is not None and ck_tpl   # 칵테일 페이지를 만들 때만 티어표에 사이트 메뉴와 칵테일 연결을 둔다
    gl = gs is not None and gl_tpl   # 용어 사전을 만들 때만 티어표에 ? 도움말을 둔다(자세히 → 링크가 죽지 않게)
    lp = ls is not None and ln_tpl
    chp = chs is not None and ch_tpl
    built = {"index"} | ({"changes"} if chp else set()) | ({"cocktails"} if ck else set()) | ({"glossary"} if gl else set()) | ({"learn"} if lp else set())
    if ph and (phs := ph_stats(ph, [w["id"] for w in ws])): stats["ph"] = phs   # 병 상세의 가격 변동(점 2개 이상인 병만, 최근 PH_KEEP 점)
    if chp and chs: stats["chg"] = chg_latest(chs)   # 티어표 머리말의 "최근 바뀐 것 N건 →"(기록이 없으면 링크 없음)
    if gl: stats["gl"] = {g["id"]: [g["ko"], g["short"]] for g in gs}
    if ck:   # 티어표 병 상세의 "이 종류로 만드는 칵테일"용: 이름·베이스·작은 그림 파일 유무만(그림은 상세를 열 때 img 로 불러 index 용량을 늘리지 않는다)
        stats["ck"] = [{"id": c["id"], "ko": c["ko"], "b": c["base"], "a": os.path.exists(os.path.join(ROOT, ART_DIR, f"{c['id']}-s.svg"))} for c in cs]
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(full(site_nav(render(ws, meta, bottles, False, stats), "index", built)))
    if ck:
        with open(os.path.join(ROOT, "cocktails.html"), "w", encoding="utf-8") as f:
            f.write(full(site_nav(render_cocktails(cs, ws, cg), "cocktails", built), CK_HEAD))
    if gl:
        with open(os.path.join(ROOT, "glossary.html"), "w", encoding="utf-8") as f:
            f.write(full(site_nav(render_glossary(gs, ls if lp else None), "glossary", built), GL_HEAD))
    if lp:
        with open(os.path.join(ROOT, "learn.html"), "w", encoding="utf-8") as f:
            f.write(full(site_nav(render_learn(ls, gs, gl), "learn", built), LN_HEAD))
    if chp:
        with open(os.path.join(ROOT, "changes.html"), "w", encoding="utf-8") as f:
            f.write(full(site_nav(render_changes(chs, ws, gl, vw), "changes", built), CH_HEAD))
    ni = write_ids_js(bottles)
    if ni: print(f"{IDS_JS} 갱신({ni}병)")
    today = datetime.date.today().isoformat()
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:   # 배포 주소는 PAGES 의 짧은 주소
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                + "".join(f'  <url><loc>https://nidwolf.com{u}</loc><lastmod>{today}</lastmod></url>\n' for k, h, n, u in PAGES if k in built) + '</urlset>\n')
    print("index.html 생성" + (" · changes.html 생성" if chp else "") + (" · cocktails.html 생성" if ck else "") + (" · glossary.html 생성" if gl else "") + (" · learn.html 생성" if lp else ""))
    stats.pop("chg", None)   # 오프라인 파일·조각에는 다른 페이지가 없으므로 "최근 바뀐 것" 링크를 넣지 않는다
    if "--single" in a:
        p = a[a.index("--single") + 1]
        with open(p, "w", encoding="utf-8") as f: f.write(full(site_nav(render(ws, meta, bottles, True, stats), "index", {"index"})))   # 오프라인 보관용: 다른 페이지 링크 없음
        print("단일 파일:", p)
    if "--fragment" in a:
        p = a[a.index("--fragment") + 1]
        with open(p, "w", encoding="utf-8") as f: f.write(site_nav(render(ws, meta, bottles, True, stats), "index", {"index"}))
        print("조각 파일:", p)

if __name__ == "__main__":
    main()
