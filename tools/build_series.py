#!/usr/bin/env python3
"""Render the whole Nokia short-form series through make_short.py."""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# Posting order from content/nokia-shorts-pack.md: 3,1,5,2,6,4,7,8
SERIES = [
    {
        "n": 3, "slug": "one_in_two", "image": "assets/01_peak.jpg",
        "script": ("In 2007, almost every second smartphone sold on Earth was a Nokia. "
                   "Across all phones, it was nearly four in ten. The company was worth roughly a "
                   "hundred and fifty billion dollars. Six years later it sold its entire phone "
                   "business to Microsoft for five point four billion euros. And here is the thing "
                   "that gets missed. It was not one mistake. It was a culture that had stopped "
                   "hearing bad news."),
    },
    {
        "n": 1, "slug": "touchscreen_first", "image": "assets/02_iphone.jpg",
        "script": ("Before the iPhone, Nokia engineers were already prototyping touchscreens. "
                   "So in January 2007, when Steve Jobs walked out with the iPhone, Nokia's "
                   "engineers weren't shocked by the hardware. They'd built touchscreens. What "
                   "shocked them was the software. It felt like it belonged on a computer, not a "
                   "phone. Nokia's phones ran Symbian, an operating system designed for buttons and "
                   "tiny screens. And that's the part they couldn't copy fast enough."),
    },
    {
        "n": 5, "slug": "three_operating_systems", "image": "assets/03_divided.jpg",
        "script": ("Inside Nokia, teams were competing against each other instead of against Apple "
                   "and Google. Different groups pushed different platforms. Symbian, then Maemo, "
                   "then MeeGo. Managers were reportedly afraid to bring bad news upward, so "
                   "leadership never heard how serious it had gotten. So Nokia kept announcing a new "
                   "software plan, then replacing it, then announcing another one. And developers did "
                   "the math. Why build apps for a platform that might not exist in eighteen months? "
                   "The app gap wasn't a design failure. It was a trust failure."),
    },
    {
        "n": 2, "slug": "burning_platform_memo", "image": "assets/05_burning.jpg",
        "script": ("In 2010, Nokia hired Stephen Elop, a former Microsoft executive, as CEO. In "
                   "February 2011, he sent his employees a memo. He compared Nokia to a man standing "
                   "on a burning oil platform in the North Sea, who has to choose between burning "
                   "alive or jumping into the freezing water. The memo leaked. Then Nokia abandoned "
                   "its own software and partnered with Microsoft's Windows Phone. And that "
                   "announcement did the damage itself. Customers realised the phones they were "
                   "about to buy were already dead ends. Symbian sales fell off a cliff."),
    },
    {
        "n": 6, "slug": "microsoft_sale", "image": "assets/06_microsoft.jpg",
        "script": ("By 2012, Samsung had overtaken Nokia as the world's biggest phone maker, ending "
                   "a fourteen year run. In September 2013, Microsoft agreed to buy Nokia's devices "
                   "and services business for about five point four billion euros. The deal closed in "
                   "April 2014. Then, in July 2015, Microsoft took a seven point six billion dollar "
                   "write down and cut around seven thousand eight hundred jobs from the division. "
                   "Microsoft lost more on Nokia than Nokia made selling it."),
    },
    {
        "n": 4, "slug": "paper_mill", "image": "assets/01_peak.jpg",
        "script": ("Nokia started in Finland in 1865 as a paper mill. Over the next century it made "
                   "rubber boots, cables, and electronics. Then in the nineteen nineties, it bet "
                   "everything on mobile phones. By 1998 it was the largest phone maker in the world. "
                   "And it held that position for fourteen years. Which means the company everyone "
                   "calls a tech failure was actually a hundred and thirty year old survivor that won "
                   "for longer than most companies even exist."),
    },
    {
        "n": 7, "slug": "nokia_isnt_dead", "image": "assets/07_payoff.jpg",
        "script": ("Everyone thinks Nokia died. It didn't. It sold the phone business, but it kept "
                   "the part that actually mattered. Network equipment. Today Nokia sells telecom "
                   "infrastructure to carriers around the world, including the 5G networks your phone "
                   "runs on. The Nokia name still shows up on handsets too, licensed to another "
                   "company. So the collapse was really a company quietly walking out of a market it "
                   "had already lost."),
    },
    {
        "n": 8, "slug": "the_real_reason", "image": "assets/00_thumb.jpg",
        "script": ("Nokia didn't fail because it was stupid. It failed because it was right for so "
                   "long that being right became the culture. Success made the company slow, made "
                   "managers hide bad news, and made leadership miss how far behind the software had "
                   "fallen. Great hardware couldn't save it, because the problem was never the "
                   "hardware. So here's the question worth sitting with. What is your thing currently "
                   "winning at, that's quietly making you deaf to the thing that's coming next?"),
    },
]


def main():
    only = set(sys.argv[1:]) or None
    specdir = os.path.join(ROOT, "specs")
    outdir = os.path.join(ROOT, "out")
    os.makedirs(specdir, exist_ok=True)
    os.makedirs(outdir, exist_ok=True)
    made = []
    for item in SERIES:
        if only and str(item["n"]) not in only:
            continue
        spec = {
            "name": f"Short {item['n']} - {item['slug']}",
            "image": item["image"],
            "voice": "en-US-ChristopherNeural",
            "rate": "+0%",
            "script": item["script"],
        }
        sp = os.path.join(specdir, f"short{item['n']}.json")
        json.dump(spec, open(sp, "w"), indent=2)
        out = os.path.join(outdir, f"short{item['n']}_{item['slug']}.mp4")
        r = subprocess.run([sys.executable, os.path.join(HERE, "make_short.py"),
                            "--spec", sp, "--out", out],
                           cwd=ROOT, capture_output=True, text=True)
        status = "OK " if r.returncode == 0 else "FAIL"
        detail = (r.stdout or r.stderr).strip().splitlines()
        print(f"[{status}] {os.path.basename(out)} :: {' | '.join(detail[-2:])}", flush=True)
        if r.returncode == 0:
            made.append(out)
    print(f"rendered {len(made)} of {len(SERIES)}", flush=True)


if __name__ == "__main__":
    main()

