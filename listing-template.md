# Listing template

Text a host copies into a prediction-market question that resolves on this registry. Fill `<…>`; one
question per contract version. Tested with an admin-role agent on six cases (2026-10-06): all resolved as
intended; this version fixes the defects it reported (title/fine-print date conflict, Zenodo DOI only
inside the repo, no rule for a missing or malformed file, moved tags, missing timezone).

Do not list while `registry.yaml` has `resolutionSource: false` or the contract is `draft`.

**Market 14 is outside this template.** It has no registry contract, two outcomes (YES/NO), and the platform adjudicates from the Appendix P box directly.

---

## Three labels (do not merge them)

Appendix P and `metadata/predictions.yml` in *Towards Superintelligence Alignment* use three different strings:

| Label | Where it lives | Example (Market 1) |
|-------|----------------|---------------------|
| **Catalog title** | Appendix `\subsection{Market N. …}`, site hub panel (`title` / `shortTitle` in YAML) | Discovering where control resides |
| **Metaculus short title** | `\begin{predictionbox}[…]` optional title; YAML `metaculusShortTitle` | Is it possible to discover where control resides in AI systems? |
| **Long title / Question** | `\textbf{Question.}` inside `predictionbox`; YAML `longTitle` | By 31 December 2027, which outcome will hold for a published method for reliably discovering the effective control units in previously unseen AI systems from unlabeled observations and interventions? |

The Metaculus short title is **not** `Market N. …`, not a registry path, and not the bare catalog noun. The long title ends at the method description and **does not** append `: YES (…), NO (…), or OTHER (…)` — those choices are separate fields.

Manuscript source: `appendices/appP-bridge-predictions.tex`. Catalog metadata: `metadata/predictions.yml`.

---

## Fields to paste (registry markets)

**Short title.** Copy `metaculusShortTitle` from `predictions.yml`, or the optional title on `\begin{predictionbox}[…]`. Must read as a standalone question for someone who has not read the book.

**Long title.** Copy the `\textbf{Question.}` paragraph from the market's `predictionbox`. End with `?`. No outcome gloss after the question mark.

**Options.** YES, NO, OTHER. (Contracts whose `outcomes` list two options use those two.)

**Dates.** Question closes <cutoff>, 23:59 UTC (the evidence cutoff). Expected resolution <cutoff + 60 days>, when the snapshot tag is created.

**Resolution criteria.** This question resolves to the value of the `outcome` field in the file `market-outcomes/<market>-v<K>.json` at git tag `snapshot-<cutoff>` of `github.com/<host>/ai-safety-claims`. Admins read that one field. They do not evaluate papers or re-score attempts: attempts the file marks non-qualifying, for any reason including unsettled judgments, do not count.

**Fine print.**
- Copy the market's fine print from Appendix P verbatim: the Common rules paragraph and its adversarial budget (serious or default), so the question stands on its own.
- Use the tag whenever it was created, if it exists by <cutoff + 90 days>, 23:59 UTC.
- If the tag is missing on GitHub, or was moved after creation, use the version titled `snapshot-<cutoff>` of the Zenodo record <concept DOI>, which is deposited when the tag is created.
- The question is annulled if, by <cutoff + 90 days>, 23:59 UTC, neither source has the file, or the file is unreadable, names a different market or contract version, has `contractStatus` other than `frozen`, has `resolutionSource` other than `true`, or has an `outcome` value not among the options.
- OTHER means no qualifying attempt existed. It is not an annulment.

**Background (not part of the resolution).** Copy the `predictionbackground` block only — plain language about what the market tests. Do **not** paste:
- the opening authbar (chapters, bridges, Lean, what the market prices about a spine assumption);
- "Closest existing work" (the authbar after the block);
- YES / NO / OTHER definitions (those belong in resolution criteria and fine print);
- numeric bars, sample floors, or checklist text (those live on `https://ai-safety-claims.com/markets/<market>/v<K>/` and in `market-contracts/`).

The background must not name a chapter, appendix section, `\text{MB*}`, or Lean. An optional further link uses anchor text that says what the reader gets, e.g. **See this plain language description** — not "concept card".

A YES on the registry is not evidence that the underlying alignment problem is solved on frontier systems.

---

## Worked example: Market 1 (`market-01`, contract v2)

**Short title.** Is it possible to discover where control resides in AI systems?

**Long title.** By 31 December 2027, which outcome will hold for a published method for reliably discovering the effective control units in previously unseen AI systems from unlabeled observations and interventions?

**Options.** YES, NO, OTHER

**Dates.** Question closes 2027-12-31, 23:59 UTC. Expected resolution when tag `snapshot-2027-12-31` is created (target within 60 days after cutoff).

**Resolution criteria.** *(Use the standard pointer block above with `<market>` = `market-01`, `<K>` = `2`, `<cutoff>` = `2027-12-31`.)*

**Fine print.** *(Copy Common rules + adversarial budget from Appendix P for this market; add tag / Zenodo / annulment bullets from the standard block above.)*

**Background.**

An effective control unit is the set of components that together produce a system's closed-loop behavior.
It may include a language model, persistent memory, a planner, a scheduler, and tool processes, even when those components live on different machines.
The question is whether a published method can find that set in a system it has not seen, from observations and interventions that do not come labeled with which parts are the agents.
The method does not have to name one unique set.
What counts against it is certifying a boundary that leaves out something that shares control.
Before the method runs, each hidden system has a frozen list of those components, a response statistic, a minimum change that counts as real, and a range of change that still counts as no effect.
Perturbing the proposed unit must move the statistic by at least that minimum, compared with a dummy intervention that looks the same but does not touch the unit.
Removing a component that is not on the list must leave the statistic inside the no-effect range.

See also [this plain language description](https://towards-alignment.com/cards/how-would-you-find-what-decides/).

---

For markets 2–13 and 15–18, repeat the same field split: short title from `metaculusShortTitle`, long title from the trimmed Question line, background from `predictionbackground` only. Markets 19–21 keep their existing appendix boxes until Phase 4.
