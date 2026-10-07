# Astro site

**Status: decided, not started.**

## Decisions (2026-10-07)
- GitHub Pages under the current org: `aintelope.github.io/ai-safety-claims`; moves with the repo.
- Sketches get pages, not prominently: not in the nav or the home table; linked from a collapsed
  "Work in progress" section on each market page; `noindex`.
- The validator stays the only computation. Astro renders an export.

## Steps
- [ ] `validator export` → `ui/data/*.json` (contracts, attempts, outcomes, adjudication status, sketch dry
      runs, evidence summaries) with a schema; `validator check` compares the export instead of
      `ui/index.html`.
- [ ] `site/` Astro app (own package.json, static, no framework; vanilla JS filters). No dependency on the
      book's site.
- [ ] Pages: home (markets, outcomes, not-a-resolution-source banner); market version (question,
      thresholds, bars, outcome, attempts, coverage grid, collapsed sketches); attempt (metrics vs
      thresholds, checks, freeze and trial facts, raw log link, files at commit); sketch (dry run);
      contribute (new → dry-run → submit, fixtures); snapshots (tags, archive links).
- [ ] Every page names the commit or tag it was built from; outcome pages link the JSON at that tag.
- [ ] CI: validate, then build from the export; deploy Pages from main; smoke-build each
      `examples/scenarios` tree.
- [ ] Retire `ui/index.html`.
