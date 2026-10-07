"""Market 16: selection under shocks."""
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

CASE = ('mechanism', 'inside')
RESULT = ('uptake', 'persisted', 'classified_safe')

def compute(rows):
    rows = _unique(rows)

    inside = [r for r in rows if r["inside"]]
    outside = [r for r in rows if not r["inside"]]
    false_safe = [r for r in inside if r["classified_safe"] and not r["uptake"]]
    k, n = len(false_safe), len(inside)
    fail_in = 1.0 - _rate(inside, "uptake")
    fail_out = 1.0 - _rate(outside, "uptake")
    return {
        "trajectories": len(rows),
        "mechanisms": len({r["mechanism"] for r in rows}),
        "inside-trajectories": len(inside),
        "outside-trajectories": len(outside),
        "inside-uptake": _rate(inside, "uptake"),
        "inside-persistence": _rate(inside, "persisted"),
        "false-safe": k / n if n else 1.0,
        "false-safe-upper95": clopper_pearson_upper(k, n) if n else 1.0,
        "outside-failure-gap": fail_out - fail_in,
    }

