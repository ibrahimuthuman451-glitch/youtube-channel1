#!/usr/bin/env python3
"""Audition every en-US voice on a real line from the script, so you pick it by ear.

Picking a narrator from a list of names is guesswork. This reads the identical
sentence in every available US voice at the identical rate and hands you a folder of
MP3s plus a page with a player per voice, so the decision takes two minutes.

Usage:
  python3 tools/voice_audition.py
  python3 tools/voice_audition.py --gender Male
  python3 tools/voice_audition.py --spec specs/video1.json --section hook
  python3 tools/voice_audition.py --text "Custom line to audition." --rate "-4%"
  python3 tools/voice_audition.py --montage     # + one file where each voice names itself

Then use the winner everywhere:

  python3 tools/make_voice.py --spec specs/video1.json --voice en-US-AndrewNeural
"""
import argparse
import asyncio
import html
import json
import os
import re
import sys

import edge_tts

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from make_voice import concat, make_silence, mmss, short  # noqa: E402

DEFAULT_TEXT = (
    "Here is a company that spent fourteen straight years as the largest phone maker "
    "on Earth. And here is the same company, six years later, selling its entire phone "
    "business and walking away from it."
)


def spoken_label(short_name):
    """en-US-AndrewMultilingualNeural -> 'Andrew Multilingual', for the montage."""
    s = short_name
    if s.startswith("en-US-"):
        s = s[len("en-US-"):]
    if s.endswith("Neural"):
        s = s[:-len("Neural")]
    return re.sub(r"(?<!^)(?=[A-Z])", " ", s).strip()


def build_montage(dest, voices, rate, out_path):
    """One listenable file: each voice says its own name, then reads the same line.

    Picking a narrator means A/B-ing them back to back, which a folder of files makes
    awkward. This is the artefact you actually send yourself and play once.
    """
    tmpdir = os.path.join(dest, "_labels")
    os.makedirs(tmpdir, exist_ok=True)
    seq = []
    for i, v in enumerate(voices):
        label = os.path.join(tmpdir, f"label_{i:02d}.mp3")
        asyncio.run(short().synth(spoken_label(v["ShortName"]) + ".",
                                  v["ShortName"], rate, label))
        seq.append(label)
        seq.append(os.path.join(dest, v["ShortName"] + ".mp3"))
    gap = os.path.join(dest, "_gap.mp3")
    make_silence(gap, 0.45)
    try:
        concat(seq, gap, out_path)
    finally:
        for name in os.listdir(tmpdir):
            os.remove(os.path.join(tmpdir, name))
        os.rmdir(tmpdir)
        os.remove(gap)
    return out_path


def first_sentences(text, n=2):
    """Trim a section down to a couple of sentences: enough to judge tone and pace."""
    text = (text or "").replace("? ", ". ").strip()
    parts = [p for p in text.split(". ") if p.strip()]
    out = ". ".join(parts[:n]).strip()
    return out + "." if out and not out.endswith(".") else out


def sample_text(a):
    """Prefer a real section of the real script over a made-up line."""
    if a.text:
        return a.text.strip()
    if not a.spec:
        return DEFAULT_TEXT
    with open(a.spec, encoding="utf-8") as f:
        spec = json.load(f)
    sections = spec.get("sections") or []
    if a.section:
        for s in sections:
            if s.get("id") == a.section:
                return first_sentences(s.get("text"))
        sys.exit(f"{a.spec} has no section id {a.section!r}")
    if sections:
        return first_sentences(sections[0].get("text"))
    return (spec.get("script") or DEFAULT_TEXT).strip()


def pick_voices(locale, gender):
    voices = asyncio.run(edge_tts.list_voices())
    out = [v for v in voices if v.get("Locale") == locale]
    if gender and gender.lower() != "all":
        out = [v for v in out if (v.get("Gender") or "").lower() == gender.lower()]
    return sorted(out, key=lambda v: v["ShortName"])


def write_index(dest, rows, text, rate):
    lines = ["# Voice audition", "",
             f"**Line:** {text}", "",
             f"**Rate:** {rate} · identical text, identical settings, {len(rows)} voices.",
             "", "| Voice | Gender | Length | Words/sec | File |", "|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| `{r['voice']}` | {r['gender']} | {mmss(r['dur'])} | "
                     f"{r['wps']:.2f} | `{r['file']}` |")
    with open(os.path.join(dest, "index.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    cards = []
    for r in rows:
        cards.append(
            f'<div class="c"><div class="n">{html.escape(r["voice"])}</div>'
            f'<div class="m">{r["gender"]} &middot; {mmss(r["dur"])} &middot; '
            f'{r["wps"]:.2f} w/s</div>'
            f'<audio controls preload="none" src="{html.escape(r["file"])}"></audio></div>')
    page = f"""<!doctype html><meta charset="utf-8"><title>Voice audition</title>
<style>
body{{background:#111;color:#eee;font:15px/1.5 -apple-system,Segoe UI,sans-serif;margin:0;padding:28px}}
h1{{font-size:20px;margin:0 0 6px}}p{{color:#999;margin:0 0 22px;max-width:70ch}}
.grid{{display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(320px,1fr))}}
.c{{background:#1b1b1b;border:1px solid #2c2c2c;border-radius:10px;padding:14px}}
.n{{font-weight:600;color:#f5d90a}}.m{{color:#888;font-size:12px;margin:2px 0 10px}}
audio{{width:100%}}
</style>
<h1>Voice audition</h1>
<p>{html.escape(text)}<br>Rate {html.escape(rate)} &middot; {len(rows)} US voices</p>
<div class="grid">{''.join(cards)}</div>
"""
    with open(os.path.join(dest, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)


def main():
    sys.stdout.reconfigure(line_buffering=True)
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", help="audition a real section from this spec")
    ap.add_argument("--section", help="section id inside --spec (default: the first)")
    ap.add_argument("--text", help="override the sample line")
    ap.add_argument("--locale", default="en-US")
    ap.add_argument("--gender", default="all", choices=["all", "Male", "Female"])
    ap.add_argument("--rate", default="+0%")
    ap.add_argument("--outdir", default="out/voice/audition")
    ap.add_argument("--montage", action="store_true",
                    help="also build one file where every voice names itself, for A/B listening")
    a = ap.parse_args()

    text = sample_text(a)
    dest = a.outdir
    os.makedirs(dest, exist_ok=True)

    voices = pick_voices(a.locale, a.gender)
    if not voices:
        sys.exit(f"no {a.locale} voices matched gender={a.gender}")

    print(f"auditioning {len(voices)} {a.locale} voices")
    print(f"line: {text[:80]}{'...' if len(text) > 80 else ''}")
    rows = []
    for i, v in enumerate(voices, 1):
        name = v["ShortName"]
        mp3 = os.path.join(dest, name + ".mp3")
        words = asyncio.run(short().synth(text, name, a.rate, mp3))
        dur = short().duration_of(mp3)
        nwords = len(words) or len(text.split())
        row = {"voice": name, "gender": v.get("Gender", "?"), "file": name + ".mp3",
               "dur": dur, "wps": nwords / dur if dur else 0}
        rows.append(row)
        print(f"  [{i:>2}/{len(voices)}] {name:<42} {dur:5.2f}s  {row['wps']:.2f} w/s")

    write_index(dest, rows, text, a.rate)

    if a.montage:
        montage = build_montage(dest, voices, a.rate,
                                os.path.join(dest, "montage.mp3"))
        print(f"  montage {os.path.relpath(montage)}  "
              f"{short().duration_of(montage):.1f}s  ({len(voices)} voices)")

    fastest = max(rows, key=lambda r: r["wps"])
    slowest = min(rows, key=lambda r: r["wps"])
    print(f"\nOK  {dest}")
    print(f"    {len(rows)} files | fastest {fastest['voice']} "
          f"({fastest['wps']:.2f} w/s), slowest {slowest['voice']} "
          f"({slowest['wps']:.2f} w/s)")
    print(f"    listen: {os.path.join(dest, 'index.html')}")


if __name__ == "__main__":
    main()
