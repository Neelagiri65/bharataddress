"""v0.4 issue #8: internal consistency sanity-check on pincodes.json.

**Sanity log, not a gate.** The embedded India Post directory is the
source of truth; this script just surfaces statistical anomalies for
human review. It is fully offline — no network calls, no external repo
dependency. (We considered cross-checking against
``captn3m0/india-pincode-regex`` but that repo only ships compiled
regexes, not a structured pincode→state map, so it can't validate
individual rows.)

What this script flags
----------------------

The first three digits of an Indian PIN identify a "sorting district"
which by India Post convention belongs to a single state. We bucket every
pincode by its 3-digit prefix and look at the set of states each prefix
maps to.

* **Clean prefixes**: prefix → exactly 1 state. Expected for the vast
  majority of buckets.
* **Border prefixes**: prefix → 2 states. Usually legitimate (a
  sorting district straddles a state border, e.g. NCR overlap).
* **Anomalous prefixes**: prefix → 3+ states. Worth a manual look —
  could be a data-entry error or a genuine multi-state circle.

The script also reports orphan states (states with very few pincodes,
which usually means a name spelling drift) and the overall row count.

Output: ``reports/pincode_crosscheck.md``.

Usage::

    python scripts/crosscheck_pincodes.py
    python scripts/crosscheck_pincodes.py --out custom/path.md
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OURS_PATH = REPO_ROOT / "bharataddress" / "data" / "pincodes.json"
REPORT_PATH = REPO_ROOT / "reports" / "pincode_crosscheck.md"


def crosscheck(ours: dict) -> dict:
    prefix_states: dict[str, set[str]] = defaultdict(set)
    state_counts: Counter[str] = Counter()
    bad_pincodes: list[str] = []

    for pin, rec in ours.items():
        if not isinstance(pin, str) or not pin.isdigit() or len(pin) != 6:
            bad_pincodes.append(pin)
            continue
        state = (rec.get("state") or "").strip()
        if not state:
            continue
        prefix_states[pin[:3]].add(state)
        state_counts[state] += 1

    clean_prefixes: list[str] = []
    border_prefixes: list[tuple[str, list[str]]] = []
    anomalous_prefixes: list[tuple[str, list[str]]] = []

    for prefix, states in sorted(prefix_states.items()):
        if len(states) == 1:
            clean_prefixes.append(prefix)
        elif len(states) == 2:
            border_prefixes.append((prefix, sorted(states)))
        else:
            anomalous_prefixes.append((prefix, sorted(states)))

    orphan_states = [(s, c) for s, c in state_counts.most_common() if c < 50]

    return {
        "total_pincodes": len(ours),
        "bad_pincodes": bad_pincodes[:20],
        "bad_pincode_count": len(bad_pincodes),
        "distinct_prefixes": len(prefix_states),
        "distinct_states": len(state_counts),
        "clean_prefix_count": len(clean_prefixes),
        "border_prefixes": border_prefixes,
        "anomalous_prefixes": anomalous_prefixes,
        "state_counts_top": state_counts.most_common(10),
        "orphan_states": orphan_states,
    }


def write_report(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out: list[str] = []
    out.append("# Pincode dataset cross-check")
    out.append("")
    out.append(
        "Internal consistency sanity log on the embedded India Post pincode "
        "directory. **Not a gate** — anomalies are surfaced for manual review, "
        "not enforced. Fully offline, no external reference repo. See the "
        "header of `scripts/crosscheck_pincodes.py` for why we don't compare "
        "against captn3m0/india-pincode-regex."
    )
    out.append("")
    out.append("## Totals")
    out.append("")
    out.append(f"- Total pincodes: **{report['total_pincodes']:,}**")
    out.append(f"- Distinct 3-digit prefixes: **{report['distinct_prefixes']:,}**")
    out.append(f"- Distinct states: **{report['distinct_states']:,}**")
    out.append(f"- Malformed pincode keys: **{report['bad_pincode_count']:,}**")
    out.append("")
    out.append("## Prefix → state coherence")
    out.append("")
    out.append(f"- Clean prefixes (single state): **{report['clean_prefix_count']:,}**")
    out.append(f"- Border prefixes (2 states): **{len(report['border_prefixes']):,}**")
    out.append(
        f"- Anomalous prefixes (3+ states): **{len(report['anomalous_prefixes']):,}**"
    )
    out.append("")
    if report["anomalous_prefixes"]:
        out.append("### Anomalous prefixes")
        out.append("")
        out.append("| prefix | states |")
        out.append("|---|---|")
        for prefix, states in report["anomalous_prefixes"]:
            out.append(f"| `{prefix}` | {', '.join(states)} |")
        out.append("")
    if report["border_prefixes"]:
        out.append("### Border prefixes (sample, first 25)")
        out.append("")
        out.append("| prefix | states |")
        out.append("|---|---|")
        for prefix, states in report["border_prefixes"][:25]:
            out.append(f"| `{prefix}` | {', '.join(states)} |")
        out.append("")
    out.append("## Top 10 states by pincode count")
    out.append("")
    out.append("| state | pincodes |")
    out.append("|---|---|")
    for state, count in report["state_counts_top"]:
        out.append(f"| {state} | {count:,} |")
    out.append("")
    if report["orphan_states"]:
        out.append("## Orphan states (<50 pincodes — possible spelling drift)")
        out.append("")
        for state, count in report["orphan_states"]:
            out.append(f"- {state}: {count}")
        out.append("")
    if report["bad_pincodes"]:
        out.append("## Sample malformed pincode keys")
        out.append("")
        out.append(", ".join(f"`{p}`" for p in report["bad_pincodes"]))
        out.append("")
    path.write_text("\n".join(out), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Internal sanity check on pincodes.json.")
    p.add_argument(
        "--out",
        type=Path,
        default=REPORT_PATH,
        help=f"Output markdown path (default: {REPORT_PATH.relative_to(REPO_ROOT)})",
    )
    args = p.parse_args(argv)

    ours = json.loads(OURS_PATH.read_text(encoding="utf-8"))
    report = crosscheck(ours)
    write_report(report, args.out)
    print(
        f"Sanity check complete. Report: {args.out.relative_to(REPO_ROOT)}\n"
        f"  totals: {report['total_pincodes']:,} pincodes, "
        f"{report['distinct_prefixes']:,} prefixes, "
        f"{report['distinct_states']:,} states\n"
        f"  clean={report['clean_prefix_count']:,} "
        f"border={len(report['border_prefixes']):,} "
        f"anomalous={len(report['anomalous_prefixes']):,}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
