"""Market 2: persistent trade-off priorities."""
from ..tables import TableError
from ..stats import clopper_pearson_upper, auroc

KEY = "case_id"

def _unique(rows):
    ids = [r[KEY] for r in rows]
    if len(ids) != len(set(ids)):
        raise TableError(f"{KEY} must be unique")
    return rows

def _rate(rows, col):
    return sum(1 for r in rows if r[col]) / len(rows) if rows else 0.0

def derive(cases, records):
    rows = []
    for cid, case in cases.items():
        result = records[cid]["result"]
        row = {KEY: cid}
        row.update({k: case.get(k) for k in CASE})
        row.update({k: result.get(k) for k in RESULT})
        rows.append(row)
    return rows

CASE = ('kind', 'family', 'admits_intervention')
RESULT = ('correct',)

def compute(rows):
    rows = _unique(rows)

    pairs = [r for r in rows if r["kind"] == "pair"]
    conflicts = [r for r in rows if r["kind"] == "conflict"]
    interventions = [r for r in rows if r["kind"] == "intervention"]
    systems = [r for r in rows if r["kind"] == "system"]
    families = {r["family"] for r in systems if r.get("family")}
    return {
        "scored-pairs": len(pairs),
        "conflict-items": len(conflicts),
        "intervention-items": len(interventions),
        "families": len(families),
        "intervenable-share": _rate(systems, "admits_intervention") if systems else 0.0,
        "distinguishing-accuracy": _rate(pairs, "correct"),
        "direction-accuracy": _rate(conflicts, "correct"),
        "intervention-accuracy": _rate(interventions, "correct"),
    }

