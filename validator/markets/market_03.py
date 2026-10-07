"""Market 3: bearer transport."""
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

CASE = ('family', 'target_changed')
RESULT = ('correct', 'false_accept')

def compute(rows):
    rows = _unique(rows)

    FAM = {"continuity","fission-fusion","reassignment","concept-change"}
    changed = [r for r in rows if r["target_changed"]]
    return {
        "mechanical-cases": len(rows),
        "all-families-present": FAM <= {r["family"] for r in rows},
        "target-changed-cases": len(changed),
        "target-accuracy": _rate(rows, "correct"),
        "false-acceptance": _rate(changed, "false_accept"),
    }

