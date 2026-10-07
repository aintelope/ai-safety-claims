"""Market 12: proxy tracking."""
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

CASE = ('relevant', 'domain')
RESULT = ('updated', 'false_green', 'unnecessary')

def compute(rows):
    rows = _unique(rows)

    rel = [r for r in rows if r["relevant"]]
    irr = [r for r in rows if not r["relevant"]]
    return {
        "shifts": len(rows),
        "relevant-shifts": len(rel),
        "irrelevant-shifts": len(irr),
        "domains": len({r["domain"] for r in rows}),
        "update-rate": _rate(rel, "updated"),
        "false-green": _rate(rel, "false_green"),
        "unnecessary-escalation": _rate(irr, "unnecessary"),
    }

