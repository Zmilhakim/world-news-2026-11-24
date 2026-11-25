#!/usr/bin/env python3
"""One-image front page of the world news of Tuesday 24 November 2026.

Standard library only, no network, no input files: the program draws every
pixel itself (shapes, pictograms and its own stroke lettering) and writes a
1024x1024 PNG to /output/entry.png. Two runs write the same bytes.

Local run:  mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
"""
import math
import os
import struct
import zlib

W = H = 1024
buf = bytearray(W * H * 3)

# ---------------------------------------------------------------- palette
PAPER = (238, 232, 220)
WHITE = (255, 255, 255)
INK = (17, 22, 32)
GREY = (74, 81, 96)
NAVY = (15, 22, 40)
GOLD = (242, 190, 60)
RED = (214, 50, 56)
ORANGE = (255, 138, 30)
YELLOW = (255, 222, 90)
STEEL = (200, 205, 214)
SMOKE = (84, 90, 102)


# ---------------------------------------------------------------- pixels
def px(x, y, c, a=1.0):
    """Blend colour c over pixel (x, y) with coverage a."""
    if a <= 0.0 or x < 0 or y < 0 or x >= W or y >= H:
        return
    o = (y * W + x) * 3
    if a >= 1.0:
        buf[o] = c[0]
        buf[o + 1] = c[1]
        buf[o + 2] = c[2]
        return
    b = 1.0 - a
    buf[o] = int(buf[o] * b + c[0] * a + 0.5)
    buf[o + 1] = int(buf[o + 1] * b + c[1] * a + 0.5)
    buf[o + 2] = int(buf[o + 2] * b + c[2] * a + 0.5)


def rect(x0, y0, x1, y1, c):
    """Solid axis-aligned rectangle on whole pixels."""
    x0 = max(0, int(round(x0)))
    y0 = max(0, int(round(y0)))
    x1 = min(W, int(round(x1)))
    y1 = min(H, int(round(y1)))
    if x1 <= x0 or y1 <= y0:
        return
    row = bytes(c) * (x1 - x0)
    for y in range(y0, y1):
        o = (y * W + x0) * 3
        buf[o:o + len(row)] = row


def fill(x0, y0, x1, y1, dist, c, alpha=1.0):
    """Fill where the signed distance function is negative, anti-aliased."""
    for y in range(int(math.floor(y0)), int(math.ceil(y1)) + 1):
        for x in range(int(math.floor(x0)), int(math.ceil(x1)) + 1):
            a = 0.5 - dist(x + 0.5, y + 0.5)
            if a > 0.0:
                px(x, y, c, (1.0 if a > 1.0 else a) * alpha)


def circle(cx, cy, r, c, alpha=1.0):
    fill(cx - r - 1, cy - r - 1, cx + r + 1, cy + r + 1,
         lambda x, y: math.hypot(x - cx, y - cy) - r, c, alpha)


def ring(cx, cy, r, t, c, alpha=1.0):
    fill(cx - r - t, cy - r - t, cx + r + t, cy + r + t,
         lambda x, y: abs(math.hypot(x - cx, y - cy) - r) - t / 2.0, c, alpha)


def ellipse(cx, cy, rx, ry, c, alpha=1.0):
    m = min(rx, ry)
    fill(cx - rx - 1, cy - ry - 1, cx + rx + 1, cy + ry + 1,
         lambda x, y: (math.hypot((x - cx) / rx, (y - cy) / ry) - 1.0) * m, c, alpha)


def seg_dist(x, y, ax, ay, bx, by):
    """Distance from a point to the segment a-b."""
    dx = bx - ax
    dy = by - ay
    d2 = dx * dx + dy * dy
    if d2 <= 1e-12:
        return math.hypot(x - ax, y - ay)
    t = ((x - ax) * dx + (y - ay) * dy) / d2
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    return math.hypot(x - ax - t * dx, y - ay - t * dy)


def line(ax, ay, bx, by, t, c, alpha=1.0):
    """Thick line with round ends."""
    r = t / 2.0
    fill(min(ax, bx) - r - 1, min(ay, by) - r - 1, max(ax, bx) + r + 1, max(ay, by) + r + 1,
         lambda x, y: seg_dist(x, y, ax, ay, bx, by) - r, c, alpha)


def path(pts, t, c, alpha=1.0):
    for i in range(len(pts) - 1):
        line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], t, c, alpha)


def poly(pts, c, alpha=1.0):
    """Even-odd polygon fill: 4 sub-scanlines a row, exact coverage along x."""
    ys = [p[1] for p in pts]
    xs = [p[0] for p in pts]
    xmin = int(math.floor(min(xs)))
    width = int(math.floor(max(xs))) - xmin + 2
    n = len(pts)
    for y in range(max(0, int(math.floor(min(ys)))), min(H - 1, int(math.floor(max(ys)))) + 1):
        acc = [0.0] * width
        for s in range(4):
            sy = y + (s + 0.5) / 4.0
            hits = []
            for i in range(n):
                ax, ay = pts[i]
                bx, by = pts[(i + 1) % n]
                if (ay <= sy < by) or (by <= sy < ay):
                    hits.append(ax + (sy - ay) * (bx - ax) / (by - ay))
            hits.sort()
            for j in range(0, len(hits) - 1, 2):
                xa = hits[j] - xmin
                xb = hits[j + 1] - xmin
                ia = int(xa)
                ib = int(xb)
                if ia == ib:
                    acc[ia] += (xb - xa) * 0.25
                else:
                    acc[ia] += (ia + 1 - xa) * 0.25
                    for k in range(ia + 1, ib):
                        acc[k] += 0.25
                    acc[ib] += (xb - ib) * 0.25
        for i in range(width):
            a = acc[i]
            if a > 0.0:
                px(xmin + i, y, c, (1.0 if a > 1.0 else a) * alpha)


def chaikin(pts, closed, rounds=3):
    """Corner cutting: turns a control polygon into a smooth curve."""
    for _ in range(rounds):
        out = []
        m = len(pts)
        last = m if closed else m - 1
        for i in range(last):
            a = pts[i]
            b = pts[(i + 1) % m]
            q = (a[0] * 0.75 + b[0] * 0.25, a[1] * 0.75 + b[1] * 0.25)
            r = (a[0] * 0.25 + b[0] * 0.75, a[1] * 0.25 + b[1] * 0.75)
            if closed:
                out.append(q)
                out.append(r)
            else:
                out.append(a if i == 0 else q)
                out.append(b if i == last - 1 else r)
        pts = out
    return pts


# ---------------------------------------------------------------- lettering
# A stroke alphabet drawn for this entry. Each glyph sits on a grid 6 units
# tall (y = 0 is the cap line, y = 6 the baseline) and is a list of strokes:
# L = straight polyline, S = smoothed open curve, O = smoothed closed curve.
FONT = {
    'A': (4, ['L 0,6 2,0 4,6', 'L 0.67,4 3.33,4']),
    'B': (4, ['L 0,0 0,6', 'S 0,0 3.6,0 3.6,3 0,3', 'S 0,3 4,3 4,6 0,6']),
    'C': (4, ['S 4,1.3 4,0 0,0 0,6 4,6 4,4.7']),
    'D': (4, ['L 0,0 0,6', 'S 0,0 4,0 4,6 0,6']),
    'E': (3.4, ['L 3.4,0 0,0 0,6 3.4,6', 'L 0,3 2.9,3']),
    'F': (3.4, ['L 3.4,0 0,0 0,6', 'L 0,3 2.9,3']),
    'G': (4, ['S 4,1.3 4,0 0,0 0,6 4,6 4,3.2', 'L 4,3.2 2.3,3.2']),
    'H': (4, ['L 0,0 0,6', 'L 4,0 4,6', 'L 0,3 4,3']),
    'I': (0, ['L 0,0 0,6']),
    'J': (3, ['S 3,0 3,6 0,6 0,4.4']),
    'K': (4, ['L 0,0 0,6', 'L 4,0 0,3.5', 'L 1.4,2.5 4,6']),
    'L': (3.3, ['L 0,0 0,6 3.3,6']),
    'M': (5, ['L 0,6 0,0 2.5,4 5,0 5,6']),
    'N': (4, ['L 0,6 0,0 4,6 4,0']),
    'O': (4, ['O 0,0 4,0 4,6 0,6']),
    'P': (4, ['L 0,0 0,6', 'S 0,0 4,0 4,3.4 0,3.4']),
    'Q': (4, ['O 0,0 4,0 4,6 0,6', 'L 2.5,4.3 4.2,6.4']),
    'R': (4, ['L 0,0 0,6', 'S 0,0 4,0 4,3.4 0,3.4', 'L 1.9,3.4 4,6']),
    'S': (4, ['S 4,1.1 4,0 0,0 0,3 4,3 4,6 0,6 0,4.9']),
    'T': (4, ['L 0,0 4,0', 'L 2,0 2,6']),
    'U': (4, ['S 0,0 0,6 4,6 4,0']),
    'V': (4, ['L 0,0 2,6 4,0']),
    'W': (5.6, ['L 0,0 1.4,6 2.8,1.6 4.2,6 5.6,0']),
    'X': (4, ['L 0,0 4,6', 'L 4,0 0,6']),
    'Y': (4, ['L 0,0 2,3 4,0', 'L 2,3 2,6']),
    'Z': (4, ['L 0,0 4,0 0,6 4,6']),
    '0': (3.6, ['O 0,0 3.6,0 3.6,6 0,6']),
    '1': (1.8, ['L 0,1.5 1.8,0 1.8,6']),
    '2': (3.6, ['S 0,1.3 0,0 3.6,0 3.6,2.9 0,6', 'L 0,6 3.6,6']),
    '3': (3.6, ['S 0,0.9 0,0 3.6,0 3.6,3 1.4,3', 'S 1.4,3 3.6,3 3.6,6 0,6 0,5.1']),
    '4': (3.8, ['L 2.8,6 2.8,0 0,4.2 3.8,4.2']),
    '5': (3.6, ['L 3.4,0 0.3,0 0,2.7', 'S 0,2.7 3.6,2.1 3.6,6 0,6 0,4.9']),
    '6': (3.6, ['S 3.2,0 0,0 0,6 3.6,6 3.6,2.8 0,2.8']),
    '7': (3.6, ['L 0,0 3.6,0 1.2,6']),
    '8': (3.6, ['O 0.3,0 3.3,0 3.3,2.9 0.3,2.9', 'O 0,2.9 3.6,2.9 3.6,6 0,6']),
    '9': (3.6, ['S 0.4,6 3.6,6 3.6,0 0,0 0,3.2 3.6,3.2']),
    '.': (0, ['L 0,6 0,6']),
    ',': (0.4, ['L 0.4,5.8 0,7']),
    ':': (0, ['L 0,2.2 0,2.2', 'L 0,6 0,6']),
    "'": (0, ['L 0,0 0,1.5']),
    '-': (2.2, ['L 0,3.3 2.2,3.3']),
    '/': (3, ['L 3,0 0,6']),
    '$': (3.6, ['S 3.6,1.1 3.6,0 0,0 0,3 3.6,3 3.6,6 0,6 0,4.9', 'L 1.8,-0.8 1.8,6.8']),
    '%': (4.2, ['L 3.9,0 0.3,6', 'O 0,0 1.7,0 1.7,2.3 0,2.3', 'O 2.5,3.7 4.2,3.7 4.2,6 2.5,6']),
    '*': (1.2, ['L 0.6,3 0.6,3']),
}
XR = 0.128      # width of one grid unit, as a share of the cap height
GAP = 0.105     # space between letters, as a share of the cap height
_glyphs = {}


def glyph(ch, cap, wt):
    """Coverage mask of one letter: (rows, padding, advance)."""
    key = (ch, cap, wt)
    if key in _glyphs:
        return _glyphs[key]
    gw, strokes = FONT[ch]
    ux = cap * XR
    uy = cap / 6.0
    r = wt * cap / 2.0
    if ch in '.:*':
        r *= 1.25
    pad = int(math.ceil(r)) + 2
    mw = int(math.ceil(gw * ux)) + 2 * pad
    mh = int(math.ceil(cap * 1.2)) + 2 * pad
    rows = [[0.0] * mw for _ in range(mh)]
    for st in strokes:
        kind = st[0]
        pts = [tuple(float(v) for v in p.split(',')) for p in st[2:].split(' ')]
        if kind != 'L':
            pts = chaikin(pts, kind == 'O')
            if kind == 'O':
                pts.append(pts[0])
        pts = [(pad + p[0] * ux, pad + p[1] * uy) for p in pts]
        for i in range(len(pts) - 1):
            ax, ay = pts[i]
            bx, by = pts[i + 1]
            for y in range(max(0, int(min(ay, by) - r - 1)), min(mh, int(max(ay, by) + r + 2))):
                row = rows[y]
                for x in range(max(0, int(min(ax, bx) - r - 1)), min(mw, int(max(ax, bx) + r + 2))):
                    a = r + 0.5 - seg_dist(x + 0.5, y + 0.5, ax, ay, bx, by)
                    if a > row[x]:
                        row[x] = 1.0 if a > 1.0 else a
    out = (rows, pad, gw * ux + 2.0 * r + cap * GAP)
    _glyphs[key] = out
    return out


def text_width(s, cap, wt, track=0.0):
    w = 0.0
    for ch in s:
        w += (cap * 0.34 if ch == ' ' else glyph(ch, cap, wt)[2]) + track
    return w - track - cap * GAP


def text(x, y, s, cap, c, wt=0.15, track=0.0):
    """Draw s with the top of its capitals at y and its left edge at x."""
    r = wt * cap / 2.0
    cx = float(x)
    for ch in s:
        if ch == ' ':
            cx += cap * 0.34 + track
            continue
        rows, pad, adv = glyph(ch, cap, wt)
        ox = int(round(cx + r)) - pad
        oy = int(round(y + r)) - pad
        for j, row in enumerate(rows):
            for i, a in enumerate(row):
                if a > 0.0:
                    px(ox + i, oy + j, c, a)
        cx += adv + track
    return cx


def text_center(xc, y, s, cap, c, wt=0.15, track=0.0):
    text(xc - text_width(s, cap, wt, track) / 2.0, y, s, cap, c, wt, track)


def wrap(s, cap, wt, maxw):
    lines = []
    cur = ''
    for word in s.split(' '):
        trial = cur + ' ' + word if cur else word
        if not cur or text_width(trial, cap, wt) <= maxw:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    lines.append(cur)
    return lines


# ---------------------------------------------------------------- pictograms
def flame(cx, base, w, h):
    poly([(cx - w, base), (cx - w * 0.55, base - h * 0.55), (cx - w * 0.2, base - h * 0.35),
          (cx + w * 0.1, base - h), (cx + w * 0.6, base - h * 0.45), (cx + w, base)], ORANGE)
    poly([(cx - w * 0.5, base), (cx - w * 0.1, base - h * 0.5), (cx + w * 0.2, base - h * 0.3),
          (cx + w * 0.5, base)], YELLOW)


def icon_space(x, y, w, h, bg):
    for sx, sy, r in [(20, 26, 1.8), (118, 20, 1.5), (122, 96, 2.0), (22, 112, 1.4),
                      (112, 168, 1.5), (16, 178, 1.8), (70, 14, 1.3), (30, 208, 1.3)]:
        circle(x + sx, y + sy, r, WHITE)
    circle(x + 30, y + 62, 14, (236, 240, 222))        # crescent moon
    circle(x + 36, y + 57, 12.5, bg)
    cx = x + w / 2.0 + 8
    top = y + 42
    poly([(cx - 13, top + 118), (cx + 13, top + 118), (cx, top + 176)], ORANGE)
    poly([(cx - 7, top + 118), (cx + 7, top + 118), (cx, top + 150)], YELLOW)
    poly([(cx - 17, top + 76), (cx - 38, top + 124), (cx - 17, top + 112)], RED)
    poly([(cx + 17, top + 76), (cx + 38, top + 124), (cx + 17, top + 112)], RED)
    body = [(cx, top), (cx + 9, top + 14), (cx + 16, top + 36), (cx + 18, top + 60), (cx + 18, top + 118),
            (cx - 18, top + 118), (cx - 18, top + 60), (cx - 16, top + 36), (cx - 9, top + 14)]
    poly(body, (240, 243, 248))
    poly([(cx, top), (cx + 9, top + 14), (cx + 14, top + 28), (cx - 14, top + 28), (cx - 9, top + 14)], RED)
    circle(cx, top + 56, 10, (30, 44, 80))
    circle(cx, top + 56, 7, (96, 170, 235))
    rect(cx - 18, top + 98, cx + 18, top + 104, RED)


def icon_tanker(x, y, w, h, bg):
    rect(x, y + 160, x + w, y + h, (16, 96, 136))       # sea
    for sx, sy, r in [(66, 100, 15), (78, 76, 18), (60, 50, 21), (84, 26, 17)]:
        circle(x + sx, y + sy, r, SMOKE)
    flame(x + 66, y + 134, 22, 50)
    poly([(x + 6, y + 132), (x + 134, y + 132), (x + 126, y + 168), (x + 20, y + 168)], (26, 28, 34))
    poly([(x + 15, y + 156), (x + 129, y + 156), (x + 126, y + 168), (x + 20, y + 168)], RED)
    rect(x + 100, y + 104, x + 126, y + 132, (240, 243, 248))
    rect(x + 104, y + 110, x + 122, y + 116, (26, 28, 34))
    rect(x + 110, y + 92, x + 116, y + 104, (240, 243, 248))
    for k in range(3):                                  # waves
        line(x + 14 + k * 44, y + 178, x + 34 + k * 44, y + 178, 3, (150, 205, 230))
    mx = x + 38
    my = y + 208
    line(mx, my, mx, y + h, 2.5, (10, 40, 60))          # mooring chain
    for k in range(8):                                  # the mine's horns
        ang = k * math.pi / 4.0
        line(mx, my, mx + 17 * math.cos(ang), my + 17 * math.sin(ang), 4, (12, 14, 18))
    circle(mx, my, 11.5, (12, 14, 18))
    circle(mx - 3.5, my - 3.5, 2.5, (110, 118, 130))


def icon_refinery(x, y, w, h, bg):
    rect(x, y + 204, x + w, y + h, (20, 22, 30))        # ground
    for sx, sy, r in [(46, 72, 18), (60, 48, 22), (42, 24, 19), (104, 62, 14), (112, 40, 16)]:
        circle(x + sx, y + sy, r, SMOKE)
    flame(x + 44, y + 100, 15, 40)
    flame(x + 106, y + 92, 9, 24)
    rect(x + 32, y + 100, x + 56, y + 204, STEEL)       # distillation column
    for k in range(4):
        rect(x + 32, y + 116 + k * 22, x + 56, y + 120 + k * 22, (120, 126, 140))
    rect(x + 102, y + 92, x + 110, y + 160, STEEL)      # flare stack
    rect(x + 70, y + 156, x + 128, y + 204, (168, 174, 188))   # storage tank
    ellipse(x + 99, y + 156, 29, 7, (214, 219, 228))
    rect(x + 56, y + 180, x + 70, y + 185, (120, 126, 140))    # pipe
    dx = x + 100                                        # the drone
    dy = y + 16
    line(dx - 12, dy - 6, dx + 12, dy + 6, 2.5, WHITE)
    line(dx - 12, dy + 6, dx + 12, dy - 6, 2.5, WHITE)
    for ox, oy in [(-12, -6), (12, 6), (-12, 6), (12, -6)]:
        ellipse(dx + ox, dy + oy, 7, 2.2, WHITE)
    circle(dx, dy, 3.5, WHITE)


def icon_trade(x, y, w, h, bg):
    boxes = [((214, 69, 65), (150, 40, 40)), ((45, 125, 210), (26, 82, 150)), ((240, 170, 40), (178, 118, 16))]
    for i, (c, dark) in enumerate(boxes):
        yy = y + 210 - (i + 1) * 40
        rect(x + 14, yy, x + 126, yy + 36, c)
        for k in range(8):
            rect(x + 22 + k * 13, yy + 6, x + 26 + k * 13, yy + 30, dark)
    rect(x + 6, y + 210, x + w - 6, y + 216, (10, 44, 36))
    text(x + 18, y + 26, '%', 46, WHITE, 0.17)
    ax = x + 104                                        # rising arrow
    poly([(ax, y + 20), (ax + 22, y + 48), (ax + 8, y + 48), (ax + 8, y + 76),
          (ax - 8, y + 76), (ax - 8, y + 48), (ax - 22, y + 48)], GOLD)


def icon_ribbon(x, y, w, h, bg):
    cx = x + w / 2.0
    ctrl = [(cx - 34, y + 176), (cx + 30, y + 92), (cx + 30, y + 30), (cx - 30, y + 30),
            (cx - 30, y + 92), (cx + 34, y + 176)]
    curve = chaikin(ctrl, False, 4)
    half = len(curve) // 2
    path(curve[half - 1:], 19, (176, 28, 48))           # the strand behind
    path(curve[:half], 19, (236, 56, 78))               # the strand in front
    base = y + 218                                      # a falling line: deaths down
    path([(x + 20, base - 22), (x + 52, base - 16), (x + 84, base - 8), (x + 116, base - 2)], 3.5, WHITE)
    for px_, py_ in [(20, 22), (52, 16), (84, 8), (116, 2)]:
        circle(x + px_, base - py_, 4.5, WHITE)


def icon_cup(x, y, w, h, bg):
    cx = x + w / 2.0
    ring(cx, y + 190, 46, 3, WHITE, 0.22)               # pitch markings
    rect(x, y + 189, x + w, y + 192, (62, 150, 96))
    gold = (244, 196, 48)
    dark = (190, 140, 20)
    ring(cx - 28, y + 58, 14, 6, gold)                  # handles
    ring(cx + 28, y + 58, 14, 6, gold)
    poly([(cx - 30, y + 30), (cx + 30, y + 30), (cx + 24, y + 74), (cx + 10, y + 96),
          (cx - 10, y + 96), (cx - 24, y + 74)], gold)
    rect(cx - 30, y + 26, cx + 30, y + 34, dark)
    rect(cx - 5, y + 96, cx + 5, y + 118, gold)
    rect(cx - 20, y + 118, cx + 20, y + 128, gold)
    rect(cx - 27, y + 128, cx + 27, y + 138, dark)
    bx = cx                                             # the ball
    by = y + 186
    circle(bx, by, 27, WHITE)
    pent = [(bx + 10 * math.sin(k * 2 * math.pi / 5), by - 10 * math.cos(k * 2 * math.pi / 5)) for k in range(5)]
    poly(pent, INK)
    for k in range(5):
        ang = k * 2 * math.pi / 5
        line(bx + 10 * math.sin(ang), by - 10 * math.cos(ang),
             bx + 25 * math.sin(ang), by - 25 * math.cos(ang), 3, INK)
    ring(bx, by, 27, 2.5, INK)


def icon_chip(x, y, w, h, bg):
    cx = x + w / 2.0
    cy = y + 104
    pin = (226, 232, 240)
    for k in range(5):                                  # pins on all four sides
        o = -32 + k * 16
        rect(cx + o - 3, cy - 58, cx + o + 3, cy - 40, pin)
        rect(cx + o - 3, cy + 40, cx + o + 3, cy + 58, pin)
        rect(cx - 58, cy + o - 3, cx - 40, cy + o + 3, pin)
        rect(cx + 40, cy + o - 3, cx + 58, cy + o + 3, pin)
    rect(cx - 42, cy - 42, cx + 42, cy + 42, (24, 30, 38))
    rect(cx - 26, cy - 26, cx + 26, cy + 26, (118, 200, 60))
    rect(cx - 14, cy - 14, cx + 14, cy + 14, (24, 30, 38))
    ax = x + 30                                         # a curved arrow: the return
    ay = y + 196
    path(chaikin([(ax + 80, ay - 16), (ax + 80, ay + 14), (ax + 10, ay + 14), (ax + 10, ay - 6)], False), 6, GOLD)
    poly([(ax - 4, ay - 4), (ax + 24, ay - 4), (ax + 10, ay - 26)], GOLD)


def icon_islands(x, y, w, h, bg):
    rect(x, y + 150, x + w, y + h, (12, 52, 96))        # deeper water
    circle(x + 104, y + 44, 17, YELLOW)                 # sun
    for k in range(3):
        line(x + 12 + k * 46, y + 176 + (k % 2) * 22, x + 32 + k * 46, y + 176 + (k % 2) * 22, 3, (150, 205, 230))
    ellipse(x + 50, y + 152, 42, 13, (232, 206, 140))   # sand
    ellipse(x + 112, y + 158, 20, 7, (232, 206, 140))
    trunk = chaikin([(x + 50, y + 148), (x + 46, y + 116), (x + 56, y + 84)], False)
    path(trunk, 6, (120, 78, 40))
    leaf = (44, 160, 84)
    for dx, dy in [(-34, 6), (-26, -20), (0, -30), (26, -18), (34, 8)]:
        path(chaikin([(x + 56, y + 84), (x + 56 + dx * 0.6, y + 80 + dy), (x + 56 + dx, y + 92 + dy)], False), 7, leaf)
    rect(x + 30, y + 196, x + 110, y + 228, WHITE)      # the treaty paper
    for k in range(3):
        rect(x + 38, y + 203 + k * 7, x + 86, y + 206 + k * 7, (150, 158, 172))
    circle(x + 98, y + 216, 6, RED)


def icon_factory(x, y, w, h, bg):
    rect(x, y + 204, x + w, y + h, (26, 12, 26))        # ground
    for sx, sy, r in [(52, 70, 18), (66, 46, 22), (48, 22, 19), (98, 58, 15)]:
        circle(x + sx, y + sy, r, SMOKE)
    flame(x + 52, y + 122, 20, 46)
    flame(x + 96, y + 120, 12, 30)
    wall = (188, 194, 206)
    poly([(x + 14, y + 204), (x + 14, y + 132), (x + 48, y + 112), (x + 48, y + 132), (x + 82, y + 112),
          (x + 82, y + 132), (x + 126, y + 112), (x + 126, y + 204)], wall)     # saw-tooth roof
    for k in range(3):
        rect(x + 24 + k * 34, y + 148, x + 44 + k * 34, y + 166, ORANGE)        # lit windows
    rect(x + 58, y + 176, x + 82, y + 204, (30, 150, 84))                       # the exit door
    line(x + 64, y + 190, x + 76, y + 190, 3, WHITE)
    poly([(x + 74, y + 184), (x + 80, y + 190), (x + 74, y + 196)], WHITE)


def icon_border(x, y, w, h, bg):
    rect(x, y + 186, x + w, y + h, (28, 30, 40))        # road
    for k in range(3):
        rect(x + w / 2.0 - 3, y + 194 + k * 16, x + w / 2.0 + 3, y + 204 + k * 16, GOLD)
    rect(x + 16, y + 96, x + 30, y + 186, STEEL)        # barrier post
    for k in range(6):                                  # striped barrier arm
        rect(x + 30 + k * 16, y + 108, x + 46 + k * 16, y + 122, RED if k % 2 == 0 else WHITE)
    cx = x + 86                                         # no-entry sign
    cy = y + 48
    circle(cx, cy, 28, RED)
    rect(cx - 18, cy - 5, cx + 18, cy + 5, WHITE)
    rect(cx - 3, cy + 28, cx + 3, y + 108, STEEL)
    for k in range(5):                                  # fence beyond the barrier
        line(x + 12 + k * 29, y + 150, x + 12 + k * 29, y + 186, 3, (120, 126, 140))
    line(x + 6, y + 160, x + w - 6, y + 160, 3, (120, 126, 140))


# ---------------------------------------------------------------- the page
PW, PH, TW = 482, 236, 140      # panel width, panel height, pictogram tile width

STORIES = [
    ('AFRICA * SPORT', (22, 128, 66), (23, 107, 58), icon_cup,
     'COURT GIVES AFRICA CUP TITLE BACK TO SENEGAL',
     "CAS OVERTURNS MOROCCO'S 3-0 FORFEIT WIN, MOROCCO PROTESTS"),
    ('MIDDLE EAST', (196, 46, 40), (12, 58, 88), icon_tanker,
     'IRAN SAYS THREE OIL TANKERS HIT MINES IN STRAIT OF HORMUZ',
     'THE CLAIM BY ITS GUARD NAVY IS NOT INDEPENDENTLY CONFIRMED'),
    ('EUROPE * SECURITY', (176, 100, 12), (42, 45, 58), icon_border,
     "RUSSIA SAYS ESTONIA IS 'ON THE VERGE' OF OPEN WAR",
     'ESTONIA WILL SHUT ITS ROAD BORDER POSTS FROM 1 DECEMBER'),
    ('TECH * BUSINESS', (14, 120, 96), (15, 91, 74), icon_chip,
     'NVIDIA BRINGS JENSEN HUANG BACK AS CHIEF EXECUTIVE',
     'BOARD INQUIRY GOES ON, AN SEC PROBE IS REPORTED'),
    ('PACIFIC * DIPLOMACY', (40, 76, 190), (16, 70, 120), icon_islands,
     'SOLOMON ISLANDS DROPS ITS SECURITY PACT WITH CHINA',
     'IT TURNS TO A NEW SECURITY TREATY WITH AUSTRALIA'),
    ('ASIA * DISASTER', (190, 36, 72), (58, 16, 48), icon_factory,
     'INDONESIA FACTORY FIRE: DEATH TOLL RISES TO 24',
     'RESCUERS: MOST DIED TRYING TO REACH AN EMERGENCY EXIT'),
]


def panel(x, y, story):
    tag, accent, tile, icon, head, sub = story
    rect(x, y, x + PW, y + PH, WHITE)
    rect(x, y, x + TW, y + PH, tile)
    icon(x, y, TW, PH, tile)
    rect(x + TW, y, x + PW, y + 5, accent)
    tx = x + TW + 16
    maxw = PW - TW - 30
    ty = y + 22
    text(tx, ty, tag, 12, accent, 0.18, 0.6)
    ty += 30
    for ln in wrap(head, 24, 0.16, maxw):
        text(tx, ty, ln, 24, INK, 0.16)
        ty += 34
    ty += 2
    rect(tx, ty, tx + 44, ty + 3, accent)
    ty += 13
    for ln in wrap(sub, 13, 0.15, maxw):      # one supporting fact under each headline
        text(tx, ty, ln, 13, GREY, 0.15)
        ty += 21


def draw():
    rect(0, 0, W, H, PAPER)
    # masthead: the day this image sums up
    rect(0, 0, W, 172, NAVY)
    text(28, 24, 'TUESDAY', 20, GOLD, 0.17, 1.5)
    label = 'WORLD NEWS IN ONE IMAGE'
    text(W - 28 - text_width(label, 20, 0.17, 1.5), 24, label, 20, GOLD, 0.17, 1.5)
    text_center(W / 2.0, 64, '24 NOVEMBER 2026', 84, WHITE, 0.15)
    rect(0, 172, W, 178, GOLD)
    # six stories
    for i, story in enumerate(STORIES):
        panel(24 + (i % 2) * (PW + 12), 192 + (i // 2) * (PH + 12), story)
    # also today
    rect(24, 936, W - 24, 1000, NAVY)
    end = text(44, 959, 'ALSO', 18, GOLD, 0.18, 1.0)
    text(end + 16, 960, 'POLICE PROBE THE INDONESIA BLAZE  *  CAF SAYS IT WILL APPLY THE CUP RULING', 17, WHITE, 0.16)


def write_png(path_):
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw += buf[y * W * 3:(y + 1) * W * 3]

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF)

    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(bytes(raw), 9)) + chunk(b'IEND', b''))
    with open(path_, 'wb') as f:
        f.write(png)


if __name__ == '__main__':
    draw()
    write_png(os.path.join(os.environ.get('MAKEFUN_OUTPUT_DIR', '/output'), 'entry.png'))
