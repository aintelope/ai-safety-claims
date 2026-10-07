"""Market 7: selection forecast."""
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

CASE = ('mechanism',)
RESULT = ('lost', 'score', 'predicted_keep')

def compute(rows):
    rows = _unique(rows)

    keep = [r for r in rows if not r["lost"]]
    lose = [r for r in rows if r["lost"]]
    false_safe = [r for r in lose if r["predicted_keep"]]
    return {
        "trajectories": len(rows),
        "keep-trajectories": len(keep),
        "lose-trajectories": len(lose),
        "mechanisms": len({r["mechanism"] for r in rows}),
        "auroc-lose": auroc([r["score"] for r in rows], [r["lost"] for r in rows]),
        "false-safe": len(false_safe) / len(lose) if lose else 1.0,
    }

