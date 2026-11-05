#!/usr/bin/env python3
"""Render a script as one performance: verbatim, measured pace, real pauses.

Two things a plain edge-tts call cannot do, and this does:

1. **Half-second pauses at every sentence and em-dash.** The unofficial endpoint
   rejects any SSML Edge itself would not generate, so `<break time="500ms"/>` is
   unavailable. Instead each sentence is synthesised on its own and the pauses are
   actual silence spliced between them.
2. **A pace target measured in words-per-minute.** Because those pauses lengthen the
   file, hitting 150 wpm overall means the speech itself has to run faster than 150.
   The rate is calibrated from a real sample, not guessed.

Financial figures and dates are read slightly slower, which is the only emphasis this
endpoint exposes (per-word stress needs SSML it will not accept).

Note on accuracy: the service's response to `--rate` is not perfectly linear, so a
calibrated run typically lands within about 5% of target rather than exactly on it.
Every run prints the achieved speech and overall wpm, so nudging `--rate` by hand is a
two-second fix if you need it tighter.

Nothing is spoken except the script: no title, no intro, no sign-off.

  python3 tools/perform_script.py --spec specs/video1.json
  python3 tools/perform_script.py --spec specs/video1.json --voice en-US-RogerNeural
  python3 tools/perform_script.py --spec specs/video1.json --wpm 150 --pause 0.5
  python3 tools/perform_script.py --spec specs/video1.json --rate "-5%"   # skip calibration

Publishing path: pass `--engine azure` with AZURE_SPEECH_KEY and AZURE_SPEECH_REGION set.
Same voices, licensed for monetised use (~12 cents for a script this size). Drafts can
stay on the free default engine. A bad key fails fast; throttles and dropped connections
are retried with backoff rather than discarding a 100-call render.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from make_voice import (  # noqa: E402
    concat,
    make_silence,
    mmss,
    require_azure_credentials,
    sections_from_spec,
    slugify,
    short,
    synth_azure,
    synth_edge,
    with_retry,
)

# Financial figures and dates. Digits cover years and percentages; the words cover the
# spelled-out amounts the TTS needs anyway ("five point four billion euros").
FIGURE = re.compile(r"\d|\b(billion|million|thousand|percent|euros?|dollars?)\b", re.I)

# Guard retained at each end of a trimmed clip so consonants are never clipped. Because
# both sides of a join keep this pad, the silence inserted between sentences must be
# reduced by 2 x PAD for the measured pause to equal the requested one.
PAD = 0.05


def split_sentences(text):
    """Split on sentence enders and em-dashes, keeping the punctuation attached."""
    text = re.sub(r"\s+", " ", text or "").strip()
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z"\'(\[])|(?<=\u2014)\s*', text)
    return [p.strip() for p in parts if p.strip()]


def trim_silence(src, dst, pad=PAD, noise="-45dB", min_sil=0.10):
    """Keep the speech plus a small pad; drop only the silence edge-tts adds at the edges.

    A blanket `silenceremove` cut 1.3s out of a 1.9s clip, i.e. it ate word tails as
    well as padding. That both clipped the audio and inflated the measured pace by
    roughly 25%. So the cut points come from detecting where speech actually starts
    and stops, reusing the same silencedetect segmentation make_short.py uses.
    """
    segs = short().speech_segments(src, noise=noise, min_sil=min_sil)
    lead = segs[0][0]
    tail = segs[-1][1]
    start = max(0.0, lead - pad)
    dur = max(0.05, (tail + pad) - start)
    short().run_ff(["-ss", f"{start:.3f}", "-i", src, "-t", f"{dur:.3f}",
                    "-ar", "24000", "-ac", "1",
                    "-c:a", "libmp3lame", "-b:a", "192k", dst])


def measure_wpm(chunks, speak, workdir):
    """Speak a few sentences exactly the way the render will, and report words per minute.

    Measuring one joined paragraph under-reads badly: TTS flows through sentence
    boundaries faster than it speaks a sentence in isolation, and the join includes
    padding that the render trims. Both effects push the computed rate too high, so
    this measures the production path chunk by chunk instead.

    `speak(text, rate, path)` is injected so calibration uses the same engine as the
    render; calibrating on edge-tts and rendering on Azure would mis-set the rate.
    """
    total_words = 0
    total_dur = 0.0
    for i, chunk in enumerate(chunks):
        probe = os.path.join(workdir, f"_cal{i}.mp3")
        trimmed = os.path.join(workdir, f"_cal{i}_trim.mp3")
        speak(chunk, "+0%", probe)
        trim_silence(probe, trimmed)
        total_words += len(chunk.split())
        total_dur += short().duration_of(trimmed)
        os.remove(probe)
        os.remove(trimmed)
    if total_dur <= 0 or total_words == 0:
        raise SystemExit("calibration failed: empty audio")
    return total_words / total_dur * 60.0


def main():
    sys.stdout.reconfigure(line_buffering=True)
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--voice", default="en-US-ChristopherNeural")
    ap.add_argument("--wpm", type=float, default=150.0,
                    help="target pace")
    ap.add_argument("--wpm-basis", default="speech", choices=["speech", "overall"],
                    help="speech = target is the reading pace and pauses are added on top "
                         "(default, matches a '150 wpm narrator' brief); "
                         "overall = target includes the inserted pauses")
    ap.add_argument("--pause", type=float, default=0.5,
                    help="silence at every period and em-dash, seconds")
    ap.add_argument("--rate", help="override calibration, e.g. -5%%")
    ap.add_argument("--engine", default="edge", choices=["edge", "azure"],
                    help="edge = free unofficial endpoint (drafts); azure = licensed, "
                         "paid, same voices (publishing)")
    ap.add_argument("--figure-slower", type=float, default=4.0,
                    help="extra percentage points of slowdown on sentences with figures/dates")
    ap.add_argument("--outdir", default="out/perform")
    a = ap.parse_args()

    if not os.path.isfile(a.spec):
        sys.exit(f"spec not found: {a.spec}")
    with open(a.spec, encoding="utf-8") as f:
        spec = json.load(f)

    sections = sections_from_spec(spec)
    if not sections:
        sys.exit(f"{a.spec}: no 'sections' text or 'script' found")

    # Verbatim only: join the sections as written, add nothing.
    text = " ".join(s["text"].strip() for s in sections)
    chunks = split_sentences(text)
    words = len(text.split())
    pauses = max(0, len(chunks) - 1)
    silence_s = pauses * a.pause

    name = spec.get("name") or os.path.splitext(os.path.basename(a.spec))[0]
    dest = os.path.join(a.outdir, slugify(name))
    os.makedirs(dest, exist_ok=True)

    # One call shape for both engines: text, rate, destination. Calibration and the
    # render both go through it, so the two can never disagree about the engine.
    engine = a.engine
    if engine == "azure":
        az_key, az_region = require_azure_credentials()

        def speak(text, rate_str, path):
            return with_retry(
                lambda: synth_azure(text, a.voice, rate_str, path, az_key, az_region),
                "tts")
    else:
        def speak(text, rate_str, path):
            return with_retry(lambda: synth_edge(text, a.voice, rate_str, path), "tts")

    # The output name is <slugified voice>.mp3 no matter which engine produced it, so an
    # --engine azure run overwrites an edge run in place. Say so before it happens rather
    # than leaving a silently swapped file (and a chunks.json whose provenance flips).
    prev_chunks = os.path.join(dest, f"{slugify(a.voice)}.chunks.json")
    if os.path.isfile(prev_chunks):
        prev_engine = "unknown"
        try:
            with open(prev_chunks, encoding="utf-8") as f:
                prev_engine = json.load(f).get("engine") or "unknown (pre-engine field)"
        except (OSError, ValueError):
            pass
        if prev_engine != engine:
            print(f"  NOTE: {os.path.relpath(dest)}/ already holds a render from "
                  f"{prev_engine};")
            print(f"        this run ({engine}) overwrites it. To keep both, re-run with "
                  f"--outdir out/perform-{engine}.")

    # Calibrate: total budget minus the silence we are about to insert = speech budget.
    if a.rate is not None:
        rate_val = float(a.rate.strip().rstrip("%"))
        measured = None
    else:
        # Sampling the top of the script measures the hook, which is written to be
        # brisker than the body: it read 169 wpm against a true 156. Sample across the
        # whole thing instead, or every render lands several percent slow.
        step = max(1, len(chunks) // 14)
        cal_chunks, seen = [], 0
        for c in chunks[::step]:
            cal_chunks.append(c)
            seen += len(c.split())
            if seen >= 150:
                break
        measured = measure_wpm(cal_chunks, speak, dest)
        if a.wpm_basis == "overall":
            budget = words / a.wpm * 60.0 - silence_s
            if budget <= 0:
                sys.exit(f"--wpm {a.wpm} is impossible with {pauses} pauses of {a.pause}s")
            needed = words / budget * 60.0
        else:
            budget = words / a.wpm * 60.0
            needed = a.wpm
        rate_val = max(-40.0, min(60.0, (needed / measured - 1.0) * 100.0))

    print(f"{name}")
    print(f"  voice {a.voice} | engine {engine} | {words} words | "
          f"{len(chunks)} chunks | {pauses} x {a.pause}s pauses")
    if measured:
        print(f"  measured {measured:.1f} wpm at +0% -> rate {rate_val:+.1f}% "
              f"to land {a.wpm:.0f} wpm ({a.wpm_basis})")

    tmp = os.path.join(dest, "_chunks")
    os.makedirs(tmp, exist_ok=True)
    parts, items, offset = [], [], 0.0
    for i, chunk in enumerate(chunks):
        slow = bool(FIGURE.search(chunk))
        r = rate_val - a.figure_slower if (slow and a.figure_slower) else rate_val
        mp3 = os.path.join(tmp, f"c{i:04d}.mp3")
        speak(chunk, f"{r:+.0f}%", mp3)
        trimmed = os.path.join(tmp, f"t{i:04d}.mp3")
        trim_silence(mp3, trimmed)
        os.remove(mp3)
        dur = short().duration_of(trimmed)
        parts.append(trimmed)
        items.append({"i": i, "text": chunk, "start": round(offset, 3),
                      "duration": round(dur, 3), "rate": round(r, 1), "figure": slow})
        offset += dur + a.pause
        if i % 20 == 0 or i == len(chunks) - 1:
            print(f"  [{i + 1:>3}/{len(chunks)}] {mmss(offset)}  {chunk[:56]}")

    gap = os.path.join(dest, "_pause.mp3")
    make_silence(gap, max(0.0, a.pause - 2 * PAD))
    out = os.path.join(dest, f"{slugify(a.voice)}.mp3")
    concat(parts, gap, out)

    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    os.remove(gap)

    total = short().duration_of(out)
    speech = total - silence_s
    with open(os.path.join(dest, f"{slugify(a.voice)}.chunks.json"), "w",
              encoding="utf-8") as f:
        json.dump({"spec": a.spec, "voice": a.voice, "rate": round(rate_val, 1),
                   "engine": engine,
                   "target_wpm": a.wpm, "wpm_basis": a.wpm_basis, "pause": a.pause,
                   "duration": round(total, 3), "words": words,
                   "overall_wpm": round(words / total * 60.0, 2),
                   "speech_wpm": round(words / speech * 60.0, 2) if speech > 0 else 0,
                   "items": items}, f, indent=1)

    print(f"\nOK  {out}")
    print(f"    runtime {mmss(total)} ({total:.1f}s) | {words} words | "
          f"{len(chunks)} sentences | {pauses} pauses")
    print(f"    overall {words / total * 60:.1f} wpm (target {a.wpm:.0f}) | "
          f"speech-only {words / speech * 60:.1f} wpm | rate {rate_val:+.1f}%")


if __name__ == "__main__":
    main()

