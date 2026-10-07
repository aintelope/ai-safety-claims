# Adjudication

Maintainer-only. One file per attempt: `adjudication/<market>/<attempt-id>.yaml`
(schema: `schemas/adjudication.schema.json`), with a `pass`, `fail`, or `unsettled` verdict and a note for
each human check the shared rules and the contract name. A missing or unsettled check at the end of the
window makes the attempt not qualifying. See `GOVERNANCE.md` for conflicts.
