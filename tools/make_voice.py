#!/usr/bin/env python3
"""Generate the voiceover for a script spec: one MP3 per section, plus captions.

This is the step the earlier series was missing. make_short.py needs a still image
before it will produce any audio, so a script with no art got no voice. This tool
needs nothing but the words, so narration can be generated, timed, proof-heard and
re-cut long before the artwork exists.

It also works on the eight short specs untouched:

  python3 tools/make_voice.py --spec specs/video1.json
  python3 tools/make_voice.py --spec specs/short1.json
  python3 tools/make_voice.py --spec specs/video1.json --voice en-GB-RyanNeural --rate "-4%"
  python3 tools/make_voice.py --spec specs/video1.json --dry-run

Spec shape: either a flat script ({"script": "..."} like specs/shortN.json) or a
long-form section list ({"sections": [{"id", "title", "text", "asset"}]}).

Outputs, under out/voice/<slug>/:
  01_hook.mp3            per-section speech
  01_hook.words.json     per-section word timings (for any later alignment)
  narration.mp3          all sections joined with a clean gap
  narration.srt          subtitles on the joined timeline
  script.txt             plain narration, one section per paragraph
  manifest.json          durations, word counts, start timecodes

Word timings reuse make_short.synth, so a section rendered here aligns exactly the
same way it would if it had been rendered straight into a video.
"""
import argparse
import asyncio
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

DEFAULT_VOICE = "en-US-ChristopherNeural"
DEFAULT_GAP = 0.55  # half a second of silence between sections, per the voice guide

_short = None


def short():
    """Import the renderer lazily so --dry-run works with no deps installed."""
    global _short
    if _short is None:
        import make_short  # noqa: E402  (deliberate late import)
        _short = make_short
    return _short


def slugify(text):
    text = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return text or "voice"


def sections_from_spec(spec):
    """Accept both spec shapes and always return a list of {id, title, text, asset}."""
    raw = spec.get("sections")
    if raw:
        out = []
        for i, s in enumerate(raw, 1):
            text = (s.get("text") or "").strip()
            if not text:
                continue
            out.append({
                "id": slugify(s.get("id") or f"section-{i}"),
                "title": s.get("title") or s.get("id") or f"Section {i}",
                "text": text,
                "asset": s.get("asset") or "",
            })
        return out
    text = (spec.get("script") or "").strip()
    if not text:
        return []
    name = spec.get("name") or "script"
    return [{"id": slugify(name), "title": name, "text": text, "asset": spec.get("image") or ""}]


def srt_time(t):
    """SRT wants 00:00:01,240 - comma decimals, always two-digit hours."""
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    ms = int(round((s - int(s)) * 1000))
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{ms:03d}"


def srt_cues(words, max_words=9, max_chars=64):
    """Long-form cues: sentence-led lines, capped in both words and characters."""
    cues, cur = [], []
    for w in words:
        cur.append(w)
        tok = w["text"].strip()
        long_enough = len(" ".join(x["text"].strip() for x in cur)) >= max_chars
        if (len(cur) >= max_words or long_enough
                or tok.endswith((".", "!", "?", ":", ";", "\u2014"))):
            cues.append(cur)
            cur = []
    if cur:
        cues.append(cur)
    return [{"text": " ".join(x["text"].strip() for x in c),
             "start": c[0]["start"], "end": c[-1]["end"]} for c in cues]


def mmss(t):
    return f"{int(t // 60)}:{int(t % 60):02d}"


def make_silence(path, seconds):
    short().run_ff(["-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                    "-t", f"{seconds:.3f}", "-ar", "24000", "-ac", "1", path])


def concat(parts, gap_file, out):
    """Join sections in order with the gap between them, re-encoded to a single track."""
    listing = os.path.join(os.path.dirname(os.path.abspath(out)), "_concat.txt")
    with open(listing, "w", encoding="utf-8") as f:
        for i, p in enumerate(parts):
            if i and gap_file:
                f.write("file '%s'\n" % os.path.abspath(gap_file).replace("'", "'\\''"))
            f.write("file '%s'\n" % os.path.abspath(p).replace("'", "'\\''"))
    try:
        short().run_ff(["-f", "concat", "-safe", "0", "-i", listing,
                        "-ar", "24000", "-ac", "1",
                        "-c:a", "libmp3lame", "-b:a", "192k", out])
    finally:
        os.remove(listing)


def main():
    # Line-buffer stdout: a 9 minute render is nearly always piped to a log or a
    # tee, and block buffering makes it look hung. build_series.py flushes per
    # print for the same reason.
    sys.stdout.reconfigure(line_buffering=True)
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True, help="spec JSON: sections list or flat script")
    ap.add_argument("--voice", help="override the spec's voice")
    ap.add_argument("--rate", help="override the spec's rate, e.g. -4%%")
    ap.add_argument("--gap", type=float, default=DEFAULT_GAP,
                    help="silence between sections, seconds")
    ap.add_argument("--outdir", default="out/voice")
    ap.add_argument("--wpm", type=float, default=150.0,
                    help="words per minute used by --dry-run estimates")
    ap.add_argument("--dry-run", action="store_true",
                    help="count words and estimate runtime; no network, no audio")
    ap.add_argument("--no-concat", action="store_true", help="skip the joined narration.mp3")
    a = ap.parse_args()

    if not os.path.isfile(a.spec):
        sys.exit(f"spec not found: {a.spec}")
    with open(a.spec, encoding="utf-8") as f:
        spec = json.load(f)
    sections = sections_from_spec(spec)
    if not sections:
        sys.exit(f"{a.spec}: no 'sections' text or 'script' found")

    voice = a.voice or spec.get("voice") or DEFAULT_VOICE
    rate = a.rate if a.rate is not None else (spec.get("rate") or "+0%")
    name = spec.get("name") or os.path.splitext(os.path.basename(a.spec))[0]
    slug = slugify(name)
    total_words = sum(len(s["text"].split()) for s in sections)

    if a.dry_run:
        span = total_words / (a.wpm / 60.0)
        print(f"{a.spec}  ({len(sections)} sections, {total_words} words)")
        print(f"  estimate {mmss(span)} at {a.wpm:.0f} wpm, "
              f"plus {a.gap}s x {max(0, len(sections) - 1)} gaps")
        for s in sections:
            d = len(s["text"].split()) / (a.wpm / 60.0)
            print(f"  {s['id']:<12} {len(s['text'].split()):>4}w  ~{d:6.1f}s  {s['asset']}")
        return

    dest = os.path.join(a.outdir, slug)
    os.makedirs(dest, exist_ok=True)

    parts, manifest, offset = [], [], 0.0
    print(name)
    print(f"  voice {voice} @ {rate} | {len(sections)} sections | {total_words} words")
    for i, s in enumerate(sections, 1):
        stem = f"{i:02d}_{s['id']}"
        mp3 = os.path.join(dest, stem + ".mp3")
        words = asyncio.run(short().synth(s["text"], voice, rate, mp3))
        if not words:
            sys.exit(f"{s['id']}: no word timings produced - check network or input")
        with open(os.path.join(dest, stem + ".words.json"), "w", encoding="utf-8") as f:
            json.dump(words, f, indent=1)
        dur = short().duration_of(mp3)
        parts.append(mp3)
        manifest.append({"id": s["id"], "title": s["title"], "asset": s["asset"],
                         "file": os.path.basename(mp3), "words": len(words),
                         "duration": round(dur, 3), "start": round(offset, 3)})
        print(f"  [{i:>2}/{len(sections)}] {stem:<36} {dur:6.2f}s "
              f"{len(words):>4}w  start {mmss(offset)}")
        offset += dur + a.gap

    total = sum(m["duration"] for m in manifest) + a.gap * max(0, len(manifest) - 1)

    if not a.no_concat:
        gap_file = os.path.join(dest, "_gap.mp3")
        make_silence(gap_file, a.gap)
        joined = os.path.join(dest, "narration.mp3")
        concat(parts, gap_file, joined)
        os.remove(gap_file)

        cues = []
        for m in manifest:
            wpath = os.path.join(dest, os.path.splitext(m["file"])[0] + ".words.json")
            with open(wpath, encoding="utf-8") as f:
                words = json.load(f)
            for c in srt_cues(words):
                cues.append({"text": c["text"], "start": c["start"] + m["start"],
                             "end": c["end"] + m["start"]})
        srt = os.path.join(dest, "narration.srt")
        with open(srt, "w", encoding="utf-8") as f:
            for i, c in enumerate(cues, 1):
                f.write(f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n"
                        f"{c['text']}\n\n")
        joined_dur = short().duration_of(joined)
        print(f"  joined {os.path.relpath(joined)}  {joined_dur:.2f}s  {len(cues)} cues")

    with open(os.path.join(dest, "script.txt"), "w", encoding="utf-8") as f:
        for s in sections:
            f.write(s["text"] + "\n\n")

    summary = {"name": name, "spec": a.spec, "voice": voice, "rate": rate,
               "gap": a.gap, "sections": len(manifest), "words": total_words,
               "duration": round(total, 3),
               "words_per_sec": round(total_words / total, 3) if total else 0,
               "items": manifest}
    with open(os.path.join(dest, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"OK  {dest}")
    print(f"    runtime {mmss(total)} ({total:.1f}s) | {total_words} words | "
          f"{len(sections)} sections")
    print(f"    {total_words / total:.2f} words/sec | voice {voice} @ {rate}")


if __name__ == "__main__":
    main()
