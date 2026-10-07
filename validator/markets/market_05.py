"""Market 5: auditor independence."""
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

CASE = ('kind', 'family')
RESULT = ('success',)

def compute(rows):
    rows = _unique(rows)

    FAM = ["no-check","record-omit","wrong-approval","other-component"]
    attacks = [r for r in rows if r["kind"] == "attack"]
    planted = [r for r in rows if r["kind"] == "planted"]
    by = {f: [r for r in attacks if r["family"] == f] for f in FAM}
    return {
        "min-attempts-per-family": min(len(v) for v in by.values()),
        "planted-bypasses": len(planted),
        "max-family-success-rate": max(_rate(v, "success") for v in by.values()),
        "bypass-discovery-rate": _rate(planted, "success"),
    }

