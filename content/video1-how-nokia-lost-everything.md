# Video 1 — How Nokia Lost Everything

**Full production pack: long-form script, asset manifest, and voiceover generator.**

| | |
|---|---|
| Format | 16:9 long-form, 1920×1080 |
| Runtime | 9:19 as uploaded — 1,361 words, 12 sections (9:04 at a 150 wpm estimate) |
| Voice | `en-US-ChristopherNeural` @ `+0%` |
| Script source of truth | `specs/video1.json` |
| Voiceover | `python3 tools/make_voice.py --spec specs/video1.json` |
| Sibling pack | `content/nokia-shorts-pack.md` (8 vertical cuts of this story) |

This is the long-form the shorts pack points back to. Every claim in it is already
established in the shorts pack, so the two can never contradict each other on camera.

---

## Why the audio was missing before — and what fixed it

The earlier shorts series was finished except for one thing: **no voices were ever
generated.** That was structural, not editorial. `tools/make_short.py` renders picture
and sound in a single pass, so it refuses to run without a still image:

```python
if not script or not image:
    sys.exit("need --script/--image or --spec with both")
```

No artwork in `assets/` meant no audio, and no audio meant no render. The narration was
hostage to the thumbnails. `tools/make_voice.py` breaks that dependency: it needs the
words and nothing else, so voice can be produced, timed, and proof-heard first.

The eight shorts can now be voiced the same way — no images required:

```bash
python3 tools/make_voice.py --spec specs/short1.json     # ...through short8.json
```

For Video 1, that same command writes one MP3 per section, a joined narration track,
an SRT on the joined timeline, and a manifest carrying the exact start timecode and
target asset for every section — which is precisely what the edit needs.

---

## Production standard

- **Picture:** 1920×1080, 24–30 fps. Slow push-in or pan on every still; never hold a
  static frame longer than 8 seconds at long-form pace.
- **Cadence:** one section = one chapter = one asset. The section boundaries in the
  manifest are the edit points.
- **Captions:** burned-in optional here (YouTube auto-captions are good enough for
  long-form), but `narration.srt` ships ready if you want them hard-coded.
- **Numbers on screen:** when the script says a number out loud, put the digits on
  screen at the same moment. That single habit is most of the difference between a
  long-form that holds and one that leaks viewers.
- **No intro.** The cold open is the first frame. A logo stinger at 0:00 costs you the
  exact people this script was written for.
- **Chapters on the progress bar.** Paste the chapter list from this doc into the
  description; it turns a 9-minute video into a browsable one.

---

## Narration

The text below is verbatim from `specs/video1.json` — the spec is the source of truth,
so edit there and re-run the generator rather than editing this copy. Every block is
one audio file and one asset.

### 1. Cold open — `00_thumb_nokia_fell_fast.jpg`

> Here is a company that spent fourteen straight years as the largest phone maker on Earth. And here is the same company, six years later, selling its entire phone business and walking away from it. The reason most people give is that Nokia missed the touchscreen. That is not what happened. Nokia did not lose to a better phone. It lost to a culture that had stopped hearing bad news. And the evidence is in the order things broke.

### 2. The peak that sounds fake — `01_the_peak_nokia_1100_era.jpg`

> In 2007, Nokia was not a fading giant. It was the giant. Almost every second smartphone sold on Earth that year was a Nokia. Across all phones, it was nearly four in ten. The company was worth roughly a hundred and fifty billion dollars, and its handsets were in the pockets of people who had never owned a phone before. If you had asked anyone in 2007 which phone company would still be standing twenty years later, Nokia would have been the obvious answer. That is the first thing to hold onto. This was not a company in decline that got unlucky. This was the most successful phone company in history, at the exact moment it was about to stop being one.

### 3. It started as a paper mill — `02_paper_mill_1865.jpg`

> To understand why, you have to go back further than most people expect. Nokia did not start in a garage in California. It started in Finland in 1865, as a paper mill. Over the next century it made rubber boots, cables, and electronics. Then, in the nineteen nineties, it bet everything on mobile phones, back when a phone was still a luxury object bolted into the dashboard of a car. That bet worked. By 1998, Nokia was the largest phone maker in the world. So the company everyone now calls a tech failure was actually a hundred and thirty year old survivor, and it won for longer than most companies even manage to exist. Companies like that do not fall over because of one bad product decision. They fall over because something inside them stops working.

### 4. January 2007 — `03_the_iphone_arrives_2007.jpg`

> In January 2007, Steve Jobs walked out on a stage and held up the iPhone. Nokia's engineers, reportedly, were not shocked by the hardware. They had already been prototyping touchscreens themselves. What shocked them was the software. It responded like a computer, not like a phone. It had a real browser, real maps, real scrolling, and it felt like it had been designed for a screen instead of a keypad. Nokia's phones ran Symbian, an operating system built for buttons and tiny screens, in an era when every kilobyte mattered. That was not a design flaw. That was a design optimised, brilliantly, for a world that had just ended.

### 5. The shape of winning — `04_symbian_fragmentation.jpg`

> And that is the trap. When you win for fourteen years, your software accumulates the shape of that success. Symbian carried years of decisions made for cheap hardware: dozens of devices to support, a developer experience that punished anyone who wanted to build something beautiful. Replacing that is not a six month project. It is a three year project, and it has to happen while you are still shipping products, still hitting quarterly numbers, and still being told by almost everyone around you that you are the market leader. So the question inside Nokia was never whether Symbian was a problem. It was whether anyone could afford to say so out loud.

### 6. Three platforms, three abandonments — `05_mistake_1_divided_company_infighting.jpg`

> Inside Nokia, teams were competing against each other instead of against Apple and Google. Different groups pushed different platforms. Symbian. Then Maemo. Then MeeGo. Each one was announced with genuine enthusiasm, each one arrived late, and each one was replaced by the next plan before it had a chance to be finished. Now put yourself in a developer's position. You are asked to build apps for a platform that might not exist in eighteen months. Meanwhile iOS has one operating system, one screen size, and a clear reason to show up. The app gap that people now point to as the cause of the collapse was not a design failure. It was a trust failure. Developers did the arithmetic, and the arithmetic said no.

### 7. Why the bad news never arrived — `06_bad_news_stops_mid_level.jpg`

> This is the part the timeline hides. Nokia did not lack information about what was happening. It lacked a route for that information to travel upward. It has been widely reported that managers inside the company were afraid to deliver bad news, that problems were softened on the way up, and that leadership was insulated from how far behind the software had actually fallen. That is not a technology problem. That is a reporting problem, and it is the most expensive kind, because it means every decision above it is made with the wrong numbers. A company can survive a competitor. It struggles to survive a culture where the person who raises the alarm is the person whose career pays for it.

### 8. The burning platform — `07_the_burning_platform_metaphor.jpg`

> In 2010, Nokia hired Stephen Elop, a former Microsoft executive, as chief executive, and gave him the job of fixing exactly this. In February 2011, he sent his employees a memo. In it, he compared Nokia to a man standing on a burning oil platform in the North Sea, who has to choose between burning alive and jumping into freezing water. It was honest, and it was brutal, and it did what internal honesty usually does. It leaked. Then Nokia abandoned its own software and partnered with Microsoft's Windows Phone. And here is the part almost every retelling skips. The announcement did damage by itself. Customers who were three months from an upgrade heard the message clearly: the phone you are about to buy is already a dead end. You do not have to guess what happened next. Symbian sales fell off a cliff.

### 9. The numbers — `08_the_end_microsoft_acquisition_lumia.jpg`

> By 2012, Samsung had overtaken Nokia as the world's biggest phone maker, ending a fourteen year run at the top. In September 2013, Microsoft agreed to buy Nokia's devices and services business for about five point four billion euros: three point seven nine billion for the devices, and one point six five billion for a licence to the patents. The deal closed in April 2014. Then, in July 2015, Microsoft took a seven point six billion dollar write down on the division, and cut around seven thousand eight hundred jobs from it. Read that number again. Microsoft lost more on Nokia than Nokia made selling it. The most valuable phone company on Earth went for less than the cost of the mistake.

### 10. Nokia isn't dead — `09_payoff_nokia_5g_telecom_infrastructure.jpg`

> But the story does not end the way the headline does. Nokia kept the part that actually mattered: network equipment. Today Nokia sells telecom infrastructure to carriers around the world, including the 5G networks your phone runs on. The Nokia name still shows up on handsets too, licensed to another company that builds the phones. So the collapse was really a company quietly walking out of a market it had already lost, in order to keep the one where it still had a moat. Everyone thinks Nokia died. It did not. It sold the part that was already gone.

### 11. The real lesson — `10_success_is_a_filter.jpg`

> So what is the actual lesson? Not do not miss a trend. Everyone knows that one, and it is useless, because trends are obvious in hindsight and ambiguous in the moment. The lesson is that success is a filter. The longer a company is right, the more its processes, its metrics, and its people are selected for confirming that it is still right. Nokia did not fail because it was stupid. It failed because it was right for so long that being right became the culture. Great hardware could not save it, because the problem was never the hardware.

### 12. Close — `11_closing_hold.jpg`

> Which brings the question home. Somewhere right now, you are winning at something. It pays your bills, it gets you promoted, it is the thing people congratulate you for. And the same thing that makes you good at it is quietly making you deaf to whatever is coming next. Nokia had fourteen years of being right, and that was exactly the runway it needed to build in order to hear bad news early. It is worth asking what your equivalent is, and who in your world is allowed to tell you the truth.

## Asset manifest

Assets live in `assets/video1/` and, like the shorts, they are **gitignored** — the
repo carries the spec, not the binaries. The filenames below are exactly what
`specs/video1.json` expects, so dropping the files in place is all the edit needs.

Seven of the twelve are already in the Drive folder
`How Nokia Lost Everything - Video Assets & Script` under their older capitalised
names; copy them down to the lowercase names and they match. Five have no source yet.

| # | Target file | Section | What it must show | Status |
|---|---|---|---|---|
| 0 | `00_thumb_nokia_fell_fast.jpg` | Cold open | Thumbnail treatment: `NOKIA FELL FAST` in yellow on dark | Exists — `00_Official_YouTube_Thumbnail_Nokia_Fell_Fast.jpg` |
| 1 | `01_the_peak_nokia_1100_era.jpg` | The peak | Peak-era 1100/bar-phone product wall, "1 in 2" energy | Exists — `01_The_Peak_Nokia_1100_Era.jpg` |
| 2 | `02_paper_mill_1865.jpg` | Paper mill | Finnish pulp mill / industrial 1800s works | **Needs sourcing** |
| 3 | `03_the_iphone_arrives_2007.jpg` | January 2007 | Jobs on stage, iPhone silhouette, 2007 date stamp | Exists — `02_The_iPhone_Arrives_2007.jpg` |
| 4 | `04_symbian_fragmentation.jpg` | Shape of winning | Splintered keypad grid / Symbian UI motif | **Needs sourcing** |
| 5 | `05_mistake_1_divided_company_infighting.jpg` | Three platforms | Three-way split graphic, arrows pointing at each other | Exists — `03_Mistake_1_Divided_Company_Infighting.jpg` |
| 6 | `06_bad_news_stops_mid_level.jpg` | Bad news | Org chart with the bottom layer greyed out and a blocked arrow | **Needs sourcing** |
| 7 | `07_the_burning_platform_metaphor.jpg` | Burning platform | North Sea rig at dusk, heat haze | Exists — `05_The_Burning_Platform_Metaphor.jpg` |
| 8 | `08_the_end_microsoft_acquisition_lumia.jpg` | The numbers | Lumia hardware, Microsoft logo, deal-date overlay | Exists — `06_The_End_Microsoft_Acquisition_Lumia.jpg` |
| 9 | `09_payoff_nokia_5g_telecom_infrastructure.jpg` | Nokia isn't dead | Cell towers / 5G antenna, cool blue | Exists — `07_Payoff_Nokia_5G_Telecom_Infrastructure.jpg` |
| 10 | `10_success_is_a_filter.jpg` | The real lesson | Single filter/funnel motif, one phrase on screen | **Needs sourcing** |
| 11 | `11_closing_hold.jpg` | Close | Reuse the thumbnail treatment, no text, room for end-card | **Needs sourcing** |

**On sourcing the five missing frames:** a text-on-dark card in the same yellow/white
treatment as the thumbnail is a legitimate, free, and on-brand answer for #4, #6, #10,
and #11 — they are conceptual beats, not historical ones. Only #2 is a real photograph
need (a period pulp mill or early Nokia works image). Do not lift press photos of
Jobs, Elop, Lumia devices, or Nokia signage from a search engine; unlicensed press
imagery is the most common way a monetised channel gets a claim or a strike.

---

## Voice direction

The generator is deliberately boring about this, because the script is doing the work.

**Not recording your own voice?** That is fine and common — but the real decision is
licensing, not accent. Audition every US voice for free, then ship on a licensed
endpoint that serves the *same* voice by name for about eleven cents a video. Full
reasoning and the decision table are in `docs/recording-voice.md`; the short version:

```bash
python3 tools/voice_audition.py --spec specs/video1.json --section hook   # pick by ear
python3 tools/make_voice.py --spec specs/video1.json --voice en-US-AndrewNeural

export AZURE_SPEECH_KEY=...  AZURE_SPEECH_REGION=eastus                   # licensed copy
python3 tools/make_voice.py --spec specs/video1.json --voice en-US-AndrewNeural --engine azure
```

```bash
# as shipped: authoritative, measured, mid-Atlantic-neutral
python3 tools/make_voice.py --spec specs/video1.json

# slower and heavier — good for the 2011 turn (memo chapter)
python3 tools/make_voice.py --spec specs/video1.json --rate "-6%"

# British male, reads colder and more BBC-documentary
python3 tools/make_voice.py --spec specs/video1.json --voice en-GB-RyanNeural
```

- **Gap between sections is 0.55 s** (`--gap`). That is the beat your editor needs to
  drop chapters and b-roll on without clipping the last syllable. Do not set it to 0.
- **One section per asset.** If you later want a section split, split it in the spec —
  the timings regenerate rather than being hand-patched.
- **Prefer your own voice?** Record it and follow `docs/recording-voice.md`; the
  pipeline already supports `--enhance` and `--revocalize` on `make_short.py`.
- The honest limit from that doc still applies here: `edge-tts` is an unofficial
  endpoint, free, and not licensed for commercial use. For a monetised channel use
  your own recording or a licensed voice — the script and spec do not change.


---

## Chapter timeline (measured from the uploaded master)

These timecodes come from `en-us-christopherneural.chunks.json`, i.e. the 9:19 perform
render that `out/video/video1_master_1080p.mp4` was cut from — **not** the earlier 8:36
`make_voice` render. Use these in the description. The older numbers drifted by up to 28
seconds per chapter and would have put every marker on the wrong beat.

| Start | Chapter | Length | Words | Asset |
|---|---|---|---|---|
| 0:00 | Cold open | 30.5s | 79 | `00_thumb_nokia_fell_fast.jpg` |
| 0:30 | The peak that sounds fake | 48.2s | 122 | `01_the_peak_nokia_1100_era.jpg` |
| 1:19 | It started as a paper mill | 58.0s | 136 | `02_paper_mill_1865.jpg` |
| 2:18 | January 2007 | 49.4s | 109 | `03_the_iphone_arrives_2007.jpg` |
| 3:08 | The shape of winning | 44.1s | 112 | `04_symbian_fragmentation.jpg` |
| 3:52 | Three platforms, three abandonments | 53.1s | 124 | `05_mistake_1_divided_company_infighting.jpg` |
| 4:46 | Why the bad news never arrived | 46.9s | 122 | `06_bad_news_stops_mid_level.jpg` |
| 5:33 | The burning platform | 62.8s | 144 | `07_the_burning_platform_metaphor.jpg` |
| 6:36 | The numbers | 56.5s | 122 | `08_the_end_microsoft_acquisition_lumia.jpg` |
| 7:34 | Nokia isn't dead | 40.9s | 99 | `09_payoff_nokia_5g_telecom_infrastructure.jpg` |
| 8:15 | The real lesson | 38.7s | 99 | `10_success_is_a_filter.jpg` |
| 8:54 | Close | 33.4s | 93 | `11_closing_hold.jpg` |

Two structural notes the timeline makes obvious:

1. **The peak lands at 0:30, not 0:00.** The cold open is 30.5 seconds of thesis before a
   single number arrives. If retention dies early, cut section 1 to 15 seconds — the
   thesis survives being halved, but the peak section cannot.
2. **The longest chapter is the burning platform (62.8s).** That is also the emotional
   turn. Give it the most visual movement: 3–4 shots, not one still.

---

## YouTube metadata

**Title options** (front-load the tension, not the noun):

1. How Nokia Lost Everything — The Real Reason (Not the iPhone)
2. Nokia Was Worth $150 Billion. Six Years Later It Sold Its Phone Business.
3. The Company That Was Right for 14 Years and Couldn't Hear the Truth

**Description** — paste as-is; the timestamp list becomes chapters on the progress bar:

```text
In 2007, almost one in two smartphones sold on Earth was a Nokia. Six years later the
company sold its entire phone business. This is what actually broke — and it wasn't
the touchscreen.

0:00 The setup
0:30 The peak that sounds fake
1:19 It started as a paper mill
2:18 January 2007
3:08 The shape of winning
3:52 Three platforms, three abandonments
4:46 Why the bad news never arrived
5:33 The burning platform
6:36 The numbers
7:34 Nokia isn't dead
8:15 The real lesson
8:54 Close

Sources: Gartner and Strategy Analytics handset data, Microsoft's 2013–2015 filings,
and contemporaneous reporting on the February 2011 internal memo.

#nokia #businesscasestudy #techhistory #leadership #marketshare
```

**Thumbnail:** reuse `00_Official_YouTube_Thumbnail_Nokia_Fell_Fast.jpg`. One text idea
that pairs with the title: `$150B → SOLD`.

**Pinned comment:** the honest framing, which is also the best-performing comment:

```text
Nokia didn't lose to a better phone. It lost a reporting channel. The phones were late
because the bad news was late.
```


---

## Uploading this as a retention test

The animatic exists to answer one question cheaply: does the script hold for nine minutes
before you spend anything on visuals? Because nothing moves on screen but text, a dip in
the curve is the writing or the pacing — not missing b-roll.

**Before publishing**

- **Thumbnail:** `python3 tools/make_thumbnail.py` writes
  `out/thumb/video1_thumbnail_1280x720.png` — the yellow/white series treatment, with every
  line measured and shrunk to fit so text cannot overflow. 1280×720 is YouTube's 16:9 slot.
- **Description:** paste the block above. Chapters only render if the list starts at 0:00
  and every entry is 10s or more apart; both hold here.
- **Public or unlisted matters.** Unlisted gives completion data but no recommendation
  traffic, so click-through rate means nothing. If you want to read CTR, publish it.

**What to read, and when**

At 24–48 hours, in Studio → Analytics → Engagement → retention curve:

| Metric | Target | If it misses |
|---|---|---|
| Retention at 0:30 | > 70% | The cold open is 30.5s of thesis before any number. Under 60%: cut section 1 to ~15s and re-upload. |
| Average % viewed | > 35% at 9:19 | Pacing is too slow — try `--wpm 165` and rebuild. |
| A single cliff | — | That chapter is what to cut. |

**Specific suspects in this script**, so you know where to look before the data arrives:

- **1:19 — the paper mill (58.0s).** Backstory before the conflict. The most likely early
  drop; the 1865 origin can survive being halved.
- **5:33 — the burning platform (62.8s).** Longest chapter, and the emotional turn. A
  cliff here means trim to ~40s, not that the memo is wrong.
- **7:34 — "Nokia isn't dead".** If viewers leave here, they came for the collapse and do
  not want the twist. That is a title problem, not a script problem.

**What it cannot tell you:** anything about performance with real footage. Do not conclude
the topic is dead from an animatic's CTR — here the thumbnail is doing all the work alone.


Every factual claim in this script was already in `content/nokia-shorts-pack.md`, which
traced them to Gartner and Strategy Analytics handset data, Microsoft's filings, and
contemporaneous reporting. **I deliberately added no new claims** while writing the
long-form, because the authority of the piece comes from the numbers surviving scrutiny
for nine straight minutes.

Three places where the wording is doing specific work, and should not be "tightened" in
the edit:

| Line | Why it is phrased that way |
|---|---|
| "Nokia's engineers, **reportedly**, were not shocked by the hardware" | Touchscreen prototyping before 2007 is widely reported but soft-sourced. The qualifier is spoken, not just on screen, so a hostile commenter cannot catch it out. |
| "It has been **widely reported** that managers were afraid to deliver bad news" | Same reason. The "fear culture" narrative rests on later interviews, not on a leaked internal metric. |
| "worth **roughly** a hundred and fifty billion dollars" | Peak market capitalisation moves with exchange rates and which day you pick. "Roughly" is the honest hedge, and it does not weaken the point. |

Deliberately left out, because they were not in the verified set and each one adds a
minute of exposition for a small gain: the Alcatel-Lucent acquisition, the licensing of
the brand to HMD by name, and the exact 2012 quarterly figures.

If you want them, add them to `specs/video1.json` as new sections — the timings and the
chapter list regenerate in one command — rather than editing this document, which will
then be out of sync with the audio.

---

## What this pack does not include

Stating the gaps plainly, so nothing here is mistaken for finished video:

- **No footage or b-roll.** Sections are still-image driven by design, matching the
  existing pipeline. Your editor supplies motion, transitions, and any archive video.
- **No music or SFX.** Neither is licensed here, and a 9-minute bed needs a real licence.
- **Five of the twelve stills are unsourced.** Rows flagged **Needs sourcing** in the
  asset manifest above. The other seven exist in the Drive folder.
- **The cut has no motion.** `tools/build_longform.py` now composites the stills (one per
  section, cover-cropped to 1080p, with a gradient scrim behind the title and captions),
  and falls back to a card for any still that is missing. What it does not do is move the
  image: no Ken Burns push, no transitions. Add those once the pictures are final.
- **No end screen or subscribe animation.** Standard 20-second outro not written, because
  the close is a question and padding after it costs retention.

---

## Commands

```bash
# 1. Inspect the script and timing without touching the network
python3 tools/make_voice.py --spec specs/video1.json --dry-run

# 2. Generate the full voiceover: 12 MP3s, narration.mp3, narration.srt, manifest.json
python3 tools/make_voice.py --spec specs/video1.json

# 3. Or voice the eight shorts that were missing audio (no images needed)
for i in 1 2 3 4 5 6 7 8; do python3 tools/make_voice.py --spec specs/short$i.json; done

# 4. Alternate delivery
python3 tools/make_voice.py --spec specs/video1.json --rate "-6%"
python3 tools/make_voice.py --spec specs/video1.json --voice en-GB-RyanNeural
python3 tools/make_voice.py --spec specs/video1.json --gap 0.9 --no-concat
```

Everything lands under `out/voice/<slug>/`, which is gitignored — the repo carries the
spec and the tool, not 10 MB of regenerable audio. Re-run whenever the script changes.

