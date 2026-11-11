#!/usr/bin/env python3
"""트렌드지수 수집·계산 (표준 라이브러리만 사용).

트렌드지수는 티어 점수와 분리된 지표다. 이 스크립트는 data/trends.json만 쓴다.
bottles.json, sources.json, observations.json은 읽기만 한다.

단계 (원하는 것만 골라 실행할 수 있고, 중간 결과는 tools/trend-data/에 저장돼 이어서 실행된다)
  ds     데일리샷 검색에서 병별 리뷰 수·구매 수를 모은다. 용량·패키지·구형 상품은 합산한다
  wiki   tools/trend_brands.json의 영어 위키백과 문서 제목을 확인하고 최근 12개월 조회수를 모은다
  naver  네이버 검색 API의 블로그·카페 결과 건수 (NAVER_CLIENT_ID, NAVER_CLIENT_SECRET이 있을 때만)
  score  모은 값으로 지수를 계산해 data/trends.json, 미등록 병 목록, 점검 목록을 쓴다

사용
  python3 tools/trend_collect.py ds wiki score      # 키 없는 B안
  NAVER_CLIENT_ID=.. NAVER_CLIENT_SECRET=.. python3 tools/trend_collect.py naver score   # A안
  python3 tools/trend_collect.py ds --refresh       # 저장된 값을 버리고 다시 측정
  python3 tools/trend_collect.py ds --only kc-9,jw-black

산식 (score 단계)
  부분 점수 = 100 × (ln(1+x) − ln(1+하한)) ÷ (ln(1+상한) − ln(1+하한)), 0~100으로 자른다
  상한은 전 병의 상위 1% 값. --keep-scales를 주면 기존 trends.json의 상한·하한을 그대로 쓴다
  B안(키 없음): 데일리샷 리뷰 70 + 영어 위키 조회수 18 + 해외 매체 등장 횟수 12
  A안(네이버 키): 네이버 블로그+카페 건수 45 + 데일리샷 리뷰 25 + 영어 위키 18 + 해외 매체 12
  naver 결과가 전 병에 대해 있으면 A안, 아니면 B안으로 계산한다

요청 간격: 데일리샷 2초, 위키미디어 6초, 네이버 0.3초. 403·429가 오면 그 단계를 멈추고 저장한다.
"""
import json, math, os, re, sys, time, urllib.error, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ROOT, "tools", "trend-data")
UA = "Mozilla/5.0 (compatible; whisky-trend-research/0.1)"
# 위키미디어는 연락처가 든 User-Agent를 요구한다. 사이트 주소만 적는다(사용자 승인 2026-11-11).
UA_WIKI = "nidwolf-trend/1.0 (https://nidwolf.com) python-urllib"
PV_MONTHS = 12

WEIGHTS = {
    "B": {"ds": 70, "wiki": 18, "src": 12},
    "A": {"naver": 45, "ds": 25, "wiki": 18, "src": 12},
}
DOMESTIC = ("naver", "ds")
WIKI_LO = 1000


class Blocked(Exception):
    pass


def load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path, obj, **kw):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, **kw)
    os.replace(tmp, path)


def http(url, pause, headers=None):
    h = {"User-Agent": UA}
    h.update(headers or {})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 429):
            raise Blocked("HTTP %d: %s" % (e.code, url))
        if e.code == 404:
            return None
        raise
    finally:
        time.sleep(pause)


# ---------------------------------------------------------------- 상품명 정규화

# 이 낱말이 나오면 그 낱말부터 끝까지를 패키지 설명으로 보고 지운다.
PACK = ("전용잔|하이볼|온더락|글라스|글랜캐런|글렌캐런|노징|위스키잔|플라스크|선물|패키지|세트|증정|쿠퍼잔|랜턴|"
        "스피커|스틱|코스터|바이알|미니어처|미니어쳐|케이스|기프트|코퍼잔|머그|텀블러|레만")
RE_PAREN = re.compile(r"\([^)]*\)|\[[^\]]*\]")
RE_VOL = re.compile(r"\d+(\.\d+)?\s*(ml|mL|ML|L|l)(?![A-Za-z가-힣])")
RE_ABV = re.compile(r"\d+(\.\d+)?\s*%")          # 도수 표기(시장별 도수 차이는 같은 병으로 본다)
RE_PACK = re.compile(r"\s*\S*(%s).*$" % PACK)
RE_MULTI = re.compile(r"\s*(x\s*\d+|\d+병)\s*$")
RE_YEAR = re.compile(r"\s+20\d\d(-\d\d\w?)?\s*$")
RE_BATCH = re.compile(r"\s*배치\s*(넘버\s*)?#?\d+.*$")
RE_BUNDLE = re.compile(r"\s&|&\s")


def base(name):
    """용량·도수·괄호·패키지·묶음 수량·배치 번호·끝의 출시 연도를 지운 상품명(띄어쓰기 유지)."""
    s = RE_PAREN.sub(" ", name)
    s = RE_VOL.sub(" ", s)
    s = RE_ABV.sub(" ", s)
    s = RE_PACK.sub("", s)
    s = RE_MULTI.sub("", s)
    s = RE_BATCH.sub("", s)
    s = RE_YEAR.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


def norm(name):
    return re.sub(r"\s+", "", base(name))


def sig(name):
    """띄어쓰기·낱말 순서가 달라도 같은 이름이면 같아지는 값. 숫자는 덩어리째 비교해 12와 21을 구분한다."""
    b = base(name)
    rest = "".join(sorted(re.sub(r"[\d\s]+", "", b)))
    return rest + "|" + ",".join(sorted(re.findall(r"\d+", b)))


def nums(name):
    return sorted(re.findall(r"\d+", base(name)))


def sales_num(s):
    if not s:
        return 0
    m = re.search(r"([\d,.]+)\s*(만)?", s)
    if not m:
        return 0
    v = float(m.group(1).replace(",", ""))
    return int(v * 10000) if m.group(2) else int(v)


# ---------------------------------------------------------------- 데일리샷

def bottle_names(b, extra):
    """병 하나에 대해 (검색어 목록, 인정할 이름 {norm: 근거}, 점검 표시)를 만든다."""
    flags = []
    e = extra.get(b["id"], {})
    accept = {norm(b["ko"]): "ko"}
    queries = []
    pp = b.get("price_product")
    if pp and e.get("reject_price_product"):
        flags.append("price_product_rejected")
    elif pp:
        # 가격에 연결된 상품명은 데일리샷 표기 그대로다. 이름 근거로 쓰되, 병 이름과 다르면 점검 표시를 남긴다.
        accept.setdefault(norm(pp), "price_product")
        if nums(pp) != nums(b["ko"]):
            flags.append("price_product_numbers_differ")
        elif sig(pp) != sig(b["ko"]):
            flags.append("price_product_name_differs")
        queries.append(base(pp))
    for a in e.get("aliases", []):
        accept.setdefault(norm(a), "alias")
    queries = list(e.get("queries", [])) + queries
    queries.append(b["ko"])
    seen, qs = set(), []
    for q in queries:
        if q and q not in seen:
            seen.add(q)
            qs.append(q)
    return qs, accept, flags


def match(b, rows, extra):
    """저장된 검색 결과에서 이 병과 같은 상품을 고른다. (같은 상품들, 나머지, 점검 표시)"""
    _, accept, flags = bottle_names(b, extra)
    prefixes = [norm(p) for p in extra.get(b["id"], {}).get("prefixes", [])]
    ko_sig = sig(b["ko"])
    matched, others = [], []
    for r in rows:
        n = norm(r["name"])
        rule = accept.get(n)
        if not rule and sig(r["name"]) == ko_sig:
            rule = "ko_reordered"
        if not rule and any(n.startswith(p) for p in prefixes):
            rule = "prefix"
        if rule:
            matched.append(dict(r, rule=rule))
        else:
            others.append(r)
    return matched, others, flags


def ds_search(q):
    body = http("https://dailyshot.co/m/search/result?q=" + urllib.parse.quote(q), 2)
    if body is None:
        return None
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', body, re.S)
    if not m:
        raise Blocked("데일리샷 응답에 __NEXT_DATA__가 없음: " + q)
    d = json.loads(m.group(1))
    try:
        return d["props"]["pageProps"]["dehydratedState"]["queries"][0]["state"]["data"]["pages"][0]
    except (KeyError, IndexError, TypeError):
        # 검색어에 따라 결과 묶음 없이 오는 쪽이 있다. 결과 없음으로 보고 기록만 남긴다.
        print("  데일리샷: 결과 묶음이 없는 응답 (%s) page=%s" % (q, d.get("page")), flush=True)
        return None


def stage_ds(bottles, opts):
    path = os.path.join(WORK, "ds_cache.json")
    cache = {} if (opts["refresh"] and not opts["only"]) else load(path, {})
    extra = load(os.path.join(ROOT, "tools", "trend_aliases.json"), {})
    todo = [b for b in bottles if (not opts["only"] or b["id"] in opts["only"])
            and (b["id"] not in cache or opts["refresh"])]
    print("데일리샷: 측정할 병", len(todo), "/ 저장된 병", len(cache))
    try:
        for i, b in enumerate(todo, 1):
            qs, _, _ = bottle_names(b, extra)
            rows, used, seen = [], [], set()
            truncated = False
            for q in qs[:3]:
                page = ds_search(q)
                used.append(q)
                if page is None:
                    continue
                if page.get("count", 0) > len(page["results"]):
                    truncated = True
                for r in page["results"]:
                    pid = r.get("top_product_id") or r.get("id")
                    name = r["top_product_name"]
                    if pid in seen or r.get("category") != "위스키" or RE_BUNDLE.search(name):
                        continue
                    seen.add(pid)
                    rows.append({"pid": pid, "name": name, "en": r.get("en_name"), "sub": r.get("subcategory"),
                                 "reviews": r.get("review_count") or 0, "sales": sales_num(r.get("sales_count"))})
                if match(b, rows, extra)[0]:
                    break
            cache[b["id"]] = {"queries": used, "rows": rows, "truncated": truncated, "date": time.strftime("%Y-%m-%d")}
            got = match(b, rows, extra)[0]
            if i % 20 == 0 or i == len(todo):
                save(path, cache)
                print("  %d/%d %s → %d건 (%d개 상품)" % (i, len(todo), b["ko"], sum(m["reviews"] for m in got), len(got)), flush=True)
    except Blocked as e:
        save(path, cache)
        print("데일리샷 중단:", e)
        return False
    save(path, cache)
    return True


# ---------------------------------------------------------------- 위키백과

def brand_of(b, brands):
    best = None
    for br in brands:
        if b["id"] in br.get("ids", []):
            return br
        for p in br.get("match", []):
            if b["en"].lower().startswith(p.lower()) and (best is None or len(p) > best[0]):
                best = (len(p), br)
    return best[1] if best else None


def pv_window():
    y, m = time.localtime().tm_year, time.localtime().tm_mon
    ey, em = (y, m - 1) if m > 1 else (y - 1, 12)          # 지난달까지
    sy, sm = ey, em - PV_MONTHS + 1
    while sm < 1:
        sy, sm = sy - 1, sm + 12
    return "%04d%02d0100" % (sy, sm), "%04d%02d2800" % (ey, em)


def stage_wiki(bottles, opts):
    brands = load(os.path.join(ROOT, "tools", "trend_brands.json"), [])
    path = os.path.join(WORK, "wiki_cache.json")
    cache = {} if opts["refresh"] else load(path, {})
    titles = sorted({br["wiki"] for br in brands if br.get("wiki")})
    start, end = pv_window()
    try:
        # 1) 제목 확인: 넘겨주기(redirect)는 본 문서 제목으로 바꾸고, 없는 문서는 표시한다
        need = [t for t in titles if t not in cache]
        for i in range(0, len(need), 40):
            chunk = need[i:i + 40]
            url = ("https://en.wikipedia.org/w/api.php?action=query&format=json&redirects=1&prop=info&titles="
                   + urllib.parse.quote("|".join(chunk)))
            d = json.loads(http(url, 6, {"User-Agent": UA_WIKI}))["query"]
            alias = {}
            for n in d.get("normalized", []):
                alias[n["from"]] = n["to"]
            for r in d.get("redirects", []):
                alias[r["from"]] = r["to"]
            pages = {p["title"]: p for p in d["pages"].values()}
            for t in chunk:
                final = alias.get(t, t)
                final = alias.get(final, final)
                p = pages.get(final)
                cache[t] = {"resolved": final, "missing": (p is None or "missing" in p),
                            "redirected": final != t, "bytes": (p or {}).get("length")}
            save(path, cache)
        # 2) 조회수
        need = [t for t in titles if not cache[t]["missing"] and cache[t].get("window") != [start, end]]
        print("위키: 조회수 받을 문서", len(need), "/ 전체", len(titles))
        for i, t in enumerate(need, 1):
            art = urllib.parse.quote(cache[t]["resolved"].replace(" ", "_"), safe="")
            url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/%s/monthly/%s/%s"
                   % (art, start, end))
            body = http(url, 6, {"User-Agent": UA_WIKI})
            cache[t]["views"] = sum(x["views"] for x in json.loads(body)["items"]) if body else 0
            cache[t]["window"] = [start, end]
            if i % 10 == 0 or i == len(need):
                save(path, cache)
                print("  %d/%d %s → %s" % (i, len(need), cache[t]["resolved"], cache[t]["views"]), flush=True)
    except Blocked as e:
        save(path, cache)
        print("위키 중단:", e)
        return False
    save(path, cache)
    return True


# ---------------------------------------------------------------- 네이버 (키가 있을 때만. 2026-11-11 현재 키가 없어 실제 호출로 검증하지 못했다)

def stage_naver(bottles, opts):
    cid, sec = os.environ.get("NAVER_CLIENT_ID"), os.environ.get("NAVER_CLIENT_SECRET")
    if not (cid and sec):
        print("네이버: 환경변수 NAVER_CLIENT_ID, NAVER_CLIENT_SECRET이 없어 건너뜀")
        return False
    path = os.path.join(WORK, "naver_cache.json")
    cache = {} if opts["refresh"] else load(path, {})
    extra = load(os.path.join(ROOT, "tools", "trend_aliases.json"), {})
    hdr = {"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": sec}
    todo = [b for b in bottles if b["id"] not in cache and (not opts["only"] or b["id"] in opts["only"])]
    try:
        for i, b in enumerate(todo, 1):
            e = extra.get(b["id"], {})
            terms = [b["ko"]] + e.get("search_aliases", [])
            row = {"terms": [], "blog": 0, "cafe": 0}
            for t in terms:
                q = '"%s"' % t + (" 위스키" if e.get("needs_context") else "")
                one = {"q": q}
                for kind, ep in (("blog", "blog"), ("cafe", "cafearticle")):
                    body = http("https://openapi.naver.com/v1/search/%s.json?display=1&query=%s" % (ep, urllib.parse.quote(q)), 0.3, hdr)
                    one[kind] = json.loads(body)["total"] if body else 0
                    row[kind] += one[kind]
                row["terms"].append(one)
            row["date"] = time.strftime("%Y-%m-%d")
            cache[b["id"]] = row
            if i % 25 == 0 or i == len(todo):
                save(path, cache)
                print("  %d/%d %s → 블로그 %d, 카페 %d" % (i, len(todo), b["ko"], row["blog"], row["cafe"]), flush=True)
    except Blocked as e:
        save(path, cache)
        print("네이버 중단:", e)
        return False
    save(path, cache)
    return True


# ---------------------------------------------------------------- 점수

def pct(values, p):
    v = sorted(values)
    if not v:
        return 0
    k = (len(v) - 1) * p
    lo, hi = int(math.floor(k)), int(math.ceil(k))
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def scale(x, lo, hi):
    if hi <= lo:
        return 0.0
    s = 100 * (math.log1p(x) - math.log1p(lo)) / (math.log1p(hi) - math.log1p(lo))
    return max(0.0, min(100.0, s))


def stage_score(bottles, opts):
    ds = load(os.path.join(WORK, "ds_cache.json"), {})
    wiki = load(os.path.join(WORK, "wiki_cache.json"), {})
    naver = load(os.path.join(WORK, "naver_cache.json"), {})
    brands = load(os.path.join(ROOT, "tools", "trend_brands.json"), [])
    sources = load(os.path.join(ROOT, "data", "sources.json"))
    obs = load(os.path.join(ROOT, "data", "observations.json"))
    out_path = os.path.join(ROOT, "data", "trends.json")
    missing = [b["id"] for b in bottles if b["id"] not in ds]
    if missing:
        print("데일리샷 측정이 없는 병 %d개. ds 단계를 먼저 끝내야 한다." % len(missing))
        return False
    extra = load(os.path.join(ROOT, "tools", "trend_aliases.json"), {})
    for b in bottles:      # 저장된 검색 결과에 현재 표기 규칙을 다시 적용한다(요청 없음)
        d = ds[b["id"]]
        d["matched"], d["others"], d["flags"] = match(b, d["rows"], extra)
        d["reviews"] = sum(m["reviews"] for m in d["matched"])
        d["sales"] = sum(m["sales"] for m in d["matched"])
    formula = "A" if all(b["id"] in naver for b in bottles) else "B"
    w = WEIGHTS[formula]

    src_en = {}
    for o in obs:
        if sources[o["source"]]["lang"] == "EN":
            src_en[o["bottle"]] = src_en.get(o["bottle"], 0) + 1

    raw = {}
    for b in bottles:
        br = brand_of(b, brands)
        wk = wiki.get(br["wiki"]) if br and br.get("wiki") else None
        flags = list(ds[b["id"]].get("flags", []))
        if not ds[b["id"]]["matched"]:
            flags.append("ds_no_product")
        if ds[b["id"]].get("truncated"):
            flags.append("ds_more_results")
        if br is None:
            flags.append("no_brand")
        elif not br.get("wiki") or (wk and wk["missing"]):
            flags.append("wiki_no_article")
        elif not br.get("sure", True):
            flags.append("wiki_unsure")
        r = {"ds_reviews": ds[b["id"]]["reviews"], "ds_sales": ds[b["id"]]["sales"],
             "ds_products": len(ds[b["id"]]["matched"]),
             "wiki_en": (wk or {}).get("views", 0) if wk and not wk["missing"] else 0,
             "wiki_title": (wk or {}).get("resolved") if wk and not wk["missing"] else None,
             "src_en": src_en.get(b["id"], 0)}
        if formula == "A":
            r["naver_blog"], r["naver_cafe"] = naver[b["id"]]["blog"], naver[b["id"]]["cafe"]
        raw[b["id"]] = (r, flags, br["brand"] if br else None)

    old = load(out_path, {}) if opts["keep_scales"] else {}
    scales = old.get("scales") if old.get("formula") == formula else None
    if not scales:
        scales = {"ds": {"lo": 0, "hi": round(pct([r["ds_reviews"] for r, _, _ in raw.values()], 0.99))},
                  "wiki": {"lo": WIKI_LO, "hi": round(pct([r["wiki_en"] for r, _, _ in raw.values()], 0.99))},
                  "src": {"lo": 0, "hi": round(pct([r["src_en"] for r, _, _ in raw.values()], 0.99))}}
        if formula == "A":
            scales["naver"] = {"lo": 0, "hi": round(pct([r["naver_blog"] + r["naver_cafe"] for r, _, _ in raw.values()], 0.99))}

    result = {}
    for b in bottles:
        r, flags, brand = raw[b["id"]]
        x = {"ds": r["ds_reviews"], "wiki": r["wiki_en"], "src": r["src_en"]}
        if formula == "A":
            x["naver"] = r["naver_blog"] + r["naver_cafe"]
        parts = {k: scale(x[k], scales[k]["lo"], scales[k]["hi"]) for k in w}
        dom_w = sum(w[k] for k in w if k in DOMESTIC)
        ovs_w = sum(w[k] for k in w if k not in DOMESTIC)
        dom = sum(parts[k] * w[k] for k in w if k in DOMESTIC) / dom_w
        ovs = sum(parts[k] * w[k] for k in w if k not in DOMESTIC) / ovs_w
        idx = sum(parts[k] * w[k] for k in w) / 100
        result[b["id"]] = {"index": round(idx), "domestic": round(dom), "overseas": round(ovs), "brand": brand,
                           "parts": {k: round(v, 1) for k, v in parts.items()}, "raw": r, "flags": flags,
                           "measured": ds[b["id"]]["date"]}

    # 등록 대기 중인 새 병(tools/trend-data/new_bottles.json)도 같은 기준으로 지수를 낸다.
    # 리뷰 수는 그 파일의 합산 값을 쓰고, 해외 매체 등장 횟수는 0이다. 상한·하한 계산에는 넣지 않는다.
    new_ids = []
    for nb in load(os.path.join(WORK, "new_bottles.json"), []):
        if nb["id"] in result:
            continue
        br = brand_of(nb, brands)
        wk = wiki.get(br["wiki"]) if br and br.get("wiki") else None
        has = bool(wk and not wk["missing"])
        if formula == "A" and nb["id"] not in naver:
            continue
        r = {"ds_reviews": nb.get("ds_reviews") or 0, "ds_sales": 0, "ds_products": 0,
             "wiki_en": wk.get("views", 0) if has else 0, "wiki_title": wk["resolved"] if has else None, "src_en": 0}
        x = {"ds": r["ds_reviews"], "wiki": r["wiki_en"], "src": 0}
        if formula == "A":
            r["naver_blog"], r["naver_cafe"] = naver[nb["id"]]["blog"], naver[nb["id"]]["cafe"]
            x["naver"] = r["naver_blog"] + r["naver_cafe"]
        parts = {k: scale(x[k], scales[k]["lo"], scales[k]["hi"]) for k in w}
        dom_w = sum(w[k] for k in w if k in DOMESTIC)
        ovs_w = sum(w[k] for k in w if k not in DOMESTIC)
        flags = ["new_bottle"] + ([] if has else ["wiki_no_article" if br else "no_brand"])
        result[nb["id"]] = {"index": round(sum(parts[k] * w[k] for k in w) / 100),
                            "domestic": round(sum(parts[k] * w[k] for k in w if k in DOMESTIC) / dom_w),
                            "overseas": round(sum(parts[k] * w[k] for k in w if k not in DOMESTIC) / ovs_w),
                            "brand": br["brand"] if br else None, "parts": {k: round(v, 1) for k, v in parts.items()},
                            "raw": r, "flags": flags, "measured": time.strftime("%Y-%m-%d")}
        new_ids.append(nb["id"])

    doc_head = {
        "version": 1,
        "measured": time.strftime("%Y-%m-%d"),
        "formula": formula,
        "formula_note": "트렌드지수 = 재료별 부분 점수의 가중 평균(0~100). 부분 점수 = 100×(ln(1+x)−ln(1+lo))÷(ln(1+hi)−ln(1+lo)). 티어 점수 계산에는 쓰지 않는다.",
        "weights": w,
        "domestic_parts": [k for k in w if k in DOMESTIC],
        "scales": scales,
        "materials": {
            "ds": "데일리샷 리뷰 수. 같은 병의 용량·패키지·구형 상품을 합산",
            "wiki": "영어 위키백과 브랜드(증류소) 문서의 최근 12개월 조회수. 브랜드 단위",
            "src": "수집된 해외(EN) 출처에 그 병이 등장한 횟수",
            "naver": "네이버 검색 API의 블로그+카페 결과 건수",
        },
    }
    # bottles.json처럼 한 줄에 한 병
    lines = ["{"]
    for k, v in doc_head.items():
        lines.append(" %s: %s," % (json.dumps(k), json.dumps(v, ensure_ascii=False)))
    lines.append(' "bottles": {')
    ids = [b["id"] for b in bottles] + new_ids
    for i, bid in enumerate(ids):
        lines.append("  %s: %s%s" % (json.dumps(bid), json.dumps(result[bid], ensure_ascii=False), "," if i < len(ids) - 1 else ""))
    lines.append(" }")
    lines.append("}")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    json.load(open(out_path, encoding="utf-8"))
    print("저장:", out_path, "/ 산식", formula, "/ 기준", json.dumps(scales, ensure_ascii=False))

    write_reports(bottles, ds, result)
    return True


def write_reports(bottles, ds, result):
    """미등록 병 목록과 합산 점검 목록을 tools/trend-data/에 쓴다."""
    extra = load(os.path.join(ROOT, "tools", "trend_aliases.json"), {})
    known_norm, known_sig, matched_pid = set(), set(), set()
    for b in bottles:
        _, accept, _ = bottle_names(b, extra)
        known_norm.update(accept)
        known_sig.add(sig(b["ko"]))
        for m in ds[b["id"]]["matched"]:
            matched_pid.add(m["pid"])
    groups, seen = {}, set()
    for b in bottles:
        for o in ds[b["id"]]["others"]:
            if o["pid"] in seen or o["pid"] in matched_pid:
                continue
            seen.add(o["pid"])
            n = norm(o["name"])
            if n in known_norm or sig(o["name"]) in known_sig or not n:
                continue
            g = groups.setdefault(n, {"name": base(o["name"]), "en": o["en"], "type": o["sub"], "reviews": 0, "sales": 0,
                                      "products": [], "seen_with": b["id"]})
            g["reviews"] += o["reviews"]
            g["sales"] += o["sales"]
            g["products"].append([o["name"], o["reviews"]])
    rows = sorted(groups.values(), key=lambda g: -g["reviews"])
    save(os.path.join(WORK, "unregistered.json"), rows, indent=1)

    # 합산 점검: 사람이 봐야 할 병
    review = []
    owner = {}
    for b in bottles:
        for m in ds[b["id"]]["matched"]:
            owner.setdefault(m["pid"], []).append(b["id"])
    for b in bottles:
        d = ds[b["id"]]
        why = []
        if not d["matched"]:
            why.append("데일리샷에서 같은 병을 찾지 못함")
        if "price_product_numbers_differ" in d["flags"]:
            why.append("가격에 연결된 상품명의 숫자가 병 이름과 다름: %s" % b.get("price_product"))
        if "price_product_name_differs" in d["flags"]:
            why.append("가격 상품명으로만 연결됨(이름 표기가 다름): %s" % b.get("price_product"))
        shared = sorted({x for m in d["matched"] for x in owner[m["pid"]] if x != b["id"]})
        if shared:
            why.append("같은 상품이 다른 병에도 합산됨: %s" % ", ".join(shared))
        bases = sorted({base(m["name"]) for m in d["matched"]})
        if len(bases) > 1:
            why.append("서로 다른 기본 이름이 합쳐짐: %s" % " / ".join(bases))
        if d.get("truncated") and d["matched"]:
            why.append("검색 결과가 한 쪽을 넘어 일부 변형이 빠졌을 수 있음")
        if why:
            review.append({"id": b["id"], "ko": b["ko"], "reviews": d["reviews"], "master_ds_reviews": b.get("ds_reviews"),
                           "matched": [[m["name"], m["reviews"], m["rule"]] for m in d["matched"]], "why": why})
    save(os.path.join(WORK, "merge_review.json"), review, indent=1)
    merged = {b["id"]: {"ko": b["ko"], "reviews": ds[b["id"]]["reviews"], "sales": ds[b["id"]]["sales"],
                        "master_ds_reviews": b.get("ds_reviews"),
                        "products": [[m["name"], m["reviews"], m["rule"]] for m in ds[b["id"]]["matched"]]} for b in bottles}
    save(os.path.join(WORK, "ds_merged.json"), merged, indent=1)
    print("미등록 병 %d개, 합산 점검 대상 %d병 → tools/trend-data/" % (len(rows), len(review)))


def main():
    args = sys.argv[1:]
    opts = {"refresh": "--refresh" in args, "keep_scales": "--keep-scales" in args, "only": None}
    if "--only" in args:
        opts["only"] = set(args[args.index("--only") + 1].split(","))
    stages = [a for a in args if a in ("ds", "wiki", "naver", "score")] or ["ds", "wiki", "naver", "score"]
    os.makedirs(WORK, exist_ok=True)
    bottles = load(os.path.join(ROOT, "data", "bottles.json"))
    fn = {"ds": stage_ds, "wiki": stage_wiki, "naver": stage_naver, "score": stage_score}
    for s in stages:
        fn[s](bottles, opts)


if __name__ == "__main__":
    main()
