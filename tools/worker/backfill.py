#!/usr/bin/env python3
"""과거분 채우기 (한 번만 실행). git 이력의 data/bottles.json 과거 판을 읽어
data/price_history.json 과 data/changes.json 의 초판을 만든다. git은 읽기만 한다(git log, git show).

  python3 tools/worker/backfill.py --dry-run   # 무엇이 만들어지는지만 본다
  python3 tools/worker/backfill.py             # 파일을 만든다(이미 있으면 멈춤. 덮어쓰려면 --force)

채우는 것
  - 새 병(new): 처음 공개한 날(가장 이른 커밋 날짜)의 병은 기준으로만 삼고, 그 뒤에 들어온 병만 적는다
  - 빠진 병(removed)
  - 가격(price): 같은 상품의 가격이 문턱값 이상 바뀐 경우. 가격 상품이 다른 상품으로 바뀐 것은 가격 변동으로 치지 않는다
  - 가격 이력: 판마다 (price_date 또는 커밋 날짜, price)를 한 점으로. 가격 상품이 바뀌면 그 병의 이력은 새로 시작한다
채우지 않는 것
  - 티어 변동: 과거 판마다 그때의 계산 규칙으로 다시 계산해야 해서 소급하지 않는다. 다음 병합부터 잡힌다
  - 트렌드지수 변동
끝에 지금 상태를 tools/worker/state/last.json 에 적어, 다음 병합(merge.py)이 여기서부터 비교하게 한다.
"""
import json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wlib                    # noqa: E402
from wlib import ROOT, DATA    # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "tools"))
import trend_collect as tc     # noqa: E402

REL = "data/bottles.json"


def git(*a):
    return subprocess.run(["git", "-C", ROOT] + list(a), check=True, capture_output=True, text=True, encoding="utf-8").stdout


def versions():
    """(날짜, 커밋, 병 목록)을 오래된 것부터. 작업 폴더의 파일이 마지막 커밋과 다르면 오늘 날짜로 하나 더한다."""
    out = []
    for line in git("log", "--reverse", "--format=%h %ad", "--date=short", "--", REL).splitlines():
        h, d = line.split()
        out.append((d, h, json.loads(git("show", "%s:%s" % (h, REL)))))
    cur = wlib.load(os.path.join(DATA, "bottles.json"))
    if not out or cur != out[-1][2]:
        out.append((time.strftime("%Y-%m-%d"), "작업 폴더", cur))
    return out


def same_product(a, b):
    pa, pb = a.get("price_product"), b.get("price_product")
    if not pa or not pb:
        return pa == pb
    return tc.base(pa) == tc.base(pb) and wlib.vol_ml(pa) == wlib.vol_ml(pb)


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    if not dry and "--force" not in args and (os.path.exists(wlib.HISTORY) or os.path.exists(wlib.CHANGES)):
        print("price_history.json 또는 changes.json이 이미 있습니다. 덮어쓰려면 --force 를 붙이세요.")
        return 1
    vs = versions()
    first_day = vs[0][0]
    hist, records = {}, []
    prev, names = {}, {}
    for d, h, bottles in vs:
        cur = {b["id"]: b for b in bottles}
        names.update({b["id"]: b["ko"] for b in bottles})
        baseline = d == first_day
        for i, b in cur.items():
            p = prev.get(i)
            if p is None and prev and not baseline:
                records.append({"date": d, "type": "new", "id": i, "from": None, "to": None})
            if b.get("price"):
                if p is not None and p.get("price") and not same_product(p, b):
                    hist.pop(i, None)                       # 다른 상품의 가격은 한 그래프에 잇지 않는다
                wlib.add_point(hist, i, b.get("price_date") or d, b["price"])
                if (p is not None and p.get("price") and same_product(p, b) and p["price"] != b["price"] and not baseline
                        and wlib.price_worth_noting(p["price"], b["price"])):
                    records.append({"date": b.get("price_date") or d, "type": "price", "id": i, "from": p["price"], "to": b["price"]})
            elif p is not None and p.get("price"):
                hist.pop(i, None)                           # 가격을 비운 병(잘못 연결됐던 상품 등)은 이력도 비운다
        if not baseline:
            for i in prev:
                if i not in cur:
                    records.append({"date": d, "type": "removed", "id": i, "from": None, "to": None, "ko": names.get(i)})
                    hist.pop(i, None)
        prev = cur
    bottles = vs[-1][2]
    today = time.strftime("%Y-%m-%d")
    changes = wlib.merge_changes([], records, today)
    state = wlib.current_state(bottles, wlib.load(os.path.join(DATA, "trends.json")))

    by = {}
    for c in changes:
        by.setdefault((c["date"], c["type"]), []).append(c["id"])
    print("읽은 판 %d개 (%s ~ %s), 기준일(처음 공개한 날) %s" % (len(vs), vs[0][0], vs[-1][0], first_day))
    print("가격 이력: %d병, 점 %d개 (점이 2개 이상인 병 %d)" % (len(hist), sum(len(v) for v in hist.values()), sum(1 for v in hist.values() if len(v) > 1)))
    print("변경 기록: %d건" % len(changes))
    for (d, t), ids in sorted(by.items(), reverse=True):
        print("   %s %s %d건: %s%s" % (d, t, len(ids), ", ".join(ids[:8]), " …" if len(ids) > 8 else ""))
    if dry:
        print("(미리 보기: 아무것도 쓰지 않았습니다)")
        return 0
    wlib.write_text(wlib.HISTORY, wlib.history_text(hist, [b["id"] for b in bottles]))
    wlib.write_text(wlib.CHANGES, wlib.changes_text(changes))
    wlib.write_text(wlib.STATE, json.dumps({"date": today, "bottles": state}, ensure_ascii=False, indent=0))
    print("저장: %s, %s, %s" % (wlib.HISTORY, wlib.CHANGES, wlib.STATE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
