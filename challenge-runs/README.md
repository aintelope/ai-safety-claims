# Challenge runs

Hidden suites and adversarial campaigns run by an independent challenge operator:
`challenge-runs/<market>/<run-id>/suite-manifest.yaml` (schema: `schemas/suite-manifest.schema.json`).
Before scoring, the operator commits the manifest and `freeze-cases.jsonl`: one line per hidden case with
its id, `case_hash` (sha256 of the full case), and the public fields; fields the contract marks
`withholdable` are left out (`"withheld": [...]`) and never published. `suiteHash` is the sha256 of that
file. Hidden cases and weights stay off the repo. Values that need withheld fields (Market 1: how many
named components are on the frozen list) come from the operator's scorer.
An attempt links its run with `challengeRun: <market>/<run-id>` and `hiddenSuiteHash`.
