#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NAS용 수집기 (Python 3.8, 표준 라이브러리만 사용).

하는 일: 입력 파일(in/bottles_min.json)에 적힌 대로 바깥 자료를 받아 원자료만 파일로 남긴다.
계산·병합·git·빌드는 하지 않는다(그 일은 PC의 merge.py가 한다).

단계
  wiki  영어 위키백과 문서의 최근 12개월 조회수 (기본으로 켜짐)
  ds    데일리샷 검색 결과(상품명·가격·평점·리뷰 수). 기본으로 꺼짐. --stages ds,wiki 로 켠다

사용 (NAS의 run.sh는 `python3.8 -I collect.py --in <in 폴더> --out <out 폴더>` 로 부른다)
  python3 collect.py --in in --out out    # 인자가 이것뿐이면 wiki만 돈다
  python3 collect.py --stages ds,wiki     # 데일리샷 포함(사용자 승인 뒤에만). in/config.json으로도 켤 수 있다
  python3 collect.py --date 2026-11-25    # 그 날짜 폴더에 쓴다(없으면 새로)
  python3 collect.py --new                # 끝나지 않은 실행이 있어도 오늘 날짜로 새로 시작
  python3 collect.py --limit 5            # 단계마다 앞의 5건만(시험용)
  python3 collect.py --plan               # 요청 없이 무엇을 할지만 출력

입력 (--in 은 폴더 또는 파일)
  bottles_min.json  make_input.py가 만든 병·문서 목록
  config.json       없어도 된다. {"stages": ["wiki", "ds"], "max_minutes": 35}

이어 하기: 가장 최근 날짜 폴더에 DONE이 없고 8일 안의 것이며 위키 조회 구간이 같으면 그 폴더를 이어서 채운다.
시간 한도: max_minutes(기본 35분)가 지나면 항목 사이에서 스스로 멈춘다(상태 partial, 종료 코드 0). 다음 실행이 이어서 받는다.

출력 (out/<날짜>/)
  wiki.jsonl    한 줄에 문서 하나  {"title","resolved","missing","views","window","at"}
  ds.jsonl      한 줄에 병 하나    {"id","queries","rows":[…],"truncated","at"}
                받는 동안에는 이름이 *.jsonl.part 이고, 그 단계가 끝나면 *.jsonl 로 바뀐다
  failed.jsonl  실패한 항목        {"stage","key","error","at"}
  run.log       실행 기록
  summary.json  단계별 성공·실패 수, 상태(done | partial | blocked | stopped | running)
  DONE          켜 둔 단계가 모두 끝났을 때만 마지막에 생긴다. PC는 이 파일이 있는 폴더만 쓴다

지키는 것
  - 요청 간격: 데일리샷 2초, 위키미디어 6초. 한 번에 한 요청만 보낸다.
  - 403·429·401 또는 예상과 다른 응답이 오면 그 자리에서 멈추고 기록한다. 다시 시도하지 않는다.
  - 그 밖의 오류(시간 초과 등)는 그 항목만 실패로 적고 넘어가되, 연달아 5번이면 멈춘다.
  - 응답은 항목마다 받아 바로 한 줄로 적고 버린다(쌓아 두지 않는다).
  - User-Agent에는 사이트 주소만 넣는다. 개인 정보는 넣지 않는다.
종료 코드: 0 정상(시간 한도로 멈춘 것 포함), 2 차단으로 멈춤, 3 연속 오류로 멈춤, 1 입력 오류
"""
import json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (compatible; whisky-trend-research/0.1)"
UA_WIKI = "nidwolf-trend/1.0 (https://nidwolf.com) python-urllib"
PAUSE_DS, PAUSE_WIKI = 2, 6
PV_MONTHS = 12
MAX_ERRORS_IN_ROW = 5
MAX_QUERIES = 3
MAX_MINUTES = 35                # run.sh의 실행 시간 상한(40분)보다 먼저 스스로 멈춘다
RESUME_DAYS = 8
START = time.time()
STAGES = ("wiki", "ds")


class Blocked(Exception):
    pass


# ---------------------------------------------------------------- 상품명 정규화
# tools/trend_collect.py의 base/norm/sig와 같은 규칙이다. 검색어를 몇 개까지 보낼지 정하는 데만 쓴다.
# 두 곳의 규칙이 어긋나지 않는지는 make_input.py가 실행할 때마다 대조한다.
PACK = ("전용잔|하이볼|온더락|글라스|글랜캐런|글렌캐런|노징|위스키잔|플라스크|선물|패키지|세트|증정|쿠퍼잔|랜턴|"
        "스피커|스틱|코스터|바이알|미니어처|미니어쳐|케이스|기프트|코퍼잔|머그|텀블러|레만")
RE_PAREN = re.compile(r"\([^)]*\)|\[[^\]]*\]")
RE_VOL = re.compile(r"\d+(\.\d+)?\s*(ml|mL|ML|L|l)(?![A-Za-z가-힣])")
RE_ABV = re.compile(r"\d+(\.\d+)?\s*%")
RE_PACK = re.compile(r"\s*\S*(%s).*$" % PACK)
RE_MULTI = re.compile(r"\s*(x\s*\d+|\d+병)\s*$")
RE_YEAR = re.compile(r"\s+20\d\d(-\d\d\w?)?\s*$")
RE_BATCH = re.compile(r"\s*배치\s*(넘버\s*)?#?\d+.*$")
RE_BUNDLE = re.compile(r"\s&|&\s")


def base(name):
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
    b = base(name)
    rest = "".join(sorted(re.sub(r"[\d\s]+", "", b)))
    return rest + "|" + ",".join(sorted(re.findall(r"\d+", b)))


def sales_num(s):
    if not s:
        return 0
    m = re.search(r"([\d,.]+)\s*(만)?", str(s))
    if not m:
        return 0
    try:
        v = float(m.group(1).replace(",", ""))
    except ValueError:
        return 0
    return int(v * 10000) if m.group(2) else int(v)


def has_match(entry, rows):
    """이 병과 같은 상품이 검색 결과에 있는지(다음 검색어를 더 보낼지 정하는 용도)."""
    accept = set(entry.get("accept", []))
    prefixes = entry.get("prefixes", [])
    excluded = set(entry.get("exclude_pids", []))
    for r in rows:
        if r["pid"] in excluded:
            continue
        n = norm(r["name"])
        if n in accept or sig(r["name"]) == entry.get("sig") or any(n.startswith(p) for p in prefixes):
            return True
    return False


# ---------------------------------------------------------------- 공통

def now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


class Run(object):
    def __init__(self, out_dir):
        self.dir = out_dir
        os.makedirs(out_dir, exist_ok=True)
        self.log_path = os.path.join(out_dir, "run.log")
        self.summary_path = os.path.join(out_dir, "summary.json")
        self.summary = {"status": "running", "started": now(), "finished": None, "stages": {}}
        if os.path.exists(self.summary_path):
            try:
                with open(self.summary_path, encoding="utf-8") as f:
                    old = json.load(f)
                self.summary["started"] = old.get("started", self.summary["started"])
                self.summary["stages"] = old.get("stages", {})
            except ValueError:
                pass

    def log(self, msg):
        line = "%s %s" % (now(), msg)
        print(line, flush=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def append(self, name, obj):
        with open(os.path.join(self.dir, name), "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")

    def done_keys(self, name, key):
        """이미 적힌 항목의 키만 읽는다(내용은 쌓지 않는다)."""
        path = os.path.join(self.dir, name)
        keys = set()
        if not os.path.exists(path):
            return keys
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    keys.add(json.loads(line)[key])
                except (ValueError, KeyError):
                    continue        # 쓰다 끊긴 마지막 줄은 버린다(그 항목은 다시 받는다)
        return keys

    def save_summary(self, status=None):
        if status:
            self.summary["status"] = status
            self.summary["finished"] = now()
        tmp = self.summary_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.summary, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.summary_path)


def http(url, pause, ua):
    """한 번만 요청한다. 차단이면 Blocked, 404면 None, 그 밖의 오류는 그대로 올린다."""
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept-Language": "ko,en;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 429):
            raise Blocked("HTTP %d: %s" % (e.code, url))
        if e.code == 404:
            return None
        raise
    finally:
        time.sleep(pause)


def run_items(run, stage, items, key_of, fetch, final_name, limit, max_minutes):
    """items를 차례로 받아 한 줄씩 적는다. 상태를 돌려준다. 받는 동안은 .part, 다 받으면 이름을 바꾼다."""
    out_name = final_name + ".part"
    if os.path.exists(os.path.join(run.dir, final_name)):
        run.log("[%s] 이미 끝난 단계라 건너뜀" % stage)
        run.summary["stages"].setdefault(stage, {})["status"] = "done"
        return "done"
    done = run.done_keys(out_name, "id" if stage == "ds" else "title")
    todo = [x for x in items if key_of(x) not in done]
    if limit:
        todo = todo[:limit]
    st = run.summary["stages"].setdefault(stage, {})
    st.update({"total": len(items), "already": len(done), "ok": 0, "failed": 0, "status": "running"})
    run.log("[%s] 전체 %d, 이미 받은 것 %d, 이번에 받을 것 %d" % (stage, len(items), len(done), len(todo)))
    run.save_summary()
    errors_in_row = 0
    status = "done"
    for i, x in enumerate(todo, 1):
        k = key_of(x)
        if time.time() - START > max_minutes * 60:
            run.log("[%s] 시간 한도 %d분이 지나 멈춤. 다음 실행이 이어서 받는다 (%d/%d)" % (stage, max_minutes, i - 1, len(todo)))
            status = "partial"
            break
        try:
            rec = fetch(x)
            run.append(out_name, rec)
            st["ok"] += 1
            errors_in_row = 0
        except Blocked as e:
            run.append("failed.jsonl", {"stage": stage, "key": k, "error": "blocked: %s" % e, "at": now()})
            run.log("[%s] 차단으로 멈춤: %s" % (stage, e))
            st["failed"] += 1
            status = "blocked"
            break
        except Exception as e:      # 시간 초과·5xx·형식 오류: 이 항목만 실패로 적고 넘어간다
            run.append("failed.jsonl", {"stage": stage, "key": k, "error": "%s: %s" % (type(e).__name__, e), "at": now()})
            run.log("[%s] 실패 %s: %s: %s" % (stage, k, type(e).__name__, e))
            st["failed"] += 1
            errors_in_row += 1
            if errors_in_row >= MAX_ERRORS_IN_ROW:
                run.log("[%s] 연달아 %d번 실패해 멈춤" % (stage, errors_in_row))
                status = "stopped"
                break
        if i % 20 == 0 or i == len(todo):
            run.log("[%s] %d/%d" % (stage, i, len(todo)))
            run.save_summary()
    if status == "done" and limit and len([x for x in items if key_of(x) not in done]) > len(todo):
        status = "partial"          # --limit 때문에 남은 것이 있다
    if status == "done":
        part = os.path.join(run.dir, out_name)
        if not os.path.exists(part):
            open(part, "a", encoding="utf-8").close()
        os.replace(part, os.path.join(run.dir, final_name))
    st["status"] = status
    run.save_summary()
    return status


# ---------------------------------------------------------------- 위키백과

def pv_window(t=None):
    t = t or time.localtime()
    y, m = t.tm_year, t.tm_mon
    ey, em = (y, m - 1) if m > 1 else (y - 1, 12)          # 지난달까지
    sy, sm = ey, em - PV_MONTHS + 1
    while sm < 1:
        sy, sm = sy - 1, sm + 12
    return "%04d%02d0100" % (sy, sm), "%04d%02d2800" % (ey, em)


def wiki_resolve(title):
    """문서가 있는지, 넘겨주기면 본 문서 제목이 무엇인지 확인한다."""
    url = ("https://en.wikipedia.org/w/api.php?action=query&format=json&redirects=1&prop=info&titles="
           + urllib.parse.quote(title))
    body = http(url, PAUSE_WIKI, UA_WIKI)
    if body is None:
        raise ValueError("제목 확인 응답 없음")
    d = json.loads(body)["query"]
    alias = {}
    for n in d.get("normalized", []):
        alias[n["from"]] = n["to"]
    for r in d.get("redirects", []):
        alias[r["from"]] = r["to"]
    final = alias.get(title, title)
    final = alias.get(final, final)
    page = None
    for p in d.get("pages", {}).values():
        if p.get("title") == final:
            page = p
    return final, (page is None or "missing" in page)


def wiki_fetch(item, window):
    title = item["title"]
    resolved, missing = item.get("resolved"), False
    if not resolved:
        resolved, missing = wiki_resolve(title)
    rec = {"title": title, "resolved": resolved, "missing": missing, "views": 0, "window": list(window), "at": now()}
    if missing:
        return rec
    art = urllib.parse.quote(resolved.replace(" ", "_"), safe="")
    url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/%s/monthly/%s/%s"
           % (art, window[0], window[1]))
    body = http(url, PAUSE_WIKI, UA_WIKI)
    if body is None:                # 404: 그 기간에 조회 기록이 없다
        rec["no_data"] = True
        return rec
    rec["views"] = sum(x["views"] for x in json.loads(body)["items"])
    return rec


# ---------------------------------------------------------------- 데일리샷

RE_NEXT = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def ds_search(q):
    body = http("https://dailyshot.co/m/search/result?q=" + urllib.parse.quote(q), PAUSE_DS, UA)
    if body is None:
        return None
    m = RE_NEXT.search(body)
    del body
    if not m:
        raise Blocked("데일리샷 응답에 __NEXT_DATA__가 없음: " + q)
    d = json.loads(m.group(1))
    try:
        return d["props"]["pageProps"]["dehydratedState"]["queries"][0]["state"]["data"]["pages"][0]
    except (KeyError, IndexError, TypeError):
        return None                 # 검색어에 따라 결과 묶음 없이 온다. 결과 없음으로 본다


def ds_fetch(entry):
    rows, used, seen = [], [], set()
    truncated = False
    for q in entry.get("queries", [])[:MAX_QUERIES]:
        if not q:
            continue
        page = ds_search(q)
        used.append(q)
        if page is None:
            continue
        results = page.get("results") or []
        if (page.get("count") or 0) > len(results):
            truncated = True
        for r in results:
            pid = r.get("top_product_id") or r.get("id")
            name = r.get("top_product_name") or r.get("name") or ""
            if pid in seen or r.get("category") != "위스키" or RE_BUNDLE.search(name):
                continue
            seen.add(pid)
            rows.append({"pid": pid, "name": name, "en": r.get("en_name"), "sub": r.get("subcategory"),
                         "reviews": r.get("review_count") or 0, "rating": r.get("review_rate"),
                         "sales": sales_num(r.get("sales_count")), "price": r.get("price"),
                         "vol": r.get("thumbnail_display_volume"), "service": r.get("service_type")})
        del page
        if has_match(entry, rows):
            break
    return {"id": entry["id"], "queries": used, "rows": rows, "truncated": truncated, "at": now()}


# ---------------------------------------------------------------- 실행

def latest_unfinished(out_root, window):
    """이어서 채울 날짜 폴더. 가장 최근 폴더에 DONE이 없고, 8일 안이며, 위키 조회 구간이 같을 때만."""
    if not os.path.isdir(out_root):
        return None
    names = sorted(n for n in os.listdir(out_root) if re.match(r"^\d{4}-\d{2}-\d{2}$", n))
    if not names:
        return None
    name = names[-1]
    d = os.path.join(out_root, name)
    if os.path.exists(os.path.join(d, "DONE")):
        return None
    try:
        age = (time.time() - time.mktime(time.strptime(name, "%Y-%m-%d"))) / 86400
        with open(os.path.join(d, "summary.json"), encoding="utf-8") as f:
            old_window = json.load(f).get("window")
    except (ValueError, OSError):
        return None
    return name if age <= RESUME_DAYS and old_window == list(window) else None


def opt(args, name, default=None):
    return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else default


def main():
    args = sys.argv[1:]
    in_path = opt(args, "--in", os.path.join(HERE, "in"))
    in_dir = in_path if os.path.isdir(in_path) else os.path.dirname(in_path)
    if os.path.isdir(in_path):
        in_path = os.path.join(in_path, "bottles_min.json")
    out_root = opt(args, "--out", os.path.join(HERE, "out"))
    config = {}
    cfg_path = os.path.join(in_dir, "config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, encoding="utf-8") as f:
                config = json.load(f)
        except ValueError as e:
            print("config.json을 읽지 못함: %s" % e)
            return 1
    stages = opt(args, "--stages")
    stages = [s for s in stages.split(",") if s] if stages else list(config.get("stages") or ["wiki"])
    limit = int(opt(args, "--limit", "0"))
    max_minutes = float(opt(args, "--max-minutes", config.get("max_minutes", MAX_MINUTES)))
    bad = [s for s in stages if s not in STAGES]
    if bad or not stages:
        print("알 수 없는 단계: %s (쓸 수 있는 값: %s)" % (bad, ",".join(STAGES)))
        return 1
    if not os.path.exists(in_path):
        print("입력 파일이 없음:", in_path)
        return 1
    with open(in_path, encoding="utf-8") as f:
        inp = json.load(f)
    if inp.get("format") != 1:
        print("입력 파일 형식이 다름(format=%r). make_input.py로 다시 만들 것" % inp.get("format"))
        return 1
    window = pv_window()
    date = opt(args, "--date")
    if not date and "--new" not in args:
        date = latest_unfinished(out_root, window)
    date = date or time.strftime("%Y-%m-%d")
    if "--plan" in args:
        print("입력 %s (만든 날 %s): 병 %d, 위키 문서 %d" % (in_path, inp.get("made"), len(inp["bottles"]), len(inp["wiki"])))
        print("단계 %s / 출력 %s / 위키 구간 %s~%s" % (stages, os.path.join(out_root, date), window[0], window[1]))
        print("예상 시간: wiki 약 %d분, ds 약 %d분" % (len(inp["wiki"]) * PAUSE_WIKI // 60 + 1,
                                                 len([b for b in inp["bottles"] if b.get("queries")]) * PAUSE_DS * 1.3 // 60 + 1))
        return 0

    done_path = os.path.join(out_root, date, "DONE")
    if os.path.exists(done_path):       # 같은 날짜가 이미 끝나 있으면 다시 받지 않는다
        with open(done_path, encoding="utf-8") as f:
            had = set(f.read().split()[-1].split(",")) if os.path.getsize(done_path) else set()
        if set(stages) <= had:
            print("%s %s 폴더는 이미 완료(DONE)돼 있어 아무것도 받지 않음" % (now(), date))
            return 0
        os.remove(done_path)            # 단계를 더 켰으면 완료 표시를 내리고 남은 단계만 받는다
    run = Run(os.path.join(out_root, date))
    run.summary["status"] = "running"
    run.summary["input_made"] = inp.get("made")
    run.summary["window"] = list(window)
    run.summary["stages_wanted"] = [s for s in STAGES if s in stages]
    run.log("시작: 단계 %s, 폴더 %s, 입력 %s(만든 날 %s), 시간 한도 %g분, python %s" % (
        ",".join(stages), date, os.path.basename(in_path), inp.get("made"), max_minutes, sys.version.split()[0]))
    code, final = 0, "done"
    for stage in STAGES:            # 위키를 먼저, 데일리샷을 나중에
        if stage not in stages:
            continue
        if stage == "wiki":
            status = run_items(run, "wiki", inp["wiki"], lambda x: x["title"], lambda x: wiki_fetch(x, window), "wiki.jsonl", limit, max_minutes)
        else:
            items = [b for b in inp["bottles"] if b.get("queries")]
            status = run_items(run, "ds", items, lambda x: x["id"], ds_fetch, "ds.jsonl", limit, max_minutes)
        if status == "blocked":
            code, final = 2, "blocked"
            break                   # 한 곳이 막히면 뒤 단계도 돌리지 않고 사람에게 넘긴다
        if status == "stopped":
            code, final = 3, "stopped"
            break
        if status == "partial":
            final = "partial"
            break                   # 남은 것이 있으면 뒤 단계로 넘어가지 않는다(다음 실행이 이어서)
    run.save_summary(final)
    if final == "done":             # 완료 표시는 맨 마지막에, 임시 이름으로 쓴 뒤 바꾼다
        tmp = os.path.join(run.dir, "DONE.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("%s %s\n" % (now(), ",".join(run.summary["stages_wanted"])))
        os.replace(tmp, os.path.join(run.dir, "DONE"))
    run.log("끝: 상태 %s / %s" % (final, json.dumps(run.summary["stages"], ensure_ascii=False)))
    return code


if __name__ == "__main__":
    sys.exit(main())
