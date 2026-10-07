# Sketches and contributor tools

**Status: done (2026-10-07).** Delete this file once committed; `sketches/README.md` is the live doc.

## Decisions
- A sketch is an attempt folder under `sketches/`; no outcome reads it. Same files and schemas.
- Submitting is a plain move to `submitted-attempts/`; the id and `filedAt` stay. The merge before the
  snapshot tag is what counts.
- Submit is refused while there are blocking gaps, fixture leftovers, or (without
  `--allow-not-qualifying`) qualification gaps.
- Fixtures are the templates: `new --from-fixture <scenario>` copies one, marked fictional.

## Done
- [x] `validator new | dry-run | submit | adjudicate pending|start|set` (`validator/contribute.py`).
- [x] Dry run lists every gap with value and threshold, coverage per family or case, maintainer checks,
      and a bar preview ("not exercised" where no cases).
- [x] Guards: fixture header, fixture values, rows identical to fixture rows; adjudication conflict guards.
- [x] CI: `check` rejects outcome fields and unknown contracts in sketches.
- [x] Fixture `m04-sketch` with expected dry-run text; `test_contribute`.
- [x] Docs: `sketches/README.md`, README, GOVERNANCE, adjudication and examples READMEs.

## Follow-ups (tracked in other plans)
- Evidence files in the dry run and skeleton: [evidence-logs.md](evidence-logs.md).
- Sketch pages on the site: [astro-ui.md](astro-ui.md).
