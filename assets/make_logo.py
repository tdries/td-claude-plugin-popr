#!/usr/bin/env python3
"""Generate the POPR logo: pixel confetti burst, Anthropic palette.

One source of truth (GRID below) emitting logo.svg and PNGs at every size we
ship. Standard library only, no Pillow and no Aseprite, so `assets/` can be
regenerated on any Mac with a stock python3.

    python3 assets/make_logo.py
"""

import pathlib
import struct
import zlib

HERE = pathlib.Path(__file__).parent
CELLS = 16  # the art is a 16x16 pixel grid
SIZES = (16, 32, 64, 128, 256, 512)  # every size is a multiple of 16, so pixels stay crisp

PALETTE = {
    "o": "#D97757",  # Anthropic primary orange
    "b": "#CC785C",  # book cloth
    "c": "#BF9C88",  # clay
    "s": "#6A9BCC",  # sky
    "g": "#BCD1CA",  # sage
    "l": "#CBCADB",  # lavender
}

# (x, y, size, colour). Direction C, "burst": an orange core with two rings of
# confetti radiating out, plus off-beat chips so it does not read as a flower.
GRID = [
    (7, 7, 2, "o"),                                          # core
    (7, 3, 1, "b"), (10, 4, 1, "s"), (11, 7, 1, "g"),        # inner ring
    (10, 10, 1, "l"), (7, 11, 1, "c"), (4, 10, 1, "s"),
    (3, 7, 1, "b"), (4, 4, 1, "g"),
    (7, 0, 1, "o"), (12, 2, 2, "o"), (14, 7, 1, "o"),        # outer ring
    (12, 12, 1, "b"), (7, 14, 2, "o"), (2, 12, 1, "g"),
    (0, 7, 1, "c"), (2, 2, 2, "o"),
    (5, 1, 1, "l"), (13, 10, 1, "s"), (1, 10, 1, "l"),       # off-beat chips
    (10, 13, 1, "s"), (14, 4, 1, "c"), (0, 4, 1, "g"),
    (9, 5, 1, "c"), (5, 9, 1, "g"), (5, 5, 1, "s"),           # mid band, fills the
    (10, 8, 1, "b"), (12, 6, 1, "l"), (2, 6, 1, "o"),         # gap between core
    (5, 12, 1, "b"), (9, 10, 1, "g"), (3, 3, 1, "l"),         # and outer ring
]


def rgba(hex_colour):
    h = hex_colour.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)


def render(size):
    """Rasterise GRID into a size*size RGBA buffer on a transparent ground."""
    if size % CELLS:
        raise ValueError(f"{size} is not a multiple of {CELLS}, pixels would blur")
    scale = size // CELLS
    px = [[(0, 0, 0, 0)] * size for _ in range(size)]
    for gx, gy, gs, key in GRID:
        colour = rgba(PALETTE[key])
        for y in range(gy * scale, (gy + gs) * scale):
            for x in range(gx * scale, (gx + gs) * scale):
                if 0 <= x < size and 0 <= y < size:
                    px[y][x] = colour
    return px


def chunk(tag, data):
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def write_png(path, px):
    """Minimal RGBA PNG writer. ponytail: stdlib beats a Pillow dependency for
    flat pixel art; if we ever need resampling or effects, reach for Pillow."""
    size = len(px)
    raw = b"".join(
        b"\x00" + b"".join(bytes(p) for p in row) for row in px  # \x00 = filter type None
    )
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)


def write_svg(path):
    rects = "\n".join(
        f'  <rect x="{x}" y="{y}" width="{s}" height="{s}" fill="{PALETTE[k]}"/>'
        for x, y, s, k in GRID
    )
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CELLS} {CELLS}" '
        f'width="512" height="512" shape-rendering="crispEdges" role="img" '
        f'aria-label="POPR pixel confetti burst">\n{rects}\n</svg>\n'
    )


def main():
    write_svg(HERE / "logo.svg")
    print("assets/logo.svg")
    for size in SIZES:
        out = HERE / f"popr-{size}.png"
        write_png(out, render(size))
        print(f"assets/{out.name}  {out.stat().st_size} bytes")


def demo():
    """Self check: the raster must match the grid exactly."""
    px = render(32)  # scale 2
    assert len(px) == 32 and len(px[0]) == 32
    # core at grid (7,7) size 2 -> pixels (14..17, 14..17) are orange
    assert px[14][14] == rgba(PALETTE["o"]), px[14][14]
    assert px[17][17] == rgba(PALETTE["o"]), px[17][17]
    # grid (6,6) is empty -> transparent
    assert px[13][13] == (0, 0, 0, 0), px[13][13]
    # a lone chip at grid (0,4) size 1 -> pixels (0..1, 8..9) are sage
    assert px[8][0] == rgba(PALETTE["g"]), px[8][0]
    assert px[10][0] == (0, 0, 0, 0), px[10][0]
    # every size we ship must divide the grid cleanly
    for s in SIZES:
        assert s % CELLS == 0, s
    print("demo ok")


if __name__ == "__main__":
    import sys

    demo() if "--demo" in sys.argv else main()
