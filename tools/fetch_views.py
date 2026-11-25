#!/usr/bin/env python3
"""많이 본 병(S7) 집계 내려받기: https://nidwolf.com/api/top → data/views.json

    python3 tools/fetch_views.py            # 받아서 저장
    python3 tools/fetch_views.py --dry-run  # 받아서 요약만 출력(저장 안 함)
    python3 tools/fetch_views.py --url http://localhost:8788/api/top   # 다른 주소(로컬 시험)

표준 라이브러리만 쓴다. 받기·형식 검사에 실패하면 기존 data/views.json 을 그대로 두고 종료 코드 1.
집계가 비어 있으면({"week": null, "top": []}, D1 연결 전 등) 기존 파일을 덮어쓰지 않는다.
이 값은 '많이 본 병' 순위에만 쓰며 티어·종합 점수·트렌드지수 계산에 넣지 않는다.
"""
import json, os, re, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "views.json")
URL = "https://nidwolf.com/api/top"
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

def valid(v):
    if not isinstance(v, dict) or not isinstance(v.get("top"), list): return "최상위가 {week, top} 객체가 아님"
    if v.get("week") is not None and not (isinstance(v["week"], str) and DATE.match(v["week"])): return f"week 형식 오류 {v.get('week')!r}"
    for x in v["top"]:
        if not (isinstance(x, list) and len(x) == 2 and isinstance(x[0], str) and isinstance(x[1], int) and not isinstance(x[1], bool) and x[1] >= 0):
            return f"top 항목 형식 오류 {x!r}"
    return None

def main():
    a = sys.argv[1:]
    url = a[a.index("--url") + 1] if "--url" in a else URL
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "nidwolf-build/1 (+fetch_views.py)", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            if r.status != 200: raise RuntimeError(f"HTTP {r.status}")
            v = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"오류: {url} 받기 실패({e.__class__.__name__}: {e}) — 기존 views.json 유지"); return 1
    err = valid(v)
    if err: print(f"오류: 응답 {err} — 기존 views.json 유지"); return 1
    print(f"받음: week {v.get('week')} ~ {v.get('to')} · {len(v['top'])}병" + (f" · 1위 {v['top'][0][1]}회" if v["top"] else ""))
    if not v.get("week"): print("집계 없음(D1 미연결 또는 기록 없음) — 기존 views.json 유지"); return 0
    if "--dry-run" in a: return 0
    out = {"week": v["week"], "to": v.get("to"), "top": v["top"]}
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(out, f, ensure_ascii=False, separators=(",", ":")); f.write("\n")
    os.replace(tmp, OUT)   # 다 쓴 뒤에 바꿔 끼워 중간에 실패해도 기존 파일이 깨지지 않게
    print("저장:", os.path.relpath(OUT, ROOT)); return 0

if __name__ == "__main__":
    sys.exit(main())
