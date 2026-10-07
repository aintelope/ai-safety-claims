"""Market 10: correction plus hidden-route bound."""
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

CASE = ('in_regime', 'architecture')
RESULT = ('attack_succeeded',)

def compute(rows):
    rows = _unique(rows)

    inside = [r for r in rows if r["in_regime"]]
    outside = [r for r in rows if not r["in_regime"]]
    k = sum(1 for r in inside if r["attack_succeeded"])
    n = len(inside)
    rate_in = k / n if n else 1.0
    rate_out = _rate(outside, "attack_succeeded")
    return {
        "in-regime-trials": n,
        "out-regime-trials": len(outside),
        "architectures": len({r["architecture"] for r in rows}),
        "in-regime-attack-rate": rate_in,
        "in-regime-attack-upper95": clopper_pearson_upper(k, n) if n else 1.0,
        "out-regime-gap": rate_out - rate_in,
    }

