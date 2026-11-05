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
  AZURE_SPEECH_KEY=... AZURE_SPEECH_REGION=eastus \
    python3 tools/make_voice.py --spec specs/video1.json --engine azure

Engines: `edge` (default) is free but rides Microsoft's unofficial Edge Read Aloud
endpoint, which carries no commercial-use grant. `azure` speaks the *same* voices
through the licensed Azure Speech API for about twelve cents per video of this length,
so the voice you auditioned is the voice you ship, legally.

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
import time

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


AZURE_URL = "https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
AZURE_FMT = "audio-24khz-48kbitrate-mono-mp3"


class TTSRetryable(Exception):
    """A failure worth retrying: a throttle, a 5xx, or a dropped connection.

    Deliberately distinct from SystemExit. A bad key or a malformed voice name will
    never fix itself, so those still exit immediately instead of burning 3 attempts on
    a 9-minute render.
    """


def with_retry(fn, what, attempts=3, base_delay=1.5):
    """Run a network call, retrying transient failures with exponential backoff.

    A long render makes 100+ endpoint calls; without this, one dropped connection an
    hour in discards the whole run. SystemExit (bad credentials, bad SSML) is not an
    Exception, so it propagates without being retried.
    """
    last = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 - endpoint libraries raise a wide variety
            last = e
            if i == attempts - 1:
                break
            delay = base_delay * (2 ** i)
            print(f"    retry {i + 1}/{attempts - 1} in {delay:.1f}s "
                  f"({type(e).__name__}: {str(e)[:90]})")
            time.sleep(delay)
    raise SystemExit(f"{what} failed after {attempts} attempts: "
                     f"{type(last).__name__}: {last}")


def synth_edge(text, voice, rate, mp3_path):
    """Free edge-tts path, wrapped so both tools share one call shape."""
    return asyncio.run(short().synth(text, voice, rate, mp3_path))


def azure_credentials():
    """Read Azure config from the environment. Never from argv, never hardcoded."""
    key = os.environ.get("AZURE_SPEECH_KEY", "")
    region = os.environ.get("AZURE_SPEECH_REGION", "")
    return key, region


def require_azure_credentials():
    key, region = azure_credentials()
    if not (key and region):
        sys.exit("--engine azure needs AZURE_SPEECH_KEY and AZURE_SPEECH_REGION in the "
                 "environment, e.g.\n"
                 "  export AZURE_SPEECH_KEY=...  AZURE_SPEECH_REGION=eastus")
    return key, region


def synth_azure(text, voice, rate, mp3_path, key, region):
    """Speak through the licensed Azure Speech endpoint using the same voice names.

    edge-tts and Azure expose the same Microsoft neural voices, so a voice chosen by
    audition survives the switch. The difference is legal: this endpoint is licensed
    for monetised use, and a script this size costs about twelve cents. There is no
    word-boundary stream on the batch REST call, so captions fall back to
    silence-based estimates instead of exact per-word timings.
    """
    import urllib.error
    import urllib.request
    from xml.sax.saxutils import escape, quoteattr

    ssml = (f"<speak version='1.0' xml:lang='en-US'>"
            f"<voice name={quoteattr(voice)}>"
            f"<prosody rate={quoteattr(rate)}>{escape(text)}</prosody>"
            f"</voice></speak>")
    req = urllib.request.Request(AZURE_URL.format(region=region),
                                 data=ssml.encode("utf-8"), method="POST")
    req.add_header("Ocp-Apim-Subscription-Key", key)
    req.add_header("Content-Type", "application/ssml+xml")
    req.add_header("X-Microsoft-OutputFormat", AZURE_FMT)
    req.add_header("User-Agent", "nokia-channel-voice")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            audio = resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        if e.code in (408, 429) or 500 <= e.code < 600:
            raise TTSRetryable(f"azure tts {e.code}: {detail}") from e
        # 401/403 bad key, 400 bad SSML, 404 bad region: retrying cannot help.
        raise SystemExit(f"azure tts {e.code} for {voice}: {detail}") from e
    except urllib.error.URLError as e:
        # DNS, TLS, proxy, timeout: the class of failure that retries actually fix.
        raise TTSRetryable(f"azure tts unreachable ({region}): {e.reason}") from e
    if len(audio) < 512:
        raise TTSRetryable(f"azure tts returned no audio for {voice}")
    with open(mp3_path, "wb") as f:
        f.write(audio)
    return mp3_path


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
                "assets": s.get("assets") or [],
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
    ap.add_argument("--engine", default="edge", choices=["edge", "azure"],
                    help="edge = free unofficial endpoint; azure = licensed, paid, same voices")
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
    engine = a.engine
    az_key = az_region = ""
    if engine == "azure":
        az_key, az_region = require_azure_credentials()
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
    print(f"  voice {voice} @ {rate} | engine {engine} | {len(sections)} sections "
          f"| {total_words} words")
    for i, s in enumerate(sections, 1):
        stem = f"{i:02d}_{s['id']}"
        mp3 = os.path.join(dest, stem + ".mp3")
        if engine == "azure":
            with_retry(lambda: synth_azure(s["text"], voice, rate, mp3, az_key, az_region),
                       f"section {s['id']}")
            words = short().timings_from_audio(mp3, s["text"])
        else:
            words = with_retry(lambda: synth_edge(s["text"], voice, rate, mp3),
                               f"section {s['id']}")
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
               "engine": engine, "gap": a.gap, "sections": len(manifest),
               "words": total_words, "duration": round(total, 3),
               "words_per_sec": round(total_words / total, 3) if total else 0,
               "items": manifest}
    with open(os.path.join(dest, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"OK  {dest}")
    print(f"    runtime {mmss(total)} ({total:.1f}s) | {total_words} words | "
          f"{len(sections)} sections")
    print(f"    {total_words / total:.2f} words/sec | voice {voice} @ {rate} | {engine}")


if __name__ == "__main__":
    main()
