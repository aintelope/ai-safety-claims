# Evidence in attempts: freeze, cases, trial extract, raw log

**Status: done (2026-10-07), except the open items below.** Delete once committed and the open items move elsewhere.

Problem: an attempt was a set of fields plus an external URL that did all the work of connecting it to
real work. Fix: the repository holds the evidence the score table is derived from.

## Decisions (2026-10-07)
- `freeze.yaml`: frozenAt (= methodFreezeAt), method (description, code url + commit), scorer. Committed
  before the run; the commit date is the public freeze record. Sketches can preregister this way.
- `freeze-cases.jsonl`: one frozen case per line with `case_hash` (sha256 of the canonical case JSON).
  Field specs per market in `required-columns.yaml` (`cases`).
- **Hidden suites: hashes only.** The operator commits case ids, hashes, and public fields before scoring
  (`challenge-runs/<run>/freeze-cases.jsonl`, sha256 = `suiteHash`) and never publishes withheld fields.
  Values that need withheld content come from the operator's scorer.
- `trials.jsonl` (the extract): one record per trial in our schema (`trial-record.schema.json`), full,
  enforced. The validator derives the score table from cases + trials and rejects a table that disagrees.
  Every trial of a run attempt starts after the freeze.
- **Raw log: any format, not enforced.** `rawLog` in attempt.yaml (sha256, bytes, format, url). Local
  copy under `raw-log/`: the whole file if at most 2,000,000 bytes, otherwise `head` and `tail` of
  1,000,000 bytes each (byte cut); then `url` is required. `validator verify-log` fetches and checks it.
- Wrapped attempts: `adapter/` (released data url + sha256, stdlib script) produces the cases and trials;
  `validator rerun-adapter` reruns it for a maintainer. Examples in `examples/adapters/`.
- Inspect logs: `validator import-inspect` turns a raw Inspect log into `trials.jsonl`; the Inspect
  file itself is the raw log.
- Why a URL and not Zenodo specifically: any URL works because sha256 pins the content. A DOI-backed
  archive (Zenodo, OSF) is recommended for durability, since a dead URL loses the evidence.

## Progress
- [x] Schemas: freeze, trial record, adapter; attempt `rawLog`; suite manifest `suiteHash` = sha256 of the
      hash-only cases file.
- [x] Case and result field specs for Markets 1 and 4; Market 1 public counts (`freeze_complete`,
      `components_count`) and scorer count (`components_named_listed`), checked when not withheld.
- [x] `validator/evidence.py`: case hashes, withheld fields (hidden suites only), field checks, raw-log
      layout (whole up to 2,000,000 bytes, else head/tail of 1,000,000 plus url), derivation per market,
      table comparison, freeze timing. Engine: evidence problems → reporting-insufficient; trials before
      the freeze → qualification-failed.
- [x] Tools (`validator/logtools.py`): `hash-cases`, `raw-log`, `verify-log`, `import-inspect` (tested on
      a real Inspect 0.3.277 JSON log in `examples/inspect/`, and on an `.eval` log via inspect_ai),
      `rerun-adapter`.
- [x] Fixtures: every attempt has evidence; hidden suites hash-only; wrapped attempts produced by
      `examples/adapters/` from `sources/`; all scenario outcomes unchanged.
- [x] Dry run: Evidence section, table-vs-trials check; `new` writes a freeze.yaml skeleton and an empty
      cases file; guard against reused fixture cases.
- [x] Tests: table disagrees with trials; trial before freeze; edited case; raw-log head/tail and url;
      verify-log; adapter rerun; Inspect extract.
- [x] Docs: README filing section, sketches, challenge-runs, examples READMEs.

## Open
- [ ] Several trials per case (epochs, repeated attacks): the unit rule says a unit fails if any trial
      fails; contracts would need a per-market aggregation. Rejected for now.
- [ ] `trials.jsonl` has no size limit; very large suites may need one.
- [ ] Git commit dates of freeze.yaml are not checked in CI (shallow checkout); a maintainer can check
      them, or CI could fetch full history.
