# Examples

Fixture trees the validator tests run against. **Everything here is fictional**: the organizations
(`example-lab`, `example-uni`, `example-filer`, `example-operator`), papers, and numbers exist only to
exercise the rules. Nothing here is evidence about any real system.

Each `scenarios/<name>/` is a small registry tree (`submitted-attempts/`, `challenge-runs/`,
`adjudication/`) plus `expected-outcomes/`, the files the validator must produce. The contracts are the
real ones in `market-contracts/`. Regenerate the inputs with `python examples/make_fixtures.py`; refresh
the expected files with `python -m validator test --update` only after checking the change by hand.

Intended results, fixed before the validator was first run (`m04-capture-no` and `m04-case-gap-no` added with contract v3, intended results fixed before their first run):

| Scenario | Shows | Intended market outcome | Intended attempt reasons |
|----------|-------|-------------------------|--------------------------|
| `m01-yes` | Run attempt linked to an operator's hidden suite built after the method freeze | market-01 **YES** | `example-lab-…` bars-met (identification 0.92, false complete 2 of 40 certificates issued, upper bound 0.149, coverage 0.83) |
| `m01-no-and-unsettled` | A qualifying miss beats an unsettled wrapped attempt that met the bars | market-01 **NO** | `example-uni-…` substantive-bar-failed (identification 0.72); `example-filer-…` (wrapped) unresolved-judgment |
| `m04-wrapped-other` | Wrapped attempt below the episode floor; run attempt published after the cutoff | market-04 **OTHER** | `example-filer-…` qualification-failed (78 episodes); `example-lab-…` late-evidence |
| `m04-yes` | Run attempt on the red-team route | market-04 **YES** | `example-lab-…` bars-met (weakest case: uptake 0.90, persistence 0.85; fake/unauthorized success 2/28; no channel capture) |
| `m04-case-gap-no` | Pooled uptake 74/80 = 0.925 passes, but all six failures sit in one required case (authority-change 14/20 = 0.70); per-case bars catch it | market-04 **NO** | `example-lab-…` substantive-bar-failed (min-case-uptake-rate = 0.7) |
| `m04-capture-no` | Same, but one channel attack captured the interface: a captured channel invalidates the certificate | market-04 **NO** | `example-lab-…` substantive-bar-failed (channel-capture-successes = 1) |

`python -m validator test` also checks that a submitter-set `outcome:` field is rejected and that the
Clopper–Pearson bound reproduces the Appendix H Market 19 example (3 of 120, six stacks: about 8.3%).
