#!/usr/bin/env python3
"""Render the POPR mark blowing apart, as a shareable animated GIF.

A promotional asset, not something POPR uses: the real burst is drawn live by
assets/banner.js, seeded from the project name. This reuses the same grid and
the same palette so the two cannot look like different products.

Needs Pillow, which is a dev-time dependency only. The output is committed.

    python3 assets/make_explode_gif.py
"""

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import make_logo as m  # noqa: E402  the grid and palette live there

HERE = pathlib.Path(__file__).parent
SIZE = 400
GROUND = "#F0EEE6"

# Pauses are expressed as a long duration on ONE frame, not as repeats of an
# identical one: the GIF encoder merges identical consecutive frames, which
# silently swallowed the hold and the blank beat and left the timing wrong.
FLY = 19          # frames of flight
RETURN = 5        # and it reassembles, so the loop does not jump
MS = 45           # per flight frame
HOLD_MS = 620     # the mark sits still, long enough to read
BLANK_MS = 160    # a beat of nothing before it comes back


def seeded(i):
    """Deterministic jitter per chip, so every render is identical."""
    x = math.sin(i * 12.9898) * 43758.5453
    return x - math.floor(x)


def chips():
    scale = SIZE / m.CELLS
    mid = SIZE / 2
    out = []
    for i, (gx, gy, gs, key) in enumerate(m.GRID):
        px, py = gx * scale, gy * scale
        side = gs * scale
        cx, cy = px + side / 2, py + side / 2
        dx, dy = cx - mid, cy - mid
        dist = math.hypot(dx, dy) or 1.0
        # Straight out from the middle, with a little wobble so it is not a wheel.
        # The speed spread is deliberately flat: scaled hard by distance, the
        # outer pieces are gone before the core has moved and it stops reading
        # as one mark coming apart.
        angle = math.atan2(dy, dx) + (seeded(i) - 0.5) * 0.7
        out.append({
            "x": px, "y": py, "side": side,
            "colour": m.PALETTE[key],
            # Tuned so the pieces are still in shot while they fade. Thrown
            # harder they leave the canvas by halfway, and every frame after
            # that is identical background, which the encoder then merges away.
            "vx": math.cos(angle) * (1.00 + 0.45 * dist / mid) * SIZE * 0.34,
            "vy": math.sin(angle) * (1.00 + 0.45 * dist / mid) * SIZE * 0.34,
        })
    return out



def build():
    from PIL import Image, ImageDraw

    frames = []
    cs = chips()

    def render(t, alpha):
        img = Image.new("RGBA", (SIZE, SIZE), tuple(m.rgba(GROUND)))
        layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        for c in cs:
            ease = 1 - (1 - t) ** 2                       # fast out, easing off
            ox = c["vx"] * ease
            oy = c["vy"] * ease + (SIZE * 0.34) * t * t   # and gravity takes them
            x0, y0 = c["x"] + ox, c["y"] + oy
            r, g, b, _ = m.rgba(c["colour"])
            d.rectangle([x0, y0, x0 + c["side"] - 1, y0 + c["side"] - 1],
                        fill=(r, g, b, int(255 * alpha)))
        img.alpha_composite(layer)
        return img.convert("RGB")

    timings = []
    frames.append(render(0.0, 1.0)); timings.append(HOLD_MS)
    for i in range(FLY):
        t = (i + 1) / FLY
        frames.append(render(t, max(0.0, 1.0 - max(0.0, (t - 0.50) / 0.50))))
        timings.append(MS)
    frames.append(render(1.0, 0.0)); timings.append(BLANK_MS)
    for i in range(RETURN):                                # reassemble, so it loops
        frames.append(render(0.0, (i + 1) / RETURN))
        timings.append(MS)
    return frames, timings


def main():
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        print("Pillow is needed for this one: pip install pillow", file=sys.stderr)
        return 1
    frames, timings = build()
    out = HERE / "logo-explode.gif"
    frames[0].save(out, save_all=True, append_images=frames[1:],
                   duration=timings, loop=0, optimize=True)
    print(f"assets/logo-explode.gif  {len(frames)} frames, "
          f"{sum(timings) / 1000:.2f}s, {out.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
