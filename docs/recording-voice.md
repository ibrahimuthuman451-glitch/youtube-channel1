# Recording Your Own Voice (and what "sound native" actually means)

## The honest answer up front

There is **no free tool that reliably converts an accented recording into a native
accent while keeping your own voice**. That is speaker/accent *conversion* — an
active research problem. Anything claiming one-click accent removal on a free tier is
either re-synthesising a **different** voice (so it isn't you any more) or just
cleaning up the audio.

What this pipeline gives you instead is three real, working options. Pick per video.

---

## Option 0 — Voiceover on its own, before any picture exists

`tools/make_voice.py` is the audio-only path. `make_short.py` renders sound and picture
in one pass and refuses to start without a still image, which is why the eight shorts sat
finished-but-silent. This one needs only the words:

```bash
python3 tools/make_voice.py --spec specs/video1.json   # 12 sections, SRT, manifest
python3 tools/make_voice.py --spec specs/short1.json   # or any flat-script spec
python3 tools/make_voice.py --spec specs/video1.json --dry-run   # word count, no network
```

It writes one MP3 per section plus a joined `narration.mp3`, a `narration.srt` on the
joined timeline, and a `manifest.json` with each section's start timecode. Options 1–3
below still apply when you want *your* voice instead; they are not replaced by this.

---

## Option 1 — Use your own voice, cleaned up

Keeps **you**. Improves intelligibility, removes room noise, and hits platform loudness.
It does **not** change your accent, and it shouldn't try to.

```bash
python3 tools/make_short.py --spec specs/short3.json \
  --audio assets/my_recording.mp3 --enhance \
  --out out/short3_myvoice.mp4
```

Chain applied (`enhance_voice` in `tools/make_short.py`):

| Filter | Purpose |
|---|---|
| `highpass=f=90` | removes rumble, desk knocks, mic handling |
| `afftdn=nf=-25` | FFT denoise — kills hiss, fans, room tone |
| `equalizer 300 Hz -2 dB` | tames boxy, "recorded in a wardrobe" low-mids |
| `equalizer 3200 Hz +2.5 dB` | presence boost — consonants land clearer |
| `acompressor` | evens out loud/quiet words so nothing is lost |
| `loudnorm I=-14` | YouTube/Reels/TikTok loudness target |

Measured on the test take: **-17.0 LUFS → -14.8 LUFS**. Captions are still placed
automatically — speech segments are found with `silencedetect`, so no transcription
is needed.

## Option 2 — Keep your pacing, swap in a native voice

This is the one that actually makes a video *sound* native. You record the script in
your own rhythm; the tool then **re-speaks the same words in a native voice, tuned to
match the length of your take**, so your pauses and emphasis survive but the delivery
is native.

```bash
python3 tools/make_short.py --spec specs/short3.json \
  --audio assets/my_recording.mp3 --revocalize \
  --out out/short3_native.mp4
```

It iterates the speech rate until the native take is within 3% of your original
length, then time-stretches (`atempo`) to land within 2%. Verified on the test take:
**34.10 s → 33.98 s** (0.35% off).

The trade-off is obvious and worth stating plainly: **the voice is no longer yours.**
Use this when the video matters more than the personality, and reveal your real voice
on camera or in a pinned comment if you want the human connection.

## Option 3 — Just use the built-in TTS

No recording at all. Fastest, consistent, free:

```bash
python3 tools/make_short.py --spec specs/short3.json --out out/short3.mp4
```

Default voice is `en-US-ChristopherNeural`. Swap with `--voice`, tune with `--rate`:

```bash
--voice en-US-AriaNeural          # female US
--voice en-GB-RyanNeural          # British male
--voice en-AU-NatashaNeural       # Australian female
--rate "-6%"                      # slower, more authoritative
```

---

## Recording tips that matter more than any filter

1. **Mic close, room soft.** 15–20 cm from the mic, in a room with curtains/bed/sofa.
   A blanket behind you beats any plugin.
2. **Record 2–3 dB quieter than you think.** Clipping cannot be fixed; hiss can.
3. **Punch in per sentence, not per paragraph.** One bad line costs one sentence.
4. **Leave half a second of silence before you start** — gives `silencedetect` a clean
   anchor.
5. **Read numbers as words** ("five point four billion euros", not "€5.4B"). TTS needs
   this too, and it reads more naturally.
6. **Export WAV or high-bitrate MP3.** The pipeline accepts either.

## If the voice is not going to be yours

Wanting a US-neutral narrator is a legitimate production decision, and it does not
require you to record anything. But the decision that matters here is **not accent, it
is licensing** — the free route and the paid route use the *same* Microsoft neural
voices, so what you are buying with money is the right to monetise.

### Audition first, free

```bash
python3 tools/voice_audition.py --spec specs/video1.json --section hook   # all 17 US voices
python3 tools/voice_audition.py --gender Male
```

Identical line, identical rate, one MP3 per voice plus `out/voice/audition/index.html`
with a player for each. Pick with your ears in two minutes instead of guessing from a
voice list. Then use that name everywhere.

### Then choose how you pay for it

| Option | Same voices? | Commercial licence | Cost for Video 1 |
|---|---|---|---|
| `edge-tts` (`--engine edge`) | Yes | **No grant.** Microsoft has declined to confirm monetised use of Edge Read Aloud output | $0 |
| **Azure AI Speech** (`--engine azure`) | **Yes — identical voice names** | Yes, included | **~$0.11** (7,624 chars at ~$15/1M) |
| ElevenLabs / PlayHT | No, different voices | Yes, on paid plans | $5–22/mo entry tiers |
| Self-hosted open weights (Kokoro-82M, Piper) | No | Yes (Apache-2.0 / MIT) | $0 + your GPU/CPU time |

The useful consequence: **audition on the free endpoint, ship on the licensed one.**
Because both expose `en-US-AndrewNeural`, the voice you chose by ear survives the
migration byte-for-byte in character — only the licence and the bill change.

```bash
export AZURE_SPEECH_KEY=...        # from a Speech resource in the Azure portal
export AZURE_SPEECH_REGION=eastus
python3 tools/make_voice.py --spec specs/video1.json --engine azure --voice en-US-AndrewNeural
```

At this script's length a video costs about eleven cents, so a 4-videos-a-month channel
costs under fifty cents. The 500K characters/month free tier on a Speech resource covers
roughly 65 videos of this size, but treat the free tier as evaluation: the pay-as-you-go
(S0) tier is the unambiguous path, and at these volumes the difference is cents.

**One trade-off when you switch:** the batch Azure REST call returns no word-boundary
stream, so captions fall back to `silencedetect` estimates rather than exact per-word
timings (the drift noted under Known limits below). Audio quality and voice are
unchanged. If frame-exact captions matter more than the licence, keep `--engine edge`
for private drafts and re-render the publish copy on Azure.

## Known limits

- **Accent is not removed** in Option 1 — by design.
- **Caption sync from a recording is estimated.** Word timings come from speech
  segments found by silence detection, not phonetic alignment. Expect ~100–200 ms
  drift on dense words. For frame-exact sync you would add Whisper forced alignment.
- **`edge-tts` is an unofficial endpoint.** Free and good, but not licensed for
  commercial use and it can break without notice. For a monetised channel, prefer
  Option 1 (your voice) or a licensed TTS.
