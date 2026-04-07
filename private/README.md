# private/ — proprietary data, never commit

This directory holds proprietary data used to evaluate `bharataddress` against real-world Indian addresses. The data comes from CashlessNow and other private sources and may include hospital names, contact details, and address fields that constitute PII.

**Nothing in this directory may be committed, pushed, or referenced in any public file** — including README.md, HANDOFF.md, commit messages, PR descriptions, issue comments, CI logs, or test failure output. The only files in `private/` that are tracked by git are this README and a single `.gitkeep`. Everything else is gitignored, and a pre-commit hook (`.githooks/pre-commit`) blocks accidental staging.

## Layout

```
private/
├── README.md       ← this file (the only tracked content file)
├── .gitkeep        ← keeps the directory visible in the tree
├── raw/            ← raw source data (CashlessNow exports, CSVs, scrapes)
├── processed/      ← cleaned JSONL files ready for evaluate.py
├── reports/        ← private eval reports (--private-report writes here)
└── scripts/        ← private-only processing scripts
```

## How to use

### Running the public evaluator against a private gold set
```bash
PYTHONPATH=. python scripts/evaluate.py \
    --gold private/processed/gold_500.jsonl \
    --private-report \
    --json private/reports/eval_gold_500.json
```
- `--gold` accepts any path; point it at a file inside `private/`.
- `--private-report` ensures the JSON report is written under `private/reports/`, never `reports/`.
- Without `--verbose`, failure dumps print only row numbers and field names — never full address strings. This is the default for a reason: even local terminal scrollback can leak into screenshots.

### Adding processing scripts
- Drop them under `private/scripts/`. They are gitignored along with everything else here.
- They should read from `private/raw/`, write to `private/processed/`, and never write outside `private/`.
- If a script needs to share an aggregate metric (e.g. "private gold_500: 52% exact match"), surface it via stdout — never embed individual addresses or row contents in any artefact that might leave this directory.

## What goes where

| Stage | Location | Allowed contents |
|---|---|---|
| Raw dumps | `private/raw/` | CashlessNow CSV exports, scrapes, vendor lists |
| Cleaned JSONL | `private/processed/` | gold-format files: `{"input": ..., "expected": {...}}` |
| Eval reports | `private/reports/` | JSON output from `evaluate.py --private-report` |
| Helper code | `private/scripts/` | one-off cleaners, normalisers, splitters |

## If private data accidentally leaks into a commit

This is the fire drill — execute it, do not deliberate.

1. **Stop pushing immediately.** If the bad commit is local, `git reset --soft HEAD~1` and re-stage cleanly.
2. **If the bad commit was already pushed**, force-push a cleaned history. `git filter-repo` (preferred) or `git filter-branch` to remove the offending blob, then `git push --force-with-lease origin main`. The pre-commit hook is the safety net; force-push is the recovery procedure.
3. **Rotate any credentials** that may have been exposed (API keys, vendor logins, anything tied to CashlessNow).
4. **Notify Neelagiri** so the GitHub repo's secret-scanning alerts can be reviewed and any caches (forks, GitHub mirror, archive.org snapshots) can be flagged for takedown.
5. **Treat the leaked data as compromised.** Anything that touched a public commit, even briefly, must be assumed to have been mirrored.

## Why this matters

`bharataddress` itself is MIT-licensed and lives in public. The competitive moat is not the parser — it is the dataset of cleaned, validated, real-world Indian addresses tied to hospitals, insurers, and TPAs. That dataset is what CashlessNow is paying to build, and it stays here.
