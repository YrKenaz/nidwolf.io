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
PRIOR, K = 86.0, 1.0                      # 종합 = (환산 점수 합 + PRIOR*K) / (출처 수 + K)
TIERS = [("S", 91), ("A", 89.5), ("B", 88.5), ("C", 87.5), ("D", 86), ("E", -1)]
TYPES = {"SM", "BL", "BB", "RY", "IR", "JP", "WD"}
STYLE, CASK, SPEC = {"peat", "sherry", "cs"}, {"bourbon", "wine", "rum", "mizunara"}, {"SiB", "SmB", "BiB", "BP", "Wh"}

def load(name):
    with open(os.path.join(ROOT, "data", name), encoding="utf-8") as f:
        return json.load(f)

def tier(s):
    return next(t for t, lo in TIERS if s >= lo)

def compute():
    sources, bottles, obs = load("sources.json"), load("bottles.json"), load("observations.json")
    errs, ids = [], [b["id"] for b in bottles]
    for i, c in collections.Counter(ids).items():
        if c > 1: errs.append(f"병 id 중복: {i}")
    by = collections.defaultdict(dict)
    for o in obs:
        if o["bottle"] not in set(ids): errs.append(f"관측값의 병 id 없음: {o['bottle']}")
        if o["source"] not in sources: errs.append(f"관측값의 출처 id 없음: {o['source']}")
        if o["source"] in by[o["bottle"]]: errs.append(f"관측값 중복: {o['bottle']} × {o['source']}")
        if not (50 <= o["value"] <= 100): errs.append(f"환산 점수 범위 밖: {o}")
        by[o["bottle"]][o["source"]] = o
    out = []
    for b in bottles:
        if b["type"] not in TYPES: errs.append(f"{b['id']}: 알 수 없는 type {b['type']}")
        for key, allowed in (("style", STYLE), ("cask", CASK), ("spec", SPEC)):
            bad = set(b[key]) - allowed
            if bad: errs.append(f"{b['id']}: {key} 값 오류 {bad}")
        if b.get("img") and not os.path.exists(os.path.join(ROOT, b["img"])): errs.append(f"{b['id']}: 이미지 파일 없음 {b['img']}")
        o = by.get(b["id"])
        if not o: errs.append(f"{b['id']}: 관측값이 하나도 없음"); continue
        n = len(o); score = round((sum(x["value"] for x in o.values()) + PRIOR * K) / (n + K), 1)
        out.append({"id": b["id"], "ko": b["ko"], "en": b["en"], "type": b["type"], "region": b["region"],
                    "score": score, "tier": tier(score), "n": n,
                    "scores": {k: x["value"] for k, x in o.items()}, "raw": {k: x.get("raw", "") for k, x in o.items()},
                    "age": b["age"], "abv": b["abv"], "style": b["style"], "cask": b["cask"], "spec": b["spec"],
                    "beg": b["beginner"], "price": b["price"], "pname": b["price_product"]})
    out.sort(key=lambda w: (-w["score"], w["ko"]))
    meta = {k: [s["name"], s["lang"], s["kind"], s["url"], s["rule"]] for k, s in sources.items()}
    return out, meta, bottles, errs

def render(ws, meta, bottles, embed):
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
    data = json.dumps({"whiskies": ws, "meta": meta, "updated": updated}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
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
    ws, meta, bottles, errs = compute()
    for e in errs: print("오류:", e)
    if errs: sys.exit(1)
    c = collections.Counter(w["tier"] for w in ws)
    print(f"{len(ws)}병 · 출처 {len(meta)}개 · " + " ".join(f"{t}{c[t]}" for t, _ in TIERS) + f" · 이미지 {sum(1 for b in bottles if b.get('img'))}장")
    if "--check" in a: return
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(full(render(ws, meta, bottles, False)))
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                f'  <url><loc>https://nidwolf.com/</loc><lastmod>{datetime.date.today().isoformat()}</lastmod></url>\n</urlset>\n')
    print("index.html 생성")
    if "--single" in a:
        p = a[a.index("--single") + 1]
        with open(p, "w", encoding="utf-8") as f: f.write(full(render(ws, meta, bottles, True)))
        print("단일 파일:", p)
    if "--fragment" in a:
        p = a[a.index("--fragment") + 1]
        with open(p, "w", encoding="utf-8") as f: f.write(render(ws, meta, bottles, True))
        print("조각 파일:", p)

if __name__ == "__main__":
    main()
