#!/usr/bin/env python3
"""Generate the small starter assets that are committed to the repo.

These are intentionally minimal, dependency-light stand-ins so the app is
playable out of the box. Replace them with proper art later.

  data/card_back.png
  data/assets/backgrounds/menu_background.png

Run: python3 scripts/make_assets.py   (from the repo root)
"""
import pathlib

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

CARD_BACK_OUTER = (34, 22, 58)   # deep purple
CARD_BACK_INNER = (18, 12, 40)
CARD_BACK_ACCENT = (210, 170, 40)
CARD_BACK_GOLD = (210, 170, 40)


def card_back(size=(348, 494)):
    """A stylized Yu-Gi-Oh-style card back (348x494 ≈ 59:86 aspect)."""
    img = Image.new("RGB", size, CARD_BACK_OUTER)
    d = ImageDraw.Draw(img)

    # Outer gold border
    d.rectangle([0, 0, size[0] - 1, size[1] - 1], outline=CARD_BACK_GOLD, width=6)

    # Inner field
    pad = 22
    d.rectangle([pad, pad, size[0] - pad - 1, size[1] - pad - 1],
                fill=CARD_BACK_INNER, outline=CARD_BACK_ACCENT, width=2)

    # Simple central motif: a ring of 8 ornaments + a centre diamond
    cx, cy = size[0] // 2, size[1] // 2
    ring_r = 86
    import math
    for i in range(8):
        a = i * math.pi / 4
        x = cx + int(ring_r * math.cos(a))
        y = cy + int(ring_r * math.sin(a))
        d.ellipse([x - 8, y - 8, x + 8, y + 8], outline=CARD_BACK_ACCENT, width=2)

    # Centre diamond
    d_diamond = 28
    d.polygon([(cx, cy - d_diamond), (cx + d_diamond, cy),
               (cx, cy + d_diamond), (cx - d_diamond, cy)],
              outline=CARD_BACK_ACCENT, width=2)

    img.save(DATA / "card_back.png")
    print("wrote", DATA / "card_back.png")


def menu_background(size=(1620, 920)):
    """A dark textured menu background with a subtle starfield."""
    img = Image.new("RGB", size, (10, 12, 22))
    d = ImageDraw.Draw(img)

    # Subtle vignette-ish radial bands (concentric, darkening outward)
    cx, cy = size[0] // 2, size[1] // 2
    for r in range(max(size), 0, -2):
        t = r / max(size)
        col = (int(30 * t), int(34 * t), int(56 * t))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)

    # Starfield
    import random
    rng = random.Random(28)
    for _ in range(420):
        x = rng.randrange(size[0])
        y = rng.randrange(size[1])
        s = rng.randint(1, 3)
        b = rng.randint(90, 170)
        d.rectangle([x, y, x + s - 1, y + s - 1], fill=(b, b, b + 20))

    # A faint card-silhouette watermark grid at the bottom
    for gx in range(0, size[0], 120):
        d.line([gx, size[1] - 6, gx + 60, size[1] - 6],
               fill=(50, 50, 80, 90), width=1)

    (DATA / "assets" / "backgrounds").mkdir(parents=True, exist_ok=True)
    img.save(DATA / "assets" / "backgrounds" / "menu_background.png")
    print("wrote", DATA / "assets" / "backgrounds" / "menu_background.png")


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    card_back()
    menu_background()


if __name__ == "__main__":
    main()
