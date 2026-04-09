# Gold set sources & attribution

The public gold sets under `tests/data/` are assembled from a mix of
hand-curated rows and rows derived from open data. This file records the
provenance and licensing for every external source.

## gold_200.jsonl (v0.3 baseline, frozen)

Hand-curated by the maintainer. Public domain dedication for the strings
themselves; the file is MIT-licensed as part of the repository.

## gold_500.jsonl (v0.4)

Built from three sources, all open and attributed below. Each row is
hand-reviewed before promotion from `gold_500_candidates.jsonl` into the
committed `gold_500.jsonl`. The candidate file is gitignored.

### Tier A — hand-curated (≥50 rows)

Authored by the maintainer to cover native-script edge cases that the
automated sources don't reach (mixed-script inputs, Indic-digit pincodes,
common abbreviations). MIT.

### Tier B1 — OSMNames

Latin-script regional rows for non-Hindi-belt states (Tamil Nadu,
Karnataka, West Bengal, Kerala, Telangana, etc.). Source:
<https://osmnames.org/> — a downloadable gazetteer derived from
OpenStreetMap.

- **Licence**: CC-BY 4.0 (inherited from OpenStreetMap).
- **Attribution**: "© OpenStreetMap contributors, via OSMNames."
- **How fetched**: `scripts/build_gold_tier_b.py --osmnames <in.tsv.gz>`.
  The dump is not redistributed in this repo; users download it
  themselves from osmnames.org.

### Tier B2 — Overpass API (native-script rows)

Native-script names for the 6 v0.4 supported scripts, pulled from OSM
nodes/ways that carry both `name:<lang>` and `addr:postcode` tags.
Targets six cities — New Delhi (hi), Chennai (ta), Hyderabad (te),
Bengaluru (kn), Kolkata (bn), Kochi (ml).

- **Licence**: ODbL 1.0 (OpenStreetMap database licence). Individual
  tag values are factual data and reproduced under ODbL's "produced
  work" provisions.
- **Attribution**: "© OpenStreetMap contributors."
- **How fetched**: `scripts/build_gold_tier_b.py --overpass`. One query
  per city, rate-limited at 1 req/sec against the public Overpass
  instance at <https://overpass-api.de/>.

## What is NOT used

- **AI4Bharat indicnlp_catalog** — metadata index, not structured
  address data. Evaluated and rejected during v0.4 scoping.
- **Bharat Scene Text Dataset (BSTD)** — 17 GB of street-sign photos.
  Overkill for ~250 text rows; Overpass gives the same coverage at
  zero storage cost.
- **Google Maps / commercial geocoders** — closed licence; cannot ship
  derived gold rows under MIT.
