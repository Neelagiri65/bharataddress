# Competitor benchmark — Indian address parsers (research, 2024–2026)

Status: **research only**, no installs, no runs. Numbers below are what the projects themselves report. We will validate against `tests/data/gold_200.jsonl` once we plug them into `scripts/evaluate.py`.

## Summary table

| Project | Type | License | Last update | Stars | Installable | Public test set | Reported metrics |
|---|---|---|---|---|---|---|---|
| **bharataddress v0.1** (us) | Deterministic (regex + lookups) | MIT | 2026-04 | — | `pip install bharataddress` | `gold_200.jsonl` (ours) | EM 8%, pincode F1 0.995, state 0.86, building# 0.91, locality 0.35 |
| shiprocket-ai/open-indicbert-indian-address-ner | ML — IndicBERT NER | Apache-2.0 | 2025-06-18 | (HF, 246 dl/mo) | `transformers` AutoModel | No (private "300%-augmented" set) | Not reported |
| shiprocket-ai/open-tinybert-indian-address-ner | ML — TinyBERT NER | Apache-2.0 | 2025-06-19 | (HF, 187 dl/mo) | `transformers` AutoModel | No (same private set) | **Micro F1 0.94** (P 0.93, R 0.94), Macro F1 0.80 |
| malharnd/Indian-Address-Parser-and-Entity-Matching | ML — DistilBERT NER | MIT | 2024-03-17 | 0 | Clone + Streamlit, weights via Google Drive | No | Not reported |
| Adityagupta-dev/Indian-Address-Parser | Hybrid spaCy + regex | MIT | 2025-01-10 | 2 | Clone + Streamlit | No | Not reported |
| ai4bharat/IndicNER | ML — general Indian-lang NER (not address-specific) | MIT | 2023 | (HF) | `transformers` | FLORES-derived | General NER F1, not address-specific |
| shriekdj/indian_address_parser | Deterministic regex | — | (older) | low | Clone | No | Not reported |
| 99roomz/lokly | Deterministic | — | Abandoned (2019-ish) | low | — | No | — |

## Detailed entries

### shiprocket-ai/open-indicbert-indian-address-ner
- URL: huggingface.co/shiprocket-ai/open-indicbert-indian-address-ner
- Base: `ai4bharat/indic-bert` (32.9 M params, ALBERT-style, 11 Indic languages)
- Last commit: 2025-06-18 · Downloads: ~246/month · License: Apache-2.0
- Entities (23 BIO tags): `building_name, city, country, floor, house_details, landmarks, locality, pincode, road, state, sub_locality, …`
- Install: `from transformers import AutoTokenizer, AutoModelForTokenClassification`. Wheel-free, but pulls torch + transformers (~2 GB).
- Model size: ~396 MB
- Test set: none public. Trained on a private "300%-augmented Indian address dataset". No metrics in the model card.
- Limitations (per card): English-optimised, struggles with regional/colloquial formats.
- vs us: deeper schema (floor, house_details, country, road), supports messier free text, but 400 MB download, no pip install, no metrics, slow on CPU. Their schema maps cleanly onto ours — easy to wrap and benchmark on `gold_200.jsonl`.

### shiprocket-ai/open-tinybert-indian-address-ner
- URL: huggingface.co/shiprocket-ai/open-tinybert-indian-address-ner
- Base: `huawei-noah/TinyBERT_General_6L_768D` (66.4 M params)
- Last commit: 2025-06-19 · Downloads: ~187/month · License: Apache-2.0
- Entities: same 23 BIO tags as the IndicBERT sibling.
- Model size: ~761 MB (heavier than the IndicBERT one despite "tiny" name — different vocab)
- **Reported metrics on Shiprocket internal test set**: Micro F1 **0.94** (P 0.93, R 0.94), Macro F1 0.80.
- Install: `transformers` AutoModel, same as above.
- vs us: this is the headline competitor — actual numbers, recent, Apache-2.0. Plug into evaluator first. The 0.94 micro F1 is on *their* set, not on noisy real-world Indian addresses; expect a drop on `gold_200.jsonl`. Our deterministic pincode → state lookup will still beat any ML model on those two fields.

### malharnd/Indian-Address-Parser-and-Entity-Matching
- URL: github.com/malharnd/Indian-Address-Parser-and-Entity-Matching
- Created 2024-03-17, 11 commits, 0 stars, MIT
- Base: DistilBERT fine-tuned for token classification
- Entities (8): `area_locality_name, city_town, flat_apartment_number, landmark, society_name, street, sub_locality, pincode`
- Install: clone repo, download weights from Google Drive, run Streamlit UI. Not pip-installable.
- Test set: none public. Private dataset.
- vs us: smaller schema, no metrics, no install path, abandoned-looking. Skip for benchmarking unless we want a third ML data point.

### Adityagupta-dev/Indian-Address-Parser
- URL: github.com/Adityagupta-dev/Indian-Address-Parser
- Created 2025-01-10, 24 commits, 2 stars, MIT
- Architecture: hybrid — spaCy NER + regex + custom rules
- Entities: cities, states, pincodes, localities (loose schema)
- Install: clone + Streamlit. Not pip-installable. "v2 coming soon" in README.
- Test set: none.
- vs us: closest in spirit (hybrid deterministic), but no package, no benchmark, weaker schema. Not worth running.

### ai4bharat/IndicNER (reference, not an address parser)
- URL: huggingface.co/ai4bharat/IndicNER · MIT
- General Indian-language NER over 11 languages. Not trained on addresses. Useful as a base model if we ever fine-tune our own.

### shriekdj/indian_address_parser & 99roomz/lokly
- Both pure-regex Python projects, both old (pre-2024), both unmaintained. Documented in the original blueprint. No metrics, no test set. Mentioned for completeness; skip for benchmarking.

## Comparison: deterministic (us) vs ML (Shiprocket)

| Dimension | bharataddress v0.1 | Shiprocket TinyBERT |
|---|---|---|
| Install | `pip install bharataddress`, ~3 MB wheel | `pip install transformers torch`, ~2 GB |
| Cold start | <50 ms (lazy JSON load) | seconds (model load) |
| Per-call latency | sub-ms | ~50–200 ms CPU, faster on GPU |
| Network | none, ever | none at inference, but 760 MB download once |
| Pincode → state | 100% (lookup table, 23,915 entries) | ML guess, no guarantee |
| Free-form messy input | weak (locality F1 0.35) | strong (claimed 0.94 micro F1 on private set) |
| Schema | 9 fields | 23 BIO tags (richer) |
| License | MIT | Apache-2.0 |
| Auditability | every decision is a rule you can read | black box |
| Reproducibility | deterministic | deterministic per-weights, retrains drift |

**Read**: deterministic wins on infra fields (pincode, state, district, building number) where we have a closed-form lookup. ML wins on the messy free-text fields (locality, sub_locality, building_name, landmark) where rules can't keep up with the long tail. The right v0.2 architecture is **deterministic spine + ML for the messy fields**, not one or the other.

## Next step (not in this doc, but the obvious follow-up)

1. Wrap shiprocket-ai/open-tinybert-indian-address-ner in a `scripts/eval_competitor.py` that maps its 23 BIO tags onto our 9 fields and runs against `gold_200.jsonl`.
2. Publish a head-to-head per-field table in the README. Our pincode/state numbers are the moat; their locality/building_name numbers are the wake-up call.
3. Decide whether v0.2 ships an *optional* `bharataddress[ml]` extra that pulls transformers and the TinyBERT weights, vs staying pure-deterministic and treating the gap as a known limitation.
