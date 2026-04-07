"""Run shiprocket-ai/open-tinybert-indian-address-ner over gold_200 and report
per-field P/R/F1 + exact-match in the same shape as scripts/evaluate.py.

Usage:
    python scripts/eval_competitor.py --json reports/eval_competitor.json

Notes
-----
This script downloads ~760 MB of model weights from Hugging Face on first
run. It is intentionally NOT a runtime dependency of bharataddress — only a
benchmark. Requires `torch` and `transformers` in the active environment.

The TinyBERT NER model emits tags like B-building, I-locality, B-pincode etc.
We collapse contiguous tag spans into field strings and map them onto the
same nine fields the bharataddress evaluator uses (substring match, same
counters, same exact-match definition).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

# Reuse the gold loader + scorer from the in-house evaluator.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate import FIELDS, evaluate, load_gold, print_report  # noqa: E402

GOLD_PATH = Path(__file__).resolve().parents[1] / "tests" / "data" / "gold_200.jsonl"
MODEL_ID = "shiprocket-ai/open-tinybert-indian-address-ner"

# Map TinyBERT label suffixes onto bharataddress field names.
# Real TinyBERT labels (from model.config.id2label):
#   building_name, city, country, floor, house_details, landmarks,
#   locality, pincode, road, state, sub_locality
# Note: TinyBERT has NO `district` and NO `building_number` — it lumps the
# latter into `house_details`. We map house_details → building_number for the
# fairest possible comparison; district is unscoreable for the competitor.
LABEL_TO_FIELD = {
    "buildingname": "building_name",
    "housedetails": "building_number",
    "floor": "sub_locality",
    "road": "sub_locality",
    "sublocality": "sub_locality",
    "landmarks": "landmark",
    "locality": "locality",
    "city": "city",
    "state": "state",
    "pincode": "pincode",
    "country": None,  # ignore
}


def _normalise_label(label: str) -> tuple[str, str]:
    """Return (BIO-prefix, normalised-tag)."""
    if label in ("O", "0"):
        return "O", ""
    prefix, _, tag = label.partition("-")
    if not tag:
        tag = prefix
        prefix = "B"
    tag = tag.lower().replace("-", "").replace("_", "").replace(" ", "")
    return prefix.upper(), tag


def _spans_to_fields(tokens: list[str], labels: list[str]) -> dict[str, str | None]:
    """Collapse BIO-tagged tokens into a dict of field -> string."""
    out: dict[str, list[str]] = {f: [] for f in FIELDS}
    current_tag: str | None = None
    current_buf: list[str] = []

    def _flush():
        nonlocal current_tag, current_buf
        if current_tag and current_buf:
            field = LABEL_TO_FIELD.get(current_tag)
            if field:
                out[field].append(" ".join(current_buf))
        current_tag = None
        current_buf = []

    import re as _re

    for tok, lab in zip(tokens, labels):
        prefix, tag = _normalise_label(lab)
        if prefix == "O" or not tag:
            _flush()
            continue
        if prefix == "B" or tag != current_tag:
            _flush()
            current_tag = tag
            current_buf = [tok]
        else:
            current_buf.append(tok)
    _flush()

    # building_number: TinyBERT lumps it into house_details. Extract the
    # leading numeric token (with optional letter suffix / dash) so the field
    # comparison is fair.
    if out["building_number"]:
        joined = ", ".join(out["building_number"])
        m = _re.search(r"[A-Za-z]{0,3}[-]?\d+[A-Za-z]?(?:[/-]\d+[A-Za-z]?)*", joined)
        out["building_number"] = [m.group(0)] if m else []

    # Join multi-span fields with ", " — same shape as bharataddress output.
    return {f: (", ".join(parts) if parts else None) for f, parts in out.items()}


class TinyBertParser:
    def __init__(self) -> None:
        self.tok = AutoTokenizer.from_pretrained(MODEL_ID)
        self.model = AutoModelForTokenClassification.from_pretrained(MODEL_ID)
        self.model.eval()
        self.id2label = self.model.config.id2label

    @torch.no_grad()
    def parse(self, text: str) -> dict:
        enc = self.tok(
            text,
            return_tensors="pt",
            truncation=True,
            return_offsets_mapping=True,
            return_special_tokens_mask=True,
        )
        offsets = enc.pop("offset_mapping")[0].tolist()
        special = enc.pop("special_tokens_mask")[0].tolist()
        logits = self.model(**enc).logits[0]
        pred_ids = logits.argmax(-1).tolist()

        # Reassemble per-word tokens (collapse subwords by taking first
        # subword's tag and its full word slice from offsets).
        tokens: list[str] = []
        labels: list[str] = []
        last_word_end = -1
        for tid, (start, end), is_special in zip(pred_ids, offsets, special):
            if is_special or start == end:
                continue
            label = self.id2label.get(tid, "O")
            # Subword continuation if start == previous end (no whitespace gap).
            if start == last_word_end and tokens:
                tokens[-1] += text[start:end]
            else:
                tokens.append(text[start:end])
                labels.append(label)
            last_word_end = end

        return _spans_to_fields(tokens, labels)


def run(cases: list[dict], parser: TinyBertParser) -> list[dict]:
    """Mirror the shape evaluate.evaluate() expects: a list of cases, but parse
    via the competitor model. We piggyback on evaluate.evaluate() by patching
    its `parse` import temporarily."""
    import evaluate as ev  # local import to avoid name shadowing

    out_cases = []
    for case in cases:
        out_cases.append(case)

    # Monkeypatch the parse function inside scripts/evaluate.py for this run.
    original = ev.parse

    class _Wrap:
        def __init__(self, d: dict) -> None:
            self._d = d

        def to_dict(self) -> dict:
            return self._d

    def _competitor_parse(text: str):
        return _Wrap(parser.parse(text))

    ev.parse = _competitor_parse  # type: ignore[assignment]
    try:
        report = ev.evaluate(out_cases)
    finally:
        ev.parse = original  # type: ignore[assignment]
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--gold", type=Path, default=GOLD_PATH)
    p.add_argument("--json", type=Path, help="Write full report JSON")
    p.add_argument("--fail-only", action="store_true")
    args = p.parse_args(argv)

    cases = load_gold(args.gold)
    if not cases:
        print(f"ERROR: no cases loaded from {args.gold}", file=sys.stderr)
        return 2

    print(f"Loading {MODEL_ID} (first run downloads ~760 MB)...", file=sys.stderr)
    parser = TinyBertParser()
    print(f"Model loaded. id2label sample: {list(parser.id2label.items())[:8]}", file=sys.stderr)

    report = run(cases, parser)
    print_report(report, fail_only=args.fail_only)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nFull report written to {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
