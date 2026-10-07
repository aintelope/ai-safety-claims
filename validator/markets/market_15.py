"""Market 15: certificate composition."""
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

CASE = ('architecture', 'faulty', 'fault_family', 'post_freeze')
RESULT = ('rejected_or_flagged', 'accepted')

def compute(rows):
    rows = _unique(rows)

    FAM = ["wrong-version","access-mismatch","correction-authority","applicability-change","wrong-predecessor","out-of-scope"]
    faulty = [r for r in rows if r["faulty"]]
    clean = [r for r in rows if not r["faulty"]]
    by = {f: [r for r in faulty if r["fault_family"] == f] for f in FAM}
    rates = [_rate(v, "rejected_or_flagged") for v in by.values() if v]
    return {
        "bundles": len(rows),
        "architectures": len({r["architecture"] for r in rows}),
        "faulty-bundles": len(faulty),
        "clean-bundles": len(clean),
        "post-freeze-incompatible": sum(1 for r in faulty if r["post_freeze"]),
        "reject-faulty": _rate(faulty, "rejected_or_flagged"),
        "min-family-reject": min(rates) if rates else 0.0,
        "false-accept": _rate(faulty, "accepted"),
        "true-accept": _rate(clean, "accepted"),
    }

