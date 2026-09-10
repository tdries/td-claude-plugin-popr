#!/usr/bin/env python3
"""Generate the POPR logo: pixel confetti burst, Anthropic palette.

One source of truth (GRID below) emitting every form the project needs.
Standard library only, no Pillow and no Aseprite, so `assets/` can be
regenerated on any Mac with a stock python3.

    python3 assets/make_logo.py           logo.svg, logo-animated.svg, all PNGs
    python3 assets/make_logo.py --icns    also POPR.icns (needs macOS iconutil)
    python3 assets/make_logo.py --gif     also burst.gif (needs Pillow, dev only)
    python3 assets/make_logo.py --demo    self check

Everything except --gif is standard library. burst.gif is a committed asset that
users never regenerate, so Pillow stays a dev-time dependency, like librsvg.
"""

import pathlib
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

HERE = pathlib.Path(__file__).parent
CELLS = 16  # the art is a 16x16 pixel grid
SIZES = (16, 32, 64, 128, 256, 512, 1024)  # all multiples of 16, so pixels stay crisp

# The ten representations macOS wants in an .icns, as (source png, iconset name).
ICONSET = [
    (16, "16x16"), (32, "16x16@2x"), (32, "32x32"), (64, "32x32@2x"),
    (128, "128x128"), (256, "128x128@2x"), (256, "256x256"),
    (512, "256x256@2x"), (512, "512x512"), (1024, "512x512@2x"),
]

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
    (9, 5, 1, "c"), (5, 9, 1, "g"), (5, 5, 1, "s"),          # mid band, fills the
    (10, 8, 1, "b"), (12, 6, 1, "l"), (2, 6, 1, "o"),        # gap between core
    (5, 12, 1, "b"), (9, 10, 1, "g"), (3, 3, 1, "l"),        # and outer ring
]


def rgba(hex_colour):
    h = hex_colour.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)


GROUND = "#F0EEE6"  # Anthropic ivory, the app icon's body
CORNER = 0.2237     # macOS rounds an app icon at roughly this fraction of its side


def render(size, ground=None):
    """Rasterise GRID into a size*size RGBA buffer.

    Transparent by default, which is what the notification's contentImage wants:
    it sits on the banner's own dark background. Pass ground to fill a rounded
    rectangle behind it instead, which is what an app icon needs. Bare confetti
    on transparent has no mass and dissolves into a smudge at 16 and 32 px, where
    an app icon spends most of its life.
    """
    if size % CELLS:
        raise ValueError(f"{size} is not a multiple of {CELLS}, pixels would blur")
    scale = size // CELLS
    px = [[(0, 0, 0, 0)] * size for _ in range(size)]
    if ground:
        body, r = rgba(ground), size * CORNER
        for y in range(size):
            for x in range(size):
                # inside the rectangle, except beyond the arc of a rounded corner
                cx = r - 0.5 - x if x < r else (x - (size - r) + 0.5 if x > size - r else 0)
                cy = r - 0.5 - y if y < r else (y - (size - r) + 0.5 if y > size - r else 0)
                if cx <= 0 or cy <= 0 or cx * cx + cy * cy <= r * r:
                    px[y][x] = body
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


def write_animated_svg(path, dur=3.0):
    """The burst as an animation: every chip starts collapsed at the core, is
    thrown outward, hangs, then drifts down and fades. Inner chips leave first.

    SMIL rather than CSS because this is consumed as <img src="...svg">, in the
    README and as the repo social preview, where stylesheets do not apply.
    """
    mid = CELLS / 2
    far = max(abs(x + s / 2 - mid) + abs(y + s / 2 - mid) for x, y, s, _ in GRID)
    parts = []
    for x, y, s, k in GRID:
        dx, dy = mid - (x + s / 2), mid - (y + s / 2)
        distance = (abs(dx) + abs(dy)) / far  # 0 at the core, 1 at the rim
        begin = round(distance * 0.45, 3)     # stagger: the core pops first
        drift = CELLS / 4
        parts.append(
            f'  <rect x="{x}" y="{y}" width="{s}" height="{s}" fill="{PALETTE[k]}" opacity="0">\n'
            f'    <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.12;0.62;1"\n'
            f'             dur="{dur}s" begin="{begin}s" repeatCount="indefinite"/>\n'
            f'    <animateTransform attributeName="transform" type="translate" additive="sum"\n'
            f'             values="{dx:.2f},{dy:.2f}; 0,0; 0,0; 0,{drift:.2f}"\n'
            f'             keyTimes="0;0.18;0.62;1" calcMode="spline"\n'
            f'             keySplines="0.2 0.9 0.3 1; 0 0 1 1; 0.5 0 0.9 0.6"\n'
            f'             dur="{dur}s" begin="{begin}s" repeatCount="indefinite"/>\n'
            f"  </rect>"
        )
    body = "\n".join(parts)
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CELLS} {CELLS}" '
        f'width="512" height="512" shape-rendering="crispEdges" role="img" '
        f'aria-label="POPR pixel confetti bursting outward and drifting down">\n'
        f"{body}\n</svg>\n"
    )


BURST_PX, BURST_FRAMES, BURST_MS = 192, 28, 45


def write_burst_gif(path):
    """The confetti burst as a transparent animated GIF, for the overlay window.

    Chips are thrown outward from the core, hang, then fall away and fade. The
    same GRID as everything else, so the animation cannot drift from the logo.
    """
    try:
        from PIL import Image
    except ImportError:
        print("Pillow not installed, skipping burst.gif (pip install pillow)", file=sys.stderr)
        return False

    mid, scale = CELLS / 2, BURST_PX // CELLS
    frames = []
    for f in range(BURST_FRAMES):
        t = f / (BURST_FRAMES - 1)
        throw = 1 - (1 - min(t / 0.35, 1)) ** 3          # fast out, easing to a stop
        fall = max(0.0, (t - 0.6) / 0.4)                 # then gravity takes them
        alpha = 255 if t < 0.6 else int(255 * (1 - fall))
        img = Image.new("RGBA", (BURST_PX, BURST_PX), (0, 0, 0, 0))
        px = img.load()
        for x, y, s, k in GRID:
            dx, dy = x + s / 2 - mid, y + s / 2 - mid
            ox = int(dx * (throw - 1) * scale * 0.9)
            oy = int(dy * (throw - 1) * scale * 0.9 + fall * BURST_PX * 0.35)
            r, g, b, _ = rgba(PALETTE[k])
            for yy in range(y * scale, (y + s) * scale):
                for xx in range(x * scale, (x + s) * scale):
                    X, Y = xx + ox, yy + oy
                    if 0 <= X < BURST_PX and 0 <= Y < BURST_PX:
                        px[X, Y] = (r, g, b, alpha)
        frames.append(img)

    def paletted(rgba_frame):
        # Quantise to 255 colours and reserve index 255 for full transparency,
        # so the window shows the desktop through the gaps rather than a box.
        a = rgba_frame.getchannel("A")
        p = rgba_frame.convert("RGB").quantize(colors=255, method=Image.MEDIANCUT)
        p.paste(255, a.point(lambda v: 255 if v <= 128 else 0))
        return p

    out = [paletted(f) for f in frames]
    out[0].save(path, save_all=True, append_images=out[1:], duration=BURST_MS,
                loop=0, transparency=255, disposal=2, optimize=False)
    return True


def write_icns(path):
    """Build the macOS icon via iconutil, which ships with the OS."""
    if not shutil.which("iconutil"):
        print("iconutil not found, skipping .icns (macOS only)", file=sys.stderr)
        return False
    with tempfile.TemporaryDirectory() as tmp:
        iconset = pathlib.Path(tmp) / "popr.iconset"
        iconset.mkdir()
        for src, name in ICONSET:
            write_png(iconset / f"icon_{name}.png", render(src, ground=GROUND))
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(path)], check=True)
    return True


def main(want_icns, want_gif):
    write_svg(HERE / "logo.svg")
    write_animated_svg(HERE / "logo-animated.svg")
    print("assets/logo.svg\nassets/logo-animated.svg")
    for size in SIZES:
        out = HERE / f"popr-{size}.png"
        write_png(out, render(size))
        print(f"assets/{out.name}  {out.stat().st_size} bytes")
    write_png(HERE / "icon-512.png", render(512, ground=GROUND))
    print("assets/icon-512.png  (app icon, on its ivory body)")
    if want_icns and write_icns(HERE / "POPR.icns"):
        print(f"assets/POPR.icns  {(HERE / 'POPR.icns').stat().st_size} bytes")
    if want_gif and write_burst_gif(HERE / "burst.gif"):
        print(f"assets/burst.gif  {(HERE / 'burst.gif').stat().st_size} bytes")


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
    # every iconset slot must have a PNG size behind it
    for src, _ in ICONSET:
        assert src in SIZES, src
    # the app icon variant fills its corners with ivory but keeps them rounded
    g = render(64, ground=GROUND)
    assert g[32][32] == rgba(GROUND) or g[32][32] == rgba(PALETTE["o"]), g[32][32]
    assert g[32][1] == rgba(GROUND), g[32][1]          # mid edge is inside the body
    assert g[0][0] == (0, 0, 0, 0), g[0][0]            # the very corner is cut away
    assert render(64)[32][1] == (0, 0, 0, 0)           # default stays transparent
    # the animation emits one chip and one pair of animations per grid entry
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp) / "a.svg"
        write_animated_svg(out)
        text = out.read_text()
    assert text.count("<rect") == len(GRID), text.count("<rect")
    assert text.count("animateTransform") == len(GRID)
    assert text.count('attributeName="opacity"') == len(GRID)
    # the 2x2 core sits dead centre, so it is the one chip with no travel
    assert text.count('values="0.00,0.00; 0,0') == 1
    # one cycle of the overlay animation, which the window's lifetime must cover
    assert abs(BURST_FRAMES * BURST_MS / 1000 - 1.26) < 0.01, BURST_FRAMES * BURST_MS
    print("demo ok")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        main("--icns" in sys.argv, "--gif" in sys.argv)
