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
