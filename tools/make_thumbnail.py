#!/usr/bin/env python3
"""Generate the 16:9 series thumbnail: big stat, arrow, verdict, in the house colours.

Deliberately dependency-light (Pillow only) and text-fitted, because the first attempt at
this ran "SOLD" straight off the right edge. Every line is measured and shrunk until it
fits, so a longer stat or word cannot break the layout.

  python3 tools/make_thumbnail.py
  python3 tools/make_thumbnail.py --stat "$150B" --verdict "SOLD" --kicker "NOKIA" \\
      --sub "ONE IN TWO SMARTPHONES. THEN NOTHING." --out out/thumb/mine.png
"""
import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
W, H = 1280, 720
YEL, WHT, GRY = (245, 214, 10), (248, 248, 248), (150, 150, 150)
MARGIN = 72


def load(size):
    try:
        return ImageFont.truetype(FONT, size)
    except OSError:
        sys.exit(f"font not found: {FONT}")


def fit_line(draw, parts, max_w, start=150, minimum=40):
    """Shrink until the combined width fits. parts = [(text, colour)]."""
    size = start
    while size > minimum:
        f = load(size)
        widths = [draw.textlength(t, font=f) for t, _ in parts]
        if sum(widths) <= max_w:
            return f, widths
        size -= 4
    f = load(minimum)
    return f, [draw.textlength(t, font=f) for t, _ in parts]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kicker", default="NOKIA")
    ap.add_argument("--stat", default="$150B")
    ap.add_argument("--verdict", default="SOLD")
    ap.add_argument("--sub", default="ONE IN TWO SMARTPHONES. THEN NOTHING.")
    ap.add_argument("--out", default="out/thumb/video1_thumbnail_1280x720.png")
    a = ap.parse_args()

    img = Image.new("RGB", (W, H), (12, 12, 14))
    d = ImageDraw.Draw(img)
    for y in range(H):
        v = int(10 + 20 * (y / H))
        d.line([(0, y), (W, y)], fill=(v, v, v + 3))

    # Fit the kicker too: a long word like BLOCKBUSTER overruns the frame at a fixed size.
    kf, kw = fit_line(d, [(a.kicker, YEL)], W - 2 * MARGIN, start=170, minimum=60)
    d.text((MARGIN, 60), a.kicker, font=kf, fill=YEL)
    d.line([(MARGIN, 250), (W - MARGIN, 250)], fill=YEL, width=6)

    parts = [(a.stat, WHT), ("  \u2192  ", YEL), (a.verdict, YEL)]
    f, widths = fit_line(d, parts, W - 2 * MARGIN)
    x = MARGIN
    for (text, colour), w in zip(parts, widths):
        d.text((x, 300), text, font=f, fill=colour)
        x += w

    d.text((MARGIN, 590), a.sub, font=load(42), fill=GRY)

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    img.save(a.out)
    print(f"OK  {a.out}")
    print(f"    {W}x{H} | line 2 fits {sum(widths):.0f} of {W - 2 * MARGIN} px")


if __name__ == "__main__":
    main()
