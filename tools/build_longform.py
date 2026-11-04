#!/usr/bin/env python3
"""Assemble a 16:9 long-form master from a script spec, its narration, and its timings.

This is the long-form cut the pipeline was missing. It is deliberately an *animatic*:
section title, burned caption, and narration on a dark card, because the twelve stills
in the asset manifest are not in the repo yet. Drop those images in later and the same
timeline can carry them instead of the plain background.

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


def main():
    sys.stdout.reconfigure(line_buffering=True)
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--audio", required=True, help="narration MP3")
    ap.add_argument("--chunks", required=True, help="chunks.json from perform_script.py")
    ap.add_argument("--out", required=True)
    ap.add_argument("--crf", default="23")
    a = ap.parse_args()

    for p in (a.spec, a.audio, a.chunks):
        if not os.path.isfile(p):
            sys.exit(f"missing input: {p}")

    with open(a.spec, encoding="utf-8") as f:
        spec = json.load(f)
    with open(a.chunks, encoding="utf-8") as f:
        data = json.load(f)
    chunks = data["items"]

    ranges, matched = section_ranges(sections_from_spec(spec), chunks)
    if matched != len(chunks):
        print(f"  WARNING: {len(chunks)} chunks but {matched} matched to sections; "
              f"titles may drift")
    print(spec.get("name", os.path.basename(a.spec)))
    print(f"  {len(chunks)} captions | {len(ranges)} sections | "
          f"{data.get('duration', 0):.1f}s narration")

    outdir = os.path.dirname(os.path.abspath(a.out))
    os.makedirs(outdir, exist_ok=True)
    work = os.path.join(outdir, "_build")
    os.makedirs(work, exist_ok=True)

    bg = build_bg(os.path.join(work, "bg.jpg"))
    ass = build_ass(ranges, chunks, os.path.join(work, "subs.ass"))

    # Escape the subtitle path: ':' and '\' are filter-graph syntax.
    sub_arg = ass.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    print("  encoding 1920x1080 ... (several minutes for a 9 minute master)")
    run_ff(["-loop", "1", "-framerate", str(FPS), "-i", bg,
            "-i", a.audio,
            "-vf", f"subtitles='{sub_arg}'",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", a.crf,
            "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", "-shortest", a.out])

    size = os.path.getsize(a.out) / (1024 * 1024)
    print(f"\nOK  {a.out}")
    print(f"    {size:.1f} MB | {data.get('duration', 0) / 60:.1f} min | "
          f"1920x1080 {FPS}fps | {len(ranges)} titles + {len(chunks)} captions")
    print("    animatic: section cards plus burned captions. Swap in the 12 stills for "
          "the finished cut.")


if __name__ == "__main__":
    main()
