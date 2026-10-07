"""Market 8: access completeness."""
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

CASE = ('family', 'incomplete', 'post_freeze', 'multi_machine')
RESULT = ('detected_or_refused', 'certified_sufficient')

def compute(rows):
    rows = _unique(rows)

    FAM = ["hidden-state","hidden-communication","hidden-actuation","hidden-controller","hidden-internal"]
    inc = [r for r in rows if r["incomplete"]]
    comp = [r for r in rows if not r["incomplete"]]
    by = {f: [r for r in inc if r["family"] == f] for f in FAM}
    return {
        "min-per-family": min((len(v) for v in by.values()), default=0),
        "complete-controls": len(comp),
        "post-freeze-incomplete": sum(1 for r in inc if r["post_freeze"]),
        "multi-machine": sum(1 for r in rows if r["multi_machine"]),
        "detection-overall": _rate(inc, "detected_or_refused"),
        "min-family-detection": min((_rate(v, "detected_or_refused") for v in by.values()), default=0.0),
        "false-sufficient": _rate(inc, "certified_sufficient"),
        "true-complete": _rate(comp, "certified_sufficient"),
    }

