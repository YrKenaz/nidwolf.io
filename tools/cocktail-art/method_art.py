#!/usr/bin/env python3
"""티어표 하단 '점수 산출 방식' 옆 도해 (표준 라이브러리만).

  python3 -B tools/cocktail-art/method_art.py
    → art/site/score.svg, tier.svg, trend.svg (+ tools/cocktail-art/method-*.html 미리보기)

문구·숫자는 tools/template.html 본문과 CLAUDE.md에 적힌 것만 쓴다.
트렌드지수 재료 비중은 data/trends.json의 weights를 읽는다(재측정으로 바뀌면 다시 실행).
"""
import html
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "art", "site")
AMBER = "#c9822b"
TIER = [("S", 5, "#5a1a12", "#fff7ea"), ("A", 15, "#8a3414", "#fff7ea"), ("B", 25, "#b85c16", "#fff7ea"),
        ("C", 25, "#d98a1f", "#231603"), ("D", 20, "#e9b949", "#231603"), ("E", 10, "#f0dc8c", "#231603")]


def f(v):
    s = f"{v:.1f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def esc(s):
    return html.escape(s, quote=True)


STYLE = (".mth-ID{color:var(--ink,#14201a);font-family:inherit;--mth-ac:var(--accent,#1e5a43);--mth-ai:var(--accent-ink,#fff)}"
         "@media(prefers-color-scheme:dark){.mth-ID{color:var(--ink,#e8eee9);--mth-ac:var(--accent,#74c7a3);--mth-ai:var(--accent-ink,#0f1613)}}"
         ".mth-ID .mth-o{stroke:currentColor;stroke-width:2.2;stroke-linejoin:round;stroke-linecap:round}"
         ".mth-ID .mth-l{fill:none;stroke:currentColor;stroke-width:1.6;stroke-linecap:round}"
         ".mth-ID .mth-a{fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}"
         ".mth-ID .mth-ac{stroke:var(--mth-ac);stroke-width:2.4}"
         ".mth-ID .mth-acf{fill:var(--mth-ac)}"
         ".mth-ID .mth-dd{stroke-dasharray:4 4}"
         ".mth-ID .mth-mu{stroke:var(--muted,#7a8a80)}"
         ".mth-ID .mth-card{fill:var(--surface,#f8faf6);stroke:currentColor;stroke-opacity:.45;stroke-width:1.3}"
         ".mth-ID .mth-nb{fill:currentColor;fill-opacity:.06;stroke:currentColor;stroke-opacity:.35;stroke-width:1.2}"
         ".mth-ID text{fill:currentColor;font-size:14.5px}"
         ".mth-ID .mth-m{fill:var(--muted,#7a8a80)}"
         ".mth-ID .mth-b{font-weight:700}"
         ".mth-ID .mth-s{font-size:13.5px}"
         ".mth-ID .mth-big{font-size:22px;font-weight:900}")


class Pic:
    def __init__(self, cid):
        self.cid, self.uid, self.o = cid, f"mth-{cid}", []

    def add(self, s):
        self.o.append(s)

    def text(self, x, y, s, cls="", anchor="start", style=""):
        c = f' class="{cls}"' if cls else ""
        a = "" if anchor == "start" else f' text-anchor="{anchor}"'
        st = f' style="{style}"' if style else ""
        self.add(f'<text{c} x="{f(x)}" y="{f(y)}"{a}{st}>{esc(s)}</text>')

    def arrow(self, d, accent=False, dashed=False, muted=False):
        cls = "mth-a" + (" mth-ac" if accent else "") + (" mth-dd" if dashed else "") + (" mth-mu" if muted else "")
        m = f"{self.uid}-{'hc' if accent else ('hm' if muted else 'h')}"
        self.add(f'<path class="{cls}" d="{d}" marker-end="url(#{m})"/>')

    def svg(self, w, h, title, desc):
        mk = lambda n, fill: (f'<marker id="{self.uid}-{n}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" '
                              f'orient="auto-start-reverse"><path d="M0,0L10,5L0,10z" {fill}/></marker>')
        defs = "<defs>" + mk("h", 'fill="currentColor"') + mk("hc", 'class="mth-acf"') + mk("hm", 'style="fill:var(--muted,#7a8a80)"') + "</defs>"
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" class="mth mth-{self.cid}" role="img" '
                f'aria-labelledby="{self.uid}-t {self.uid}-d"><title id="{self.uid}-t">{esc(title)}</title>'
                f'<desc id="{self.uid}-d">{esc(desc)}</desc><style>{STYLE.replace("ID", self.cid)}</style>{defs}{"".join(self.o)}</svg>\n')


# ---------------------------------------------------------------- 아이콘 (원점 = 아이콘 중심, 약 20×20)
def ic_sheet_star():
    return ('<rect class="mth-o" style="fill:#fbf6ea;stroke-width:1.6" x="-8" y="-10" width="16" height="20" rx="2"/>'
            '<path d="M0,-6l1.8,3.6 4,.6-2.9,2.8.7,4L0,3.1-3.6,5l.7-4-2.9-2.8 4-.6z" fill="#e0a526" stroke="currentColor" stroke-width=".8"/>')


def ic_meta():
    return ('<rect class="mth-o" style="fill:#fbf6ea;stroke-width:1.6" x="-9" y="-10" width="18" height="20" rx="2"/>'
            '<path d="M-5,6V1M-1,6V-4M3,6V-1" stroke="#c9822b" stroke-width="3" stroke-linecap="round"/>')


def ic_rank():
    out = ['<rect class="mth-o" style="fill:#fbf6ea;stroke-width:1.6" x="-8" y="-10" width="16" height="20" rx="2"/>']
    for i, y in enumerate((-5, 0, 5)):
        out.append(f'<text x="-4.5" y="{y + 2.5}" text-anchor="middle" style="font-size:6.5px;font-weight:700;fill:#2a1806">{i + 1}</text>'
                   f'<path d="M-1,{y}H5" stroke="#2a1806" stroke-width="1.4" stroke-linecap="round"/>')
    return "".join(out)


def ic_bullets():
    out = ['<rect class="mth-o" style="fill:#fbf6ea;stroke-width:1.6" x="-8" y="-10" width="16" height="20" rx="2"/>']
    for y in (-5, 0, 5):
        out.append(f'<circle cx="-4" cy="{y}" r="1.4" fill="#2a1806"/><path d="M-1,{y}H5" stroke="#2a1806" stroke-width="1.4" stroke-linecap="round"/>')
    return "".join(out)


def ic_bubble():
    return ('<path class="mth-o" style="fill:#fbf6ea;stroke-width:1.6" d="M-9,-8H9Q11,-8 11,-6V4Q11,6 9,6H-2L-7,10V6H-9Q-11,6 -11,4V-6Q-11,-8 -9,-8Z"/>'
            '<path d="M-6,-3H6M-6,1H3" stroke="#2a1806" stroke-width="1.4" stroke-linecap="round"/>')


def ic_book():
    return ('<path class="mth-o" style="fill:#fbf6ea;stroke-width:1.6" d="M0,-7Q-5,-10 -10,-8V8Q-5,6 0,9Q5,6 10,8V-8Q5,-10 0,-7ZM0,-7V9"/>'
            '<path d="M-7,-3H-3M-7,1H-3M3,-3H7M3,1H7" stroke="#2a1806" stroke-width="1.2" stroke-linecap="round"/>')


def ic_news():
    return ('<rect class="mth-o" style="fill:#fbf6ea;stroke-width:1.6" x="-10" y="-9" width="20" height="18" rx="2"/>'
            '<rect x="-7" y="-6" width="6" height="5" fill="#c9822b"/>'
            '<path d="M1,-5H7M1,-2H7M-7,2H7M-7,5H7" stroke="#2a1806" stroke-width="1.2" stroke-linecap="round"/>')


def ic_clock():
    return ('<circle class="mth-o" style="fill:#fbf6ea;stroke-width:1.6" r="9"/>'
            '<path d="M0,-5V0L4,2" stroke="#2a1806" stroke-width="1.6" stroke-linecap="round" fill="none"/>')


def put(p, fn, x, y, s=1.0):
    t = f"translate({f(x)} {f(y)})" + (f" scale({s})" if s != 1 else "")
    p.add(f'<g transform="{t}">{fn()}</g>')


# ---------------------------------------------------------------- 그림 1: 점수 산출
def fig_score():
    p = Pic("score")
    p.text(68, 14, "출처", "mth-b mth-s", "middle")
    rows = [(ic_sheet_star, "점수표·평점", "그대로"), (ic_meta, "메타 평점", "선형 변환"), (ic_rank, "순위 리스트", "고르게 폄")]
    for j, (ic, name, how) in enumerate(rows):
        y = 36 + j * 32
        p.add(f'<rect class="mth-card" x="4" y="{y - 13}" width="128" height="26" rx="8"/>')
        put(p, ic, 21, y)
        p.text(38, y + 5, name)
        p.text(196, y - 5, how, "mth-s mth-m", "middle")
        p.arrow(f"M136,{y}H256")
    # 100점 척도
    p.add('<rect class="mth-o" style="fill:#fbf6ea" x="262" y="22" width="20" height="92" rx="5"/>')
    p.add(f'<rect x="263.2" y="31" width="17.6" height="81.8" rx="4" style="fill:{AMBER};fill-opacity:.7"/>')
    for k in range(6):
        p.add(f'<path class="mth-l" style="stroke-width:1.2" d="M282,{f(26 + k * 17.2)}h5"/>')
    p.text(272, 14, "100점 척도", "mth-b mth-s", "middle")
    # 추천 목록: 점수에 넣지 않음
    y = 136
    p.add(f'<rect class="mth-card" x="4" y="{y - 13}" width="128" height="26" rx="8" style="stroke-dasharray:4 3"/>')
    put(p, ic_bullets, 21, y)
    p.text(38, y + 5, "추천 목록")
    p.arrow(f"M136,{y}H152", muted=True, dashed=True)
    p.text(158, y - 2, "매체 추천 N회", "mth-s")
    p.text(158, y + 15, "점수에 넣지 않음", "mth-s mth-m")
    # 같은 매체는 한 표
    for dx in (0, 8):
        p.add(f'<rect class="mth-card" x="{300 + dx}" y="{26 + dx}" width="40" height="30" rx="5"/>')
        put(p, ic_rank, 320 + dx, 41 + dx, .8)
    p.add('<path class="mth-l" d="M352,30q8,0 8,8v14q0,8 6,8q-6,0 -6,8"/>')
    p.add(f'<circle class="mth-o" style="fill:{AMBER}" cx="380" cy="60" r="11"/>')
    p.text(380, 65, "1", "mth-b", "middle", "fill:#2a1806")
    p.text(348, 92, "같은 매체는", "mth-s", "middle")
    p.text(348, 109, "한 표", "mth-b mth-s", "middle")
    # 식
    p.arrow("M272,118V150")
    p.arrow("M348,116V150")
    p.add('<rect class="mth-nb" x="4" y="154" width="392" height="54" rx="10"/>')
    p.text(14, 186, "종합 점수 =", "mth-b")
    p.text(252, 175, "매체 그룹별 점수의 합 + 종류별 사전 평균", "mth-s", "middle")
    p.add('<path class="mth-l" style="stroke-width:1.8" d="M110,181H394"/>')
    p.text(252, 199, "독립 출처 수 + 1", "mth-s", "middle")
    desc = ("출처 형식별로 100점 척도로 맞춘다: 점수표·평점은 그대로, 메타 평점은 선형 변환, 순위 리스트는 고르게 폄. "
            "추천 목록은 점수에 넣지 않고 매체 추천 N회로만 표시. 같은 매체의 여러 리스트는 한 표로 묶는다. "
            "종합 점수 = (매체 그룹별 점수의 합 + 종류별 사전 평균) ÷ (독립 출처 수 + 1).")
    return p.svg(400, 210, "점수 산출 방식: 출처를 100점 척도로 맞추고, 같은 매체는 한 표로 묶어 종류별 사전 평균과 함께 나눈다.", desc)


# ---------------------------------------------------------------- 그림 2: 티어 비율·옛 병·확신도
def fig_tier():
    p = Pic("tier")
    p.text(4, 16, "점수 상위부터", "mth-b mth-s")
    p.arrow("M100,11H130")
    x, W0 = 4.0, 392
    for t, pct, bg, fg in TIER:
        w = W0 * pct / 100
        p.add(f'<rect x="{f(x)}" y="22" width="{f(w)}" height="24" style="fill:{bg}"/>')
        p.text(x + w / 2, 39, t, "mth-b", "middle", f"fill:{fg}")
        p.text(x + w / 2, 62, f"{pct}%", "mth-s", "middle")
        x += w
    p.add('<rect x="4" y="22" width="392" height="24" rx="4" style="fill:none;stroke:currentColor;stroke-width:1.6"/>')
    # 옛 병
    put(p, ic_clock, 14, 82)
    p.text(30, 87, "옛 병", "mth-b mth-s")
    p.text(70, 87, "경계 계산에서 빼고, 자기 점수로 티어만 정함", "mth-s mth-m")
    # 확신도
    p.add('<path class="mth-l" style="stroke-opacity:.25;stroke-dasharray:3 4" d="M4,98H396"/>')
    p.text(4, 116, "확신도", "mth-b mth-s")
    bx = 316
    p.add(f'<path class="mth-l" style="stroke-dasharray:3 3" d="M{bx},122V188"/>')
    p.text(bx - 6, 116, "티어 경계", "mth-s mth-m", "end")
    rows = [("잠정", "독립 출처 1곳", 280, None), ("경계", "점수 ± 표준오차가 경계를 넘음", 300, 30), ("확정", "경계 안", 270, 18)]
    for j, (name, d, cx, err) in enumerate(rows):
        y = 136 + j * 22
        p.text(4, y + 5, name, "mth-b")
        p.text(44, y + 5, d, "mth-s")
        p.add(f'<path class="mth-l" style="stroke-opacity:.3" d="M250,{y}H392"/>')
        if err:
            p.add(f'<path class="mth-l" style="stroke-width:2.4;stroke:{AMBER}" d="M{cx - err},{y}H{cx + err}M{cx - err},{y - 5}v10M{cx + err},{y - 5}v10"/>')
            p.add(f'<circle class="mth-o" style="fill:{AMBER};stroke-width:1.6" cx="{cx}" cy="{y}" r="5"/>')
        else:
            p.add(f'<circle class="mth-o" style="fill:var(--surface,#f8faf6);stroke-width:1.6;stroke-dasharray:2 2" cx="{cx}" cy="{y}" r="5"/>')
    desc = ("티어는 점수 상위부터 S 5%, A 15%, B 25%, C 25%, D 20%, E 10% 비율로 나눈다. "
            "옛 병은 경계 계산에서 빼고, 자기 점수로 티어만 정한다. "
            "확신도: 독립 출처 1곳이면 잠정, 점수 ± 표준오차가 티어 경계를 넘으면 경계, 경계 안이면 확정.")
    return p.svg(400, 192, "티어 비율과 확신도: 점수 상위부터 5·15·25·25·20·10%로 나누고, 출처 수와 오차 범위로 잠정·경계·확정을 표시한다.", desc)


# ---------------------------------------------------------------- 그림 3: 트렌드지수
def fig_trend():
    tr = json.load(open(os.path.join(ROOT, "data", "trends.json"), encoding="utf-8"))
    wt = tr["weights"]
    dom = set(tr.get("domestic_parts") or [])
    names = {"ds": "데일리샷 리뷰 수", "wiki": "위키백과 조회수", "src": "해외 출처 등장 횟수", "naver": "네이버 검색 결과 수"}
    icons = {"ds": ic_bubble, "wiki": ic_book, "src": ic_news, "naver": ic_bubble}
    shades = ["#c9822b", "#e0a95a", "#efcd8f", "#f5e2b8"]
    keys = list(wt.keys())
    total = sum(wt.values())
    p = Pic("trend")
    p.text(4, 16, "재료와 비중", "mth-b mth-s")
    p.text(396, 16, f"합 {total}", "mth-s mth-m", "end")
    for j, k in enumerate(keys):
        y = 40 + j * 32
        p.add(f'<rect class="mth-card" x="4" y="{y - 14}" width="392" height="28" rx="8"/>')
        put(p, icons.get(k, ic_news), 22, y)
        p.add(f'<rect x="40" y="{y - 6}" width="12" height="12" rx="3" style="fill:{shades[j % 4]};stroke:currentColor;stroke-width:1"/>')
        p.text(60, y + 5, names.get(k, k))
        p.text(386, y + 6, str(wt[k]), "mth-b", "end", "font-size:16px")
    # 비중 막대
    by = 40 + len(keys) * 32 + 2
    x = 4.0
    seg = {}
    for j, k in enumerate(keys):
        w = 392 * wt[k] / total
        p.add(f'<rect x="{f(x)}" y="{by}" width="{f(w)}" height="22" style="fill:{shades[j % 4]}"/>')
        if w > 22:
            p.text(x + w / 2, by + 16, str(wt[k]), "mth-b mth-s", "middle", "fill:#2a1806")
        seg[k] = (x, x + w)
        x += w
    p.add(f'<rect x="4" y="{by}" width="392" height="22" rx="4" style="fill:none;stroke:currentColor;stroke-width:1.6"/>')
    # 국내·해외 묶음
    def brace(x0, x1, label):
        y = by + 28
        p.add(f'<path class="mth-l" d="M{f(x0 + 2)},{y}v5H{f(x1 - 2)}v-5"/>')
        p.text((x0 + x1) / 2, y + 22, label, "mth-s", "middle")
    dk = [k for k in keys if k in dom]
    ok = [k for k in keys if k not in dom]
    if dk:
        brace(seg[dk[0]][0], seg[dk[-1]][1], "국내 점수")
    if ok:
        brace(seg[ok[0]][0], seg[ok[-1]][1], "해외 점수")
    # 가중 평균 → 게이지
    gy0 = by + 64
    p.arrow(f"M130,{gy0}V{gy0 + 20}")
    p.text(140, gy0 + 15, "재료별 부분 점수(0~100)의 가중 평균", "mth-s mth-m")
    cx, cy, r = 130, gy0 + 104, 70
    import math
    def pt(a, rr):
        t = math.pi * (1 - a / 100)
        return cx + rr * math.cos(t), cy - rr * math.sin(t)
    x0, y0 = pt(0, r)
    x1, y1 = pt(100, r)
    p.add(f'<path d="M{f(x0)},{f(y0)}A{r},{r} 0 0 1 {f(x1)},{f(y1)}" style="fill:none;stroke:currentColor;stroke-opacity:.15;stroke-width:16"/>')
    xa, ya = pt(62, r)
    p.add(f'<path d="M{f(x0)},{f(y0)}A{r},{r} 0 0 1 {f(xa)},{f(ya)}" style="fill:none;stroke:{AMBER};stroke-width:16"/>')
    for a in range(0, 101, 25):
        u, v = pt(a, r + 10)
        w2, z = pt(a, r + 15)
        p.add(f'<path class="mth-l" d="M{f(u)},{f(v)}L{f(w2)},{f(z)}"/>')
    nx, ny = pt(62, r - 18)
    p.add(f'<path class="mth-o" style="fill:none;stroke-width:3" d="M{cx},{cy}L{f(nx)},{f(ny)}"/><circle class="mth-o" style="fill:var(--surface,#f8faf6)" cx="{cx}" cy="{cy}" r="5"/>')
    p.text(x0, cy + 18, "0", "mth-s mth-m", "middle")
    p.text(x1, cy + 18, "100", "mth-s mth-m", "middle")
    p.text(cx, cy + 22, "트렌드지수", "mth-b", "middle")
    p.text(cx, cy + 40, "누적 인지도", "mth-s mth-m", "middle")
    # 티어와 별개
    tx, ty = 262, gy0 + 52
    p.add(f'<rect class="mth-nb" x="{tx - 8}" y="{ty - 22}" width="144" height="120" rx="10" style="stroke-dasharray:4 3"/>')
    mx = tx + 8
    for t, pct, bg, fg in TIER:
        p.add(f'<rect x="{mx}" y="{ty - 8}" width="18" height="18" rx="3" style="fill:{bg}"/>')
        p.text(mx + 9, ty + 6, t, "mth-b", "middle", f"fill:{fg};font-size:12px")
        mx += 20
    p.add(f'<path class="mth-a mth-mu mth-dd" d="M{cx + 50},{cy - 50}Q{tx - 30},{ty + 10} {tx - 12},{ty + 26}"/>')
    ex, ey = tx - 20, ty + 4
    p.add(f'<g transform="translate({ex} {ey + 14})"><circle r="9" style="fill:var(--surface,#f8faf6);stroke:#b3261e;stroke-width:2"/>'
          f'<path d="M-4,-4L4,4M4,-4L-4,4" stroke="#b3261e" stroke-width="2.4" stroke-linecap="round"/></g>')
    p.text(tx + 64, ty + 36, "티어·종합 점수·", "mth-s", "middle")
    p.text(tx + 64, ty + 54, "확신도 계산에는", "mth-s", "middle")
    p.text(tx + 64, ty + 72, "넣지 않음", "mth-b mth-s", "middle")
    H = cy + 50
    parts = ", ".join(f"{names.get(k, k)} {wt[k]}" for k in keys)
    desc = (f"트렌드지수 재료와 비중(합 {total}): {parts}. "
            + (f"{', '.join(names[k] for k in dk)}는 국내 점수, 나머지는 해외 점수. " if dk else "")
            + "재료별 부분 점수(0~100)의 가중 평균이 0~100 트렌드지수(누적 인지도)가 된다. 티어·종합 점수·확신도 계산에는 넣지 않는다. "
            "게이지 바늘 위치는 예시다.")
    return p.svg(400, int(H), "트렌드지수: 세 재료를 비중대로 가중 평균한 0~100 누적 인지도이며, 티어 점수와는 별개다.", desc)


FIGS = [("score", fig_score), ("tier", fig_tier), ("trend", fig_trend)]
TOKENS = """:root{--bg:#eef1ec;--surface:#f8faf6;--ink:#14201a;--muted:#56675d;--line:#d2d9d1;--accent:#1e5a43;--accent-ink:#fff}
:root[data-theme=dark]{--bg:#0f1613;--surface:#17211c;--ink:#e8eee9;--muted:#95a59b;--line:#2b3931;--accent:#74c7a3;--accent-ink:#0f1613;color-scheme:dark}
body{margin:0;padding:16px;background:var(--bg);color:var(--ink);font-family:"Noto Sans KR","Malgun Gothic",system-ui,sans-serif;font-size:15px;line-height:1.55}
.m{display:grid;grid-template-columns:minmax(0,68ch) 400px;gap:14px 40px;max-width:1148px}.m p{margin:0}.m svg{width:100%;display:block}
.fig{grid-column:2;display:flex;flex-direction:column;gap:14px}
@media(max-width:900px){.m{grid-template-columns:1fr}.fig{grid-column:1}}"""


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def main():
    out = {}
    for cid, fn in FIGS:
        svg = fn()
        write(os.path.join(OUT, f"{cid}.svg"), svg)
        out[cid] = svg
        print(f"  {cid}.svg  {len(svg.encode()) / 1024:5.1f} KB")
    # 미리보기: 실제 본문 길이와 비슷한 자리 표시 글
    lorem = "출처마다 형식이 달라서 먼저 100점 척도로 맞춥니다. " * 6
    for theme in ("dark", "light"):
        body = (f'<div class="m"><div><h2>점수 산출 방식</h2><p>{lorem}</p><p>{lorem}</p><p>{lorem}</p></div>'
                f'<div class="fig" style="grid-row:1">{out["score"]}{out["tier"]}</div>'
                f'<div><h3>트렌드지수</h3><p>{lorem}</p><p>{lorem}</p><p>{lorem}</p></div><div class="fig">{out["trend"]}</div></div>')
        write(os.path.join(ROOT, "tools", "cocktail-art", f"method-{theme}.html"),
              f'<!doctype html><html lang="ko" data-theme="{theme}"><meta charset="utf-8"><style>{TOKENS}</style><body>{body}</body></html>')
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
