#!/usr/bin/env python3
"""Generate the POPR logo: pixel confetti burst, Anthropic palette.

One source of truth (GRID below) emitting every form the project needs.
Standard library only, no Pillow and no Aseprite, so `assets/` can be
regenerated on any Mac with a stock python3.

    python3 assets/make_logo.py           logo.svg, logo-animated.svg, all PNGs
    python3 assets/make_logo.py --icns    also POPR.icns (needs macOS iconutil)
    python3 assets/make_logo.py --demo    self check

Standard library throughout. The confetti burst is drawn procedurally by
assets/banner.js at runtime, seeded from the project name, so there is no
animation asset here to keep in sync.
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
    (6, 6, 4, "o"),                                     # the core
    (7, 1, 3, "b"), (12, 4, 3, "s"), (12, 11, 3, "l"),  # eight pieces thrown
    (6, 12, 3, "o"), (2, 11, 3, "c"), (1, 6, 3, "g"),   # clear of it
    (2, 1, 3, "o"),
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


# The app icon is bare confetti on transparent, at every size.
#
# It carried an ivory body for a while, so it would not dissolve into a grey
# smudge at the 16 and 32 px sizes System Settings lists use. Then an .icns
# carries several representations, so it held both: body when small, bare when
# large. macOS picks a SMALL representation for the notification banner, so the
# banner drew a white square on its dark background either way.
#
# The banner is where this icon is seen a hundred times a day and the Settings
# row is seen once, so the banner wins and the small sizes take the hit.
ICNS_GROUND = None


def write_icns(path):
    """Build the macOS icon via iconutil, which ships with the OS."""
    if not shutil.which("iconutil"):
        print("iconutil not found, skipping .icns (macOS only)", file=sys.stderr)
        return False
    with tempfile.TemporaryDirectory() as tmp:
        iconset = pathlib.Path(tmp) / "popr.iconset"
        iconset.mkdir()
        for src, name in ICONSET:
            write_png(iconset / f"icon_{name}.png", render(src, ground=ICNS_GROUND))
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(path)], check=True)
    return True


def main(want_icns):
    write_svg(HERE / "logo.svg")
    write_animated_svg(HERE / "logo-animated.svg")
    print("assets/logo.svg\nassets/logo-animated.svg")
    for size in SIZES:
        out = HERE / f"popr-{size}.png"
        write_png(out, render(size))
        print(f"assets/{out.name}  {out.stat().st_size} bytes")
    if want_icns and write_icns(HERE / "POPR.icns"):
        print(f"assets/POPR.icns  {(HERE / 'POPR.icns').stat().st_size} bytes")


def demo():
    """Self check: the raster must match the grid exactly."""
    scale = 2
    px = render(CELLS * scale)
    covered = {(x + dx, y + dy)
               for x, y, s, _ in GRID for dx in range(s) for dy in range(s)}

    for gx, gy, gs, key in GRID:                    # every chip lands as its colour
        want = rgba(PALETTE[key])
        for cx, cy in ((gx, gy), (gx + gs - 1, gy + gs - 1)):
            got = px[cy * scale][cx * scale]
            assert got == want, (gx, gy, key, got, want)

    empty = [(x, y) for y in range(CELLS) for x in range(CELLS) if (x, y) not in covered]
    assert empty, "the grid is completely full, so it is a square, not confetti"
    for cx, cy in empty:                            # and the gaps stay gaps
        assert px[cy * scale][cx * scale] == (0, 0, 0, 0), (cx, cy)

    assert len(covered) < CELLS * CELLS * 0.55, "too dense to read as confetti"
    for _, _, s, _ in GRID:
        assert s >= 3, "chips smaller than 3 cells vanish at icon sizes"

    for s in SIZES:                                 # sizes must divide the grid
        assert s % CELLS == 0, s
    for src, _ in ICONSET:
        assert src in SIZES, src

    assert ICNS_GROUND is None, "a body here shows as a white square on the banner"

    with tempfile.TemporaryDirectory() as tmp:      # the animation covers every chip
        out = pathlib.Path(tmp) / "a.svg"
        write_animated_svg(out)
        text = out.read_text()
    assert text.count("<rect") == len(GRID), text.count("<rect")
    assert text.count("animateTransform") == len(GRID)

    print(f"demo ok: {len(GRID)} chips, {len(covered)} of {CELLS * CELLS} cells filled")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        main("--icns" in sys.argv)
