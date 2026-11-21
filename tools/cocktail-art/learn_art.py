#!/usr/bin/env python3
"""'그림으로 배우는 위스키' 그림 생성기 (표준 라이브러리만).

  python3 -B tools/cocktail-art/learn_art.py
    → art/learn/<id>.svg (PC, 720×460), art/learn/<id>-m.svg (휴대폰, 360×880)
    → tools/cocktail-art/learn-{dark,light}[-390].html (미리보기)

라벨 문구는 기획 콘티(docs/ideas/06-그림으로-배우는-위스키.md)의 표를 그대로 쓴다.
"""
import html
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "art", "learn")

# 그림 3 아래 단 예시(설명용 가상 값). 리더 확인 결과에 따라 바꾼다.
CASK_AGES = (10, 12, 15)
MIN_TICK = 3          # 시간 줄에 눈금만 두는 최소 숙성(스카치 3년). None이면 생략
LABEL_AGE = min(CASK_AGES)

WOOD = "#b07a45"
WHISKY = "#c9822b"
GRAIN = "#e9d8a6"
NEWSPIRIT = "#f4f1e6"
COPPER = "#c8763a"
BARLEY = "#e2b866"
GREEN = "#5e9e4a"


def f(v):
    s = f"{v:.1f}"
    s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def esc(s):
    return html.escape(s, quote=True)


def text_w(s, size=14, bold=False):
    w = 0.0
    for ch in s:
        o = ord(ch)
        if o >= 0x1100:
            w += size * .96
        elif ch == " ":
            w += size * .3
        elif ch in "()·~":
            w += size * .4
        elif ch.isdigit() or ch.islower():
            w += size * .58
        else:
            w += size * .66
    return w * (1.05 if bold else 1)


def wrap(s, maxw, size=14, bold=False):
    words, lines, cur = s.split(" "), [], ""
    for w in words:
        t = (cur + " " + w) if cur else w
        if cur and text_w(t, size, bold) > maxw:
            lines.append(cur)
            cur = w
        else:
            cur = t
    lines.append(cur)
    return lines


class Pic:
    """SVG 조각 모음. uid는 id 접두어(PC/휴대폰 판이 한 페이지에 함께 있어도 겹치지 않게 다르게 준다)."""

    def __init__(self, uid):
        self.uid = uid
        self.o = []

    def add(self, s):
        self.o.append(s)

    # --- 글자
    def text(self, x, y, s, cls="lrn-t", anchor="start"):
        a = "" if anchor == "start" else f' text-anchor="{anchor}"'
        self.add(f'<text class="{cls}" x="{f(x)}" y="{f(y)}"{a}>{esc(s)}</text>')

    def lines(self, x, y, lines, cls="lrn-t", anchor="start", lh=18):
        for i, s in enumerate(lines):
            self.text(x, y + i * lh, s, cls, anchor)

    def wtext(self, x, y, s, maxw, cls="lrn-t", anchor="start", lh=18, size=14):
        ls = wrap(s, maxw, size)
        self.lines(x, y, ls, cls, anchor, lh)
        return len(ls)

    # --- 도형
    def arrow(self, d, accent=False, dashed=False):
        cls = "lrn-a" + (" lrn-ac" if accent else "") + (" lrn-dd" if dashed else "")
        m = f"{self.uid}-{'hc' if accent else 'h'}"
        self.add(f'<path class="{cls}" d="{d}" marker-end="url(#{m})"/>')

    def box(self, x, y, w, h, label, color, size=16):
        self.add(f'<rect class="lrn-o" x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="10" '
                 f'style="fill:{color};fill-opacity:.25"/>')
        self.text(x + w / 2, y + h / 2 + size * .36, label, "lrn-bx", "middle")

    def band(self, x, y, w, h, label):
        self.add(f'<rect class="lrn-band" x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="8"/>')
        self.text(x + w / 2, y + h / 2 + 5.5, label, "lrn-bt", "middle")

    def note(self, x, y, w, h, label):
        self.add(f'<rect class="lrn-nb" x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="8"/>')
        self.text(x + w / 2, y + h / 2 + 5, label, "lrn-t", "middle")

    def num(self, x, y, n, r=12):
        self.add(f'<circle class="lrn-band" cx="{f(x)}" cy="{f(y)}" r="{r}"/>')
        self.text(x, y + 5, str(n), "lrn-nt", "middle")

    def icon(self, fn, x, y, s=1.0, *a):
        t = f"translate({f(x)} {f(y)})" + (f" scale({s})" if s != 1 else "")
        self.add(f'<g transform="{t}">{fn(*a)}</g>')

    def svg(self, w, h, cid, title, desc):
        style = STYLE.replace("ID", cid)
        defs = (f'<defs><marker id="{self.uid}-h" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" '
                f'orient="auto-start-reverse"><path d="M0,0L10,5L0,10z" fill="currentColor"/></marker>'
                f'<marker id="{self.uid}-hc" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" '
                f'orient="auto-start-reverse"><path d="M0,0L10,5L0,10z" class="lrn-acf"/></marker></defs>')
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" class="lrn lrn-{cid}" role="img" '
                f'aria-labelledby="{self.uid}-t {self.uid}-d"><title id="{self.uid}-t">{esc(title)}</title>'
                f'<desc id="{self.uid}-d">{esc(desc)}</desc><style>{style}</style>{defs}{"".join(self.o)}</svg>\n')


STYLE = (".lrn-ID{color:var(--ink,#14201a);font-family:inherit;--lrn-ac:var(--accent,#1e5a43);--lrn-ai:var(--accent-ink,#fff)}"
         "@media(prefers-color-scheme:dark){.lrn-ID{color:var(--ink,#e8eee9);--lrn-ac:var(--accent,#74c7a3);--lrn-ai:var(--accent-ink,#0f1613)}}"
         ".lrn-ID .lrn-o{stroke:currentColor;stroke-width:2.6;stroke-linejoin:round;stroke-linecap:round;vector-effect:non-scaling-stroke}"
         ".lrn-ID .lrn-l{fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;vector-effect:non-scaling-stroke}"
         ".lrn-ID .lrn-a{fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}"
         ".lrn-ID .lrn-ac{stroke:var(--lrn-ac);stroke-width:2.6}"
         ".lrn-ID .lrn-acf{fill:var(--lrn-ac)}"
         ".lrn-ID .lrn-dd{stroke-dasharray:5 4}"
         ".lrn-ID .lrn-sm{fill:none;stroke:var(--muted,#7a8a80);stroke-width:2;stroke-dasharray:2 4;stroke-linecap:round;vector-effect:non-scaling-stroke}"
         ".lrn-ID .lrn-band{fill:var(--lrn-ac)}"
         ".lrn-ID .lrn-nb{fill:currentColor;fill-opacity:.07;stroke:currentColor;stroke-opacity:.35;stroke-width:1.2}"
         ".lrn-ID .lrn-pn{fill:currentColor;fill-opacity:.035;stroke:currentColor;stroke-opacity:.25;stroke-width:1.2}"
         ".lrn-ID .lrn-hl{fill:none;stroke:#fff;stroke-opacity:.55;stroke-width:3;stroke-linecap:round}"
         ".lrn-ID text{fill:currentColor;font-size:14px}"
         ".lrn-ID .lrn-m{fill:var(--muted,#7a8a80)}"
         ".lrn-ID .lrn-bx{font-size:16px;font-weight:700}"
         ".lrn-ID .lrn-hd{font-size:16px;font-weight:700}"
         ".lrn-ID .lrn-bt{fill:var(--lrn-ai);font-size:15px;font-weight:700}"
         ".lrn-ID .lrn-nt{fill:var(--lrn-ai);font-size:13px;font-weight:700}"
         ".lrn-ID .lrn-big{font-size:30px;font-weight:900;fill:#2a1806}")


# ================================================================ 아이콘 (원점 중심)
def o(d, fill, extra=""):
    return f'<path class="lrn-o" d="{d}" style="fill:{fill}"{extra}/>'


def ic_barley(color=BARLEY, slim=False):
    out = [f'<path class="lrn-l" d="M0,30Q2,4 0,-26"/>']
    rx, ry = (2.8, 5.2) if slim else (3.8, 6.4)
    awn = 14 if slim else 9
    for i in range(5):
        y = 14 - i * (8 if not slim else 8.5)
        for sgn in (-1, 1):
            x = sgn * (rx + .6)
            out.append(f'<ellipse class="lrn-o" style="fill:{color};stroke-width:1.6" cx="{f(x)}" cy="{f(y)}" rx="{rx}" ry="{ry}" '
                       f'transform="rotate({sgn * 24} {f(x)} {f(y)})"/>')
            out.append(f'<path class="lrn-l" style="stroke-width:1.2" d="M{f(x + sgn * 2)},{f(y - ry + 1)}l{f(sgn * awn * .45)},{f(-awn)}"/>')
    out.append(f'<ellipse class="lrn-o" style="fill:{color};stroke-width:1.6" cx="0" cy="-28" rx="{rx * .8}" ry="{ry * .9}"/>')
    return "".join(out)


def ic_malt():
    return (f'<path class="lrn-l" style="stroke:{GREEN};stroke-width:2.6" d="M3,-10q2,-14 12,-20"/>'
            f'<path class="lrn-o" style="fill:{GREEN};stroke-width:1.6" d="M15,-30q8,-2 10,4q-7,3 -10,-4z"/>'
            f'<ellipse class="lrn-o" style="fill:{BARLEY}" cx="0" cy="4" rx="9" ry="15" transform="rotate(18 0 4)"/>'
            f'<path class="lrn-l" d="M-5,18q-5,7 -12,6M-2,19q-1,8 -6,12M-6,15q-8,2 -12,-2" style="stroke-width:1.4"/>'
            f'<path class="lrn-l" style="stroke-opacity:.5" d="M-1,-8q-3,12 1,24"/>')


def ic_corn():
    out = ['<path class="lrn-o" style="fill:#7cae54" d="M-4,28C-22,18 -20,-6 -14,-18C-12,0 -8,12 -2,20Z"/>',
           '<ellipse class="lrn-o" style="fill:#f2c84b" cx="2" cy="-2" rx="11" ry="26"/>']
    for r in range(7):
        for c in (-5, 0, 5):
            y = -20 + r * 6.5
            out.append(f'<circle cx="{2 + c}" cy="{f(y)}" r="1.7" fill="#c98f12"/>')
    out.append('<path class="lrn-o" style="fill:#8cc063" d="M4,28C22,20 22,0 16,-12C14,4 10,14 4,20Z"/>')
    return "".join(out)


def ic_rye():
    return ic_barley("#c9a46a", slim=True)


def ic_potstill(fill=COPPER):
    return (o("M-20,26C-32,8 -22,-14 -6,-16L-4,-30Q0,-36 6,-34L30,-22L28,-17L6,-27L6,-16C22,-14 32,8 20,26Z", fill) +
            '<path class="lrn-hl" d="M-16,14C-20,6 -16,-4 -10,-8"/>' +
            '<path class="lrn-l" d="M-22,26H22" style="stroke-width:2.6"/>')


def ic_column():
    return (o("M-24,30V-24Q-24,-30 -16,-30Q-8,-30 -8,-24V30Z", COPPER) +
            o("M4,30V-16Q4,-22 12,-22Q20,-22 20,-16V30Z", COPPER) +
            '<path class="lrn-l" d="M-24,-10H-8M-24,6H-8M-24,20H-8M4,0H20M4,16H20" style="stroke-opacity:.6"/>' +
            '<path class="lrn-o" style="fill:none" d="M-16,-30Q-16,-38 -4,-38Q12,-38 12,-22"/>')


def ic_flame(s=1):
    return (f'<path class="lrn-o" style="fill:#f08a24;stroke-width:2" d="M0,{-16 * s}C{8 * s},{-6 * s} {12 * s},{2 * s} {8 * s},{10 * s}'
            f'Q0,{18 * s} {-8 * s},{10 * s}C{-12 * s},{2 * s} {-6 * s},{-4 * s} 0,{-16 * s}Z"/>'
            f'<path d="M0,{-4 * s}C{4 * s},{1 * s} {5 * s},{6 * s} {2 * s},{10 * s}Q0,{12 * s} {-2 * s},{10 * s}C{-5 * s},{6 * s} {-3 * s},{1 * s} 0,{-4 * s}Z" fill="#f7c948"/>')


def ic_japan():
    isl = ["M22,-50L34,-47L44,-40L38,-31L28,-33L19,-39Z",
           "M24,-26L29,-14L23,0L14,10L4,16L-8,22L-20,26L-32,32L-37,27L-26,20L-12,13L0,7L10,-1L16,-13L18,-24Z",
           "M-18,31L-6,29L-4,35L-16,38Z",
           "M-41,33L-32,35L-30,45L-38,50L-45,42Z"]
    return "".join(f'<path class="lrn-o" style="fill:var(--lrn-ac);fill-opacity:.3" d="{d}"/>' for d in isl)


def ic_barrel(w=120, h=60, head_fill=None, tag=None, char=False):
    """옆으로 눕힌 오크통. 왼쪽 끝에 통 머리(타원)."""
    x0, x1, hh, b, e = -w / 2, w / 2, h / 2, h * .12, w * .07
    body = (f"M{f(x0 + e)},{f(-hh)}Q0,{f(-hh - b)} {f(x1 - e)},{f(-hh)}Q{f(x1 + e * .7)},0 {f(x1 - e)},{f(hh)}"
            f"Q0,{f(hh + b)} {f(x0 + e)},{f(hh)}Q{f(x0 - e * .7)},0 {f(x0 + e)},{f(-hh)}Z")
    out = [o(body, WOOD)]
    for t in (-hh * .45, hh * .45):
        out.append(f'<path class="lrn-l" style="stroke-opacity:.35" d="M{f(x0 + e * 2.5)},{f(t)}Q0,{f(t * 1.15)} {f(x1 - e)},{f(t)}"/>')
    for xh in (x0 + w * .3, x1 - w * .2):
        out.append(f'<path class="lrn-l" style="stroke-width:2.4" d="M{f(xh)},{f(-hh - b * .8)}Q{f(xh + 4)},0 {f(xh)},{f(hh + b * .8)}"/>')
    hf = head_fill or "#c99560"
    out.append(f'<ellipse class="lrn-o" style="fill:{hf}" cx="{f(x0 + e * .9)}" cy="0" rx="{f(e * 1.6)}" ry="{f(hh * .96)}"/>')
    if char:
        out.append(f'<ellipse cx="{f(x0 + e * .9)}" cy="0" rx="{f(e * 1.0)}" ry="{f(hh * .68)}" fill="#2a1a10"/>')
        out.append(f'<g transform="translate({f(x0 + e * .9)} {f(hh * .2)})">{ic_flame(.75)}</g>')
    if tag:
        tw = 14 * len(tag) + 14
        out.append(f'<g transform="rotate(-6 {f(w * .12)} 0)"><rect class="lrn-o" style="fill:#fbf6ea;stroke-width:1.8" '
                   f'x="{f(w * .12 - tw / 2)}" y="-12" width="{f(tw)}" height="24" rx="3"/>'
                   f'<circle cx="{f(w * .12 - tw / 2 + 5)}" cy="0" r="2" fill="currentColor"/>'
                   f'<text x="{f(w * .12 + 3)}" y="5" text-anchor="middle" style="fill:#2a1806;font-size:14px;font-weight:700">{esc(tag)}</text></g>')
    return "".join(out)


def ic_bottle(liquid=WHISKY, label=None, s=1.0):
    d = ("M-7,-62H7V-44Q7,-38 15,-32Q24,-25 24,-12V52Q24,60 16,60H-16Q-24,60 -24,52V-12Q-24,-25 -15,-32Q-7,-38 -7,-44Z")
    out = [o(d, liquid), '<rect x="-8" y="-70" width="16" height="9" rx="2" class="lrn-o" style="fill:#7a4a2a"/>',
           '<path class="lrn-hl" d="M-17,-10V36"/>']
    if label is not None:
        out.append('<rect class="lrn-o" style="fill:#fbf6ea;stroke-width:2" x="-18" y="2" width="36" height="38" rx="4"/>')
        if label:
            out.append(f'<text class="lrn-big" x="0" y="32" text-anchor="middle">{esc(label)}</text>')
    return "".join(out)


def ic_drop(color="#cfe9ee"):
    return o("M0,-14C6,-6 9,0 9,4A9,9 0 0 1 -9,4C-9,0 -6,-6 0,-14Z", color)


def ic_kiln():
    """싹 난 보리를 판 위에서 불로 말림."""
    out = [o("M-34,4H34L30,12H-30Z", "#9a9a9a")]
    for i, x in enumerate(range(-26, 30, 9)):
        out.append(f'<ellipse class="lrn-o" style="fill:{BARLEY};stroke-width:1.5" cx="{x}" cy="-1" rx="4" ry="6" transform="rotate({(i % 3 - 1) * 20} {x} -1)"/>')
        if i % 2 == 0:
            out.append(f'<path class="lrn-l" style="stroke:{GREEN};stroke-width:1.8" d="M{x + 1},-7q2,-6 6,-8"/>')
    out.append(f'<g transform="translate(-12 28)">{ic_flame(.8)}</g><g transform="translate(12 28)">{ic_flame(.8)}</g>')
    return "".join(out)


def ic_peat():
    return (o("M-16,-2Q-18,-12 -6,-14Q6,-16 14,-10Q20,-4 14,2Q2,6 -10,4Z", "#5b3b22") +
            '<path d="M-8,-8l4,1M4,-10l3,2M-2,-3l5,0" stroke="#8a6a4a" stroke-width="1.6" stroke-linecap="round"/>' +
            f'<g transform="translate(0 16)">{ic_flame(.7)}</g>')


def ic_tub(liquid=GRAIN, steam=True, foam=False, tall=False):
    top = -30 if tall else -16
    vessel = f"M-36,{top}L-31,24Q-30,30 -24,30H24Q30,30 31,24L36,{top}"
    lvl = top + 12
    out = [f'<path d="M{-36 + 1.2},{lvl}L-31,24Q-30,30 -24,30H24Q30,30 31,24L{36 - 1.2},{lvl}Z" fill="{liquid}"/>']
    if foam:
        for i, x in enumerate(range(-30, 34, 9)):
            out.append(f'<circle class="lrn-o" style="fill:#fbf7ec;stroke-width:1.4" cx="{x}" cy="{lvl - (i % 2) * 2}" r="{4.5 + (i % 2)}"/>')
        for x, y in ((-16, lvl + 18), (8, lvl + 26), (18, lvl + 12), (-4, lvl + 34)):
            out.append(f'<circle class="lrn-o" style="fill:#f3e6b8;stroke-width:1.4" cx="{x}" cy="{y}" r="4"/>'
                       f'<circle class="lrn-o" style="fill:#f3e6b8;stroke-width:1.2" cx="{x + 4.5}" cy="{y - 3}" r="2"/>')
    else:
        for x, y in ((-20, lvl + 10), (-6, lvl + 22), (10, lvl + 14), (20, lvl + 26), (-14, lvl + 30), (4, lvl + 34)):
            out.append(f'<ellipse cx="{x}" cy="{y}" rx="2.4" ry="3.6" fill="{BARLEY}" stroke="currentColor" stroke-width="1"/>')
    out.append(f'<path class="lrn-o" style="fill:none" d="{vessel}"/>')
    if steam:
        for dx in (-12, 2, 16):
            out.append(f'<path class="lrn-sm" style="stroke-dasharray:none;stroke-width:1.8" d="M{dx},{top - 6}c-5,-5 5,-8 0,-13c-5,-5 5,-8 0,-13"/>')
    return "".join(out)


def ic_two_stills():
    out = []
    for i, x in enumerate((-30, 30)):
        out.append(f'<g transform="translate({x} 0) scale(.82)">{ic_potstill()}</g>')
        out.append(f'<circle class="lrn-o" style="fill:#fbf6ea;stroke-width:1.6" cx="{x - 2}" cy="8" r="8"/>'
                   f'<text x="{x - 2}" y="13" text-anchor="middle" style="fill:#2a1806;font-size:12px;font-weight:700">{i + 1}</text>')
    out.append(f'<g transform="translate(62 18) scale(.7)">{ic_drop(NEWSPIRIT)}</g>')
    return "".join(out)


def ic_casks_calendar():
    out = []
    for x, y in ((-34, 12), (14, 12), (-10, -18)):
        out.append(f'<g transform="translate({x} {y})">{ic_barrel(46, 26)}</g>')
    for i in range(3):
        x = 42 + i * 0
        y = -26 + i * 17
        out.append(f'<rect class="lrn-o" style="fill:#fbf6ea;stroke-width:1.6" x="46" y="{y}" width="20" height="14" rx="2"/>'
                   f'<rect x="46" y="{y}" width="20" height="4" fill="var(--lrn-ac)"/>')
    return "".join(out)


def ic_bottle_drop():
    return (f'<g transform="scale(.62)">{ic_bottle(WHISKY, "")}</g>'
            f'<g transform="translate(-30 -6) scale(.9)">{ic_drop()}</g>'
            f'<path class="lrn-a lrn-dd" d="M-30,8Q-28,18 -18,22" style="stroke-width:1.6"/>')


def bubble(p, x, y, w, lines, tail=(-1, 1), lh=18):
    h = len(lines) * lh + 14
    tx = x + (14 if tail[0] < 0 else w - 14)
    p.add(f'<path class="lrn-o" style="fill:var(--surface,#f8faf6);stroke-width:2" d="M{f(x + 10)},{f(y)}H{f(x + w - 10)}Q{f(x + w)},{f(y)} {f(x + w)},{f(y + 10)}'
          f'V{f(y + h - 10)}Q{f(x + w)},{f(y + h)} {f(x + w - 10)},{f(y + h)}H{f(tx + 8)}L{f(tx - 10)},{f(y + h + 12)}L{f(tx - 2)},{f(y + h)}'
          f'H{f(x + 10)}Q{f(x)},{f(y + h)} {f(x)},{f(y + h - 10)}V{f(y + 10)}Q{f(x)},{f(y)} {f(x + 10)},{f(y)}Z"/>')
    p.lines(x + w / 2, y + 21, lines, "lrn-t", "middle", lh)


# ================================================================ 그림 1: 위스키 종류 한눈에
def fig1_scotland(p, ox, oy, h):
    p.add(f'<g transform="translate({ox} {oy})">')
    p.add(f'<rect class="lrn-pn" x="3" y="2" width="354" height="{h - 4}" rx="12"/>')
    p.band(8, 6, 344, 26, "스코틀랜드")
    p.icon(ic_barley, 52, 74, .95)
    p.icon(ic_potstill, 140, 76, .95)
    p.icon(ic_column, 272, 76, .95)
    p.text(52, 124, "물 + 맥아 보리", "lrn-t", "middle")
    p.text(140, 124, "단식 증류기", "lrn-t", "middle")
    p.text(272, 124, "연속식 증류기(대체로)", "lrn-t", "middle")
    p.arrow("M96,132V156")
    p.text(104, 149, "한 증류소에서", "lrn-t lrn-m")
    p.arrow("M272,132V156")
    p.box(36, 158, 120, 32, "싱글몰트", "#c9822b")
    p.box(222, 158, 100, 32, "그레인", GRAIN)
    p.arrow("M96,192V214")
    p.arrow("M272,192V214")
    p.arrow("M158,182L220,218")
    p.box(26, 218, 140, 32, "블렌디드 몰트", "#d49a3a")
    p.box(222, 218, 100, 32, "블렌디드", "#d49a3a")
    p.text(96, 270, "여러 증류소의 싱글몰트를 섞음", "lrn-t lrn-m", "middle")
    p.text(272, 270, "싱글몰트 + 그레인", "lrn-t lrn-m", "middle")
    p.note(8, h - 34, 344, 26, "오크통에서 3년 이상 · 40% 이상")
    p.add('</g>')


def fig1_usa(p, ox, oy, h):
    p.add(f'<g transform="translate({ox} {oy})">')
    p.add(f'<rect class="lrn-pn" x="3" y="2" width="354" height="{h - 4}" rx="12"/>')
    p.band(8, 6, 344, 26, "미국")
    p.icon(ic_corn, 96, 76, .95)
    p.icon(ic_rye, 264, 74, .95)
    p.text(96, 124, "옥수수 51% 이상", "lrn-t", "middle")
    p.text(264, 124, "호밀 51% 이상", "lrn-t", "middle")
    p.arrow("M96,132V158")
    p.arrow("M264,132V158")
    p.box(46, 162, 100, 32, "버번", "#b8652a")
    p.box(214, 162, 100, 32, "라이", "#b5702e")
    by = (196 + h - 36) / 2 + 2
    p.arrow(f"M112,196L{f(150)},{f(by - 32)}")
    p.arrow(f"M248,196L{f(210)},{f(by - 32)}")
    p.icon(ic_barrel, 180, by, .85, 110, 52, None, None, True)
    p.note(8, h - 32, 344, 26, "새로 그을린 오크통 · 40% 이상")
    p.add('</g>')


def fig1_ireland(p, ox, oy, h):
    p.add(f'<g transform="translate({ox} {oy})">')
    p.add(f'<rect class="lrn-pn" x="3" y="2" width="354" height="{h - 4}" rx="12"/>')
    p.band(8, 6, 344, 26, "아일랜드")
    p.icon(ic_barley, 30, 72, .72)
    p.text(52, 76, "+", "lrn-hd", "middle")
    p.icon(ic_malt, 74, 74, .85)
    p.icon(ic_potstill, 140, 74, .8)
    p.lines(52, 112, ["맥아 보리 +", "맥아 아닌 보리"], "lrn-t", "middle")
    p.text(140, 112, "단식 증류기", "lrn-t", "middle")
    p.arrow("M176,66H198")
    p.box(202, 50, 140, 32, "싱글 팟 스틸", "#d8a24a")
    p.text(272, 104, "아일랜드 고유 방식", "lrn-t lrn-m", "middle")
    p.add('</g>')


def fig1_japan(p, ox, oy, h):
    p.add(f'<g transform="translate({ox} {oy})">')
    p.add(f'<rect class="lrn-pn" x="3" y="2" width="354" height="{h - 4}" rx="12"/>')
    p.band(8, 6, 344, 26, "일본")
    p.icon(ic_japan, 92, 84, .95)
    p.box(196, 54, 120, 32, "재패니즈", "#c9822b")
    p.text(256, 108, "업계 자율 기준(2021~)", "lrn-t lrn-m", "middle")
    p.add('</g>')


FIG1_TITLE = "위스키 종류 한눈에: 위스키 이름은 어디서, 무엇으로, 어떤 방식으로 만들었는지에 따라 정해진다."
FIG1_DESC = ("네 칸 그림. 스코틀랜드: 물 + 맥아 보리를 단식 증류기로 한 증류소에서 만들면 싱글몰트, "
             "여러 증류소의 싱글몰트를 섞으면 블렌디드 몰트, 연속식 증류기(대체로)로 만들면 그레인, 싱글몰트 + 그레인은 블렌디드. "
             "오크통에서 3년 이상 · 40% 이상. "
             "미국: 옥수수 51% 이상이면 버번, 호밀 51% 이상이면 라이. 새로 그을린 오크통 · 40% 이상. "
             "아일랜드: 맥아 보리 + 맥아 아닌 보리를 단식 증류기로 만드는 싱글 팟 스틸, 아일랜드 고유 방식. "
             "일본: 재패니즈, 업계 자율 기준(2021~).")


def fig1(mobile):
    cid = "1-types"
    p = Pic(f"lrn-{cid}" + ("-m" if mobile else ""))
    if mobile:
        fig1_scotland(p, 0, 0, 314)
        fig1_usa(p, 0, 314, 290)
        fig1_ireland(p, 0, 604, 138)
        fig1_japan(p, 0, 742, 138)
        return p.svg(360, 880, cid, FIG1_TITLE, FIG1_DESC)
    fig1_scotland(p, 0, 2, 314)
    fig1_usa(p, 360, 2, 314)
    fig1_ireland(p, 0, 318, 140)
    fig1_japan(p, 360, 318, 140)
    return p.svg(720, 460, cid, FIG1_TITLE, FIG1_DESC)


# ================================================================ 그림 2: 위스키가 만들어지는 길
STAGES = [
    ("맥아 만들기", ["보리를 싹 틔워 말린다"]),
    ("당화", ["뜨거운 물에 담가 당을 뽑는다", "보리 자신의 효소로"]),
    ("발효", ["효모를 넣어 알코올을 만든다"]),
    ("증류", ["단식 증류기로 대체로 두 번", "94.8% 미만으로 증류"]),
    ("숙성", ["오크통", "스카치는 3년 이상"]),
    ("병입", ["물로 도수를 맞춘다", "40% 이상"]),
]
CS_TEXT = "캐스크 스트렝스는 물을 거의 타지 않는다"


def stage_icon(p, i, x, y, s=1.0):
    if i == 0:
        p.icon(ic_malt, x - 46, y - 10, .9 * s)
        p.icon(ic_kiln, x + 6, y - 6, .9 * s)
    elif i == 1:
        p.icon(lambda: ic_tub(GRAIN, True, False), x, y, s)
    elif i == 2:
        p.icon(lambda: ic_tub(GRAIN, False, True, True), x, y + 4, s)
    elif i == 3:
        p.icon(ic_two_stills, x - 6, y, s)
    elif i == 4:
        p.icon(ic_casks_calendar, x - 10, y, s)
    elif i == 5:
        p.icon(ic_bottle_drop, x, y, s)


def stage_texts(p, i, x, y, anchor, maxw):
    title, subs = STAGES[i]
    n = 0
    for sline in subs:
        n += p.wtext(x, y + n * 18, sline, maxw, "lrn-t", anchor)
    return n


def peat_branch(p, x, y, label_x, label_y, anchor="start"):
    """① 피트 갈래: 피트 덩이 + 회색 점선 연기."""
    p.icon(ic_peat, x, y, .9)
    p.add(f'<path class="lrn-sm" d="M{f(x - 4)},{f(y - 14)}C{f(x - 14)},{f(y - 30)} {f(x - 30)},{f(y - 26)} {f(x - 42)},{f(y - 40)}"/>')
    p.add(f'<path class="lrn-sm" d="M{f(x + 4)},{f(y - 14)}C{f(x)},{f(y - 34)} {f(x - 20)},{f(y - 34)} {f(x - 30)},{f(y - 48)}"/>')
    p.text(label_x, label_y, "피트 연기로 말리기(선택)", "lrn-t lrn-m", anchor)


FIG2_TITLE = "위스키가 만들어지는 길: 몰트위스키는 보리에서 병까지 여섯 단계를 거친다."
FIG2_DESC = ("여섯 단계가 순서대로 이어진다. 1 맥아 만들기: 보리를 싹 틔워 말린다. 갈래로 피트 연기로 말리기(선택). "
             "2 당화: 뜨거운 물에 담가 당을 뽑는다, 보리 자신의 효소로. 3 발효: 효모를 넣어 알코올을 만든다. "
             "4 증류: 단식 증류기로 대체로 두 번, 94.8% 미만으로 증류. 5 숙성: 오크통, 스카치는 3년 이상. "
             "6 병입: 물로 도수를 맞춘다, 40% 이상. 말풍선: 캐스크 스트렝스는 물을 거의 타지 않는다. "
             "액체 색은 당화·발효에서 옅은 곡물색, 증류 직후 거의 투명, 숙성 뒤 호박색이다.")


def fig2(mobile):
    cid = "2-process"
    p = Pic(f"lrn-{cid}" + ("-m" if mobile else ""))
    if not mobile:
        cw, ch = 240, 230
        pos = [(0, 0), (1, 0), (2, 0), (2, 1), (1, 1), (0, 1)]
        for i, (c, r) in enumerate(pos):
            x0, y0 = c * cw, r * ch
            p.add(f'<rect class="lrn-pn" x="{x0 + 8}" y="{y0 + 4}" width="{cw - 16}" height="{ch - 10}" rx="12"/>')
            p.num(x0 + 28, y0 + 26, i + 1)
            p.text(x0 + 46, y0 + 32, STAGES[i][0], "lrn-hd")
            cx = x0 + cw / 2
            if i == 0:
                stage_icon(p, 0, cx - 18, y0 + 96)
                peat_branch(p, x0 + 186, y0 + 124, cx, y0 + 194, "middle")
                p.text(cx, y0 + 174, STAGES[0][1][0], "lrn-t", "middle")
            elif i == 5:
                stage_icon(p, 5, x0 + 66, y0 + 112)
                bubble(p, x0 + 100, y0 + 54, 128, ["캐스크 스트렝스는", "물을 거의", "타지 않는다"], tail=(-1, 1))
                p.lines(cx, y0 + 186, STAGES[5][1], "lrn-t", "middle")
            else:
                stage_icon(p, i, cx, y0 + 104)
                stage_texts(p, i, cx, y0 + 174, "middle", cw - 30)
        # ㄹ자 화살표
        for c in range(2):
            p.arrow(f"M{(c + 1) * cw - 10},{108}H{(c + 1) * cw + 10}")
            p.arrow(f"M{(c + 1) * cw + 10},{ch + 108}H{(c + 1) * cw - 10}")
        p.arrow(f"M{2 * cw + cw / 2},{ch - 8}V{ch + 8}")
        return p.svg(720, 460, cid, FIG2_TITLE, FIG2_DESC)
    # 휴대폰: 세로로 쌓고 왼쪽 번호를 선으로 잇는다
    hs = [150, 136, 130, 136, 136, 192]
    y0 = 0
    for i, hgt in enumerate(hs):
        p.add(f'<rect class="lrn-pn" x="40" y="{y0 + 3}" width="316" height="{hgt - 8}" rx="12"/>')
        p.num(20, y0 + 22, i + 1)
        if i < 5:
            p.arrow(f"M20,{y0 + 38}V{y0 + hgt + 4}")
        p.text(54, y0 + 28, STAGES[i][0], "lrn-hd")
        if i == 0:
            stage_icon(p, 0, 112, y0 + 84, .9)
            p.wtext(186, y0 + 62, STAGES[0][1][0], 166)
            p.icon(ic_peat, 206, y0 + 112, .9)
            p.add(f'<path class="lrn-sm" d="M202,{y0 + 98}C196,{y0 + 84} 182,{y0 + 90} 166,{y0 + 76}"/>')
            p.lines(232, y0 + 108, ["피트 연기로", "말리기(선택)"], "lrn-t lrn-m")
            # 피트 라벨이 연기와 겹치지 않게 아이콘을 오른쪽 아래에
        elif i == 5:
            stage_icon(p, 5, 104, y0 + 104, 1.0)
            p.lines(186, y0 + 60, STAGES[5][1])
            bubble(p, 160, y0 + 96, 188, wrap(CS_TEXT, 172), tail=(-1, 1))
        else:
            stage_icon(p, i, 112, y0 + 82, .9)
            stage_texts(p, i, 186, y0 + 62, "start", 166)
        y0 += hgt
    return p.svg(360, 880, cid, FIG2_TITLE, FIG2_DESC)


# ================================================================ 그림 3: 통에서 보내는 시간
CASKS = [
    ("새 오크통", ["안쪽을 불로 그을림", "버번은 새 통만"], dict(char=True)),
    ("버번통", ["한 번 쓴 버번통을 다른 위스키에"], dict(tag="버번")),
    ("셰리통", ["셰리 와인을 담았던 통"], dict(tag="셰리")),
    ("피니시", ["마지막에 다른 통으로 옮겨 더 숙성"], dict(small=True)),
]
FIG3_TITLE = "통에서 보내는 시간: 어떤 통에서 얼마나 오래 두었는지가 라벨의 숫자와 낱말로 적힌다."


def fig3_desc():
    ages = ", ".join(f"{a}년" for a in CASK_AGES)
    tick = f" 시간 줄에는 {MIN_TICK}년(스카치 최소) 눈금이 있다." if MIN_TICK else ""
    return ("위 단 '어떤 통에서': 새 오크통(안쪽을 불로 그을림, 버번은 새 통만)에서 버번통(한 번 쓴 버번통을 다른 위스키에)으로 화살표, "
            "셰리통(셰리 와인을 담았던 통), 피니시(마지막에 다른 통으로 옮겨 더 숙성). 스카치는 700리터 이하 오크통. "
            f"아래 단 '얼마나 오래': 시간 줄 위에 {ages} (예시) 원액 통이 있고 모두 병 하나로 모인다.{tick} "
            f"병 라벨에는 가장 어린 {LABEL_AGE}이 강조된다. 라벨 숫자는 가장 어린 원액 기준. 숫자가 없으면 NAS(숙성년수 미표기).")


def cask_icon(p, i, x, y, s=1.0):
    opt = CASKS[i][2]
    if opt.get("small"):
        p.icon(ic_barrel, x, y, s, 84, 44)
    else:
        p.icon(ic_barrel, x, y, s, 116, 58, None, opt.get("tag"), opt.get("char", False))


def age_bars(p, x0, x1, y_axis, row_gap, small=False):
    """원액마다 0년부터 숙성년수까지 막대 + 끝에 통. 반환: [(나이, 통 오른쪽 x, 행 y)]."""
    top = max(CASK_AGES) + 1
    px = lambda a: x0 + (x1 - x0) * a / top
    p.arrow(f"M{f(x0)},{f(y_axis)}H{f(x1 + 6)}")
    for a in range(0, top + 1):
        p.add(f'<path class="lrn-l" style="stroke-opacity:.45" d="M{f(px(a))},{f(y_axis - 4)}V{f(y_axis + 4)}"/>')
    p.text(x0, y_axis + 22, "0", "lrn-t lrn-m", "middle")
    rows = sorted(CASK_AGES, reverse=True)
    n = len(rows)
    if MIN_TICK:
        p.add(f'<path class="lrn-l" style="stroke-opacity:.6;stroke-dasharray:3 4" d="M{f(px(MIN_TICK))},{f(y_axis - n * row_gap - 6)}V{f(y_axis + 5)}"/>')
        p.text(px(MIN_TICK) - (6 if small else 0), y_axis + 22, f"{MIN_TICK}년(스카치 최소)", "lrn-t lrn-m", "start" if small else "middle")
    cw, chh = (34, 20) if small else (46, 26)
    out = []
    for j, a in enumerate(rows):
        y = y_axis - (n - j) * row_gap + 4
        young = a == LABEL_AGE
        p.add(f'<rect x="{f(x0)}" y="{f(y - 5)}" width="{f(px(a) - x0)}" height="10" rx="5" '
              f'style="fill:{WHISKY};fill-opacity:{.85 if young else .4}"/>')
        p.icon(ic_barrel, px(a), y, 1, cw, chh)
        lx = px(a) + cw / 2 + 6
        p.text(lx, y + 5, f"{a}년", "lrn-hd" if young else "lrn-t", "start")
        out.append((a, lx + (34 if young else 30), y))
    return out


def fig3(mobile):
    cid = "3-cask"
    p = Pic(f"lrn-{cid}" + ("-m" if mobile else ""))
    if not mobile:
        p.add('<rect class="lrn-band" x="8" y="10" width="6" height="22" rx="3"/>')
        p.text(22, 27, "어떤 통에서", "lrn-hd")
        xs = (96, 276, 456, 630)
        for i, x in enumerate(xs):
            cask_icon(p, i, x, 84)
            p.text(x, 146, CASKS[i][0], "lrn-hd", "middle")
            n = 0
            for sl in CASKS[i][1]:
                n += p.wtext(x, 168 + n * 18, sl, 160, "lrn-t", "middle")
        p.arrow("M160,84H208")
        p.arrow("M520,84H578")
        p.note(220, 206, 280, 26, "스카치는 700리터 이하 오크통")
        p.add('<path class="lrn-l" style="stroke-opacity:.25;stroke-dasharray:4 5" d="M8,244H712"/>')
        p.add('<rect class="lrn-band" x="8" y="258" width="6" height="22" rx="3"/>')
        p.text(22, 275, "얼마나 오래", "lrn-hd")
        p.text(22, 297, "(예시)", "lrn-t lrn-m")
        rows = age_bars(p, 40, 500, 426, 38)
        bx, by = 640, 360
        for a, sx, sy in rows:
            young = a == LABEL_AGE
            p.arrow(f"M{f(sx)},{f(sy)}C{f(sx + 50)},{f(sy)} {f(bx - 70)},{f(by + 8)} {f(bx - 32)},{f(by + 8)}", accent=young)
        p.icon(lambda: ic_bottle(WHISKY, str(LABEL_AGE)), bx, by, 1.0)
        p.text(530, 280, "라벨 숫자는 가장 어린 원액 기준", "lrn-t", "middle")
        p.text(712, 452, "숫자가 없으면 NAS(숙성년수 미표기)", "lrn-t lrn-m", "end")
        return p.svg(720, 460, cid, FIG3_TITLE, fig3_desc())
    # 휴대폰
    p.add('<rect class="lrn-band" x="8" y="10" width="6" height="22" rx="3"/>')
    p.text(22, 27, "어떤 통에서", "lrn-hd")
    y = 44
    for i in range(4):
        cy = y + 44
        cask_icon(p, i, 74, cy, .85)
        p.text(150, y + 32, CASKS[i][0], "lrn-hd")
        n = 0
        for sl in CASKS[i][1]:
            n += p.wtext(150, y + 54 + n * 18, sl, 200)
        if i == 0:
            p.arrow(f"M74,{cy + 32}V{cy + 58}")
        if i == 2:
            p.arrow(f"M74,{cy + 32}V{cy + 62}")
        y += 96
    p.note(30, y + 4, 300, 26, "스카치는 700리터 이하 오크통")
    y += 46
    p.add(f'<path class="lrn-l" style="stroke-opacity:.25;stroke-dasharray:4 5" d="M8,{y}H352"/>')
    y += 14
    p.add(f'<rect class="lrn-band" x="8" y="{y}" width="6" height="22" rx="3"/>')
    p.text(22, y + 17, "얼마나 오래", "lrn-hd")
    p.text(116, y + 17, "(예시)", "lrn-t lrn-m")
    ty = y + 140
    rows = age_bars(p, 22, 280, ty, 34, small=True)
    bx, by = 110, ty + 116
    for a, sx, sy in rows:
        young = a == LABEL_AGE
        p.arrow(f"M{f(sx)},{f(sy)}C{f(348)},{f(sy)} {f(348)},{f(by - 10)} {f(bx + 34)},{f(by - 4)}", accent=young)
    p.icon(lambda: ic_bottle(WHISKY, str(LABEL_AGE)), bx, by, 1.0)
    p.lines(238, by + 2, ["라벨 숫자는", "가장 어린 원액 기준"], "lrn-t", "middle")
    p.text(180, 872, "숫자가 없으면 NAS(숙성년수 미표기)", "lrn-t lrn-m", "middle")
    return p.svg(360, 880, cid, FIG3_TITLE, fig3_desc())


# ================================================================ 출력·미리보기
FIGS = [("1-types", fig1), ("2-process", fig2), ("3-cask", fig3)]
TOKENS = """:root{--bg:#eef1ec;--surface:#f8faf6;--ink:#14201a;--muted:#56675d;--line:#d2d9d1;--accent:#1e5a43;--accent-ink:#fff}
:root[data-theme=dark]{--bg:#0f1613;--surface:#17211c;--ink:#e8eee9;--muted:#95a59b;--line:#2b3931;--accent:#74c7a3;--accent-ink:#0f1613;color-scheme:dark}
body{margin:0;padding:16px;background:var(--bg);color:var(--ink);font-family:"Noto Sans KR","Malgun Gothic",system-ui,sans-serif}
h2{font-size:18px;margin:20px 0 8px}.fig{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:12px;max-width:900px}
.fig svg{width:100%;display:block}"""


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def main():
    titles = {"1-types": "위스키 종류 한눈에", "2-process": "위스키가 만들어지는 길", "3-cask": "통에서 보내는 시간"}
    out = {}
    for cid, fn in FIGS:
        for mobile in (False, True):
            name = f"{cid}{'-m' if mobile else ''}.svg"
            svg = fn(mobile)
            write(os.path.join(OUT, name), svg)
            out[name] = svg
            print(f"  {name:18s} {len(svg.encode()) / 1024:5.1f} KB")
    d = os.path.join(ROOT, "tools", "cocktail-art")
    for theme in ("dark", "light"):
        for mob in (False, True):
            body = "".join(f'<h2>{titles[c]}</h2><div class="fig">{out[c + ("-m" if mob else "") + ".svg"]}</div>' for c, _ in FIGS)
            extra = "body{box-sizing:border-box;width:390px}.fig{padding:6px}" if mob else ""
            write(os.path.join(d, f"learn-{theme}{'-390' if mob else ''}.html"),
                  f'<!doctype html><html lang="ko" data-theme="{theme}"><meta charset="utf-8"><style>{TOKENS}{extra}</style><body>{body}</body></html>')
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
