# Challenge runs

Hidden suites and adversarial campaigns run by an independent challenge operator:
`challenge-runs/<market>/<run-id>/suite-manifest.yaml` (schema: `schemas/suite-manifest.schema.json`).
Manifests hold hashes, counts, dates, and released labels only. Hidden cases and weights stay off the repo.
An attempt links its run with `challengeRun: <market>/<run-id>` and `hiddenSuiteHash`.
