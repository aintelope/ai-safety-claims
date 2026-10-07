# Listing template

Text a host copies into a prediction-market question that resolves on this registry. Fill `<…>`; one
question per contract version. Tested with an admin-role agent on six cases (2026-10-06): all resolved as
intended; this version fixes the defects it reported (title/fine-print date conflict, Zenodo DOI only
inside the repo, no rule for a missing or malformed file, moved tags, missing timezone).

Do not list while `registry.yaml` has `resolutionSource: false` or the contract is `draft`.

---

**Title.** What is the `outcome` field of `market-outcomes/<market>-v<K>.json` at tag `snapshot-<cutoff>` in `github.com/<host>/ai-safety-claims`?

**Options.** YES, NO, OTHER. (Contracts whose `outcomes` list two options use those two.)

**Dates.** Question closes <cutoff>, 23:59 UTC (the evidence cutoff). Expected resolution <cutoff + 60 days>, when the snapshot tag is created.

**Resolution criteria.** This question resolves to the value of the `outcome` field in the file `market-outcomes/<market>-v<K>.json` at git tag `snapshot-<cutoff>` of `github.com/<host>/ai-safety-claims`. Admins read that one field. They do not evaluate papers or re-score attempts: attempts the file marks non-qualifying, for any reason including unsettled judgments, do not count.

**Fine print.**
- Copy the market's fine print from Appendix H verbatim: the Common rules paragraph and its adversarial budget (serious or default), so the question stands on its own.
- Use the tag whenever it was created, if it exists by <cutoff + 90 days>, 23:59 UTC.
- If the tag is missing on GitHub, or was moved after creation, use the version titled `snapshot-<cutoff>` of the Zenodo record <concept DOI>, which is deposited when the tag is created.
- The question is annulled if, by <cutoff + 90 days>, 23:59 UTC, neither source has the file, or the file is unreadable, names a different market or contract version, has `contractStatus` other than `frozen`, has `resolutionSource` other than `true`, or has an `outcome` value not among the options.
- OTHER means no qualifying attempt existed. It is not an annulment.

**Background (not part of the resolution).** The registry scores published AI-safety evaluations against `market-contracts/<market>/contract-v<K>.yaml` (readable at `https://ai-safety-claims.com/markets/<market>/v<K>/`, a page that stays fixed for this version), copied from Appendix H of *Towards Superintelligence Alignment*. YES: at least one qualifying attempt met the frozen performance bars. NO: every qualifying attempt missed them. OTHER: no qualifying attempt existed. A YES is not evidence that the underlying alignment problem is solved.
