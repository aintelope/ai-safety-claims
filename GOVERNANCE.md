# Governance

**Draft.** The repository is hosted for now by aintelope, which is not independent of the book project
the contracts come from (`registry.yaml`: `hostIndependent: false`). Until an independent host takes
over, the scaffold author may merge anything, `registry.yaml` keeps `resolutionSource: false`, no
outcome file resolves any question, and attempts submitted or authored by aintelope or Gunnar Zarncke
are not accepted.

## Host

The host owns the repository and appoints the maintainers. A host must:

- be independent of the book project whose appendix the contracts come from;
- not trade the listed markets, or disclose positions and recuse (below);
- be able to merge and adjudicate within each 60-day window.

On transfer: the host takes the GitHub organization, sets `registry.yaml` `host`, enables branch
protection and a CODEOWNERS rule so only maintainers merge `adjudication/`, `market-outcomes/`,
`market-contracts/`, and `shared-rules/`, freezes the first contracts, and tags `snapshot-0` (all OTHER).
Only then does `resolutionSource` become true. No question is listed before that.

## Roles

| Role | Does |
|------|------|
| Submitter | Files sketches and attempts by pull request. Never writes outcome fields. |
| Challenge operator | Builds hidden suites or runs adversarial routes after the relevant freeze; files manifests in `challenge-runs/`. |
| Maintainer | Merges, records human checks in `adjudication/`, runs the validator, creates snapshot tags. |

Sketches (`sketches/`) never feed an outcome. Any maintainer may merge or archive them without
adjudication, and no position disclosure is needed for them.

## Conflicts

- A maintainer does not adjudicate an attempt they submitted, operated, or authored, or one by their employer.
- Maintainers and challenge operators disclose positions in markets that resolve on this registry, in the
  pull request that touches them. A maintainer with a position recuses from that market's adjudication.
- If no unconflicted maintainer is available, the checks stay `unsettled`, and the attempt is not qualifying.

## Disputes

Anyone may open an issue on an adjudication within the window. The maintainer answers in the issue before
the snapshot tag. After the tag, the outcome stands; a correction goes into a later contract version and a
new question.

## Contracts

- A frozen contract version never changes. Errata, including typo fixes, make a new version with its own
  outcome file; a listed question names one version.
- Contract changes must not tighten or loosen bars relative to the source appendix. A new scientific claim
  needs a new contract version, not a schema or validator tweak.

## Snapshot tags

- `snapshot-<evidence cutoff date>` is created when the 60-day window closes.
- Tags are never moved or deleted. One Zenodo record is created with `snapshot-0`; each later snapshot
  tag is deposited as a new version of it, titled with the tag name, when the tag is created. Listed
  questions quote the record's concept DOI (see `listing-template.md`).
- If neither tag nor Zenodo copy exists 30 days after the window closes, the question is annulled.

## Decoupling from the manuscript (planned)

Today the contracts and shared rules are copies of Appendix H of *Towards Superintelligence Alignment*
(TSA), and the appendix text wins on any disagreement. That ties the registry's rules to one book and its
author, which conflicts with the host independence above. The plan is to decouple them:

- The registry's own contracts and shared rules become the authoritative text. The appendix points to
  them instead of the other way round.
- The registry may hold contracts that do not come from TSA, and may diverge from or drop TSA contracts.
  The rule that contract changes follow the source appendix then applies only to contracts that still
  name TSA as their source.
- Contract versions get their own numbering, independent of the book's contract versions.

Until a host takes over and does this, the appendix still wins, and rule changes are made in both places.

## Transfer and shutdown

If the host stops, it transfers the organization to a successor meeting the host criteria above, or
archives the repository read-only. Existing tags and Zenodo deposits remain the resolution record.
