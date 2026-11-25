#!/usr/bin/env python3
"""NAS 수집기의 입력 파일 tools/worker/in/bottles_min.json 을 만든다 (PC에서 실행).

저장소 자료(data/bottles.json, tools/trend_aliases.json, tools/trend_brands.json, 위키 제목 확인 기록)에서
수집에 필요한 최소 정보만 뽑는다. 요청은 보내지 않는다.

  python3 tools/worker/make_input.py                 # 전 병
  python3 tools/worker/make_input.py --limit 20      # 앞의 20병만(시범용)
  python3 tools/worker/make_input.py --only id,id    # 고른 병만
  python3 tools/worker/make_input.py --out 경로

형식 (format 1)
  {"format": 1, "made": "2026-11-25",
   "bottles": [{"id", "pid"(ds_url의 상품 번호 또는 null), "queries": [검색어 최대 3개],
                "accept": [같은 상품으로 인정할 이름(정규화)], "sig": 병 이름 서명,
                "prefixes": [...], "exclude_pids": [...]}],
   "wiki": [{"title": 브랜드 표의 문서 제목, "resolved": 확인된 본 문서 제목 또는 null}]}

실행할 때마다 수집기(collect.py)의 상품명 정규화가 trend_collect.py와 같은 결과를 내는지 대조한다.
"""
import json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
import trend_collect as tc   # noqa: E402
import collect as wc         # noqa: E402


def pid_of(url):
    m = re.search(r"/item/(\d+)", url or "")
    return int(m.group(1)) if m else None


def check_same_rules(names):
    """collect.py와 trend_collect.py의 정규화 결과가 한 글자라도 다르면 멈춘다."""
    bad = [n for n in names if wc.norm(n) != tc.norm(n) or wc.sig(n) != tc.sig(n) or wc.base(n) != tc.base(n)]
    if bad:
        raise SystemExit("상품명 정규화 규칙이 collect.py와 trend_collect.py에서 다릅니다. 예: %r" % bad[:5])
    return len(names)


def build(bottles, only=None, limit=0):
    extra = tc.load(os.path.join(ROOT, "tools", "trend_aliases.json"), {})
    brands = tc.load(os.path.join(ROOT, "tools", "trend_brands.json"), [])
    wiki_cache = tc.load(os.path.join(tc.WORK, "wiki_cache.json"), {})
    picked = [b for b in bottles if not only or b["id"] in only]
    if limit:
        picked = picked[:limit]
    out, titles = [], []
    for b in picked:
        qs, accept, _ = tc.bottle_names(b, extra)
        e = extra.get(b["id"], {})
        item = {"id": b["id"], "pid": pid_of(b.get("ds_url")), "queries": qs[:wc.MAX_QUERIES],
                "accept": sorted(accept), "sig": tc.sig(b["ko"])}
        if e.get("prefixes"):
            item["prefixes"] = [tc.norm(p) for p in e["prefixes"]]
        if e.get("exclude_pids"):
            item["exclude_pids"] = list(e["exclude_pids"])
        out.append(item)
        br = tc.brand_of(b, brands)
        if br and br.get("wiki") and br["wiki"] not in titles:
            titles.append(br["wiki"])
    wiki = []
    for t in sorted(titles):
        c = wiki_cache.get(t)
        if c and c.get("missing"):
            continue                # 문서가 없다고 확인된 제목은 보내지 않는다
        wiki.append({"title": t, "resolved": c["resolved"] if c else None})
    return {"format": 1, "made": time.strftime("%Y-%m-%d"), "bottles": out, "wiki": wiki}


def main():
    args = sys.argv[1:]
    out_path = args[args.index("--out") + 1] if "--out" in args else os.path.join(HERE, "in", "bottles_min.json")
    only = set(args[args.index("--only") + 1].split(",")) if "--only" in args else None
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else 0
    bottles = tc.load(os.path.join(ROOT, "data", "bottles.json"))
    names = [b["ko"] for b in bottles] + [b["price_product"] for b in bottles if b.get("price_product")]
    for d in tc.load(os.path.join(tc.WORK, "ds_cache.json"), {}).values():
        names += [r["name"] for r in d.get("rows", [])]
    n = check_same_rules(sorted(set(names)))
    doc = build(bottles, only, limit)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    lines = ['{"format": 1, "made": %s,' % json.dumps(doc["made"]), ' "bottles": [']
    lines += ["  " + json.dumps(b, ensure_ascii=False) + ("," if i < len(doc["bottles"]) - 1 else "") for i, b in enumerate(doc["bottles"])]
    lines += [" ],", ' "wiki": [']
    lines += ["  " + json.dumps(w, ensure_ascii=False) + ("," if i < len(doc["wiki"]) - 1 else "") for i, w in enumerate(doc["wiki"])]
    lines += [" ]", "}"]
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    json.load(open(out_path, encoding="utf-8"))
    print("저장: %s / 병 %d(상품 번호 있음 %d) / 위키 문서 %d(제목 확인 필요 %d) / 정규화 대조 %d개 이름 일치"
          % (out_path, len(doc["bottles"]), sum(1 for b in doc["bottles"] if b["pid"]), len(doc["wiki"]),
             sum(1 for w in doc["wiki"] if not w["resolved"]), n))


if __name__ == "__main__":
    main()
