#!/usr/bin/env python3
"""NAS 수집 결과(원자료 폴더)를 저장소 자료에 합친다 (PC에서 실행).

  python3 tools/worker/merge.py tools/worker/out/2026-11-25 --dry-run   # 바뀔 내용만 본다(아무것도 쓰지 않음)
  python3 tools/worker/merge.py tools/worker/out/2026-11-25             # 실제로 합친다
  옵션: --rescale ds,wiki,src   그 재료의 상한을 지금 자료로 다시 잡는다(기본은 기존 상한 유지)
        --allow-partial         끝까지 돌지 못한 단계의 자료도 쓴다(기본은 쓰지 않음)
        --date 2026-11-25       기록에 적을 날짜(기본은 폴더 이름)

하는 일
  1. wiki.jsonl → 위키 조회수 갱신.  ds.jsonl → 데일리샷 검색 결과 갱신(있을 때만)
  2. data/bottles.json: price·price_date·ds_rating·ds_reviews (ds 자료가 있을 때만)
  3. data/trends.json: 전 병 다시 계산(상한은 그대로)
  4. data/price_history.json: 이번에 잰 가격을 병마다 한 점씩 더한다
  5. data/changes.json: 직전 병합 때의 상태(tools/worker/state/last.json)와 비교해 변경 기록을 더한다
  6. 바꾸기 전 파일을 tools/worker/backup/<시각>/ 에 복사해 둔다
자동으로 반영하지 않고 "확인 필요"로 빼는 경우(가격): 직전보다 40% 넘게 바뀜, 상품이 검색 결과에서 사라짐,
  가격이 비어 있음, 상품명·용량이 달라짐, 기존 가격이 없던 병.
커밋·배포는 하지 않는다. 끝나면 build.py --check 를 돌려 확인한다.
"""
import json, os, shutil, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wlib                    # noqa: E402
from wlib import ROOT, DATA    # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "tools"))
import trend_collect as tc     # noqa: E402

CACHE_FILES = ("ds_cache.json", "wiki_cache.json", "naver_cache.json", "new_bottles.json")


def read_jsonl(path):
    if not os.path.exists(path) and os.path.exists(path + ".part"):
        path += ".part"             # 끝나지 않은 단계(--allow-partial일 때만 여기까지 온다)
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except ValueError:
                    continue            # 쓰다 끊긴 줄


def pid_of(url):
    import re
    m = re.search(r"/item/(\d+)", url or "")
    return int(m.group(1)) if m else None


def merge_wiki(raw_dir, cache, checks):
    n = changed = 0
    for r in read_jsonl(os.path.join(raw_dir, "wiki.jsonl")):
        n += 1
        old = cache.get(r["title"], {})
        if (r.get("no_data") or r.get("missing")) and old.get("views"):
            checks.append({"kind": "wiki", "key": r["title"], "why": "이번에는 문서 또는 조회 기록이 없다고 나옴. 기존 값 유지", "old": old.get("views")})
            continue
        new = {"resolved": r["resolved"], "missing": bool(r.get("missing")), "redirected": r["resolved"] != r["title"],
               "bytes": old.get("bytes"), "views": r.get("views", 0), "window": r["window"]}
        if old.get("views") != new["views"] or old.get("window") != new["window"]:
            changed += 1
        cache[r["title"]] = new
    return n, changed


def merge_ds(raw_dir, bottles, cache, extra, date, checks):
    """검색 결과 저장분을 바꾸고, 병별 가격·평점·리뷰 수의 새 값을 정한다. 돌려주는 값: (받은 병 수, {id: 바꿀 필드})."""
    by_id = {b["id"]: b for b in bottles}
    updates, n = {}, 0
    for r in read_jsonl(os.path.join(raw_dir, "ds.jsonl")):
        b = by_id.get(r["id"])
        if b is None:
            continue
        n += 1
        old = cache.get(b["id"])
        new_matched = tc.match(b, r["rows"], extra)[0]
        if old and tc.match(b, old.get("rows", []), extra)[0] and not new_matched:
            checks.append({"kind": "ds", "key": b["id"], "why": "지난번에는 있던 상품이 이번 검색 결과에 하나도 없음. 리뷰 수·가격 모두 기존 값 유지"})
            continue
        pid = pid_of(b.get("ds_url"))
        if pid and old and any(x["pid"] == pid for x in old.get("rows", [])) and not any(x["pid"] == pid for x in r["rows"]):
            checks.append({"kind": "price", "key": b["id"], "why": "가격 상품(번호 %d)이 검색 결과에서 사라짐. 리뷰 수·가격 모두 기존 값 유지" % pid,
                           "old": b.get("price"), "old_product": b.get("price_product"), "new": None, "new_product": None})
            continue
        cache[b["id"]] = {"queries": r["queries"], "rows": r["rows"], "truncated": r["truncated"], "date": date}
        up = {}
        # 평점·리뷰 수: 리뷰 수는 같은 병으로 합친 상품의 합(트렌드지수와 같은 값), 평점은 가격 상품(없으면 리뷰가 가장 많은 상품)의 값
        row = next((x for x in r["rows"] if x["pid"] == pid), None) if pid else None
        if pid:
            total = sum(m["reviews"] for m in new_matched)
            rated = row if row and row.get("rating") else max((m for m in new_matched if m.get("rating")), key=lambda m: m["reviews"], default=None)
            if total >= 5 and rated:
                up["ds_reviews"], up["ds_rating"] = total, round(float(rated["rating"]), 1)
            else:
                up["ds_reviews"], up["ds_rating"] = None, None
        # 가격: ds_url의 상품 번호와 같은 상품의 값만 쓴다
        if pid:
            why = None
            if row is None:
                why = "가격 상품(번호 %d)이 검색 결과에 없음" % pid
            elif not row.get("price"):
                why = "가격이 비어 있음(품절 등)"
            elif not b.get("price"):
                why = "기존 가격이 없던 병이라 자동으로 채우지 않음"
            elif b.get("price_product") and (tc.base(row["name"]) != tc.base(b["price_product"])
                                             or wlib.vol_ml(row["name"]) != wlib.vol_ml(b["price_product"])):
                why = "상품명 또는 용량이 달라짐"
            elif abs(row["price"] - b["price"]) / b["price"] > wlib.OUTLIER_PCT:
                why = "직전보다 %d%% 바뀜" % round(100 * (row["price"] - b["price"]) / b["price"])
            if why:
                checks.append({"kind": "price", "key": b["id"], "why": why, "old": b.get("price"), "old_product": b.get("price_product"),
                               "new": row.get("price") if row else None, "new_product": row["name"] if row else None})
            else:
                up["price"], up["price_date"] = row["price"], date
                if row["name"] != b.get("price_product"):
                    up["price_product"] = row["name"]
        if up:
            updates[b["id"]] = up
    return n, updates


def main():
    args = sys.argv[1:]
    pos = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in ("--rescale", "--date"))]
    if len(pos) != 1 or not os.path.isdir(pos[0]):
        print(__doc__)
        return 1
    raw_dir = os.path.abspath(pos[0])
    dry = "--dry-run" in args
    date = args[args.index("--date") + 1] if "--date" in args else os.path.basename(raw_dir.rstrip("/"))
    try:
        time.strptime(date, "%Y-%m-%d")
    except ValueError:
        print("날짜를 알 수 없음(%s). --date 2026-11-25 처럼 적을 것" % date)
        return 1
    rescale = args[args.index("--rescale") + 1].split(",") if "--rescale" in args else None
    summary = wlib.load(os.path.join(raw_dir, "summary.json"), {})
    stages = summary.get("stages", {})
    usable = {s for s, v in stages.items() if v.get("status") == "done" or "--allow-partial" in args}
    skipped = sorted(set(stages) - usable)
    if not os.path.exists(os.path.join(raw_dir, "DONE")) and "--allow-partial" not in args:
        print("주의: 이 폴더에는 완료 표시(DONE)가 없습니다. 끝난 단계의 자료만 씁니다.")

    bottles = wlib.load(os.path.join(DATA, "bottles.json"))
    old_bottles_text = wlib.bottles_text(bottles)
    if old_bottles_text != open(os.path.join(DATA, "bottles.json"), encoding="utf-8").read():
        print("data/bottles.json의 줄 형식이 예상과 달라 멈춥니다(다시 쓰면 형식이 바뀜).")
        return 1
    old_trends = wlib.load(os.path.join(DATA, "trends.json"))
    extra = tc.load(os.path.join(ROOT, "tools", "trend_aliases.json"), {})
    before = wlib.load(wlib.STATE)
    state_now = wlib.current_state(bottles, old_trends)       # 병합 전 상태(티어는 병합과 무관하므로 그대로 쓴다)
    if before is None:
        before = {"date": None, "bottles": state_now}
        print("직전 상태 기록(tools/worker/state/last.json)이 없어 지금 상태를 기준으로 삼습니다. 새 병·티어 변동은 다음 병합부터 잡힙니다.")

    # 저장된 수집 결과는 임시 폴더의 사본에서 고친다. --dry-run이면 원본은 건드리지 않는다.
    tmp = tempfile.mkdtemp(prefix="nidwolf-merge-")
    try:
        for f in CACHE_FILES:
            src = os.path.join(tc.WORK, f)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(tmp, f))
        checks = []
        wiki_cache = tc.load(os.path.join(tmp, "wiki_cache.json"), {})
        ds_cache = tc.load(os.path.join(tmp, "ds_cache.json"), {})
        wiki_n = wiki_changed = ds_n = 0
        updates = {}
        if "wiki" in usable:
            wiki_n, wiki_changed = merge_wiki(raw_dir, wiki_cache, checks)
            tc.save(os.path.join(tmp, "wiki_cache.json"), wiki_cache)
        if "ds" in usable:
            ds_n, updates = merge_ds(raw_dir, bottles, ds_cache, extra, date, checks)
            tc.save(os.path.join(tmp, "ds_cache.json"), ds_cache)
        field_changes = []
        for b in bottles:
            for k, v in updates.get(b["id"], {}).items():
                if b.get(k) != v:
                    if k != "price_date":
                        field_changes.append((b["id"], k, b.get(k), v))
                    b[k] = v
        new_bottles_text = wlib.bottles_text(bottles)

        # 트렌드지수: 전 병 다시 계산. 상한은 기존 값을 쓴다(--rescale로 지정한 재료만 다시 잡는다)
        tmp_trends = os.path.join(tmp, "trends.json")
        shutil.copy2(os.path.join(DATA, "trends.json"), tmp_trends)
        real_work, tc.WORK = tc.WORK, tmp
        try:
            ok = tc.stage_score(bottles, {"refresh": False, "only": None, "keep_scales": True, "freeze": False, "rescale": rescale,
                                          "recompute": None, "out_path": tmp_trends, "no_reports": dry})
        finally:
            if dry:
                tc.WORK = real_work
        if not ok:
            print("트렌드지수 계산을 끝내지 못해 멈춥니다.")
            return 1
        new_trends = wlib.load(tmp_trends)
        if "ds" not in usable:          # 데일리샷을 다시 재지 않았으면 파일 머리의 측정일은 그대로 둔다(위키만 갱신)
            new_trends["measured"] = old_trends.get("measured")
        new_trends_text = open(tmp_trends, encoding="utf-8").read().replace(
            ' "measured": %s,' % json.dumps(time.strftime("%Y-%m-%d")), ' "measured": %s,' % json.dumps(new_trends["measured"]), 1)
        ot, nt = old_trends["bottles"], new_trends["bottles"]
        trend_moves = sorted(((i, ot[i]["index"], nt[i]["index"]) for i in nt if i in ot and ot[i]["index"] != nt[i]["index"]),
                             key=lambda x: -abs(x[2] - x[1]))
        raw_moves = sum(1 for i in nt if i in ot and ot[i]["raw"] != nt[i]["raw"])
        raw_by_key = {}
        for i in nt:
            if i in ot:
                for k in nt[i]["raw"]:
                    if ot[i]["raw"].get(k) != nt[i]["raw"][k]:
                        raw_by_key.setdefault(k, []).append(i)
        flag_moves = [(i, ot[i]["flags"], nt[i]["flags"]) for i in nt if i in ot and ot[i]["flags"] != nt[i]["flags"]]

        # 가격 이력: 이번에 가격을 반영한 병마다 한 점
        hist = wlib.load(wlib.HISTORY, {})
        points = 0
        for b in bottles:
            if "price" in updates.get(b["id"], {}):
                wlib.add_point(hist, b["id"], date, b["price"])
                points += 1

        # 변경 기록: 직전 병합 때의 상태와 비교
        after = {b["id"]: {"tier": state_now[b["id"]]["tier"], "price": b.get("price"),
                           "trend": nt.get(b["id"], {}).get("index"), "ko": b["ko"]} for b in bottles}
        new_records = wlib.diff_states(before["bottles"], after, date)
        changes = wlib.merge_changes(wlib.load(wlib.CHANGES, []), new_records, date)

        # ---- 요약
        by_type = {}
        for c in new_records:
            by_type.setdefault(c["type"], []).append(c)
        print("\n== 병합 %s: %s (기록 날짜 %s) ==" % ("미리 보기(아무것도 쓰지 않음)" if dry else "실행", raw_dir, date))
        print("수집 상태: %s / 쓴 단계 %s%s" % (summary.get("status"), sorted(usable) or "없음",
                                           (" / 끝나지 않아 쓰지 않은 단계 %s" % skipped) if skipped else ""))
        print("위키: 받은 문서 %d, 값이 바뀐 문서 %d" % (wiki_n, wiki_changed))
        print("데일리샷: 받은 병 %d, bottles.json에서 바뀌는 값 %d건(가격 %d, 리뷰 수 %d, 평점 %d, 상품명 %d)" % (
            ds_n, len(field_changes), *(sum(1 for f in field_changes if f[1] == k) for k in ("price", "ds_reviews", "ds_rating", "price_product"))))
        print("트렌드지수: 지수가 바뀌는 병 %d, 원자료가 바뀌는 병 %d, 상한 %s" % (len(trend_moves), raw_moves, json.dumps(new_trends["scales"])))
        print("   원자료 항목별 바뀌는 병 수: %s / 점검 표시가 바뀌는 병 %d%s" % (
            ", ".join("%s %d" % (k, len(v)) for k, v in sorted(raw_by_key.items())) or "없음", len(flag_moves),
            (" (%s)" % ", ".join(f[0] for f in flag_moves[:8])) if flag_moves else ""))
        for i, a, b_ in trend_moves[:15]:
            print("   %s %d → %d" % (i, a, b_))
        if len(trend_moves) > 15:
            print("   … 외 %d병" % (len(trend_moves) - 15))
        print("가격 이력: 더해지는 점 %d개" % points)
        print("변경 기록: 새로 %d건 (%s), 보관 %d건" % (len(new_records), ", ".join("%s %d" % (t, len(v)) for t, v in sorted(by_type.items())) or "없음", len(changes)))
        for c in new_records[:20]:
            print("   %s %s %s → %s" % (c["type"], c["id"], c["from"], c["to"]))
        print("확인 필요(자동 반영하지 않음): %d건" % len(checks))
        for c in checks[:30]:
            print("   [%s] %s: %s%s" % (c["kind"], c["key"], c["why"], (" (%s → %s)" % (c.get("old"), c.get("new"))) if c["kind"] == "price" else ""))
        report = {"date": date, "dry_run": dry, "stages_used": sorted(usable), "stages_skipped": skipped,
                  "wiki": {"received": wiki_n, "changed": wiki_changed}, "ds": {"received": ds_n},
                  "bottle_field_changes": field_changes, "trend_moves": trend_moves, "trend_raw_changes": raw_by_key, "trend_flag_changes": flag_moves, "price_points": points,
                  "new_records": new_records, "needs_check": checks}
        tc.save(os.path.join(raw_dir, "merge_preview.json" if dry else "merge_result.json"), report, indent=1)
        if dry:
            print("\n자세한 목록: %s" % os.path.join(raw_dir, "merge_preview.json"))
            return 0

        # ---- 실제 반영: 먼저 백업, 그다음 쓰기
        tc.WORK = real_work
        bdir = os.path.join(HERE, "backup", time.strftime("%Y%m%d-%H%M%S"))
        os.makedirs(bdir)
        targets = [os.path.join(DATA, "bottles.json"), os.path.join(DATA, "trends.json"), wlib.HISTORY, wlib.CHANGES, wlib.STATE,
                   os.path.join(tc.WORK, "ds_cache.json"), os.path.join(tc.WORK, "wiki_cache.json")]
        for p in targets:
            if os.path.exists(p):
                shutil.copy2(p, os.path.join(bdir, os.path.relpath(p, ROOT).replace(os.sep, "__")))
        if new_bottles_text != old_bottles_text:
            wlib.write_text(os.path.join(DATA, "bottles.json"), new_bottles_text)
        wlib.write_text(os.path.join(DATA, "trends.json"), new_trends_text)
        for f in ("ds_cache.json", "wiki_cache.json"):
            shutil.copy2(os.path.join(tmp, f), os.path.join(tc.WORK, f))
        wlib.write_text(wlib.HISTORY, wlib.history_text(hist, [b["id"] for b in bottles]))
        wlib.write_text(wlib.CHANGES, wlib.changes_text(changes))
        wlib.write_text(wlib.STATE, json.dumps({"date": date, "bottles": after}, ensure_ascii=False, indent=0))
        print("\n반영했습니다. 바꾸기 전 파일: %s" % bdir)
        print("다음: python3 -B tools/build.py --check  →  확인 뒤 빌드·커밋(사람이 결정)")
        return 0
    finally:
        tc.WORK = real_work if "real_work" in locals() else tc.WORK
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
