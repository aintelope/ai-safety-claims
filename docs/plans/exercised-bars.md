# Exercised bars and decoupling from the manuscript

**Status: done (2026-10-07).** Delete this file once committed.

## Decisions
- A bar whose denominator the test design supplies needs at least one such case; otherwise the attempt is
  not qualifying (OTHER), not a NO. An empty denominator from the method's own output is a missed bar.
- Same text in Appendix H (book repo, reading rules), `shared-rules/common-v1.yaml` (`exercisedBars`),
  and README.
- The registry will be decoupled from the manuscript (independence; non-TSA contracts): `GOVERNANCE.md`
  § Decoupling, and step 5 of the book's `drafts/plans/predictions/eval-registry-split.md`.

## Done
- [x] `exercisedBy` on contract bars; validator adds `exercised:<bar>` qualification checks.
- [x] Market 4: all bars; Market 1: identification and coverage (false-certificate bars stay without).
- [x] Fixture `m04-no-fakes-other` (OTHER, was NO before).
- [x] Appendix H sentence; book `sync:predictions` and `make check` pass; book session log written.

## Open
- [x] Author call (2026-10-07): one design-supplied case per bar is enough; see
      `registry-open-questions.md` item 1.
