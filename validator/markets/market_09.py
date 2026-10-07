"""Market 9: hidden-route bounds."""
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

CASE = ('certified', 'planted_capable')
RESULT = ('bound', 'hidden_success', 'unrestricted_success', 'planted_handled')

def compute(rows):
    rows = _unique(rows)

    import statistics
    cert = [r for r in rows if r["certified"]]
    planted = [r for r in rows if r["planted_capable"]]
    holds = sum(1 for r in rows if r["hidden_success"] <= r["bound"])
    return {
        "cases": len(rows),
        "certified": len(cert),
        "planted-routes": len(planted),
        "bound-holds": holds / len(rows) if rows else 0.0,
        "median-bound": statistics.median(r["bound"] for r in cert) if cert else 1.0,
        "unrestricted-success": sum(r["unrestricted_success"] for r in rows) / len(rows) if rows else 0.0,
        "planted-detection": _rate(planted, "planted_handled"),
    }

