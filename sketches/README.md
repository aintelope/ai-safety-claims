# Sketches

A sketch is an attempt that isn't finished yet: a pilot run, a partial score table, a plan with the first
rows filled in. It has the same folder layout and files as an attempt in `submitted-attempts/`, but **no
outcome file ever reads `sketches/`**, so a sketch can't move a market to YES, NO, or OTHER. Use it to
build up an attempt in public, get feedback, or leave work that someone else can continue.

## Start one

To run an evaluation, start it in the
[workbench](https://github.com/aintelope/ai-safety-claims-workbench): `workbench export` writes the sketch
here, evidence included. To file results you already have, start here:

```bash
# Blank: real attempt.yaml fields, the contract's score-table header, commented templates for the rest.
.venv/bin/python -m validator new --market market-04 --submitter your-slug --slug short-name

# From a fixture: copy a complete fictional attempt and replace its values with your own.
.venv/bin/python -m validator new --market market-04 --submitter your-slug --slug short-name --from-fixture m04-yes
```

Either way you get `sketches/<submitter>-<today>-<slug>/`. Fixtures live in `examples/scenarios/`; the
one named in `--from-fixture` shows a complete attempt for that market. `m04-sketch` shows a partial one.

## Evidence

A sketch can preregister: commit `freeze.yaml` and `freeze-cases.jsonl` before running anything, and
the commit date records the freeze. After the run add `trials.jsonl` and the raw log
(`import-inspect`, `raw-log`). The dry run checks them like an attempt's; see the README's filing section.

## See where it stands

```bash
.venv/bin/python -m validator dry-run sketches/<id>
```

The dry run runs every check the validator would, but doesn't stop at the first failure and doesn't decide
anything. It lists:

- **Fix before submitting**: missing fields and files, schema errors, leftover fixture values.
- **Missing for a qualifying attempt**: each sample-size, coverage, freeze, and adversarial floor, with the
  current value and the threshold. This includes the exercised-bar rule: every bar needs at least one case
  it is computed over.
- **Evidence**: raw log, frozen cases, trials, and whether the score table matches the trials.
- **Coverage so far**: counts per system family or correction case.
- **Maintainer checks after submission**: the human checks a maintainer will record.
- **Bar preview**: current values against the bars. This is not a result.

## Submit

Submitting is a plain move of the folder from `sketches/` to `submitted-attempts/`. The id, `filedAt`,
and all files stay the same. You can do the move with `git mv` yourself; the helper does it after a dry run:

```bash
.venv/bin/python -m validator submit sketches/<id>
```

It refuses while anything is under "Fix before submitting", and while the attempt would not qualify. A
non-qualifying attempt belongs here, not in `submitted-attempts/`. The exception is a published result that
really misses the floors and should be on record: pass `--allow-not-qualifying`.

What counts for a market is the merge into `submitted-attempts/` before that market's snapshot tag, not
`filedAt`. `filedAt` is the day the sketch folder was opened, and ids never change.

## Rules

- Never write `qualifying`, `barsMet`, `outcome`, or `reason`. CI rejects them here as everywhere else.
- `attempt.yaml` must name an existing contract version. CI checks nothing else in a sketch.
- Sketches are not adjudicated. Maintainers may merge them freely and archive stale ones.
- A pilot's cases have been seen by its authors. They can't later serve as the hidden suite of the same
  method.
