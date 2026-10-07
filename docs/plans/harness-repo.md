# Workbench repo for runnable code

**Status: scaffold built locally (2026-10-07), not pushed.** The user creates
`aintelope/ai-safety-claims-workbench`; the local checkout is `../ai-safety-claims-workbench` with
`origin` set, no commits yet.

The registry stays data-only and never runs contributed code. The workbench holds runnable evaluations
and exports sketches in the registry's evidence format ([evidence-logs.md](evidence-logs.md)).

## Decisions (2026-10-07)
- Name: `ai-safety-claims-workbench`, under `aintelope`.
- Two contribution types under `contrib/{submitter}-{date}-{slug}/`:
  - **inspect** (default, most examples): an Inspect task on the market scaffold. The adapter is the
    standard: `metadata.case_id` on samples and result fields in scorer metadata, read by the registry's
    `import-inspect`.
  - **custom**: a self-contained directory with its own entrypoint and raw-log format, plus an adapter
    script to `trials.jsonl`. One example.
- The workbench reuses the registry's commands (hash-cases, import-inspect, raw-log, derive-table,
  dry-run) instead of reimplementing hashing or derivation.

## Done
- [x] Package `workbench` (Apache-2.0): `new`, `freeze [--commit]`, `run`, `export`.
- [x] Freeze discipline: clean tree to freeze; freeze.yaml records the commit; `--commit` commits and tags
      `freeze/<id>`; `run` refuses uncommitted or post-freeze changes; tasks read frozen cases only.
- [x] Market 4 scaffold: cases from episodes.yaml (setup, channel prefix, correction, optional pressure,
      probe, target, regex check, all hashed); protocol with a REMEMBER: memory across a context reset;
      rule scorer writing uptake / persisted_after_reset / sham_succeeded.
- [x] Templates (inspect, custom) and three examples (two Inspect, one custom), all exporting cleanly.
- [x] Registry additions: `derive-table`, `raw-log --update-attempt`; derivation no longer blocked by
      unrelated evidence gaps.
- [x] Tests: each example end to end against a scratch registry copy; freeze guards; `new` for both
      types. CI checks out the registry and runs with the mock model (no API keys).

## Market 1 sketch (2026-10-07)
- [x] Workbench `markets/market_01`: frozen cases from `systems.yaml` (freeze_complete and
      components_count derived).
- [x] Contribution `zarncke-2026-10-07-lab-sim-intervention-uad` (custom): the book's lab-simulation
      intervention UAD (`uad_intervention.py`, pre-registered defaults, book commit 636f685 pinned and
      checked) on 7 ecology scenarios × 8 seeds = 56 systems covering all five families.
      `build_systems.py` (reads ground truth) → `systems.yaml`; `run.py` (method, a guard raises if method
      code reads `LabConfig.units`); `adapter.py` (scorer).
- [x] Verified in scratch copies: freeze → run → export → registry dry run. Evidence consistent.
      Preview: identification 0.93, coverage 1.0, false-complete 8/48 = 0.167 (upper 0.28): the
      `shared_slot` miss known from lab-sim LS-20 issues complete certificates naming only eng1.
- Findings to keep in view:
  - `LabConfig.units` is world wiring as well as ground truth; removing it removes the units, so the
    method gets the real config for its reruns and the guard checks it never reads the field.
  - Seeds of the deterministic mock run behave identically: 56 systems are 7 distinct ones, so the
    count and the Clopper-Pearson bound overstate independence (unit rule).
  - Family mapping and the declared response statistic / minimum change / no-effect range are author
    judgments, not checked by intervention.
- [ ] Not yet frozen or exported for real: needs commits in the workbench (user to approve).
- [ ] Toward an attempt: an independent operator's hidden suite, an adversarial subset built after the
      freeze, a serious adversarial route, structurally distinct systems instead of seeds.

## Open
- [ ] User: create the GitHub repo, first commit, push.
- [ ] Model-graded checks as an option next to regex checks (needs a judge model; not in CI).
- [ ] Market 1 scaffold: composed systems with frozen component lists; hidden-suite flow with an operator.
- [ ] Publishing the raw log for large runs (`export --url`) and the freeze tag push in the docs' example.
