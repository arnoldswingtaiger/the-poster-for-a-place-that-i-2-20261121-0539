#!/usr/bin/env python3
"""VELMORA -- a travel poster for a place that does not exist.

Draws one 1024x1024 travel poster for the Floating Isles of Velmora:
a lighthouse standing on a floating island above a sea of clouds at
golden hour, with the place's name set large across the evening sky.

Pure Python 3 standard library. The grader runs the program in a
sandbox with no network and nothing installed, so the canvas, the
bitmap letterforms and the PNG encoder are all built in here.

Deterministic: no clock, no randomness, no input files -- two runs
write the same bytes.

Usage:
    python3 main.py                          # writes /output/entry.png
    MAKEFUN_OUTPUT_DIR=out python3 main.py   # writes out/entry.png
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024
OUT_NAME = "entry.png"

# ------------------------------------------------------------------ palette

INK_SHADOW = (18, 14, 44)     # title shadow, birds
CREAM = (255, 243, 210)       # title
PALE_GOLD = (255, 230, 190)   # subtitle and rules
SUN_CORE = (255, 228, 160)
SUN_HALO = (255, 190, 120)
ROCK_DARK = (56, 44, 66)
ROCK = (76, 58, 84)
ROCK_LIT = (98, 76, 102)
LEAF_DARK = (40, 84, 60)
LEAF = (52, 104, 74)
LEAF_LIT = (74, 138, 92)
TOWER = (248, 244, 232)
ROOF_RED = (196, 60, 52)
LAMP = (255, 220, 130)
BEAM = (255, 226, 150)
FALL = (214, 232, 244)
CLOUD_A = (252, 230, 196)
CLOUD_B = (250, 222, 200)
CLOUD_C = (246, 210, 182)
CLOUD_D = (238, 196, 176)
CLOUD_E = (252, 236, 205)

SKY_STOPS = (
    (0.00, (13, 20, 58)),
    (0.22, (38, 44, 104)),
    (0.40, (94, 62, 128)),
    (0.55, (186, 92, 112)),
    (0.66, (240, 150, 96)),
    (0.74, (252, 205, 138)),
    (0.80, (250, 224, 178)),
    (1.00, (238, 196, 172)),
)


# ------------------------------------------------------------- bitmap font
# 5x7 letterforms, one row per string, '#' set and '.' clear. Only the
# characters this poster needs, plus the rest of the alphabet for free.

FONT = {
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", ".#.#.", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
}


def text_width(text, scale):
    """Pixel width of `text` drawn at `scale` (6 units per character)."""
    if not text:
        return 0
    return len(text) * 6 * scale - scale


# ------------------------------------------------------------------- canvas

def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


class Canvas:
    """An RGB image held as one bytearray per row."""

    def __init__(self, width, height):
        self.w = width
        self.h = height
        self.rows = [bytearray(width * 3) for _ in range(height)]

    def span(self, y, x0, x1, color, alpha=255):
        """Paint one horizontal run, blended when alpha < 255."""
        if y < 0 or y >= self.h:
            return
        x0 = max(0, x0)
        x1 = min(self.w - 1, x1)
        if x1 < x0:
            return
        row = self.rows[y]
        if alpha >= 255:
            row[x0 * 3:(x1 + 1) * 3] = bytes(color) * (x1 - x0 + 1)
            return
        if alpha <= 0:
            return
        r, g, b = color
        inv = 255 - alpha
        for x in range(x0, x1 + 1):
            i = x * 3
            row[i] = (r * alpha + row[i] * inv) // 255
            row[i + 1] = (g * alpha + row[i + 1] * inv) // 255
            row[i + 2] = (b * alpha + row[i + 2] * inv) // 255

    def rect(self, x, y, w, h, color, alpha=255):
        for yy in range(y, y + h):
            self.span(yy, x, x + w - 1, color, alpha)

    def vgrad(self, stops):
        """Fill the canvas with a vertical gradient through `stops`."""
        for y in range(self.h):
            t = y / (self.h - 1)
            for i in range(len(stops) - 1):
                t0, c0 = stops[i]
                t1, c1 = stops[i + 1]
                if t0 <= t <= t1:
                    f = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
                    color = lerp(c0, c1, f)
                    break
            else:
                color = stops[-1][1]
            self.rows[y][:] = bytes(color) * self.w

    def ellipse(self, cx, cy, rx, ry, color, alpha=255):
        for y in range(max(0, cy - ry), min(self.h - 1, cy + ry) + 1):
            dy = (y - cy) / ry
            dx = rx * math.sqrt(max(0.0, 1.0 - dy * dy))
            self.span(y, int(math.ceil(cx - dx)), int(math.floor(cx + dx)),
                      color, alpha)

    def circle(self, cx, cy, r, color, alpha=255):
        self.ellipse(cx, cy, r, r, color, alpha)

    def polygon(self, pts, color, alpha=255):
        """Scanline-fill a polygon (even-odd rule)."""
        ys = [p[1] for p in pts]
        y0 = max(0, min(ys))
        y1 = min(self.h - 1, max(ys))
        n = len(pts)
        for y in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x0, yy0 = pts[i]
                x1, yy1 = pts[(i + 1) % n]
                if (yy0 <= y < yy1) or (yy1 <= y < yy0):
                    t = (y - yy0) / (yy1 - yy0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.span(y, int(math.ceil(xs[i])),
                          int(math.floor(xs[i + 1])), color, alpha)

    def line(self, x0, y0, x1, y1, color, alpha=255, width=1):
        """Draw a line by stepping along its longer axis."""
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        half = width // 2
        for i in range(steps + 1):
            t = i / steps
            x = int(round(x0 + (x1 - x0) * t))
            y = int(round(y0 + (y1 - y0) * t))
            self.rect(x - half, y - half, width, width, color, alpha)

    def text(self, s, x, y, scale, color, alpha=255):
        cx = x
        for ch in s:
            glyph = FONT.get(ch, FONT[" "])
            for gy, bits in enumerate(glyph):
                for gx, bit in enumerate(bits):
                    if bit == "#":
                        self.rect(cx + gx * scale, y + gy * scale,
                                  scale, scale, color, alpha)
            cx += 6 * scale


# ------------------------------------------------------- deterministic stars

def _lcg(seed):
    while True:
        seed = (1103515245 * seed + 12345) & 0x7FFFFFFF
        yield seed


def draw_stars(cv):
    """A scattering of early stars in the upper sky (fixed seed)."""
    gen = _lcg(20261121)
    for _ in range(46):
        x = 16 + next(gen) % (W - 32)
        y = 16 + next(gen) % 400
        r = 1 + next(gen) % 2
        a = 50 + next(gen) % 110
        cv.circle(x, y, r, (255, 244, 224), a)


# -------------------------------------------------------------------- scene

def draw_sun(cv):
    """The low sun, setting into the cloud sea between the islands."""
    cx, cy = 370, 685
    for r in range(280, 92, -8):
        cv.circle(cx, cy, r, SUN_HALO, 6)
    for r in range(150, 84, -8):
        cv.circle(cx, cy, r, SUN_HALO, 10)
    # A warm rim so the disc holds its edge against the pale clouds.
    cv.circle(cx, cy, 82, (255, 205, 120))
    cv.circle(cx, cy, 78, SUN_CORE)
    cv.circle(cx - 20, cy - 22, 50, (255, 248, 220))


def draw_sky_clouds(cv):
    """Two thin evening clouds drifting past the sun."""
    cv.ellipse(230, 646, 120, 13, (250, 200, 160), 110)
    cv.ellipse(250, 636, 76, 10, (252, 214, 176), 110)
    cv.ellipse(560, 618, 140, 12, (248, 192, 158), 100)
    cv.ellipse(536, 608, 88, 9, (250, 208, 172), 100)


def draw_back_clouds(cv):
    """The cloud sea's far edge, behind the islands."""
    cv.ellipse(170, 730, 330, 58, CLOUD_C, 255)
    cv.ellipse(560, 762, 400, 64, CLOUD_B, 255)
    cv.ellipse(900, 736, 330, 56, CLOUD_C, 255)
    cv.ellipse(360, 800, 360, 60, CLOUD_A, 255)
    cv.ellipse(760, 806, 360, 58, CLOUD_B, 255)


def draw_far_island(cv):
    """A small hazy isle to the left, far away."""
    cv.polygon([(95, 545), (335, 545), (300, 600), (250, 640),
                (215, 655), (180, 640), (130, 600)], (104, 82, 108))
    cv.ellipse(215, 542, 110, 30, (86, 118, 96))
    cv.ellipse(215, 534, 100, 22, (104, 138, 110))
    cv.line(252, 600, 250, 706, FALL, 120, 3)
    cv.line(262, 604, 262, 690, FALL, 90, 2)


def draw_high_island(cv):
    """A tiny isle high on the right, adrift in the evening sky."""
    cv.polygon([(800, 470), (940, 470), (920, 508), (888, 536),
                (870, 544), (852, 536), (820, 508)], (110, 88, 116))
    cv.ellipse(870, 466, 70, 20, (96, 126, 104))
    cv.ellipse(870, 460, 62, 15, (114, 146, 118))
    cv.line(892, 512, 890, 566, FALL, 100, 2)


def _tower_half_width(y):
    """Half-width of the lighthouse tower at height y (tapers upward)."""
    return 13.0 + (522 - y) * (13.0 - 10.0) / (522 - 448)


def draw_lighthouse(cv):
    """The poster's landmark: a white tower with a red cap and a beam."""
    cx = 720
    # Light beams first, so the tower paints over their roots.
    cv.polygon([(736, 434), (992, 372), (992, 512), (736, 446)],
               BEAM, 55)
    cv.polygon([(704, 434), (470, 398), (470, 474), (704, 446)],
               BEAM, 30)
    # Tapered tower.
    cv.polygon([(cx - 13, 522), (cx + 13, 522), (cx + 10, 448),
                (cx - 10, 448)], TOWER)
    # Two red bands, following the taper.
    for y0, y1 in ((470, 482), (496, 508)):
        hw0 = _tower_half_width(y0)
        hw1 = _tower_half_width(y1)
        cv.polygon([(cx - hw0, y0), (cx + hw0, y0), (cx + hw1, y1),
                    (cx - hw1, y1)], ROOF_RED)
    # Lamp room, lamp and cap.
    cv.rect(cx - 16, 430, 32, 18, (30, 30, 44))
    cv.circle(cx, 439, 6, LAMP)
    cv.polygon([(cx - 20, 430), (cx + 20, 430), (cx, 412)], ROOF_RED)
    cv.line(cx, 412, cx, 404, ROOF_RED, 255, 2)
    # Door and a lit window.
    cv.rect(cx - 4, 504, 8, 18, (48, 40, 60))
    cv.rect(cx - 3, 456, 6, 8, LAMP)


def draw_waterfall(cv, x, y0, y1):
    """Three streaks of falling water, fading as they drop."""
    steps = 14
    for s in range(steps):
        t0 = s / steps
        t1 = (s + 1) / steps
        ya = int(y0 + (y1 - y0) * t0)
        yb = int(y0 + (y1 - y0) * t1)
        a = int(185 * (1 - t0 * 0.7))
        wob = int(3 * math.sin(t0 * 9.0))
        cv.rect(x - 4 + wob, ya, 8, yb - ya + 1, FALL, a)
        cv.rect(x + 7 + wob, ya, 3, yb - ya + 1, FALL, max(0, a - 45))
        cv.rect(x - 11 + wob, ya, 2, yb - ya + 1, FALL, max(0, a - 70))
    cv.ellipse(x, y1 + 6, 42, 13, (240, 246, 250), 90)


def draw_main_island(cv):
    """The big floating isle with the lighthouse on top."""
    cx, top = 655, 560
    # Rock: underside tapering to a point; the sun is on the left, so
    # the left facet is lit and the right one falls into shade, with a
    # diagonal seam between them.
    cv.polygon([(445, top), (865, top), (830, 640), (780, 720),
                (700, 790), (655, 810), (610, 790), (530, 720),
                (480, 640)], ROCK)
    cv.polygon([(445, top), (680, top), (655, 810), (610, 790),
                (530, 720), (480, 640)], ROCK_LIT)
    cv.polygon([(680, top), (865, top), (830, 640), (780, 720),
                (700, 790), (655, 810)], ROCK_DARK)
    # Grassy cap with a sunlit rim and a few trees.
    cv.ellipse(cx, top - 4, 195, 46, LEAF)
    cv.ellipse(cx, top - 12, 188, 36, LEAF_LIT)
    for tx, ty, tr in ((520, 546, 17), (560, 536, 21), (600, 530, 15),
                       (770, 540, 19), (800, 554, 15), (830, 546, 12)):
        cv.circle(tx, ty, tr, LEAF_DARK)
    # The waterfall pours off the island's left edge.
    draw_waterfall(cv, 522, 578, 812)
    # The landmark.
    draw_lighthouse(cv)


def draw_front_clouds(cv):
    """Clouds in front of the islands' lower halves: they float on them."""
    cv.ellipse(240, 786, 210, 42, CLOUD_B, 255)
    cv.ellipse(700, 806, 270, 46, CLOUD_E, 255)
    cv.ellipse(180, 866, 300, 60, CLOUD_A, 255)
    cv.ellipse(850, 872, 320, 64, CLOUD_C, 255)
    cv.ellipse(520, 926, 380, 70, CLOUD_B, 255)
    cv.ellipse(60, 986, 260, 60, CLOUD_B, 255)
    cv.ellipse(420, 1012, 420, 70, CLOUD_A, 255)
    cv.ellipse(900, 992, 300, 64, CLOUD_D, 255)
    # Soft highlights on the cloud tops.
    cv.ellipse(200, 846, 190, 26, (255, 240, 214), 120)
    cv.ellipse(700, 788, 180, 22, (255, 242, 218), 120)
    cv.ellipse(520, 906, 240, 26, (255, 240, 214), 110)
    # Low drifts and shaded folds, so the sea reads deep, not flat.
    cv.ellipse(980, 760, 220, 40, CLOUD_B, 255)
    cv.ellipse(60, 740, 190, 36, CLOUD_A, 255)
    cv.ellipse(330, 968, 200, 30, CLOUD_D, 130)
    cv.ellipse(760, 950, 220, 32, CLOUD_D, 120)
    cv.ellipse(120, 900, 150, 24, (255, 244, 222), 100)


def draw_birds(cv):
    """A few birds crossing the evening sky."""
    for bx, by, s in ((350, 380, 13), (420, 348, 16), (472, 396, 11),
                      (800, 330, 15), (852, 372, 12), (300, 430, 10)):
        cv.line(bx - s, by - 5, bx, by, INK_SHADOW, 200, 2)
        cv.line(bx, by, bx + s, by - 5, INK_SHADOW, 200, 2)


def draw_type(cv):
    """The place's name, large, with its descriptor beneath it."""
    name = "VELMORA"
    scale = 16
    nx = (W - text_width(name, scale)) // 2
    ny = 108
    cv.text(name, nx + 6, ny + 6, scale, INK_SHADOW, 110)
    cv.text(name, nx, ny, scale, CREAM)
    sub = "THE FLOATING ISLES"
    sscale = 4
    sx = (W - text_width(sub, sscale)) // 2
    sy = 250
    cv.text(sub, sx, sy, sscale, PALE_GOLD)
    rule_y = sy + 12
    cv.rect(150, rule_y, sx - 150 - 24, 3, PALE_GOLD, 160)
    cv.rect(sx + text_width(sub, sscale) + 24, rule_y,
            874 - (sx + text_width(sub, sscale) + 24), 3, PALE_GOLD, 160)


def draw_frame(cv):
    """A quiet double rule in from the edges, as old posters have."""
    cv.rect(22, 22, W - 44, 3, CREAM, 90)
    cv.rect(22, H - 25, W - 44, 3, CREAM, 90)
    cv.rect(22, 22, 3, H - 44, CREAM, 90)
    cv.rect(W - 25, 22, 3, H - 44, CREAM, 90)
    cv.rect(30, 30, W - 60, 1, CREAM, 60)
    cv.rect(30, H - 31, W - 60, 1, CREAM, 60)
    cv.rect(30, 30, 1, H - 60, CREAM, 60)
    cv.rect(W - 31, 30, 1, H - 60, CREAM, 60)


def build_poster():
    cv = Canvas(W, H)
    cv.vgrad(SKY_STOPS)
    draw_stars(cv)
    draw_sun(cv)
    draw_sky_clouds(cv)
    draw_back_clouds(cv)
    draw_far_island(cv)
    draw_high_island(cv)
    draw_main_island(cv)
    draw_front_clouds(cv)
    draw_birds(cv)
    draw_type(cv)
    draw_frame(cv)
    return cv


# ---------------------------------------------------------------- PNG writer

def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    return out + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def encode_png(cv):
    """Encode the canvas as PNG: filter Up on every row but the first,
    which suits the poster's long vertical gradients and flat areas."""
    raw = bytearray()
    prev = bytes(cv.w * 3)
    for i, row in enumerate(cv.rows):
        if i == 0:
            raw.append(0)
            raw.extend(row)
        else:
            raw.append(2)
            raw.extend((a - b) & 0xFF for a, b in zip(row, prev))
        prev = bytes(row)
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + _chunk(b"IEND", b""))


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    data = encode_png(build_poster())
    path = os.path.join(out_dir, OUT_NAME)
    with open(path, "wb") as f:
        f.write(data)
    print(f"wrote {path} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
