#!/usr/bin/env python3
"""칵테일 잔 그림(SVG) 생성기.

data/cocktails.json(또는 --data로 준 파일)을 읽어 칵테일마다
  art/cocktails/<id>.svg    상세용(층·지시선·순서 번호·라벨)
  art/cocktails/<id>-s.svg  목록 카드용(잔과 층만)
을 만든다. 표준 라이브러리만 쓰며 같은 입력이면 같은 파일이 나온다.

층 규칙
- ingredients 순서대로 아래에서 위로 쌓는다. ml가 있는 재료만 층이 된다.
- 층 경계는 높이가 아니라 부피로 정한다. 잔 안쪽을 회전체로 보고
  V(h) = ∫ π r(y)² dy (선형 구간은 원뿔대 공식)를 계산해 각 층 부피가 ml에 비례하도록 h를 역산한다.
- ml가 null인 재료(비터스·각설탕·달걀흰자 등)는 층 대신 라벨 줄의 점선 칩으로 보인다.

실행
  python3 -B tools/cocktail_art.py                         # data/cocktails.json → art/cocktails/
  python3 -B tools/cocktail_art.py --data tools/cocktail-art/sample.json
  python3 -B tools/cocktail_art.py --sheet                 # 잔 8종 시험 그림 + 미리보기 HTML(tools/cocktail-art/)
  python3 -B tools/cocktail_art.py --verify                # 부피 계산 검증 수치 출력
"""
import argparse
import html
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 340, 300          # 상세 그림 viewBox
BASE_Y = 268             # 잔 바닥(받침 아래 끝) y
CX = 80                  # 잔 중심 x
LX = 160                 # 라벨 열 시작 x
SMALL_BOX = (0, 34, 160, 240)  # 목록용 viewBox (x, y, w, h)

GLASS_KO = {"rocks": "록스 잔", "highball": "하이볼 잔", "coupe": "쿠페 잔", "martini": "마티니 잔",
            "mug": "머그", "julep": "줄렙 컵", "wine": "와인 잔", "shot": "샷 잔"}
ICE_KO = {"none": "얼음 없음", "cube": "각얼음", "large": "큰 얼음", "crushed": "잘게 부순 얼음"}
# 잔의 실질 용량(ml, 얼음 포함 기준)과 얼음이 차지하는 비율 — 액면 높이(채움 정도)를 정하는 데만 쓴다
NOMINAL = {"rocks": 300, "highball": 350, "coupe": 160, "martini": 170, "mug": 300,
           "julep": 350, "wine": 400, "shot": 60}
ICE_SHARE = {"none": 0, "cube": .4, "large": .3, "crushed": .5}
DILUTION = {"shake": 1.25, "stir": 1.2, "build": 1.0, "hot": 1.0}


def f(v):
    s = f"{v:.1f}"
    s = s.rstrip("0").rstrip(".") if "." in s else s
    return "0" if s in ("-0", "") else s


def pts(seq):
    return " ".join(f"{f(x)},{f(y)}" for x, y in seq)


# ---------------------------------------------------------------- 잔 모양
def ellipse_knots(depth, radius, step_deg=10):
    """아래가 둥근 그릇: h = D(1-cosθ), r = R sinθ."""
    out = []
    for d in range(0, 91, step_deg):
        t = math.radians(d)
        out.append((depth * (1 - math.cos(t)), radius * math.sin(t)))
    return out


def stem_below(t, stem, foot_r=40):
    """굽 달린 잔의 그릇 아래 바깥선: (안쪽 바닥에서 아래로 깊이, 반지름)."""
    return [(t + 2, 6), (t + 9, 4), (stem - 9, 4), (stem - 5, 10), (stem - 2.5, foot_r), (stem, foot_r - 2)]


def tumbler_below(base, r0, t):
    ro = r0 + t
    return [(base - 6, ro), (base - 1.5, ro - 1.5), (base, ro - 6)]


def glass_spec(kind):
    """안쪽 윤곽 knots[(h, r)] (아래→위), 벽 두께 t, 안쪽 바닥 y, 바깥 아래 윤곽 below."""
    if kind == "rocks":
        k, t, base = [(0, 53), (140, 60)], 4.5, 16
    elif kind == "highball":
        k, t, base = [(0, 30), (200, 33)], 4, 13
    elif kind == "mug":
        k, t, base = [(0, 44), (160, 48)], 4.5, 14
    elif kind == "julep":
        k, t, base = [(0, 38), (175, 50)], 3.5, 10
    elif kind == "shot":
        k, t, base = [(0, 34), (110, 42)], 5, 26
    elif kind == "coupe":
        k, t, stem = ellipse_knots(80, 64), 3.5, 90
        return dict(knots=k, t=t, yb=BASE_Y - stem, below=stem_below(t, stem))
    elif kind == "martini":
        k, t, stem = [(0, 2), (100, 64)], 3.5, 85
        return dict(knots=k, t=t, yb=BASE_Y - stem, below=stem_below(t, stem))
    elif kind == "wine":
        k = ellipse_knots(70, 50) + [(105, 47), (135, 40)]
        t, stem = 3.5, 80
        return dict(knots=k, t=t, yb=BASE_Y - stem, below=stem_below(t, stem, 36))
    else:
        raise ValueError(f"알 수 없는 잔 종류: {kind}")
    return dict(knots=k, t=t, yb=BASE_Y - base, below=tumbler_below(base, k[0][1], t))


def r_at(knots, h):
    if h <= knots[0][0]:
        return knots[0][1]
    for (h0, r0), (h1, r1) in zip(knots, knots[1:]):
        if h <= h1:
            return r0 + (r1 - r0) * (h - h0) / (h1 - h0) if h1 > h0 else r1
    return knots[-1][1]


def vol_at(knots, h):
    """높이 h까지의 회전체 부피(원뿔대 합)."""
    v = 0.0
    for (h0, r0), (h1, r1) in zip(knots, knots[1:]):
        if h <= h0:
            break
        top = min(h, h1)
        rt = r_at(knots, top)
        dh = top - h0
        v += math.pi * dh * (r0 * r0 + r0 * rt + rt * rt) / 3
    return v


def h_for_vol(knots, v):
    lo, hi = 0.0, knots[-1][0]
    for _ in range(60):
        mid = (lo + hi) / 2
        if vol_at(knots, mid) < v:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def side(knots, h0, h1, sign):
    """h0→h1 구간 안쪽 벽 점들(sign=-1 왼쪽, +1 오른쪽)."""
    hs = [h0] + [h for h, _ in knots if h0 < h < h1] + [h1]
    return [(CX + sign * r_at(knots, h), h) for h in hs]


def glass_paths(g):
    k, t, yb = g["knots"], g["t"], g["yb"]
    left = [(CX - (r + t), yb - h) for h, r in reversed(k)] + [(CX - r, yb + d) for d, r in g["below"]]
    right = [(2 * CX - x, y) for x, y in reversed(left)]
    inner_r = [(CX + r, yb - h) for h, r in reversed(k)]
    inner_l = [(CX - r, yb - h) for h, r in k]
    wall = "M" + pts(left + right + inner_r + inner_l) + "Z"
    cavity = "M" + pts(inner_l + inner_r) + "Z"
    return wall, cavity


# ---------------------------------------------------------------- 계산
def layers_of(c, g):
    """[(재료 인덱스, h0, h1)] — 부피 기준."""
    liq = [(i, ing) for i, ing in enumerate(c["ingredients"]) if isinstance(ing.get("ml"), (int, float)) and ing["ml"] > 0]
    total = sum(ing["ml"] for _, ing in liq)
    if not liq:
        return [], 0.0
    k = g["knots"]
    cap = vol_at(k, k[-1][0])
    nominal = NOMINAL[c["glass"]] * (1 - ICE_SHARE.get(c.get("ice", "none"), 0))
    frac = min(.88, max(.32, total * DILUTION.get(c.get("method"), 1.0) / nominal))
    # 가독성 우선: 굽 달린 잔은 84%, 록스 잔은 얼음이 있으면 60% 이상(없으면 50% 이상)
    if c["glass"] in ("coupe", "martini", "wine"):
        frac = .84
    elif c.get("ice") == "crushed":
        frac = max(frac, .72)
    elif c["glass"] == "rocks":
        frac = max(frac, .6 if c.get("ice", "none") != "none" else .5)
    liquid_v = cap * frac
    out, acc, h0 = [], 0.0, 0.0
    for i, ing in liq:
        acc += ing["ml"]
        h1 = h_for_vol(k, liquid_v * acc / total)
        out.append((i, h0, h1))
        h0 = h1
    return out, h0


def disp_amount(ing):
    """라벨용 양. 긴 설명형 표기('잔을 채울 만큼(약 135ml…)')는 '약 135ml'로 줄인다(대체 텍스트는 원문)."""
    a = ing.get("amount") or ""
    ml = ing.get("ml")
    if isinstance(ml, (int, float)) and len(a) > 9:
        return f"약 {f(ml)}ml"
    return a


def lum(hexcolor):
    h = hexcolor.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return .2126 * r + .7152 * g + .0722 * b


def rgb(hexcolor):
    h = hexcolor.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def similar(a, b):
    return math.dist(rgb(a), rgb(b)) < 70


def text_w(s, size=14.5, bold=False):
    w = 0.0
    for ch in s:
        o = ord(ch)
        if o >= 0x1100:
            w += size * .96
        elif ch == " ":
            w += size * .3
        elif ch.isdigit() or ch.islower():
            w += size * .56
        else:
            w += size * .64
    return w * (1.04 if bold else 1)


# ---------------------------------------------------------------- 그림 조각
def ice_shapes(c, g, top_h):
    ice = c.get("ice", "none")
    k, yb = g["knots"], g["yb"]
    if ice == "none" or top_h <= 0:
        return ""
    out = []
    if ice == "cube":
        r0 = r_at(k, top_h * .3)
        s = min(r0 * .8, 36)
        y, n, side_ = s * .6 + 3, 0, -1
        while y < top_h + s * .2 and n < 6:
            r = r_at(k, y)
            x = CX + side_ * r * .32
            rot = 8 * side_
            out.append(f'<rect x="{f(x - s / 2)}" y="{f(yb - y - s / 2)}" width="{f(s)}" height="{f(s)}" rx="5" '
                       f'transform="rotate({rot} {f(x)} {f(yb - y)})"/>')
            y += s * .82
            side_ = -side_
            n += 1
    elif ice == "large":
        s = min(r_at(k, 0) * 1.25, top_h * 1.1, 64)
        y = s / 2 + 2
        out.append(f'<rect x="{f(CX - s / 2)}" y="{f(yb - y - s / 2)}" width="{f(s)}" height="{f(s)}" rx="7" '
                   f'transform="rotate(-6 {f(CX)} {f(yb - y)})"/>')
    elif ice == "crushed":
        row, y = 0, 5
        while y < top_h + 3:
            r = r_at(k, y) - 5
            x = CX - r + (5 if row % 2 else 0) + 3
            col = 0
            while x < CX + r - 3:
                w = 7 + (col * 3 + row) % 4
                out.append(f'<rect x="{f(x)}" y="{f(yb - y - 3.5)}" width="{f(w)}" height="7" rx="2.5" '
                           f'transform="rotate({(col * 37 + row * 23) % 50 - 25} {f(x + w / 2)} {f(yb - y)})"/>')
                x += w + 5
                col += 1
            y += 10
            row += 1
    return "".join(out)


def bubbles(g, h0, h1):
    k, yb = g["knots"], g["yb"]
    out = []
    for j, (fx, fy) in enumerate(((-.4, .25), (.3, .45), (-.1, .7), (.45, .82), (-.5, .9))):
        h = h0 + (h1 - h0) * fy
        if h1 - h0 < 14 and j > 1:
            break
        r = r_at(k, h)
        out.append(f'<circle cx="{f(CX + fx * r)}" cy="{f(yb - h)}" r="{2 if j % 2 else 2.6}"/>')
    return "".join(out)


def highlight(g):
    k, yb = g["knots"], g["yb"]
    top = k[-1][0]
    inset = 7 if k[0][1] > 10 else 10

    def line(a, b):
        hs = [top * a] + [h for h, _ in k if top * a < h < top * b] + [top * b]
        return "M" + pts([(CX - r_at(k, h) + inset, yb - h) for h in hs])
    return f'<path class="cka-h" d="{line(.12, .62)}"/><path class="cka-h" d="{line(.7, .8)}"/>'


def handle(g):
    k, yb, t = g["knots"], g["yb"], g["t"]
    x0 = CX - k[0][1] - t
    yt, ybm = yb - k[-1][0] * .82, yb - k[-1][0] * .18
    return (f'<path class="cka-o" d="M{f(x0 + .5)},{f(yt)}C{f(x0 - 34)},{f(yt - 4)} {f(x0 - 34)},{f(ybm + 4)} {f(x0 + .5)},{f(ybm)}"/>'
            f'<path class="cka-o" d="M{f(x0 + .5)},{f(yt + 12)}C{f(x0 - 20)},{f(yt + 10)} {f(x0 - 20)},{f(ybm - 10)} {f(x0 + .5)},{f(ybm - 12)}"/>')


def julep_bands(g):
    k, yb, t = g["knots"], g["yb"], g["t"]
    out = []
    for h in (k[-1][0] - 9, 6):
        r = r_at(k, h) + t
        out.append(f'<path class="cka-b" d="M{f(CX - r)},{f(yb - h)}H{f(CX + r)}"/>')
    return "".join(out)


FRUIT = (("오렌지", "#ef8a24"), ("레몬", "#f1d33a"), ("라임", "#7cc04b"), ("자몽", "#f07a6a"))


def garnish_kinds(c):
    """garnish 글에서 그릴 것 고르기. '또는'이 있으면 앞의 것만."""
    out = []
    for gtxt in c.get("garnish") or []:
        w = gtxt.split("또는")[0]
        if "체리" in w:
            out.append(("cherry", None))
        elif "민트" in w:
            out.append(("mint", None))
        elif "시나몬" in w:
            out.append(("cinnamon", None))
        elif "생강" in w:
            out.append(("ginger", None))
        else:
            for key, col in FRUIT:
                if key in w:
                    out.append(("peel" if "껍질" in w else "wheel", col))
                    break
    return out[:3]


def garnish_svg(c, g):
    k, yb = g["knots"], g["yb"]
    rt, ytop = k[-1][1], yb - k[-1][0]
    out = []
    for slot, (kind, col) in enumerate(garnish_kinds(c)):
        x, y = CX + rt * (.62 - slot * .55), ytop
        if kind == "cherry":
            out.append(f'<path class="cka-o" style="stroke-width:1.8" d="M{f(x)},{f(y - 8)}q4,-12 12,-16"/>'
                       f'<circle class="cka-o" style="fill:#b3122e;stroke-width:2" cx="{f(x)}" cy="{f(y - 4)}" r="6.5"/>'
                       f'<circle cx="{f(x - 2)}" cy="{f(y - 6.5)}" r="1.6" fill="#fff" fill-opacity=".7"/>')
        elif kind == "mint":
            out.append(f'<path class="cka-o" style="fill:#4f9a4a;stroke-width:1.8" d="M{f(x)},{f(y)}c-12,-4 -14,-14 -10,-20c6,4 10,12 10,20z'
                       f'M{f(x)},{f(y)}c10,-6 12,-15 8,-21c-6,4 -9,12 -8,21z"/>')
        elif kind == "cinnamon":
            out.append(f'<rect class="cka-o" style="fill:#8a4b22;stroke-width:1.8" x="{f(x - 3)}" y="{f(y - 30)}" width="7" height="38" rx="3" '
                       f'transform="rotate(14 {f(x)} {f(y)})"/>')
        elif kind == "ginger":
            out.append(f'<ellipse class="cka-o" style="fill:#e6cf8f;stroke-width:1.8" cx="{f(x)}" cy="{f(y - 3)}" rx="9" ry="6"/>')
        elif kind == "wheel":
            out.append(f'<circle class="cka-o" style="fill:{col};stroke-width:2" cx="{f(x)}" cy="{f(y)}" r="11"/>'
                       f'<circle cx="{f(x)}" cy="{f(y)}" r="7" fill="#fff" fill-opacity=".35"/>'
                       f'<path class="cka-b" style="stroke-opacity:.5" d="M{f(x - 7)},{f(y)}H{f(x + 7)}M{f(x)},{f(y - 7)}V{f(y + 7)}"/>')
        else:  # 껍질(필·트위스트)
            out.append(f'<path class="cka-o" style="fill:{col};stroke-width:2" d="M{f(x - 10)},{f(y - 2)}'
                       f'c4,-12 14,-14 20,-8c-4,-2 -10,0 -12,6c-2,4 -6,5 -8,2z"/>')
    return "".join(out)


def steam(g):
    k, yb = g["knots"], g["yb"]
    ytop = yb - k[-1][0] - 8
    return "".join(f'<path class="cka-m" style="stroke-width:2;opacity:.7" d="M{f(CX + dx)},{f(ytop)}c-6,-6 6,-10 0,-16c-6,-6 6,-10 0,-16"/>'
                   for dx in (-14, 0, 14))


def chip_icon(kind, color, x, y, name=""):
    if "민트" in name:
        kind = "other"
    elif "생강" in name:
        return f'<ellipse class="cka-o" style="fill:{color};stroke-width:1.6" cx="{f(x)}" cy="{f(y)}" rx="6.5" ry="4.5"/>'
    elif "정향" in name:
        return (f'<path class="cka-o" style="stroke:{color};stroke-width:2.2" d="M{f(x)},{f(y - 1)}V{f(y + 7)}"/>'
                f'<circle class="cka-o" style="fill:{color};stroke-width:1.4" cx="{f(x)}" cy="{f(y - 3)}" r="3.6"/>')
    if kind == "sugar":
        return f'<rect class="cka-o" style="fill:{color};stroke-width:1.6" x="{f(x - 5.5)}" y="{f(y - 5.5)}" width="11" height="11" rx="2"/>'
    if kind in ("bitters", "water", "syrup", "juice", "liqueur"):
        return f'<path class="cka-o" style="fill:{color};stroke-width:1.6" d="M{f(x)},{f(y - 7)}c4,5 6,8 6,10a6,6 0 0 1 -12,0c0,-2 2,-5 6,-10z"/>'
    if kind in ("egg", "dairy"):
        return f'<ellipse class="cka-o" style="fill:{color};stroke-width:1.6" cx="{f(x)}" cy="{f(y)}" rx="5.5" ry="7"/>'
    if kind == "other":
        return f'<path class="cka-o" style="fill:{color};stroke-width:1.6" d="M{f(x - 6)},{f(y + 5)}c0,-8 6,-12 12,-12c0,8 -6,12 -12,12z"/>'
    return f'<circle class="cka-o" style="fill:{color};stroke-width:1.6" cx="{f(x)}" cy="{f(y)}" r="5"/>'


PCT = "\0pct"
STYLE = (".cka-{id}{{color:var(--ink,#14201a);font-family:inherit}}"
         "@media(prefers-color-scheme:dark){{.cka-{id}{{color:var(--ink,#e8eee9)}}}}"
         ".cka-{id} .cka-o{{fill:none;stroke:currentColor;stroke-width:2.6;stroke-linejoin:round;stroke-linecap:round}}"
         ".cka-{id} .cka-w{{fill:currentColor;fill-opacity:.14}}"
         ".cka-{id} .cka-g{{fill:currentColor;fill-opacity:.05}}"
         ".cka-{id} .cka-l{{stroke:currentColor;stroke-opacity:.4;stroke-width:1}}"
         ".cka-{id} .cka-e{{stroke:currentColor;stroke-width:1.6;stroke-dasharray:4 3}}"
         ".cka-{id} .cka-i rect{{fill:#fff;fill-opacity:.16;stroke:currentColor;stroke-opacity:.5;stroke-width:1.4}}"
         ".cka-{id} .cka-u circle{{fill:none;stroke:#fff;stroke-opacity:.85;stroke-width:1.2}}"
         ".cka-{id} .cka-h{{fill:none;stroke:#fff;stroke-opacity:.6;stroke-width:4;stroke-linecap:round}}"
         ".cka-{id} .cka-b{{fill:none;stroke:currentColor;stroke-opacity:.45;stroke-width:1.5}}"
         ".cka-{id} .cka-m{{fill:none;stroke:var(--muted,#7a8a80);stroke-width:1.2}}")
STYLE_LABELS = (".cka-{id} .cka-t{{fill:currentColor;font-size:14.5px}}"
                ".cka-{id} .cka-a{{font-weight:700}}"
                ".cka-{id} .cka-q{{fill:var(--muted,#7a8a80);font-size:12px}}"
                ".cka-{id} .cka-n{{font-size:12px;font-weight:700;text-anchor:middle}}"
                ".cka-{id} .cka-c{{fill:var(--muted,#7a8a80);font-size:12.5px;text-anchor:middle}}"
                ".cka-{id} .cka-p{{fill:none;stroke:var(--muted,#7a8a80);stroke-width:1;stroke-dasharray:3 2}}")


def title_text(c, lays):
    ings = c["ingredients"]
    layer_txt = ", ".join(f'{ings[i]["ko"]} {ings[i]["amount"]}' for i, _, _ in lays)
    extra = [f'{ing["ko"]} {ing.get("amount") or ""}'.strip() for ing in ings if not (isinstance(ing.get("ml"), (int, float)) and ing["ml"] > 0)]
    s = f'{c["ko"]}: {GLASS_KO.get(c["glass"], c["glass"])}, {ICE_KO.get(c.get("ice", "none"), "")}. '
    if layer_txt:
        s += f"아래부터 {layer_txt} 층."
    if extra:
        s += " 함께 넣는 재료: " + ", ".join(extra) + "."
    order = ", ".join(f'{n}. {ing["ko"]}' for n, ing in enumerate(ings, 1))
    return s + f" 넣는 순서: {order}."


def glass_body(c, g, lays, top_h, uid, small=False):
    k, yb = g["knots"], g["yb"]
    ings = c["ingredients"]
    wall, cavity = glass_paths(g)
    o = []
    if c["glass"] == "mug":
        o.append(handle(g))
    o.append(f'<path class="cka-w" d="{wall}"/><path class="cka-g" d="{cavity}"/>')
    for n, (i, h0, h1) in enumerate(lays):
        poly = side(k, h0, h1, -1) + side(k, h0, h1, 1)[::-1]
        o.append(f'<polygon class="cka-l" fill="{ings[i]["color"]}" points="{pts((x, yb - h) for x, h in poly)}"/>')
    for n, (i, h0, h1) in enumerate(lays):
        if ings[i].get("kind") == "soda":
            o.append(f'<g class="cka-u">{bubbles(g, h0, h1)}</g>')
    for n in range(1, len(lays)):
        a, b = ings[lays[n - 1][0]], ings[lays[n][0]]
        if similar(a["color"], b["color"]):
            h = lays[n][1]
            r = r_at(k, h)
            o.append(f'<path class="cka-e" d="M{f(CX - r)},{f(yb - h)}H{f(CX + r)}"/>')
    if top_h > 0:
        r = r_at(k, top_h) - 6
        o.append(f'<path class="cka-h" style="stroke-width:2;stroke-opacity:.5" d="M{f(CX - r)},{f(yb - top_h + 3)}H{f(CX + r * .4)}"/>')
    ice = ice_shapes(c, g, top_h)
    if ice:
        o.append(f'<clipPath id="{uid}-c"><path d="{cavity}"/></clipPath><g class="cka-i" clip-path="url(#{uid}-c)">{ice}</g>')
    o.append(highlight(g))
    if c["glass"] == "julep":
        o.append(julep_bands(g))
    o.append(f'<path class="cka-o" d="{wall}"/>')
    if not small:
        if c.get("method") == "hot":
            o.append(steam(g))
        o.append(garnish_svg(c, g))
    return "".join(o)


def labels(c, g, lays, top_h):
    k, yb, t = g["knots"], g["yb"], g["t"]
    ings = c["ingredients"]
    by_idx = {i: (h0, h1) for i, h0, h1 in lays}
    avail_base = W - 6
    rows = []
    boundary_after = 0.0
    total_ml = sum(ings[i]["ml"] for i in by_idx) or 1
    for n, ing in enumerate(ings):
        is_layer = n in by_idx
        tx = LX + 24 + (0 if is_layer else 18)
        avail = avail_base - tx
        words = ing["ko"].split(" ") + [None]  # None = 양, PCT = 전체 대비 비율
        pct = ""
        if is_layer and by_idx[n][1] - by_idx[n][0] >= 14 and len(by_idx) > 1:
            pct = f"· {round(ing['ml'] * 100 / total_ml)}%"
            words.append(PCT)
        lines, cur, cw = [], [], 0.0
        for w_ in words:
            s = disp_amount(ing) if w_ is None else pct if w_ == PCT else w_
            ww = text_w(s, size=12 if w_ == PCT else 14.5, bold=w_ is None) + (text_w(" ") if cur else 0)
            if cur and cw + ww > avail:
                lines.append(cur)
                cur, cw = [], 0.0
                ww = text_w(s, size=12 if w_ == PCT else 14.5, bold=w_ is None)
            cur.append(w_)
            cw += ww
        lines.append(cur)
        if lines[-1] == [PCT]:  # 비율이 혼자 다음 줄로 밀리면 생략
            lines.pop()
            pct = ""
        hgt = 24 + 18 * (len(lines) - 1)
        if is_layer:
            h0, h1 = by_idx[n]
            want = yb - (h0 + h1) / 2
            boundary_after = h1
        else:
            want = yb - boundary_after - (4 if boundary_after else -6)
        rows.append(dict(n=n, ing=ing, layer=is_layer, lines=lines, h=hgt, want=want, tx=tx, pct=pct))
    # 아래(①)부터 위로 순서를 지키며 겹치지 않게 배치
    lo, hi = 14, BASE_Y - 4
    ys = [r["want"] for r in rows]
    for _ in range(200):
        moved = False
        for j in range(1, len(rows)):
            gap = rows[j - 1]["h"] / 2 + rows[j]["h"] / 2 + 3
            if ys[j - 1] - ys[j] < gap - 1e-6:
                push = (gap - (ys[j - 1] - ys[j])) / 2
                ys[j - 1] += push
                ys[j] -= push
                moved = True
        for j, r in enumerate(rows):
            ys[j] = min(hi - r["h"] / 2, max(lo + r["h"] / 2, ys[j]))
        if not moved:
            break
    for j in range(1, len(rows)):  # 마지막 보정(위로만)
        gap = rows[j - 1]["h"] / 2 + rows[j]["h"] / 2 + 3
        ys[j] = min(ys[j], ys[j - 1] - gap)
    o = []
    for r, y in zip(rows, ys):
        ing = r["ing"]
        top_line_y = y - (len(r["lines"]) - 1) * 9
        if r["layer"]:
            h0, h1 = by_idx[r["n"]]
            hm = (h0 + h1) / 2
            rr = r_at(k, hm)
            dx = rr * (.2 + .22 * (r["n"] % 3))  # 얇은 층이 이어질 때 점이 겹치지 않게 엇갈림
            o.append(f'<path class="cka-m" d="M{f(CX + dx)},{f(yb - hm)}H{f(CX + rr + t + 5)}L{f(LX - 4)},{f(top_line_y)}"/>'
                     f'<circle cx="{f(CX + dx)}" cy="{f(yb - hm)}" r="2.6" fill="currentColor"/>')
        else:
            wmax = max(sum(text_w(disp_amount(ing) if w_ is None else w_, bold=w_ is None) for w_ in ln) + text_w(" ") * (len(ln) - 1)
                       for ln in r["lines"])
            o.append(f'<rect class="cka-p" x="{f(LX + 17)}" y="{f(y - r["h"] / 2 + 1)}" width="{f(wmax + 36)}" height="{f(r["h"] - 2)}" rx="9"/>')
            o.append(chip_icon(ing.get("kind", ""), ing["color"], LX + 32, top_line_y, ing["ko"]))
        dark_txt = lum(ing["color"]) > .5
        o.append(f'<circle class="cka-o" style="fill:{ing["color"]};stroke-width:1.5" cx="{LX + 9}" cy="{f(top_line_y)}" r="9.5"/>'
                 f'<text class="cka-n" x="{LX + 9}" y="{f(top_line_y + 4.2)}" fill="{"#1a1a1a" if dark_txt else "#fff"}">{r["n"] + 1}</text>')
        for li, ln in enumerate(r["lines"]):
            parts = []
            for w_ in ln:
                if w_ is None:
                    parts.append(f'<tspan class="cka-a">{html.escape(disp_amount(ing))}</tspan>')
                elif w_ == PCT:
                    parts.append(f'<tspan class="cka-q">{r["pct"]}</tspan>')
                else:
                    parts.append(html.escape(w_))
            o.append(f'<text class="cka-t" x="{f(r["tx"])}" y="{f(top_line_y + 5 + li * 18)}">{" ".join(parts)}</text>')
    return "".join(o)


def render(c, small=False):
    cid = c["id"]
    g = glass_spec(c["glass"])
    lays, top_h = layers_of(c, g)
    uid = f"cka-{cid}{'-s' if small else ''}"
    title = title_text(c, lays)
    style = STYLE.format(id=cid) + ("" if small else STYLE_LABELS.format(id=cid))
    body = glass_body(c, g, lays, top_h, uid, small)
    if small:
        vb = " ".join(str(v) for v in SMALL_BOX)
        extra = ""
    else:
        vb = f"0 0 {W} {H}"
        extra = labels(c, g, lays, top_h) + (
            f'<text class="cka-c" x="{CX}" y="{H - 10}">{GLASS_KO.get(c["glass"], "")} · {ICE_KO.get(c.get("ice", "none"), "")}</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" class="cka cka-{cid}" role="img" aria-labelledby="{uid}-t">'
            f'<title id="{uid}-t">{html.escape(title)}</title><style>{style}</style>{body}{extra}</svg>\n')


# ---------------------------------------------------------------- 시험 그림·미리보기
SHEET_COLORS = ("#c8781e", "#e9c46a")


def sheet_items():
    out = []
    for gk in ("rocks", "highball", "coupe", "martini", "mug", "julep", "wine", "shot"):
        out.append({"id": f"glass-{gk}", "ko": GLASS_KO[gk], "glass": gk, "method": "build", "ice": "none",
                    "ingredients": [{"ko": "아래층", "ml": 30, "amount": "30ml", "kind": "whiskey", "color": SHEET_COLORS[0]},
                                    {"ko": "위층", "ml": 30, "amount": "30ml", "kind": "juice", "color": SHEET_COLORS[1]}],
                    "garnish": []})
    out.append({"id": "test-many", "ko": "얇은 층 시험", "glass": "rocks", "method": "stir", "ice": "cube",
                "ingredients": [
                    {"ko": "각설탕", "ml": None, "amount": "1개", "kind": "sugar", "color": "#f4efe2"},
                    {"ko": "라이 위스키", "ml": 40, "amount": "40ml", "kind": "whiskey", "color": "#b8651a"},
                    {"ko": "스위트 베르무트", "ml": 10, "amount": "10ml", "kind": "vermouth", "color": "#7a1f2b"},
                    {"ko": "드라이 베르무트", "ml": 5, "amount": "5ml", "kind": "vermouth", "color": "#e8d9a0"},
                    {"ko": "베네딕틴 리큐어", "ml": 5, "amount": "5ml", "kind": "liqueur", "color": "#d8a23a"},
                    {"ko": "페이쇼드 비터스", "ml": None, "amount": "2대시", "kind": "bitters", "color": "#c0392b"},
                    {"ko": "앙고스투라 아로마틱 비터스", "ml": None, "amount": "2대시", "kind": "bitters", "color": "#8e2a1c"}],
                "garnish": ["레몬 껍질"]})
    return out


def num_vol(knots, h0, h1, n=4000):
    """검산용: 얇은 원판 n장으로 직접 적분(원뿔대 공식과 독립)."""
    dh = (h1 - h0) / n
    return sum(math.pi * r_at(knots, h0 + (j + .5) * dh) ** 2 * dh for j in range(n))


def verify():
    print("부피 검증: 30ml + 30ml 두 층. 원판 4000장 수치 적분으로 다시 잰 부피(viewBox 단위³)")
    for c in sheet_items()[:8]:
        g = glass_spec(c["glass"])
        lays, top = layers_of(c, g)
        k = g["knots"]
        (_, a0, a1), (_, b0, b1) = lays
        v1, v2 = num_vol(k, a0, a1), num_vol(k, b0, b1)
        hv1, hv2 = num_vol(k, 0, b1 / 2), num_vol(k, b1 / 2, b1)
        print(f'  {c["glass"]:8s} 아래층 높이 {a1 - a0:6.2f} 부피 {v1:9.1f} | 위층 높이 {b1 - b0:6.2f} 부피 {v2:9.1f} | '
              f'부피비 {v1 / v2:.4f} | 높이로 나눴다면 부피비 {hv1 / hv2:.3f}')


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


TOKENS = """:root{--bg:#eef1ec;--surface:#f8faf6;--ink:#14201a;--muted:#56675d;--line:#d2d9d1}
:root[data-theme=dark]{--bg:#0f1613;--surface:#17211c;--ink:#e8eee9;--muted:#95a59b;--line:#2b3931;color-scheme:dark}
body{margin:0;padding:16px;background:var(--bg);color:var(--ink);font-family:"Noto Sans KR","Malgun Gothic",system-ui,sans-serif}
h2{font-size:16px;margin:18px 0 8px}.row{display:flex;flex-wrap:wrap;gap:12px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:10px}
.detail svg{width:100%;display:block}.small svg{width:96px;height:144px;display:block}
.small .card{text-align:center;font-size:12px}.detail{flex:1 1 300px;max-width:330px}.cap{font-size:13px;font-weight:700}.cap small{font-weight:400;color:var(--muted)}"""


FOCUS = ("penicillin", "new-york-sour", "sazerac", "mint-julep", "irish-coffee")
SAMPLE3 = ("highball", "old-fashioned", "whiskey-sour")


def page(theme, body, mobile=False):
    extra = "body{box-sizing:border-box;width:390px;padding:16px}.detail{max-width:none}" if mobile else ""
    return (f'<!doctype html><html lang="ko" data-theme="{theme}"><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><style>{TOKENS}{extra}</style><body>{body}</body></html>')


def preview(sheet, items):
    d = os.path.join(ROOT, "tools", "cocktail-art")
    byid = {c["id"]: c for c in items}
    pick = lambda ids: [byid[i] for i in ids if i in byid]
    cap = lambda c: f'<div class="cap">{html.escape(c["ko"])} <small>{c["id"]}</small></div>'
    for theme in ("dark", "light"):
        det = lambda cs: "".join(f'<div class="card detail">{cap(c)}{render(c)}</div>' for c in cs)
        sm = "".join(f'<div class="card">{render(c, True)}<div>{html.escape(c["ko"])}</div></div>' for c in items)
        gl = "".join(f'<div class="card detail">{render(c)}</div>' for c in sheet)
        write(os.path.join(d, f"preview-{theme}.html"), page(theme,
              f'<h2>상세 그림 {len(items)}종</h2><div class="row">{det(items)}</div>'
              f'<h2>목록용 작은 그림 (96×144)</h2><div class="row small">{sm}</div>'))
        write(os.path.join(d, f"focus-{theme}.html"), page(theme,
              f'<h2>견본 3종</h2><div class="row">{det(pick(SAMPLE3))}</div>'
              f'<h2>재료가 많은 항목</h2><div class="row">{det(pick(FOCUS))}</div>'))
        write(os.path.join(d, f"glasses-{theme}.html"), page(theme,
              f'<h2>잔 8종 (30ml + 30ml) · 얇은 층 시험</h2><div class="row">{gl}</div>'))
        write(os.path.join(d, f"preview-{theme}-390.html"), page(theme,
              f'<div class="row">{det(pick(SAMPLE3) + pick(FOCUS))}</div>', mobile=True))


def main():
    ap = argparse.ArgumentParser(description="칵테일 잔 그림 생성")
    ap.add_argument("--data", default=os.path.join(ROOT, "data", "cocktails.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "art", "cocktails"))
    ap.add_argument("--sheet", action="store_true", help="잔 8종 시험 그림과 미리보기 HTML 생성")
    ap.add_argument("--verify", action="store_true", help="부피 검증 수치 출력")
    a = ap.parse_args()
    if a.verify:
        verify()
        return
    with open(a.data, encoding="utf-8") as fh:
        items = json.load(fh)
    sizes = []
    for c in items:
        if c.get("glass") not in GLASS_KO:
            sys.exit(f'{c.get("id")}: glass 값 "{c.get("glass")}"을 알 수 없음')
        for small in (False, True):
            p = os.path.join(a.out, f'{c["id"]}{"-s" if small else ""}.svg')
            svg = render(c, small)
            write(p, svg)
            sizes.append((os.path.basename(p), len(svg.encode())))
    for name, n in sizes:
        print(f"  {name:32s} {n / 1024:5.1f} KB")
    print(f"{len(items)}종 → {a.out}")
    if a.sheet:
        sheet = sheet_items()
        for c in sheet:
            write(os.path.join(ROOT, "tools", "cocktail-art", f'{c["id"]}.svg'), render(c))
        preview(sheet, items)
        print("시험 그림·미리보기 → tools/cocktail-art/")


if __name__ == "__main__":
    main()
