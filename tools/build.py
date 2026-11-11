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
import json, os, sys, base64, datetime, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
K = 1.0                                   # 종합 = (매체 그룹별 점수 합 + 종류별 사전 평균*K) / (독립 출처 수 + K)
SHARE = [("S", 0.05), ("A", 0.15), ("B", 0.25), ("C", 0.25), ("D", 0.20), ("E", 0.10)]   # 티어별 비율(점수 상위부터). 경계 점수는 빌드 때 계산
TIERS = []
TYPES = {"SM", "BL", "BB", "RY", "IR", "JP", "WD"}
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
        if b.get("img") and not os.path.exists(os.path.join(ROOT, b["img"])): errs.append(f"{b['id']}: 이미지 파일 없음 {b['img']}")
        o = by.get(b["id"])
        if not o: errs.append(f"{b['id']}: 관측값이 하나도 없음"); continue
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
             "beg": b["beginner"], "price": b["price"], "pname": b["price_product"], "pdate": b.get("price_date"),
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
    img, src = {}, {}
    for b in bottles:
        if not b.get("img"): continue
        if embed:
            with open(os.path.join(ROOT, b["img"]), "rb") as f:
                img[b["id"]] = "data:image/webp;base64," + base64.b64encode(f.read()).decode()
        else:
            img[b["id"]] = b["img"]
        if b.get("img_source"): src[b["id"]] = b["img_source"]
    updated = datetime.date.today().isoformat()
    data = json.dumps({"whiskies": ws, "meta": meta, "updated": updated, "stats": stats}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    with open(os.path.join(ROOT, "tools", "template.html"), encoding="utf-8") as f:
        t = f.read()
    return t.replace("__DATA__", data).replace("__IMAGES__", json.dumps({"img": img, "src": src}, ensure_ascii=False, separators=(",", ":")))

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

def main():
    a = sys.argv[1:]
    ws, meta, bottles, errs, stats = compute()
    for e in errs: print("오류:", e)
    if errs: sys.exit(1)
    c = collections.Counter(w["tier"] for w in ws)
    print(f"{len(ws)}병 · 출처 {len(meta)}개 · " + " ".join(f"{t}{c[t]}" for t, _ in TIERS) + f" 미평가{c['N']}" + f" · 잠정 {sum(1 for w in ws if w['flag']=='prov')} 경계 {sum(1 for w in ws if w['flag']=='border')} 확정 {sum(1 for w in ws if w['flag']=='firm')} · 경계 {stats['tiers']} · 병 내 sd {stats['sd']} · 사전 평균 {stats['prior']}" + f" · 이미지 {sum(1 for b in bottles if b.get('img'))}장")
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
