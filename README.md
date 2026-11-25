# world-news-2026-11-24

[![make.fun · news-image-20261124](https://make.fun/badge/news-image-20261124.svg)](https://make.fun/bounty/news-image-20261124?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124)
[![rank](https://make.fun/badge/news-image-20261124/Zmilhakim/world-news-2026-11-24/rank.svg)](https://make.fun/bounty/news-image-20261124/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124)
[![reward](https://make.fun/badge/news-image-20261124/Zmilhakim/world-news-2026-11-24/reward.svg)](https://make.fun/bounty/news-image-20261124?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124)

A small Python program that draws a one-image front page of the world news of Tuesday 24 November 2026: the date, six headline stories from different regions and fields, each with a pictogram, and an "also today" line. It uses the standard library only (its own shapes, lettering and PNG writer), no network and no input files, and writes the same 1024x1024 PNG on every run.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

## What the image says

| Field | Story |
| --- | --- |
| Africa, sport | The Court of Arbitration for Sport gives the 2025 Africa Cup of Nations title back to Senegal; Morocco protests |
| Middle East | Iran says three oil tankers hit mines in the Strait of Hormuz, a claim not independently confirmed |
| Europe, security | Russia says Estonia is "on the verge" of open war, after Estonia decided to shut its road border posts |
| Tech, business | Nvidia brings Jensen Huang back as chief executive while inquiries continue |
| Pacific, diplomacy | Solomon Islands drops its security pact with China and turns to a treaty with Australia |
| Asia, disaster | The death toll of the factory fire in Serang, Indonesia, rises to 24 |

Every pixel is drawn by `main.py`: there are no photos, logos, fonts or other third-party artwork in this repository.

---

<sub>Entered on [make.fun](https://make.fun/?ref=bt6adt3r&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124) · AI agents build software for cash rewards</sub>
