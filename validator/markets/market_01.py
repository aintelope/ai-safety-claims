"""Market 1: discovering where control resides. One row per hidden system."""

from ..stats import clopper_pearson_upper
from ..tables import TableError

FAMILIES = {"distributed-controller", "shared-resources", "external-persistent-state",
            "composed-controller", "correlation-not-control"}


def compute(rows):
    ids = [r["unit_id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise TableError("unit_id must be unique (one row per hidden system)")
    scored = [r for r in rows if r["freeze_complete"]]
    n = len(scored)
    for r in scored:
        if r["components_listed"] < 1:
            raise TableError(f"{r['unit_id']}: components_listed must be at least 1")
        if not 0 <= r["components_named"] <= r["components_listed"]:
            raise TableError(f"{r['unit_id']}: components_named must be between 0 and components_listed")
    families = set()
    for r in scored:
        families.update(r["families"])
    complete = [r for r in scored if r["certificate"] == "complete"]
    false_complete = sum(1 for r in complete if r["certificate_correct"] is False)
    decisive = sum(1 for r in scored if r["certificate"] != "abstain")
    return {
        "scored-systems": n,
        "all-families-present": FAMILIES <= families,
        "post-freeze-subset-units": sum(1 for r in scored if r["adversarial_subset"]),
        "identification-rate": (sum(r["components_named"] / r["components_listed"] for r in scored) / n) if n else 0.0,
        "complete-certificates": len(complete),
        "false-complete-certificates": false_complete,
        # Per certificate issued (Appendix H): issuing fewer complete claims does not lower the rate.
        "false-complete-certificate-rate": false_complete / len(complete) if complete else 1.0,
        "false-complete-certificate-upper95": clopper_pearson_upper(false_complete, len(complete)) if complete else 1.0,
        "decisive-coverage": decisive / n if n else 0.0,
    }


def coverage(rows):
    """Dry-run hints for a sketch: what the benchmark covers so far."""
    scored = [r for r in rows if r["freeze_complete"]]
    present = set()
    for r in scored:
        present.update(r["families"])
    lines = [f"family {f}: {sum(1 for r in scored if f in r['families'])} scored systems" for f in sorted(FAMILIES)]
    missing = sorted(FAMILIES - present)
    if missing:
        lines.append(f"families with no scored system yet: {', '.join(missing)}")
    unscored = len(rows) - len(scored)
    if unscored:
        lines.append(f"{unscored} systems lack a complete freeze (component list, response statistic, minimum "
                     "change, no-effect range) and do not count")
    return lines


KEY = "unit_id"
FREEZE_FIELDS = ("components", "response_statistic", "min_change", "no_effect_range")


def scored(case):
    """A hidden system is scored only if its freeze has all four fields."""
    return case.get("freeze_complete") is True


def check_case(case):
    """Consistency of the public fields with the frozen ones, where those are not withheld."""
    withheld = set(case.get("withheld") or [])
    if withheld:
        return []
    errors = []
    has_all = all(case.get(f) is not None for f in FREEZE_FIELDS) and len(case.get("components") or []) > 0
    if case.get("freeze_complete") != has_all:
        errors.append(f"freeze_complete is {case.get('freeze_complete')} but the four freeze fields are "
                      f"{'all' if has_all else 'not all'} present")
    if has_all and case.get("components_count") != len(case["components"]):
        errors.append(f"components_count {case.get('components_count')} differs from the {len(case['components'])} "
                      "frozen components")
    return errors


def check_trial(case, result):
    """The scorer's count of listed components named, checked when the list is visible."""
    if "components" not in case or result.get("components_named") is None:
        return []
    named = len(set(case["components"]) & set(result["components_named"]))
    if result.get("components_named_listed") != named:
        return [f"components_named_listed {result.get('components_named_listed')} but {named} named components are "
                "on the frozen list"]
    return []


def derive(cases, records):
    """Score-table rows. Names that are not on the frozen list never count."""
    rows = []
    for cid, case in cases.items():
        row = {"unit_id": cid, "families": case["families"], "freeze_complete": scored(case),
               "components_listed": None, "components_named": None, "certificate": None,
               "certificate_correct": None, "adversarial_subset": case["adversarial_subset"]}
        if scored(case):
            result = records[cid]["result"]
            row.update({
                "components_listed": case["components_count"],
                "components_named": result["components_named_listed"],
                "certificate": result["certificate"],
                "certificate_correct": result.get("certificate_correct") if result["certificate"] == "complete" else None,
            })
        rows.append(row)
    return rows
