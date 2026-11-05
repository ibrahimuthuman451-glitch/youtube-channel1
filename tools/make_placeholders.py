#!/usr/bin/env python3
"""Generate a branded 1920x1080 placeholder still for every section that lacks one.

Step 0 of the workflow. Run it before build_longform so no section falls back to a bare
card, and the master looks deliberate rather than unfinished.

Each file is written to the *exact* path its section's `asset` field names, so
build_longform picks it up with no extra flags or spec edits.

It will not overwrite a real still unless you pass --overwrite. Filling gaps is the point;
painting over artwork you already sourced is not.

  python3 tools/make_placeholders.py --spec specs/video1.json
  python3 tools/make_placeholders.py --spec specs/video1.json --dry-run
  python3 tools/make_placeholders.py --spec specs/video1.json --overwrite
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from PIL import Image, ImageDraw  # noqa: E402

from make_thumbnail import load  # noqa: E402
from make_voice import sections_from_spec  # noqa: E402

W, H = 1920, 1080
YEL, GRY, DIM = (245, 214, 10), (150, 150, 150), (95, 95, 100)
MARGIN = 130

# Keep generated content out of the band the ASS layer uses (title sits around y=80,
# captions from ~y=880). Everything here lives between these y values.
SAFE_TOP, SAFE_BOTTOM = 300, 780


def target_path(asset, assets_dir):
    """Where this section's still belongs, whether or not it exists yet."""
    rel = asset[len("assets/"):] if asset.startswith("assets/") else asset
    return os.path.join(assets_dir, rel)


def draw_placeholder(path, index, total, filename):
    """Dark branded card: section number and the filename to supply.

    The section title is deliberately *not* drawn here. build_longform already renders it
    from the ASS title layer at the top of frame, so painting it into the still as well
    would put it on screen twice.

    The corner ticks sit outside the text columns - the first attempt drew them at the
    text origin and their arms cut through "PLACEHOLDER" and the counter.
    """
    img = Image.new("RGB", (W, H), (12, 12, 14))
    d = ImageDraw.Draw(img)
    for y in range(H):
        v = int(9 + 20 * (y / H))
        d.line([(0, y), (W, y)], fill=(v, v, v + 3))

    for cx, cy, sx, sy in ((46, 46, 1, 1), (W - 46, 46, -1, 1)):
        d.line([(cx, cy), (cx + 54 * sx, cy)], fill=YEL, width=4)
        d.line([(cx, cy), (cx, cy + 54 * sy)], fill=YEL, width=4)

    d.text((MARGIN, 62), "PLACEHOLDER", font=load(30), fill=DIM)
    counter = f"{index:02d} / {total:02d}"
    cw = d.textlength(counter, font=load(30))
    d.text((W - MARGIN - cw, 62), counter, font=load(30), fill=DIM)

    # Section number, large, centred in the safe band (clear of the ASS title and captions).
    num = f"{index:02d}"
    nf = load(230)
    nw = d.textlength(num, font=nf)
    d.text(((W - nw) / 2, SAFE_TOP), num, font=nf, fill=YEL)

    # The filename to drop in, so replacing the placeholder takes no guessing.
    d.line([(W / 2 - 130, 640), (W / 2 + 130, 640)], fill=(70, 70, 74), width=2)
    ff = load(30)
    fw = d.textlength(filename, font=ff)
    d.text(((W - fw) / 2, 668), filename, font=ff, fill=GRY)

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    img.save(path, quality=92)
    return path


def main():
    sys.stdout.reconfigure(line_buffering=True)
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--assets", default="assets",
                    help="assets root the spec paths are relative to")
    ap.add_argument("--overwrite", action="store_true",
                    help="replace stills that already exist (default: only fill gaps)")
    ap.add_argument("--dry-run", action="store_true",
                    help="list what would be created without writing anything")
    a = ap.parse_args()

    if not os.path.isfile(a.spec):
        sys.exit(f"spec not found: {a.spec}")
    with open(a.spec, encoding="utf-8") as f:
        spec = json.load(f)

    sections = sections_from_spec(spec)
    if not sections:
        sys.exit(f"{a.spec}: no sections found")

    total = len(sections)
    made, kept, skipped = [], 0, 0
    print(spec.get("name", os.path.basename(a.spec)))
    print(f"  {total} sections | assets root: {a.assets}/")

    for i, s in enumerate(sections, 1):
        asset = s.get("asset") or ""
        if not asset:
            skipped += 1
            print(f"  [{i:>2}/{total}] SKIP  no asset path in spec")
            continue
        path = target_path(asset, a.assets)
        filename = os.path.basename(asset)
        exists = os.path.isfile(path)
        if exists and not a.overwrite:
            kept += 1
            continue
        if a.dry_run:
            made.append(path)
            print(f"  [{i:>2}/{total}] would create {os.path.relpath(path)}")
            continue
        draw_placeholder(path, i, total, filename)
        made.append(path)
        print(f"  [{i:>2}/{total}] wrote   {os.path.relpath(path)}")

    verb = "would create" if a.dry_run else "created"
    print(f"\nOK  {verb} {len(made)}, kept {kept} existing, skipped {skipped}")
    if made and not a.dry_run:
        print(f"    {W}x{H} branded stills, one per section")
        print("    now: python3 tools/build_longform.py --spec "
              f"{a.spec} --audio ... --chunks ... --out ... --ken-burns")
    elif kept and not a.dry_run:
        print("    every section already has a still - nothing to do "
              "(pass --overwrite to replace)")


if __name__ == "__main__":
    main()
