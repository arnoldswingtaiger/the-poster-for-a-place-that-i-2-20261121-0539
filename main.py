#!/usr/bin/env python3
"""Velmora, the Floating Isles -- a poster for a place that is not there.

A small program that paints a 1024 by 1024 travel poster and saves it as
``entry.png``: a lighthouse on a drifting island above a sea of clouds at
golden hour, the invented name VELMORA set big across the evening sky.

Everything is drawn by hand in this one file with the Python standard
library only -- the picture surface, the letter shapes and the PNG writer
are all in here, so the program runs in a bare sandbox with no network and
no third-party packages. Nothing is read from disk and nothing depends on
the clock, so running it twice writes the same bytes twice.

Run it with ``python3 main.py``; the poster lands in ``/output/entry.png``,
or in ``$MAKEFUN_OUTPUT_DIR/entry.png`` when that variable is set.
"""

import math, os, struct, zlib

W = 1024
H = 1024

# --- the poster's colours -------------------------------------------------
DUSK = (16, 12, 40)
PAPER = (255, 244, 214)
GILT = (255, 231, 192)
DISC = (255, 222, 148)
RIM = (255, 203, 118)
HALO = (255, 188, 118)
CLIFF = (74, 56, 82)
CLIFF_LT = (96, 74, 100)
CLIFF_DK = (54, 42, 64)
TURF = (50, 102, 72)
TURF_LT = (72, 136, 90)
TURF_DK = (38, 82, 58)
CHALK = (247, 243, 230)
CRIMSON = (194, 58, 50)
LANTERN = (255, 219, 128)
GLOW = (255, 224, 148)
STREAM = (212, 230, 242)
PUFF1 = (252, 231, 197)
PUFF2 = (250, 223, 201)
PUFF3 = (246, 211, 183)
PUFF4 = (238, 197, 177)
PUFF5 = (252, 237, 206)

# --- the evening sky, as stops along the way down -------------------------
SKY_T = (0.0, 0.24, 0.42, 0.56, 0.67, 0.75, 0.81, 1.0)
SKY_C = (
    (12, 19, 56),
    (36, 42, 102),
    (92, 60, 126),
    (184, 90, 110),
    (238, 148, 94),
    (250, 203, 136),
    (248, 222, 176),
    (236, 194, 170),
)

# --- letter shapes: five bits wide, seven rows tall -----------------------
# Each glyph is seven integers; bit 4 is the leftmost pixel of the row.
# Only the characters the poster prints are drawn here.
GLYPHS = {
    " ": (0, 0, 0, 0, 0, 0, 0),
    "A": (0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    "B": (0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110),
    "C": (0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110),
    "D": (0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11110),
    "E": (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111),
    "F": (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000),
    "G": (0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01110),
    "H": (0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    "I": (0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    "J": (0b00111, 0b00010, 0b00010, 0b00010, 0b00010, 0b10010, 0b01100),
    "K": (0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001),
    "L": (0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111),
    "M": (0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001),
    "N": (0b10001, 0b11001, 0b11001, 0b10101, 0b10011, 0b10011, 0b10001),
    "O": (0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "P": (0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000),
    "Q": (0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101),
    "R": (0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001),
    "S": (0b01111, 0b10000, 0b10000, 0b01110, 0b00001, 0b00001, 0b11110),
    "T": (0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100),
    "U": (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "V": (0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b01010, 0b00100),
    "W": (0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b11011, 0b10001),
    "X": (0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001),
    "Y": (0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100),
    "Z": (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111),
    "-": (0, 0, 0, 0b11111, 0, 0, 0),
    ".": (0, 0, 0, 0, 0, 0b01100, 0b01100),
}


def word_w(text, scale):
    """How wide `text` comes out at `scale` (six units a character)."""
    return len(text) * 6 * scale - scale if text else 0


# --- the picture surface --------------------------------------------------
# One flat bytearray, three bytes a pixel, row after row. Everything the
# poster needs -- runs, boxes, discs, polygons, lines, letters -- is a
# small method on this class, and nothing else in the file touches pixels.


def blend(a, b, t):
    """The colour `t` of the way from `a` to `b` (0 is all `a`)."""
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


class Pic:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    def hspan(self, y, x0, x1, rgb, a=255):
        """Paint one horizontal run; blend it in when `a` is under 255."""
        if y < 0 or y >= self.h:
            return
        x0 = max(0, x0)
        x1 = min(self.w - 1, x1)
        if x1 < x0:
            return
        base = (y * self.w + x0) * 3
        n = x1 - x0 + 1
        if a >= 255:
            self.px[base:base + n * 3] = bytes(rgb) * n
            return
        if a <= 0:
            return
        r, g, b = rgb
        inv = 255 - a
        for k in range(n):
            i = base + k * 3
            self.px[i] = (r * a + self.px[i] * inv) // 255
            self.px[i + 1] = (g * a + self.px[i + 1] * inv) // 255
            self.px[i + 2] = (b * a + self.px[i + 2] * inv) // 255

    def box(self, x, y, w, h, rgb, a=255):
        for yy in range(y, y + h):
            self.hspan(yy, x, x + w - 1, rgb, a)

    def grad(self):
        """Wash the whole surface with the sky, top to bottom."""
        for y in range(self.h):
            t = y / (self.h - 1)
            rgb = SKY_C[-1]
            for i in range(len(SKY_T) - 1):
                lo, hi = SKY_T[i], SKY_T[i + 1]
                if lo <= t <= hi:
                    f = 0.0 if hi == lo else (t - lo) / (hi - lo)
                    rgb = blend(SKY_C[i], SKY_C[i + 1], f)
                    break
            base = y * self.w * 3
            self.px[base:base + self.w * 3] = bytes(rgb) * self.w

    def oval(self, cx, cy, rx, ry, rgb, a=255):
        top = max(0, cy - ry)
        bot = min(self.h - 1, cy + ry)
        for y in range(top, bot + 1):
            dy = (y - cy) / ry
            dx = rx * math.sqrt(max(0.0, 1.0 - dy * dy))
            self.hspan(y, int(math.ceil(cx - dx)), int(math.floor(cx + dx)), rgb, a)

    def disc(self, cx, cy, r, rgb, a=255):
        self.oval(cx, cy, r, r, rgb, a)

    def poly(self, pts, rgb, a=255):
        """Fill a polygon by sweeping its edges down the rows."""
        ys = [p[1] for p in pts]
        y0 = max(0, min(ys))
        y1 = min(self.h - 1, max(ys))
        for y in range(y0, y1 + 1):
            xs = []
            for i, (x0, yy0) in enumerate(pts):
                x1, yy1 = pts[(i + 1) % len(pts)]
                if (yy0 <= y < yy1) or (yy1 <= y < yy0):
                    xs.append(x0 + (y - yy0) / (yy1 - yy0) * (x1 - x0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.hspan(y, int(math.ceil(xs[i])), int(math.floor(xs[i + 1])), rgb, a)

    def seg(self, x0, y0, x1, y1, rgb, a=255, w=1):
        """A line, walked along whichever axis is longer."""
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        half = w // 2
        for i in range(steps + 1):
            t = i / steps
            x = round(x0 + (x1 - x0) * t)
            y = round(y0 + (y1 - y0) * t)
            self.box(x - half, y - half, w, w, rgb, a)

    def word(self, s, x, y, scale, rgb, a=255):
        """Set one line of text from the bitmap glyphs."""
        cx = x
        for ch in s:
            rows = GLYPHS.get(ch, GLYPHS[" "])
            for gy, bits in enumerate(rows):
                for gx in range(5):
                    if bits >> (4 - gx) & 1:
                        self.box(cx + gx * scale, y + gy * scale, scale, scale, rgb, a)
            cx += 6 * scale


# --- the scene ------------------------------------------------------------
# Painted back to front: sky, stars, sun, thin clouds, the far cloud sea,
# the isles, the near cloud sea, birds, the name, the frame.


def _next_seed(seed):
    while True:
        seed = (1664525 * seed + 1013904223) & 0xFFFFFFFF
        yield seed


def paint_stars(pic):
    """A few early stars up high, placed by a fixed seed."""
    gen = _next_seed(777)
    for _ in range(52):
        x = 16 + next(gen) % (W - 32)
        y = 16 + next(gen) % 416
        r = 1 + next(gen) % 2
        a = 50 + next(gen) % 110
        pic.disc(x, y, r, (255, 244, 224), a)


def paint_sun(pic):
    """The sun going down between the isles, into the cloud sea."""
    cx, cy = 352, 692
    for r in range(272, 88, -9):
        pic.disc(cx, cy, r, HALO, 6)
    for r in range(148, 86, -8):
        pic.disc(cx, cy, r, HALO, 10)
    pic.disc(cx, cy, 79, RIM)
    pic.disc(cx, cy, 74, DISC)
    pic.disc(cx - 18, cy - 20, 46, (255, 247, 218))


def paint_wisps(pic):
    """Two thin evening clouds drifting past the sun."""
    pic.oval(222, 650, 118, 12, (250, 200, 160), 110)
    pic.oval(242, 640, 74, 10, (252, 214, 176), 110)
    pic.oval(552, 622, 138, 12, (248, 192, 158), 100)
    pic.oval(528, 612, 86, 9, (250, 208, 172), 100)


def paint_cloudsea_back(pic):
    """The far edge of the cloud sea, behind the islands."""
    pic.oval(168, 732, 328, 58, PUFF3, 255)
    pic.oval(556, 764, 398, 64, PUFF2, 255)
    pic.oval(898, 738, 328, 56, PUFF3, 255)
    pic.oval(358, 802, 358, 60, PUFF1, 255)
    pic.oval(758, 808, 358, 58, PUFF2, 255)


def paint_isle_far(pic):
    """A small hazy isle far off to the left."""
    pic.poly([(88, 548), (328, 548), (294, 602), (246, 642), (212, 656),
              (178, 642), (126, 602)], (104, 82, 108))
    pic.oval(210, 545, 108, 30, (86, 118, 96))
    pic.oval(210, 537, 98, 22, (104, 138, 110))
    pic.seg(248, 602, 246, 708, STREAM, 120, 3)
    pic.seg(258, 606, 258, 692, STREAM, 90, 2)


def paint_isle_high(pic):
    """A tiny isle adrift high on the right."""
    pic.poly([(796, 472), (936, 472), (916, 510), (884, 538), (866, 546),
              (848, 538), (816, 510)], (110, 88, 116))
    pic.oval(866, 468, 68, 20, (96, 126, 104))
    pic.oval(866, 462, 60, 15, (114, 146, 118))
    pic.seg(888, 514, 886, 568, STREAM, 100, 2)


def _tower_w(y):
    """How wide the beacon's tower is at height `y` (it narrows upward)."""
    return 13.0 + (524 - y) * 3.0 / 76.0


def paint_beacon(pic):
    """The poster's landmark: a white tower, red cap, lit lamp, beams."""
    cx = 714
    pic.poly([(730, 436), (988, 374), (988, 514), (730, 448)], GLOW, 55)
    pic.poly([(698, 436), (466, 400), (466, 476), (698, 448)], GLOW, 30)
    pic.poly([(cx - 13, 524), (cx + 13, 524), (cx + 10, 450), (cx - 10, 450)],
             CHALK)
    for y0, y1 in ((472, 484), (498, 510)):
        w0 = _tower_w(y0)
        w1 = _tower_w(y1)
        pic.poly([(cx - w0, y0), (cx + w0, y0), (cx + w1, y1), (cx - w1, y1)],
                 CRIMSON)
    pic.box(cx - 16, 432, 32, 18, (30, 30, 44))
    pic.disc(cx, 441, 6, LANTERN)
    pic.poly([(cx - 20, 432), (cx + 20, 432), (cx, 414)], CRIMSON)
    pic.seg(cx, 414, cx, 406, CRIMSON, 255, 2)
    pic.box(cx - 4, 506, 8, 18, (48, 40, 60))
    pic.box(cx - 3, 458, 6, 8, LANTERN)


def paint_falls(pic, x, y0, y1):
    """Water spilling off an island's edge, thinning as it drops."""
    steps = 14
    for s in range(steps):
        t0 = s / steps
        t1 = (s + 1) / steps
        ya = int(y0 + (y1 - y0) * t0)
        yb = int(y0 + (y1 - y0) * t1)
        a = int(185 * (1 - t0 * 0.7))
        wob = int(3 * math.sin(t0 * 9.0))
        pic.box(x - 4 + wob, ya, 8, yb - ya + 1, STREAM, a)
        pic.box(x + 7 + wob, ya, 3, yb - ya + 1, STREAM, max(0, a - 45))
        pic.box(x - 11 + wob, ya, 2, yb - ya + 1, STREAM, max(0, a - 70))
    pic.oval(x, y1 + 6, 42, 13, (240, 246, 250), 90)


def paint_isle_main(pic):
    """The big isle, grass on top and rock tapering to a point below."""
    cx, top = 648, 566
    pic.poly([(438, top), (858, top), (824, 644), (774, 722), (694, 790),
              (648, 812), (604, 790), (524, 722), (474, 644)], CLIFF)
    pic.poly([(438, top), (674, top), (648, 812), (604, 790), (524, 722),
              (474, 644)], CLIFF_LT)
    pic.poly([(674, top), (858, top), (824, 644), (774, 722), (694, 790),
              (648, 812)], CLIFF_DK)
    pic.oval(cx, top - 4, 192, 45, TURF)
    pic.oval(cx, top - 12, 185, 35, TURF_LT)
    for tx, ty, tr in ((514, 548, 17), (554, 538, 21), (594, 532, 15),
                       (764, 542, 19), (794, 556, 15), (824, 548, 12)):
        pic.disc(tx, ty, tr, TURF_DK)
    paint_falls(pic, 516, 584, 814)
    paint_beacon(pic)


def paint_cloudsea_front(pic):
    """Clouds in front of the isles' lower halves, so they float on them."""
    pic.oval(238, 788, 208, 42, PUFF2, 255)
    pic.oval(698, 808, 268, 46, PUFF5, 255)
    pic.oval(178, 868, 298, 60, PUFF1, 255)
    pic.oval(848, 874, 318, 64, PUFF3, 255)
    pic.oval(518, 928, 378, 70, PUFF2, 255)
    pic.oval(58, 988, 258, 60, PUFF2, 255)
    pic.oval(418, 1014, 418, 70, PUFF1, 255)
    pic.oval(898, 994, 298, 64, PUFF4, 255)
    pic.oval(198, 848, 188, 26, (255, 240, 214), 120)
    pic.oval(698, 790, 178, 22, (255, 242, 218), 120)
    pic.oval(518, 908, 238, 26, (255, 240, 214), 110)
    pic.oval(978, 762, 218, 40, PUFF2, 255)
    pic.oval(58, 742, 188, 36, PUFF1, 255)
    pic.oval(328, 970, 198, 30, PUFF4, 130)
    pic.oval(758, 952, 218, 32, PUFF4, 120)
    pic.oval(118, 902, 148, 24, (255, 244, 222), 100)


def paint_birds(pic):
    """A few birds crossing the evening sky."""
    for bx, by, s in ((346, 382, 13), (416, 350, 16), (468, 398, 11),
                      (796, 332, 15), (848, 374, 12), (296, 432, 10)):
        pic.seg(bx - s, by - 5, bx, by, DUSK, 200, 2)
        pic.seg(bx, by, bx + s, by - 5, DUSK, 200, 2)


def paint_title(pic):
    """The invented name, big, with its descriptor set beneath it."""
    name = "VELMORA"
    scale = 16
    nx = (W - word_w(name, scale)) // 2
    ny = 108
    pic.word(name, nx + 6, ny + 6, scale, DUSK, 110)
    pic.word(name, nx, ny, scale, PAPER)
    sub = "THE FLOATING ISLES"
    sscale = 4
    sx = (W - word_w(sub, sscale)) // 2
    sy = 250
    pic.word(sub, sx, sy, sscale, GILT)
    ry = sy + 12
    pic.box(150, ry, sx - 150 - 24, 3, GILT, 160)
    pic.box(sx + word_w(sub, sscale) + 24, ry,
            874 - (sx + word_w(sub, sscale) + 24), 3, GILT, 160)


def paint_border(pic):
    """A quiet double rule in from the edges, as old posters have."""
    pic.box(22, 22, W - 44, 3, PAPER, 90)
    pic.box(22, H - 25, W - 44, 3, PAPER, 90)
    pic.box(22, 22, 3, H - 44, PAPER, 90)
    pic.box(W - 25, 22, 3, H - 44, PAPER, 90)
    pic.box(30, 30, W - 60, 1, PAPER, 60)
    pic.box(30, H - 31, W - 60, 1, PAPER, 60)
    pic.box(30, 30, 1, H - 60, PAPER, 60)
    pic.box(W - 31, 30, 1, H - 60, PAPER, 60)


def render():
    """Paint the whole poster, back to front, and hand it back."""
    pic = Pic(W, H)
    pic.grad()
    paint_stars(pic)
    paint_sun(pic)
    paint_wisps(pic)
    paint_cloudsea_back(pic)
    paint_isle_far(pic)
    paint_isle_high(pic)
    paint_isle_main(pic)
    paint_cloudsea_front(pic)
    paint_birds(pic)
    paint_title(pic)
    paint_border(pic)
    return pic


# --- writing the PNG ------------------------------------------------------
# The encoder is small on purpose: an 8-bit RGB header, one compressed
# data block holding every row (each row but the first stored as the
# difference from the row above it, which suits long gradients), and the
# four-byte checks that close each chunk.


def _chunk(kind, payload):
    head = struct.pack(">I", len(payload)) + kind + payload
    return head + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)


def png_bytes(pic):
    body = bytearray()
    prev = bytes(pic.w * 3)
    for y in range(pic.h):
        row = bytes(pic.px[y * pic.w * 3:(y + 1) * pic.w * 3])
        if y == 0:
            body.append(0)
            body += row
        else:
            body.append(2)
            body += bytes((a - b) & 0xFF for a, b in zip(row, prev))
        prev = row
    head = struct.pack(">IIBBBBB", pic.w, pic.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", head)
            + _chunk(b"IDAT", zlib.compress(bytes(body), 9))
            + _chunk(b"IEND", b""))


def main():
    dest = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(dest, exist_ok=True)
    blob = png_bytes(render())
    target = os.path.join(dest, "entry.png")
    with open(target, "wb") as fh:
        fh.write(blob)
    print("wrote %s (%d bytes)" % (target, len(blob)))


raise SystemExit(main())
