#!/usr/bin/env python3
"""merge.py와 backfill.py가 같이 쓰는 것: 문턱값, 가격 이력·변경 기록의 형식과 읽기·쓰기."""
import datetime, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data")
STATE = os.path.join(HERE, "state", "last.json")       # 직전 병합 때의 병별 상태(티어·가격·트렌드지수)
HISTORY = os.path.join(DATA, "price_history.json")
CHANGES = os.path.join(DATA, "changes.json")

# 변경 기록에 적는 문턱값
PRICE_PCT = 0.05        # 가격이 5% 이상 바뀌었거나
PRICE_ABS = 3000        # 3,000원 이상 바뀌었을 때만 적는다
TREND_PTS = 5           # 트렌드지수는 5점 이상 바뀌었을 때만 적는다
# 자동 반영을 막는 문턱값
OUTLIER_PCT = 0.40      # 가격이 직전보다 40% 넘게 바뀌면 사람이 확인한다
# 보관 한도
HISTORY_MAX = 104       # 병당 가격 점 수(주 1회면 2년치)
KEEP_DAYS = 84          # 변경 기록 보관 기간(12주)

TYPE_ORDER = {"new": 0, "tier": 1, "price": 2, "trend": 3, "removed": 4}


def load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    with open(tmp, encoding="utf-8") as f:
        json.load(f)                 # 쓴 것이 올바른 JSON인지 확인한 뒤에 바꿔 놓는다
    os.replace(tmp, path)


def dumps(x):
    return json.dumps(x, ensure_ascii=False)


def bottles_text(bottles):
    """data/bottles.json의 형식(한 줄에 한 병)."""
    return "[\n" + ",\n".join(dumps(b) for b in bottles) + "\n]\n"


def history_text(hist, order):
    """data/price_history.json: {"<id>": [["2026-11-11", 74800], …], …}  한 줄에 한 병, bottles.json 순서."""
    ids = [i for i in order if i in hist] + sorted(i for i in hist if i not in set(order))
    return "{\n" + ",\n".join(" %s: %s" % (dumps(i), dumps(hist[i])) for i in ids) + "\n}\n" if ids else "{}\n"


def changes_text(changes):
    """data/changes.json: [{"date","type","id","from","to"}, …]  한 줄에 한 건, 최근 날짜가 위."""
    return "[\n" + ",\n".join(" " + dumps(c) for c in changes) + "\n]\n" if changes else "[]\n"


def vol_ml(name):
    """상품명에 적힌 용량(ml). 없으면 None."""
    if not name:
        return None
    m = re.search(r"(\d{2,4})\s*ml", name, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d(?:\.\d+)?)\s*L(?![A-Za-z가-힣])", name)
    return int(float(m.group(1)) * 1000) if m else None


def add_point(hist, bid, date, price):
    """가격 점 하나를 더한다. 같은 날짜가 이미 있으면 그 값을 바꾼다. 값이 같아도 측정일은 적는다."""
    pts = hist.setdefault(bid, [])
    pts[:] = [p for p in pts if p[0] != date]
    pts.append([date, price])
    pts.sort(key=lambda p: p[0])
    del pts[:-HISTORY_MAX]


def price_worth_noting(old, new):
    d = abs(new - old)
    return d >= PRICE_ABS or (old and d / old >= PRICE_PCT)


def diff_states(before, after, date, removed_names=None):
    """두 상태({id: {"tier","price","trend"}})를 비교해 변경 기록을 만든다."""
    out = []
    removed_names = removed_names or {}
    for i, a in after.items():
        b = before.get(i)
        if b is None:
            out.append({"date": date, "type": "new", "id": i, "from": None, "to": None})
            continue
        if a.get("tier") and b.get("tier") and a["tier"] != b["tier"]:
            out.append({"date": date, "type": "tier", "id": i, "from": b["tier"], "to": a["tier"]})
        if a.get("price") and b.get("price") and a["price"] != b["price"] and price_worth_noting(b["price"], a["price"]):
            out.append({"date": date, "type": "price", "id": i, "from": b["price"], "to": a["price"]})
        if a.get("trend") is not None and b.get("trend") is not None and abs(a["trend"] - b["trend"]) >= TREND_PTS:
            out.append({"date": date, "type": "trend", "id": i, "from": b["trend"], "to": a["trend"]})
    for i, b in before.items():
        if i not in after:
            out.append({"date": date, "type": "removed", "id": i, "from": None, "to": None,
                        "ko": removed_names.get(i) or b.get("ko")})
    return out


def merge_changes(existing, new, today):
    """새 기록을 더하고(같은 날짜·종류·병은 새것으로 바꿈) 12주가 지난 것은 버린다. 최근 날짜가 위."""
    cut = (datetime.date.fromisoformat(today) - datetime.timedelta(days=KEEP_DAYS)).isoformat()
    by = {}
    for c in list(existing or []) + list(new):
        by[(c["date"], c["type"], c["id"])] = c
    keep = [c for c in by.values() if c["date"] >= cut]
    keep.sort(key=lambda c: c["id"])
    keep.sort(key=lambda c: TYPE_ORDER.get(c["type"], 9))
    keep.sort(key=lambda c: c["date"], reverse=True)
    return keep


def current_state(bottles, trends):
    """지금 저장소 자료의 병별 상태. 티어는 build.py의 계산 결과를 그대로 쓴다(price·trends와 무관)."""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import build
    ws, _, _, errs, _ = build.compute()
    if errs:
        raise SystemExit("build.py 계산에 오류가 있어 멈춥니다: %s" % errs[:3])
    tiers = {w["id"]: w["tier"] for w in ws}
    tb = (trends or {}).get("bottles", {})
    return {b["id"]: {"tier": tiers.get(b["id"]), "price": b.get("price"),
                      "trend": tb.get(b["id"], {}).get("index"), "ko": b["ko"]} for b in bottles}
