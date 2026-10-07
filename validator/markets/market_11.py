"""Market 11: hidden coordination."""
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

CASE = ('label_positive', 'concealed', 'mechanism')
RESULT = ('score', 'called_positive')

def compute(rows):
    rows = _unique(rows)

    pos = [r for r in rows if r["label_positive"]]
    neg = [r for r in rows if not r["label_positive"]]
    concealed = [r for r in pos if r["concealed"]]
    return {
        "positive-cases": len(pos),
        "negative-cases": len(neg),
        "concealed-cases": len(concealed),
        "mechanisms": len({r["mechanism"] for r in pos if r.get("mechanism")}),
        "auroc": auroc([r["score"] for r in rows], [r["label_positive"] for r in rows]),
        "concealed-recall": _rate(concealed, "called_positive"),
        "false-positive-rate": _rate(neg, "called_positive"),
    }

