#!/usr/bin/env python3
"""Assemble a 16:9 long-form master from a script spec, its narration, and its timings.

This assembles a 16:9 long-form master from a spec, its narration, and its timings.

Each section shows its still from `--assets` (cover-cropped to 1920x1080), or a dark card
when that still is not there yet, with a scrim behind the captions and the title so both
stay legible over a photo. Text is drawn by the ASS layer rather than drawtext: the prose
is full of apostrophes and colons that would have to be escaped into the filter graph.
Sections are tiled end to end from the measured chunk timeline, so the pauses between
sections never leave a hole in the picture.

Inputs come from a perform_script.py run, so captions and section boundaries are the
measured ones rather than guesses.

  python3 tools/build_longform.py --spec specs/video1.json \\
      --audio out/perform/video-1-how-nokia-lost-everything/en-us-christopherneural.mp3 \\
      --chunks out/perform/video-1-how-nokia-lost-everything/en-us-christopherneural.chunks.json \\
      --out out/video/video1_master.mp4
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from make_short import FONT, run_ff  # noqa: E402
from make_voice import sections_from_spec  # noqa: E402
from perform_script import split_sentences  # noqa: E402

W, H, FPS = 1920, 1080, 30
WHITE = "&H00FFFFFF"
YELLOW = "&H0000D7FF"   # ASS colours are &HAABBGGRR, so this is the brand yellow


def ass_time(t):
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def section_ranges(sections, chunks):
    """Map each spec section onto the measured chunk timeline.

    perform_script.py split the whole script into sentences in order, so a section owns
    a contiguous run of chunks. If the counts do not line up then the sections were
    split differently and every title would sit on the wrong beat, so this reports the
    mismatch instead of drifting silently.
    """
    ranges, i = [], 0
    for s in sections:
        n = len(split_sentences(s.get("text", "")))
        span = chunks[i:i + n]
        if not span:
            break
        ranges.append({"title": s.get("title") or s.get("id", ""),
                       "start": span[0]["start"],
                       "end": span[-1]["start"] + span[-1]["duration"]})
        i += len(span)
    return ranges, i


def build_bg(path):
    """Dark card with a soft vertical gradient: quiet enough that captions stay the subject."""
    from PIL import Image
    bg = Image.new("RGB", (W, H), (14, 14, 16))
    px = bg.load()
    for y in range(H):
        v = int(10 + 16 * (y / H))
        row = (v, v, v + 3)
        for x in range(W):
            px[x, y] = row
    bg.save(path, quality=95)
    return path


def build_ass(ranges, chunks, path):
    """Two layers of text: the section title up top, the spoken sentence at the bottom."""
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Title,{FONT},58,{YELLOW},&H00101010,&H80000000,-1,0,0,0,100,100,1,0,1,6,0,8,120,120,80,1
Style: Cap,{FONT},46,{WHITE},&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,5,0,2,150,150,100,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for r in ranges:
        lines.append(f"Dialogue: 0,{ass_time(r['start'])},{ass_time(r['end'])},"
                     f"Title,,0,0,0,,{r['title']}")
    for c in chunks:
        end = c["start"] + c["duration"] + 0.15
        text = c["text"].replace("\n", " ").strip()
        lines.append(f"Dialogue: 0,{ass_time(c['start'])},{ass_time(end)},"
                     f"Cap,,0,0,0,,{text}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(lines) + "\n")
    return path


def resolve_still(asset, assets_dir):
    """Map a spec asset path onto a real file, or None if it is not there yet.

    Spec paths look like `assets/video1/00_thumb.jpg`. Only the part after `assets/` is
    used, so `--assets /tmp/testset` can point at a stand-in set without editing specs.
    """
    if not asset:
        return None
    rel = asset[len("assets/"):] if asset.startswith("assets/") else asset
    p = os.path.join(assets_dir, rel)
    return p if os.path.isfile(p) else None


def normalize_still(src, dst):
    """Cover-fit to 1920x1080.

    `force_original_aspect_ratio=increase` then `crop` is the chain that makes a portrait
    phone photo and a 2.35:1 still both fill the frame without letterboxing or stretching.
    """
    run_ff(["-i", src,
            "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                   f"crop={W}:{H},setsar=1",
            "-frames:v", "1", "-q:v", "2", dst])
    return dst


def build_scrim(path, top_opacity, top_h, bot_opacity, bot_h):
    """A transparent PNG with black ramping in from the top and bottom edges.

    A flat `drawbox` band gives a hard horizontal seam that reads as letterboxing. A
    gradient reads as a deliberate treatment, and it keeps both the title and the
    captions legible over a bright photo without flattening the picture.
    """
    from PIL import Image
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = img.load()
    for y in range(H):
        a = 0.0
        if top_h > 0 and y < top_h:
            a = top_opacity * (1.0 - y / top_h) ** 1.4
        if bot_h > 0 and y >= H - bot_h:
            a = bot_opacity * ((y - (H - bot_h)) / bot_h) ** 1.4
        if a > 0:
            alpha = int(round(255 * min(1.0, a)))
            for x in range(W):
                px[x, y] = (0, 0, 0, alpha)
    img.save(path)
    return path


def ken_burns_chain(idx, frames, zoom_max):
    """A slow push-in, one frame per input frame, travelling 1.0x -> zoom_max.

    Two deliberate differences from the usual snippet:

    * the per-frame step is derived from *this section's* frame count, so a 30s section
      and a 63s section both travel the full zoom across their own length. A fixed
      `zoom+0.0005` reaches the ceiling after 300 frames (10s at 30fps) and then sits
      still for the remaining 53s.
    * it emits exactly one output frame per input frame (`d=1`). The caller loops each
      still with `-loop 1 -t`, so pairing that with `d=<total frames>` would duplicate
      every frame by the section length.

    It also takes the *original* still, not the pre-cropped 1080p one, so the 1.5x
    upscale has real pixels to work with.
    """
    up_w, up_h = W * 3 // 2, H * 3 // 2
    step = (zoom_max - 1.0) / max(1, frames)
    return (f"[{idx}:v]scale={up_w}:{up_h}:force_original_aspect_ratio=increase,"
            f"crop={up_w}:{up_h},"
            f"zoompan=z='min(1+{step:.8f}*on,{zoom_max})':d=1:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"s={W}x{H}:fps={FPS},format=yuv420p,setsar=1[k{idx}]")


def main():
    sys.stdout.reconfigure(line_buffering=True)
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--audio", required=True, help="narration MP3")
    ap.add_argument("--chunks", required=True, help="chunks.json from perform_script.py")
    ap.add_argument("--out", required=True)
    ap.add_argument("--crf", default="23")
    ap.add_argument("--assets", default="assets",
                    help="assets root holding the per-section stills (spec paths are "
                         "relative to it, e.g. assets/video1/01_x.jpg)")
    ap.add_argument("--scrim-height", type=int, default=300,
                    help="height in px of the dark band behind the captions")
    ap.add_argument("--scrim-opacity", type=float, default=0.60,
                    help="opacity of the caption scrim (0-1)")
    ap.add_argument("--title-scrim", type=float, default=0.45,
                    help="opacity of the band behind the section title, so it stays "
                         "legible over a bright photo (0 disables)")
    ap.add_argument("--title-scrim-height", type=int, default=190)
    ap.add_argument("--ken-burns", action="store_true",
                    help="slow push-in on each section (1.0x -> --zoom-max) instead of "
                         "a held still; slower to encode")
    ap.add_argument("--zoom-max", type=float, default=1.15,
                    help="final zoom for --ken-burns")
    a = ap.parse_args()

    for p in (a.spec, a.audio, a.chunks):
        if not os.path.isfile(p):
            sys.exit(f"missing input: {p}")

    with open(a.spec, encoding="utf-8") as f:
        spec = json.load(f)
    with open(a.chunks, encoding="utf-8") as f:
        data = json.load(f)
    chunks = data["items"]

    secs = sections_from_spec(spec)
    ranges, matched = section_ranges(secs, chunks)
    if matched != len(chunks):
        print(f"  WARNING: {len(chunks)} chunks but {matched} matched to sections; "
              f"titles may drift")
    print(spec.get("name", os.path.basename(a.spec)))
    print(f"  {len(chunks)} captions | {len(ranges)} sections | "
          f"{data.get('duration', 0):.1f}s narration")

    # Tile the whole timeline: a section runs until the next one starts, and the last
    # one runs to the end of the audio. Without this, the 0.5s pauses between sections
    # would leave gaps in the picture.
    total = data.get("duration") or (chunks[-1]["start"] + chunks[-1]["duration"])
    durations = []
    for i, r in enumerate(ranges):
        end = ranges[i + 1]["start"] if i + 1 < len(ranges) else total
        durations.append(max(0.5, end - r["start"]))

    stills = [resolve_still(s.get("asset"), a.assets) for s in secs]
    found = sum(1 for s in stills if s)
    if stills:
        print(f"  stills: {found} of {len(stills)} found under {a.assets}/ "
              f"({'card fallback for the rest' if found < len(stills) else 'all sections'})")

    outdir = os.path.dirname(os.path.abspath(a.out))
    os.makedirs(outdir, exist_ok=True)
    work = os.path.join(outdir, "_build")
    os.makedirs(work, exist_ok=True)

    bg = build_bg(os.path.join(work, "bg.jpg"))
    ass = build_ass(ranges, chunks, os.path.join(work, "subs.ass"))

    # Escape the subtitle path: ':' and '\' are filter-graph syntax.
    sub_arg = ass.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")

    enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", a.crf,
           "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-movflags", "+faststart", "-shortest", a.out]

    if found:
        # Ken Burns needs the untouched still for zoom headroom; the static path
        # pre-crops once to 1080p.
        if a.ken_burns:
            paths = [s if s else bg for s in stills]
        else:
            paths = [normalize_still(s, os.path.join(work, f"sec{i:02d}.jpg"))
                     if s else bg for i, s in enumerate(stills)]

        inputs = []
        for path, dur in zip(paths, durations):
            inputs += ["-loop", "1", "-framerate", str(FPS),
                       "-t", f"{dur:.3f}", "-i", path]

        n = len(paths)
        if a.ken_burns:
            chains = "".join(
                ken_burns_chain(i, max(1, int(round(durations[i] * FPS))), a.zoom_max) + ";"
                for i in range(n))
            mode = f"ken burns 1.0x->{a.zoom_max}x"
        else:
            chains = "".join(f"[{i}:v]format=yuv420p,setsar=1[k{i}];" for i in range(n))
            mode = "static stills"
        join = "".join(f"[k{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[bgv];"

        # Gradient scrim overlaid as its own looped input: hard drawbox bands looked
        # like letterboxing on a wide still.
        scrim_png = build_scrim(os.path.join(work, "scrim.png"),
                                a.title_scrim, a.title_scrim_height,
                                a.scrim_opacity, a.scrim_height)
        inputs += ["-loop", "1", "-framerate", str(FPS),
                   "-t", f"{sum(durations):.3f}", "-i", scrim_png]
        # Audio last: the scrim must keep index n so the filter graph can name it.
        inputs += ["-i", a.audio]
        fc = (chains + join +
              f"[bgv]format=yuv420p[b1];"
              f"[{n}:v]format=rgba[s1];"
              f"[b1][s1]overlay=0:0:format=auto,format=yuv420p[sc];"
              f"[sc]subtitles='{sub_arg}'[v]")

        print(f"  encoding 1920x1080 with {found}/{n} stills, {mode} ... "
              f"(several minutes)")
        run_ff(inputs + ["-filter_complex", fc,
                         "-map", "[v]", "-map", f"{n + 1}:a"] + enc)
    else:
        print("  encoding 1920x1080 ... (no stills found, single card)")
        run_ff(["-loop", "1", "-framerate", str(FPS), "-i", bg,
                "-i", a.audio,
                "-vf", f"subtitles='{sub_arg}'"] + enc)

    size = os.path.getsize(a.out) / (1024 * 1024)
    print(f"\nOK  {a.out}")
    print(f"    {size:.1f} MB | {data.get('duration', 0) / 60:.1f} min | "
          f"1920x1080 {FPS}fps | {len(ranges)} titles + {len(chunks)} captions")
    print("    stills: " + (f"{found}/{len(ranges)} sections use a still, the rest fall "
                           f"back to the card" if found else
                           "none found - section cards only"))


if __name__ == "__main__":
    main()
