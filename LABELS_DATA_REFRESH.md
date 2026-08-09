# Refreshing the /labels data

`labels/index.html` embeds a hardcoded `LABELS` string (`Name:count` pairs,
pipe-separated) plus a date range in the intro copy. This is a snapshot, not
live data — refresh it manually when you want newer numbers.

## Data source

**`K:\Dev\Beatport Automation\data\scrapes\*.json`** — one file per scrape
run, named `scrape_YYYYMMDD_HHMMSS.json`.

This is local to that machine/folder. There is no Google Drive involvement —
`GOOGLE_DRIVE_PLAN.md` in that project describes a sync plan that was never
carried out, and nothing in the scraper's code reads from a Drive-mapped
drive letter. If you go looking for this data, it's on disk in that repo,
not in Drive.

Each scrape file looks like:

```json
{
  "scraped_at": "2026-08-07T23:35:34.026810",
  "start_date": "2026-07-19",
  "end_date": "2026-08-07",
  "track_count": 2914,
  "tracks": [
    {
      "track_id": "23548878",
      "title": "Space Rush",
      "label": "Hooversound Recordings",
      "release_date": "2026-08-07",
      "...": "artists, mix, preview_url, track_url, artwork_url"
    }
  ]
}
```

Scrape windows overlap between files, so tracks must be deduplicated by
`track_id` before counting anything.

## What "releases" means here

The `LABELS` data does **not** count raw tracks. Each scraped record is a
single track, but an EP/VA compilation puts several tracks under one label
on one release date — counting tracks directly triples-plus some labels'
numbers relative to what "releases" actually means.

**A "release" = one distinct `(label, release_date)` pair.** Four tracks
from the same label dropping the same day count as 1 release, not 4.

Filters applied on top of that:
- Minimum 3 releases in the window to be included at all (cuts out
  one-off/noise entries — without this there are ~2,300+ labels instead of
  ~780).
- Exclude three non-label distribution aggregators that would otherwise
  dominate the list: **DistroKid, TuneCore, recordJet**. These aren't
  labels — they're generic services thousands of independent artists route
  through, so their "release counts" are meaningless in this context.

## Regenerating

```python
import json, glob, collections

files = sorted(glob.glob(r"K:\Dev\Beatport Automation\data\scrapes\scrape_*.json"))
tracks = {}
for f in files:
    data = json.load(open(f, encoding="utf-8"))
    for t in data.get("tracks", []):
        tid = t.get("track_id")
        if tid:
            tracks[tid] = t          # last scrape wins per track_id, dedupes overlap

START, END = "2026-01-01", "2026-08-09"   # inclusive, YYYY-MM-DD — pick your window
EXCLUDE = {"distrokid", "tunecore", "recordjet"}

by_label = collections.defaultdict(set)
for t in tracks.values():
    rd = t.get("release_date") or ""
    if START <= rd <= END:
        by_label[t.get("label") or "Unknown"].add(rd)   # set of dates = releases

counts = {l: len(dates) for l, dates in by_label.items()
          if l.lower() not in EXCLUDE and len(dates) >= 3}

pairs = "|".join(f"{l}:{c}" for l, c in sorted(counts.items(), key=lambda kv: kv[0].lower()))
```

`pairs` is the exact string that goes between the quotes in
`var LABELS = "..."` in `labels/index.html` (search for `var LABELS = `).

Also update the date range text in **two** places in that file (search for
the old date string):
1. The static intro paragraph (`<p class="lp-sub" id="lp-intro">`)
2. The JS template string used when a visitor arrives with `?name=` in the URL

## Sanity-checking before you push

- Spot-check a well-known label's count against `grep -c` on the distinct
  dates in the raw JSON — if a heavily-active label's number looks like
  roughly 3x what you'd expect, you've probably counted tracks instead of
  distinct dates.
- Compare total label count to the previous version — should be in the same
  ballpark (hundreds, not thousands) given the >=3 threshold.
