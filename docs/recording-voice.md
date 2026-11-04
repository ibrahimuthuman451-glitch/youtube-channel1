# Recording Your Own Voice (and what "sound native" actually means)

## The honest answer up front

There is **no free tool that reliably converts an accented recording into a native
accent while keeping your own voice**. That is speaker/accent *conversion* — an
active research problem. Anything claiming one-click accent removal on a free tier is
either re-synthesising a **different** voice (so it isn't you any more) or just
cleaning up the audio.

What this pipeline gives you instead is three real, working options. Pick per video.

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

## Known limits

- **Accent is not removed** in Option 1 — by design.
- **Caption sync from a recording is estimated.** Word timings come from speech
  segments found by silence detection, not phonetic alignment. Expect ~100–200 ms
  drift on dense words. For frame-exact sync you would add Whisper forced alignment.
- **`edge-tts` is an unofficial endpoint.** Free and good, but not licensed for
  commercial use and it can break without notice. For a monetised channel, prefer
  Option 1 (your voice) or a licensed TTS.
