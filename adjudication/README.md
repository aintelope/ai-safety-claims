# Adjudication

Maintainer-only. One file per attempt: `adjudication/<market>/<attempt-id>.yaml`
(schema: `schemas/adjudication.schema.json`), with a `pass`, `fail`, or `unsettled` verdict and a note for
each human check the shared rules and the contract name. A missing or unsettled check at the end of the
window makes the attempt not qualifying. See `GOVERNANCE.md` for conflicts.

```bash
python -m validator adjudicate pending                         # attempts with checks not yet pass or fail
python -m validator adjudicate start <attempt-id> --maintainer you   # file with every check unsettled
python -m validator adjudicate set <attempt-id> <check-id> pass --note "evidence reviewed" --maintainer you
```

The helper refuses a maintainer who submitted the attempt, sketches, unknown check ids, empty notes, and
edits to another maintainer's record. Conflicts it can't see (employer, authorship, positions) are yours
to declare.
