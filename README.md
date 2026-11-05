# Nokia Collapse — script, voice, and video pipeline

Research-backed content on how Nokia lost the phone market, plus the free tooling that
turns a script into narration and a cut. No API keys required for the default path.

## What is in here

| Path | What it is |
|---|---|
| `content/video1-how-nokia-lost-everything.md` | The long-form production pack: 9-minute script, chapter timeline, asset manifest, metadata, retention plan |
| `content/nokia-shorts-pack.md` | 8 vertical shorts derived from the same research |
| `specs/video1.json` | Machine-readable narration (12 sections) — source of truth for audio |
| `specs/short1..8.json` | The shorts, same shape |
| `docs/recording-voice.md` | Voice options, licensing, and what the tools actually do |
| `tools/` | The pipeline (see below) |

## Quickstart

```bash
pip install -r requirements.txt

# see the script and its timing without touching the network
python3 tools/make_voice.py --spec specs/video1.json --dry-run

# narration: one MP3 per section + joined track + SRT + manifest
python3 tools/make_voice.py --spec specs/video1.json

# one continuous take with 0.5s pauses at every sentence, paced to 150 wpm
python3 tools/perform_script.py --spec specs/video1.json

# same take on the licensed engine (same voices, ~11c for this script)
AZURE_SPEECH_KEY=... AZURE_SPEECH_REGION=eastus \
  python3 tools/perform_script.py --spec specs/video1.json --engine azure

# 1080p master with section titles and burned captions
# (drops in any stills found under assets/, card fallback for the rest)
# add --ken-burns for a slow push-in on each section
python3 tools/build_longform.py --spec specs/video1.json \
  --audio out/perform/video-1-how-nokia-lost-everything/en-us-christopherneural.mp3 \
  --chunks out/perform/video-1-how-nokia-lost-everything/en-us-christopherneural.chunks.json \
  --out out/video/video1_master_1080p.mp4

# pick a narrator by ear (all 17 US voices)
python3 tools/voice_audition.py --spec specs/video1.json --section hook --montage
```

Other tools: `make_short.py` (9:16 short from one still + script), `build_series.py`
(render all 8 shorts), `make_thumbnail.py` (16:9 thumbnail).

## Where the media lives

**Generated media is not in this repo.** `out/`, `assets/`, `.render/` and `nokia_out/`
are gitignored: audio and video are large, and they are fully regenerable from `specs/`.
A fresh clone gives you the scripts and the tools, not the MP4. Re-run the commands above,
or download the built files separately if you were given them.

`assets/` is where stills go (12 are expected for Video 1; the manifest in the content doc
lists each filename and what it must show). The repo ships no images.

## Licensing note

The default engine is `edge-tts`, which rides Microsoft's unofficial Edge Read Aloud
endpoint and carries **no commercial-use grant**. Before publishing monetised video,
render with a licensed voice: `docs/recording-voice.md` covers the options, and
`make_voice.py --engine azure` serves the *same* voices under a proper licence for about
eleven cents per video of this length.
