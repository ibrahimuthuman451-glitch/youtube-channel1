#!/usr/bin/env python3
"""Turn a script + still image into a finished 9:16 vertical video. Free, no watermark.

Pipeline: edge-tts (free neural voice, word-level timings) -> ASS captions -> ffmpeg
with a Ken Burns move. No API keys, no credits, no uploads.

Usage:
  python3 tools/make_short.py --script "text" --image a.jpg --out b.mp4
  python3 tools/make_short.py --spec specs/short3.json --out out/short3.mp4
"""
import argparse
import asyncio
import json
import os
import re
import subprocess
import sys

import edge_tts
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()

W, H, FPS = 1080, 1920, 30
CW, CH = W * 2, H * 2  # compose at 2x so the zoom move stays sharp
FG_FRAC = 0.55  # share of frame height the sharp image should occupy
FONT = "DejaVu Sans"
MARGIN_V = 340  # sits in the blurred band below the image, clear of platform UI


def duration_of(path):
    """ffprobe is not shipped with imageio-ffmpeg, so read Duration from stderr."""
    p = subprocess.run([FF, "-hide_banner", "-i", path], capture_output=True, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", p.stderr or "")
    if not m:
        raise RuntimeError(f"could not read duration of {path}")
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


async def synth(text, voice, rate, mp3_path):
    """Render speech and return per-word timings.

    edge-tts 7.x emits SentenceBoundary only, so each sentence's real duration is
    distributed across its words weighted by length plus punctuation pauses.
    """
    comm = edge_tts.Communicate(text, voice, rate=rate)
    words, sentences = [], []
    with open(mp3_path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append({
                    "text": chunk["text"],
                    "start": chunk["offset"] / 1e7,
                    "end": (chunk["offset"] + chunk["duration"]) / 1e7,
                })
            elif chunk["type"] == "SentenceBoundary":
                sentences.append({
                    "text": chunk["text"],
                    "start": chunk["offset"] / 1e7,
                    "end": (chunk["offset"] + chunk["duration"]) / 1e7,
                })
    if words:
        return words
    return expand_sentences(sentences)


def expand_sentences(sentences):
    """Distribute each sentence duration across its words."""
    out = []
    for s in sentences:
        toks = s["text"].split()
        if not toks:
            continue
        weights = []
        for t in toks:
            w = len(t.strip(".,!?;:—\"'()")) + 2
            if t.endswith(","):
                w += 2.5
            elif t.endswith((".", "!", "?", ";", ":")):
                w += 4.0
            weights.append(w)
        total = sum(weights) or 1.0
        span = max(0.05, s["end"] - s["start"])
        t0 = s["start"]
        for tok, wt in zip(toks, weights):
            d = span * wt / total
            out.append({"text": tok, "start": t0, "end": t0 + d})
            t0 += d
    return out


def group_cards(words, max_words=3):
    """Group words into short caption cards, breaking on punctuation."""
    cards, cur = [], []
    for w in words:
        cur.append(w)
        trimmed = w["text"].strip()
        if len(cur) >= max_words or trimmed.endswith((".", "!", "?", ",", ":", ";", "—")):
            cards.append(cur)
            cur = []
    if cur:
        cards.append(cur)
    return [{"text": " ".join(x["text"].strip() for x in c),
             "start": c[0]["start"], "end": c[-1]["end"]} for c in cards]


def ass_time(t):
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def prepare_frame(src, dst, mode="auto"):
    """Build a 1080x1920 frame from a landscape still.

    Landscape art loses most of its content to a 9:16 crop, so 'blur' composites a
    blurred, darkened copy behind an uncropped foreground — the standard vertical
    treatment. 'crop' centre-crops instead, which suits already-tall images.
    """
    from PIL import Image, ImageFilter, ImageEnhance

    im = Image.open(src).convert("RGB")
    w, h = im.size
    if mode == "auto":
        mode = "crop" if (w / h) <= 1.02 else "blur"

    if mode == "crop":
        s = max(CW / w, CH / h)
        im2 = im.resize((max(CW, int(w * s + 0.5)), max(CH, int(h * s + 0.5))), Image.LANCZOS)
        left = (im2.width - CW) // 2
        top = (im2.height - CH) // 2
        im2.crop((left, top, left + CW, top + CH)).save(dst, quality=95)
        return mode

    # Blurred fill background
    s = max(CW / w, CH / h)
    bg = im.resize((max(CW, int(w * s + 0.5)), max(CH, int(h * s + 0.5))), Image.LANCZOS)
    left = (bg.width - CW) // 2
    top = (bg.height - CH) // 2
    bg = bg.crop((left, top, left + CW, top + CH))
    bg = bg.filter(ImageFilter.GaussianBlur(radius=68))
    bg = ImageEnhance.Brightness(bg).enhance(0.52)

    # Sharp foreground: fill at least FG_FRAC of the height, cropping sides if needed
    s = max(CW / w, (FG_FRAC * CH) / h)
    fg = im.resize((max(1, int(w * s + 0.5)), max(1, int(h * s + 0.5))), Image.LANCZOS)
    if fg.width > CW:
        cut = (fg.width - CW) // 2
        fg = fg.crop((cut, 0, cut + CW, fg.height))
    if fg.height > CH:
        fg = fg.crop((0, 0, fg.width, CH))
    bg.paste(fg, ((CW - fg.width) // 2, (CH - fg.height) // 2))
    bg.save(dst, quality=95)
    return mode


def build_ass(cards, path):

    """White captions, with numeric cards pushed to yellow for emphasis."""
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Base,{FONT},66,&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,1,0,1,7,0,2,60,60,{MARGIN_V},1
Style: Pop,{FONT},92,&H0000D7FF,&H00101010,&H80000000,-1,0,0,0,100,100,1,0,1,8,0,2,60,60,{MARGIN_V},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for i, c in enumerate(cards):
        # Cards tile the timeline: each one holds until the next begins, so exactly
        # one card is ever on screen (overlapping cards looked broken).
        if i + 1 < len(cards):
            end = cards[i + 1]["start"]
        else:
            end = c["end"] + 0.25
        text = c["text"].replace("\n", " ").strip()
        style = "Pop" if any(ch.isdigit() for ch in text) else "Base"
        lines.append(
            f"Dialogue: 0,{ass_time(c['start'])},{ass_time(end)},{style},,0,0,0,,"
            f"{text}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(lines) + "\n")


def build_video(image, audio, ass, out, dur):
    # Image is already composed at 2160x3840; slow zoom-in, then burn captions.
    vf = (
        f"zoompan=z='min(1.0+0.0011*on,1.14)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d=1:s={W}x{H}:fps={FPS},"
        f"eq=contrast=1.06:saturation=1.05,"
        f"subtitles={ass},"
        f"scale=out_range=tv,format=yuv420p"
    )
    cmd = [
        FF, "-y", "-hide_banner", "-loglevel", "error",
        "-loop", "1", "-framerate", str(FPS), "-i", image,
        "-i", audio,
        "-vf", vf,
        "-t", f"{dur:.2f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", "-shortest",
        out,
    ]
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script")
    ap.add_argument("--spec", help="JSON spec with script + image")
    ap.add_argument("--image")
    ap.add_argument("--out", required=True)
    ap.add_argument("--voice", default="en-US-ChristopherNeural")
    ap.add_argument("--rate", default="+0%")
    ap.add_argument("--fit", default="auto", choices=["auto", "crop", "blur"])
    ap.add_argument("--workdir", default="/workspace/.render")
    a = ap.parse_args()

    script, image = a.script, a.image
    if a.spec:
        spec = json.load(open(a.spec))
        script, image = spec["script"], spec["image"]

    if not script or not image:
        sys.exit("need --script/--image or --spec with both")
    os.makedirs(a.workdir, exist_ok=True)
    outdir = os.path.dirname(os.path.abspath(a.out))
    os.makedirs(outdir, exist_ok=True)

    base = os.path.splitext(os.path.basename(a.out))[0]
    mp3 = os.path.join(a.workdir, base + ".mp3")
    ass = os.path.join(a.workdir, base + ".ass")
    frame = os.path.join(a.workdir, base + "_frame.jpg")

    mode = prepare_frame(image, frame, a.fit)
    words = asyncio.run(synth(script, a.voice, a.rate, mp3))
    if not words:
        sys.exit("TTS returned no word timings — check network")
    cards = group_cards(words)
    build_ass(cards, ass)
    dur = duration_of(mp3)
    build_video(frame, mp3, ass, a.out, dur)

    print(f"OK  {a.out}")
    print(f"    duration {dur:.2f}s | {len(words)} words | {len(cards)} caption cards")
    print(f"    {len(words)/dur:.2f} words/sec | fit mode: {mode}")


if __name__ == "__main__":
    main()

