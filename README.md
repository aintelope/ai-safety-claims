# ai-safety-claims

A registry that scores published AI-safety evaluations against frozen **market contracts** and writes one
outcome file per contract version: YES, NO, or OTHER. A prediction-market admin resolves a question by
opening that file at a named git tag and reading its `outcome` field.

> **Status: scaffold. Not a resolution source.** Hosted for now by aintelope, which is not independent
> of the book project the contracts come from (`registry.yaml`: `resolutionSource: false`). Contracts are
> drafts. Until an independent host owns the repo and tags `snapshot-0`, no file here resolves any
> question.[^interim] See [`GOVERNANCE.md`](GOVERNANCE.md).

[^interim]: Until then, attempts submitted or authored by aintelope or Gunnar Zarncke are not accepted.

## What an outcome means

- **YES**: at least one qualifying attempt met the frozen performance bars.
- **NO**: at least one qualifying attempt existed, and every qualifying attempt missed the bars.
- **OTHER**: no qualifying attempt existed.

A qualifying attempt meets the shared qualification rules plus the contract's sample-size, coverage,
freeze, and adversarial thresholds, and reports the required outputs even if its rates miss. It must also
exercise every bar: if a rate is computed over cases the test design supplies (say, fake corrections) and
the attempt has none, it is not qualifying rather than a NO. A YES says a published method met these bars
by the deadline. It does not say the underlying alignment problem is solved, or that any deployed system
is safe.

## Where the contracts come from

The markets are defined in Appendix H, "Dated Predictions on the Bridges," of the book
[*Towards Superintelligence Alignment*](https://github.com/GunnarZarncke/towards-asi-alignment). Each
contract copies its appendix box verbatim and adds machine-readable thresholds. Until the appendix is cut
down to pointers, the appendix text wins on any disagreement. Ambiguities found while copying are listed
under `openQuestions` in the contract; a contract stays `draft` until they are settled. Version numbers follow the book's contract versions.

| Contract | Title | Evidence cutoff | Status |
|----------|-------|-----------------|--------|
| [`market-01` v2](market-contracts/market-01/contract-v2.yaml) | Discovering where control resides | 2027-12-31 | draft |
| [`market-04` v3](market-contracts/market-04/contract-v3.yaml) | Corrections change the system | 2027-12-31 | draft |

The other catalog markets get contracts as they are copied. Market 14 (deployment criteria are binding)
is not handled here: its evidence is a few public documents, so it is listed directly as a YES/NO question.

## How it works

1. A contract in `market-contracts/market-NN/contract-vK.yaml` is frozen at a git tag.
2. Anyone files an **attempt** by pull request: `submitted-attempts/<attempt-id>/` with `attempt.yaml`,
   `score-table.csv`, and whatever else the contract lists.
3. Hidden suites built by an independent **challenge operator** live in `challenge-runs/` (hashes and
   counts only; hidden cases stay off the repo).
4. The **validator** recomputes rates and confidence bounds from the score table and checks files, dates,
   freeze order, and adversarial-route thresholds.
5. The **maintainer** records the calls a script cannot make (independence, ground truth, broad capability)
   in `adjudication/`.
6. The validator writes `market-outcomes/market-NN-vK.json`; CI fails if that file disagrees with the
   inputs on `main`.

Attempt types: `run` (the submitter ran the evaluation) and `wrapped` (anyone files a published result by
others, within the wrapping rule in [`shared-rules/common-v1.yaml`](shared-rules/common-v1.yaml)).
`stack` and `challenge` are reserved for the tournament markets.

## Filing an attempt

- Directory and id: `{submitter}-{filedAt}-{slug}`, e.g. `example-lab-2027-05-02-boundary-finder-v1`.
  Lowercase `[a-z0-9-]`; the date is the day the folder is first opened. Ids never change after filing.
- `attempt.yaml` follows [`schemas/attempt.schema.json`](schemas/attempt.schema.json).
- `score-table.csv` has the columns in the contract's `required-columns.yaml`.
- The evidence it is derived from (rule: `evidence` in [`shared-rules/common-v1.yaml`](shared-rules/common-v1.yaml)):
  - `freeze.yaml`: what was fixed before scoring (method, code commit, scorer). Commit it before the run.
  - `freeze-cases.jsonl`: one frozen case per line with its `case_hash` (`python -m validator hash-cases`).
    For a hidden suite the challenge operator's file holds ids, hashes, and public fields only.
  - `trials.jsonl`: one record per trial in the registry's format
    ([`schemas/trial-record.schema.json`](schemas/trial-record.schema.json));
    `python -m validator import-inspect` extracts it from an Inspect log. The validator re-derives the
    score table from the cases and trials and rejects a table that disagrees.
  - `raw-log/` and `rawLog` in `attempt.yaml`: the harness's own log in any format, whole up to 2 MB,
    otherwise its first and last 1 MB with a URL to the full file (`python -m validator raw-log`).
    Any URL works, since the sha256 pins the content; a DOI-backed archive keeps it reachable.
  - Wrapped attempts: `adapter/` with the released data's URL and sha256 and the script that turned it
    into the cases and trials (examples in [`examples/adapters/`](examples/adapters/)).
- Never write `qualifying`, `barsMet`, `outcome`, or `reason` in any file you submit; the validator
  rejects the tree if you do.
- A complete score table that misses the bars is still a qualifying attempt, and counts toward NO.
- To write and run an evaluation, use the workbench,
  [aintelope/ai-safety-claims-workbench](https://github.com/aintelope/ai-safety-claims-workbench): Inspect
  scaffolds per market (or a self-contained directory with an adapter), freeze discipline, and
  `workbench export`, which writes a sketch here with all evidence files.
- Not there yet? Start a **sketch** instead: the same folder under `sketches/`, which no outcome reads.
  `python -m validator dry-run <dir>` lists what it still misses, and submitting is a plain move to
  `submitted-attempts/`. See [`sketches/README.md`](sketches/README.md).

See [`examples/`](examples/) for complete fictional attempts.

## Deadlines

- **Evidence cutoff**: the contract's resolve-by date. The result must be public by then.
- **Window**: 60 days after the cutoff. Attempts for evidence public by the cutoff may still be filed,
  and the maintainer adjudicates, within the window. A human check still unsettled when the window closes
  makes that attempt not qualifying.
- **Snapshot**: tag `snapshot-<cutoff date>` is created when the window closes, with a Zenodo copy.
- **Missing snapshot**: if neither the tag nor its Zenodo copy exists 30 days after the window closes, the
  question is annulled. That is a registry failure, not OTHER.

## Running the validator

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m validator build   # write market-outcomes/ and ui/index.html
.venv/bin/python -m validator check   # what CI runs: fail if those files are out of date
.venv/bin/python -m validator test    # fixture scenarios and statistics tests

.venv/bin/python -m validator new --market market-04 --submitter you --slug name [--from-fixture m04-yes]
.venv/bin/python -m validator dry-run sketches/<id>   # what a sketch or attempt still misses
.venv/bin/python -m validator submit sketches/<id>    # guarded move to submitted-attempts/
.venv/bin/python -m validator adjudicate pending      # maintainers: open human checks
.venv/bin/python -m validator verify-log <dir>         # maintainers: fetch and check the full raw log
.venv/bin/python -m validator rerun-adapter <dir> --source <file>   # maintainers: rerun a wrapped adapter
```

`ui/index.html` is a static page of contracts, attempts, and outcomes.

## Layout

```text
registry.yaml          host and resolution-source flag
GOVERNANCE.md          host, conflicts, disputes, tags, transfer
LICENSE                Apache-2.0 (code)
LICENSE-CONTENT.md     CC BY 4.0 (everything else)
listing-template.md    question text a host copies to list a contract
schemas/               JSON Schema for every file type
shared-rules/          rules every contract shares (qualification, adversarial routes, glossary, wrapping)
market-contracts/      one folder per market; contract-vK.yaml + required-columns.yaml
sketches/              unfinished attempts, same layout; never read by an outcome
submitted-attempts/    one folder per attempt
challenge-runs/        hidden-suite manifests from challenge operators
adjudication/          maintainer-only human calls
market-outcomes/       generated; what a market admin reads
validator/             the checker
examples/              fictional fixture scenarios
resolution-tags/       notes per snapshot tag
ui/                    generated static page
```

## License

Code (`validator/`, `schemas/`, `examples/make_fixtures.py`, `.github/`) is licensed under the
[Apache License 2.0](LICENSE). Everything else (contracts, shared rules, documentation, attempts, score
tables, manifests, adjudication records, outcome files, UI) is licensed under
[CC BY 4.0](LICENSE-CONTENT.md).

**Submissions.** By opening a pull request you license what you add under the same terms: code under
Apache-2.0, everything else under CC BY 4.0, and you confirm you have the right to do so. A wrapped attempt
reports facts from someone else's paper (numbers, dates, counts); link the paper and do not copy its text
or figures beyond short quotes.

