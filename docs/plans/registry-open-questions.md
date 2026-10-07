# Registry open questions (author picks)

**Status: settled (2026-10-07).** Delete when folded into frozen contracts and the book plan no longer lists them.

Source: author decisions on the six items in the book repo's
`drafts/plans/predictions/eval-registry-split.md` § Open questions.

These rules are fixed for this contract version. Changing them later means a new contract version, decided the usual way.

| # | Question | Decision |
|---|----------|----------|
| 1 | Minimum negative cases | One design-supplied case per bar (`exercisedBars` / `exercisedBy`). No extra floor for Market 4 fakes or Market 1 correlation foils. |
| 2 | Distinct benchmark systems | Different seeds count as distinct. |
| 3 | Unlabeled + config rerun | Rerunning with the system's own configuration counts as allowed access. |
| 4 | Family assignment | Maintainer check (`system-families-correct` on Market 1). |
| 5 | Freeze-field checks | Show per scored system (`freeze-fields-demonstrated`). |
| 6 | Repeated trials per case | One trial per `case_id` only (validator enforces). Repeated runs are not allowed. |

## Where recorded

- `shared-rules/common-v1.yaml`: `oneTrialPerCase`, `distinctBenchmarkSystems`, glossary `unlabeled-intervention-access`
- `market-contracts/market-01/contract-v2.yaml`: human checks updated
- Book plan: `eval-registry-split.md` § Open questions (settled block)
