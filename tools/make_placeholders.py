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


def draw_placeholder(path, index, total, filename, w=W, h=H):
    """Dark branded card: section number and the filename to supply.

    The section title is deliberately *not* drawn here. build_longform already renders it
    from the ASS title layer at the top of frame, so painting it into the still as well
    would put it on screen twice.

    Every position is derived from the frame size, so the same layout works for 1920x1080
    long-form and 1080x1920 vertical shorts. The proportions reproduce the original 16:9
    design exactly.
    """
    img = Image.new("RGB", (w, h), (12, 12, 14))
    d = ImageDraw.Draw(img)
    for y in range(h):
        v = int(9 + 20 * (y / h))
        d.line([(0, y), (w, y)], fill=(v, v, v + 3))

    # Vertical frames get a wider inset: make_short's 9:16 framing zooms in slightly, and
    # at the 16:9 margin the corner labels were being clipped at the frame edges.
    inset = 0.14 if h > w else 0.068
    margin, arm = int(w * inset), int(w * 0.028)
    tick, lab_y = int(w * (0.085 if h > w else 0.024)), int(h * 0.057)
    for cx, sx in ((tick, 1), (w - tick, -1)):
        d.line([(cx, tick), (cx + arm * sx, tick)], fill=YEL, width=4)
        d.line([(cx, tick), (cx, tick + arm)], fill=YEL, width=4)

    d.text((margin, lab_y), "PLACEHOLDER", font=load(int(h * 0.028)), fill=DIM)
    counter = f"{index:02d} / {total:02d}"
    cf = load(int(h * 0.028))
    cw = d.textlength(counter, font=cf)
    d.text((w - margin - cw, lab_y), counter, font=cf, fill=DIM)

    num = f"{index:02d}"
    nf = load(int(h * 0.213))
    nw = d.textlength(num, font=nf)
    d.text(((w - nw) / 2, int(h * 0.278)), num, font=nf, fill=YEL)

    rule_y = int(h * 0.593)
    d.line([(w / 2 - int(w * 0.068), rule_y), (w / 2 + int(w * 0.068), rule_y)],
           fill=(70, 70, 74), width=2)
    ff = load(int(h * 0.028))
    fw = d.textlength(filename, font=ff)
    d.text(((w - fw) / 2, int(h * 0.618)), filename, font=ff, fill=GRY)

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
    ap.add_argument("--size", default="1920x1080",
                    help="WxH of the generated still; use 1080x1920 for vertical shorts")
    a = ap.parse_args()

    if not os.path.isfile(a.spec):
        sys.exit(f"spec not found: {a.spec}")
    try:
        out_w, out_h = (int(x) for x in a.size.lower().split("x"))
    except ValueError:
        sys.exit(f"--size must look like 1920x1080 or 1080x1920, got {a.size!r}")
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
        draw_placeholder(path, i, total, filename, out_w, out_h)
        made.append(path)
        print(f"  [{i:>2}/{total}] wrote   {os.path.relpath(path)}")

    verb = "would create" if a.dry_run else "created"
    print(f"\nOK  {verb} {len(made)}, kept {kept} existing, skipped {skipped}")
    if made and not a.dry_run:
        print(f"    {out_w}x{out_h} branded stills, one per section")
        print("    now: python3 tools/build_longform.py --spec "
              f"{a.spec} --audio ... --chunks ... --out ... --ken-burns")
    elif kept and not a.dry_run:
        print("    every section already has a still - nothing to do "
              "(pass --overwrite to replace)")


if __name__ == "__main__":
    main()
