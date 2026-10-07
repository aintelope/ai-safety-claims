# Astro site

**Status: first version built (2026-10-08).** Open items below.

## Decisions (2026-10-07)
- GitHub Pages under the current org: `aintelope.github.io/ai-safety-claims`; moves with the repo.
- Sketches get pages, not prominently: not in the nav or the home table; linked from a collapsed
  "Work in progress" section on each market page; `noindex`.
- The validator stays the only computation. Astro renders an export.

## Built (2026-10-08)
- [x] `validator export` writes `site/src/data/registry.json` (contracts of every version with score-table
      spec and outcome, shared rules, registry settings, sketch dry runs, repository and commit). Not committed;
      generated in CI before each build.
- [x] Astro app in `site/` (Astro 7, static, no framework): home with the markets table and the
      not-a-resolution-source banner; `/markets/market-NN/` (latest version) and `/markets/market-NN/vK/`
      (stable per version, linked from the listing template) with the full contract: question, outcomes,
      background, YES requires, output, qualification thresholds, bars, freeze order, adversarial budget,
      maintainer checks, score-table columns, shared rules inline, current outcome, and a collapsed sketch list;
      `/rules/common-v1/`; `/sketches/` and `/sketches/<id>/` (noindex, linked only from market pages and the
      footer).
- [x] `pages.yml` builds the site after `validator check` and deploys `site/dist`; `validate.yml` also builds
      it on every push and pull request. `ui/index.html` and `validator/ui.py` retired.
- [x] Checked locally: 39 pages build; no horizontal overflow at 390px.

## Open
- [ ] Per-attempt pages (metrics against thresholds, evidence summary, raw log link).
- [ ] Snapshots page (tags and archive links) once snapshot tags exist.
- [ ] A smoke build per `examples/scenarios` tree (needs export to take a root).
