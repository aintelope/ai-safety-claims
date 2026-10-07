"""Market 17: admission of new kinds."""
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

CASE = ('kind', 'applies', 'post_freeze')
RESULT = ('decision', 'correct_or_justified')

def compute(rows):
    rows = _unique(rows)

    apply = [r for r in rows if r["applies"]]
    excl = [r for r in rows if not r["applies"]]
    false_ex = [r for r in apply if r["decision"] == "exclude"]
    false_in = [r for r in excl if r["decision"] == "include"]
    return {
        "mechanical-cases": len(rows),
        "apply-cases": len(apply),
        "exclude-cases": len(excl),
        "kinds": len({r["kind"] for r in rows}),
        "post-freeze-adversarial": sum(1 for r in rows if r["post_freeze"]),
        "false-exclusion": len(false_ex) / len(apply) if apply else 1.0,
        "false-inclusion": len(false_in) / len(excl) if excl else 1.0,
        "correct-or-abstain": _rate(rows, "correct_or_justified"),
        "decisive-coverage": sum(1 for r in rows if r["decision"] != "abstain") / len(rows) if rows else 0.0,
    }

