# CLAUDE.md — bharataddress project rules

Project-level overrides and reminders for Claude Code sessions in this repo. Read this at the start of every session, in addition to the global `~/.claude/CLAUDE.md`.

## Project context

`bharataddress` is a deterministic Indian address parser. Public, MIT-licensed, zero runtime dependencies, ships an embedded India Post pincode directory. The parser core is in `bharataddress/parser.py`. Public eval is `tests/data/gold_200.jsonl` + `scripts/evaluate.py`. The architectural constraint is binding: `parse()` makes zero network calls (enforced by a socket monkeypatch test).

## Private Data Rules — NON-NEGOTIABLE

Some sessions involve proprietary data from CashlessNow and other private sources. This data lives under `private/` and is gitignored except for `private/README.md`. The pre-commit hook at `.githooks/pre-commit` blocks accidental staging of anything else in `private/`, anything matching sensitive markers (`cashlessnow`, `hospital_data`, `proprietary`, `_pii_`, `_sensitive_`), and anything larger than 1 MB.

The hook is the safety net. The rules below are the primary defence — they apply to Claude's behaviour, not just to git.

### Absolute prohibitions

1. **Never read, reference, quote, or include any content from `private/` in any commit message, PR description, README update, HANDOFF.md update, code comment, docstring, or any other file that will be tracked by git.**
2. **Never log or print full address strings from a private gold set in any output that gets committed.** Aggregate metrics only — counts, percentages, F1 scores. No individual rows.
3. **If the user pastes raw hospital, address, or contact data in chat, process it but never echo it back in a form that could be copy-pasted into a public file.** Quote single field names if you must (e.g. "the `district` column"); never quote a full row.
4. **When running `evaluate.py` against private data, always pass `--private-report` and a `--json` path under `private/reports/`.** The flag forces the JSON output into `private/reports/` and refuses to write anywhere else. Without it, a private gold set's failure dump (which contains real addresses) would land in the public `reports/` directory.
5. **When running `evaluate.py` against private data, never pass `--verbose`.** The default suppresses addresses in failure output. Verbose is only for the public gold set, where every row is already published.
6. **HANDOFF.md updates after a private-data session must report aggregate numbers only.** Format: `"private gold_500: 52% exact match, building_name F1 0.61"`. Never reference an individual row, address, district, or hospital.

### When in doubt

- If you are not sure whether a piece of data is private, treat it as private. Move it to `private/`, don't commit it, ask the user.
- If the pre-commit hook blocks a commit, do not bypass with `--no-verify`. Read the error, understand which rule fired, and either move the file or split the commit. The hook is calibrated to block real risks, not pedantically.
- If you accidentally type a private address into a file, an error message, or a commit message, stop, remove it, and reset before pushing. The fire drill in `private/README.md` covers post-leak recovery.

## Standard project conventions

- All commands run from project root. Use `PYTHONPATH=.` for scripts that import `bharataddress` outside an editable install.
- Tests: `PYTHONPATH=. python3 -m pytest tests/ -q`. 37 tests, all must pass before any tag.
- Public eval: `PYTHONPATH=. python3 scripts/evaluate.py --json reports/eval_v0.X.Y.json`. Reports under `reports/` are committed.
- Private eval: `PYTHONPATH=. python3 scripts/evaluate.py --gold private/processed/<file>.jsonl --private-report --json private/reports/<file>.json`. Reports under `private/reports/` are gitignored.
- Don't hand-edit `bharataddress/data/pincodes.json` — rebuild via `scripts/build_pincode_data.py`.
- The substring matcher in `evaluate.py` is two-way and case-insensitive — don't tighten it without rebaselining the whole gold set.
- HANDOFF.md must be updated at the end of every session (per global rules) and committed before pushing.
