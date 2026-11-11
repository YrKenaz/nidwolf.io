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
import json, os, sys, re, base64, datetime, collections

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
        o = by.get(b["id"], [])
        g = collections.defaultdict(list)
        for x in o:
            if x["value"] is not None: g[sources[x["source"]]["group"]].append(x["value"])
        rows.append((b, o, [sum(v) / len(v) for v in g.values()]))
    if errs: return [], {}, bottles, errs, {}
    # 종류별 사전 평균, 병 내 표준편차(독립 출처 2곳 이상인 병으로 추정)
    tm = collections.defaultdict(list); ss = df = 0
    for b, o, gm in rows:
        if gm:
            m = sum(gm) / len(gm); tm[b["type"]].append(m)
            if len(gm) > 1: ss += sum((x - m) ** 2 for x in gm); df += len(gm) - 1
    prior = {t: sum(v) / len(v) for t, v in tm.items()}
    sd = (ss / df) ** 0.5 if df else 2.0
    set_tiers([round((sum(gm) + prior[b["type"]] * K) / (len(gm) + K), 1) for b, o, gm in rows if gm])
    out = []
    for b, o, gm in rows:
        n = len(gm)
        w = {"id": b["id"], "ko": b["ko"], "en": b["en"], "type": b["type"], "region": b["region"], "n": n,
             "obs": [{"s": x["source"], "v": x["value"], "raw": x.get("raw", "")} for x in o],
             "rec": sum(1 for x in o if x["value"] is None),
             "age": b["age"], "abv": b["abv"], "style": b["style"], "cask": b["cask"], "spec": b["spec"],
             "beg": b["beginner"], "price": b["price"], "pname": b["price_product"], "pdate": b.get("price_date"), "pml": b.get("price_ml"),
             "ds": [b["ds_rating"], b["ds_reviews"]] if b.get("ds_rating") else None}
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
    stats = {"prior": {t: round(v, 1) for t, v in prior.items()}, "sd": round(sd, 2), "k": K, "tiers": [[t, lo] for t, lo in TIERS]}
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
    return t.replace("__DATA__", data).replace("__IMAGES__", json.dumps({"img": img, "src": src, "cr": cr}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))

DESC = "한국·영어권 위스키 티어표와 순위·평점 리스트를 100점 척도로 합산한 위스키 티어표. 종류·숙성년수·피트·셰리·CS·가격대별로 골라 볼 수 있습니다."
HEAD = ('<!doctype html>\n<html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        f'<meta name="description" content="{DESC}">'
        '<link rel="canonical" href="https://nidwolf.com/"><link rel="icon" href="/Nidwolf-ico.ico">'
        f'<meta property="og:title" content="위스키 종합 티어표"><meta property="og:description" content="{DESC}">'
        '<meta property="og:type" content="website"><meta property="og:url" content="https://nidwolf.com/">'
        '<style>body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n')

def full(t):
    t = t.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "")
    return HEAD + t.replace('<div class="wrap">', '</head><body>\n<div class="wrap">', 1) + "\n</body></html>\n"

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

def main():
    a = sys.argv[1:]
    ws, meta, bottles, errs, stats = compute()
    for e in errs: print("오류:", e)
    if errs: sys.exit(1)
    stats["trend"], tmsg = add_trends(ws)
    c = collections.Counter(w["tier"] for w in ws)
    print(f"{len(ws)}병 · 출처 {len(meta)}개 · " + " ".join(f"{t}{c[t]}" for t, _ in TIERS) + f" 미평가{c['N']}" + f" · 잠정 {sum(1 for w in ws if w['flag']=='prov')} 경계 {sum(1 for w in ws if w['flag']=='border')} 확정 {sum(1 for w in ws if w['flag']=='firm')} · 경계 {stats['tiers']} · 병 내 sd {stats['sd']} · 사전 평균 {stats['prior']}" + f" · 이미지 {sum(1 for b in bottles if b.get('img'))}장({photo_coverage(bottles) * 100:.1f}%, " + (f"기준 {PHOTO_MIN_COVERAGE * 100:g}% 이상이라 화면에 실음" if photos_on(bottles) else f"기준 {PHOTO_MIN_COVERAGE * 100:g}% 미만이라 화면에 싣지 않음") + "".join(f", {k} {v}" for k, v in collections.Counter(b.get("img_license") or "라이선스 없음" for b in bottles if b.get("img")).most_common()) + ")")
    print(tmsg)
    z = [w["id"] for w in ws if not w["obs"]]
    print(f"관측값 0건 {len(z)}병" + (f" (미평가 줄에 표시. 의도한 것이 아니면 관측값 누락을 확인할 것): {', '.join(z[:20])}{' …' if len(z) > 20 else ''}" if z else ""))
    if "--check" in a: return
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(full(render(ws, meta, bottles, False, stats)))
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                f'  <url><loc>https://nidwolf.com/</loc><lastmod>{datetime.date.today().isoformat()}</lastmod></url>\n</urlset>\n')
    print("index.html 생성")
    if "--single" in a:
        p = a[a.index("--single") + 1]
        with open(p, "w", encoding="utf-8") as f: f.write(full(render(ws, meta, bottles, True, stats)))
        print("단일 파일:", p)
    if "--fragment" in a:
        p = a[a.index("--fragment") + 1]
        with open(p, "w", encoding="utf-8") as f: f.write(render(ws, meta, bottles, True, stats))
        print("조각 파일:", p)

if __name__ == "__main__":
    main()
