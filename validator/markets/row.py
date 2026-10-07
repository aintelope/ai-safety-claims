"""Shared helpers for catalog market modules (one unique id column, rate helpers)."""

from ..tables import TableError
from ..stats import auroc, clopper_pearson_upper  # noqa: F401


def unique(rows, key):
    ids = [r[key] for r in rows]
    if len(ids) != len(set(ids)):
        raise TableError(f"{key} must be unique")
    return rows


def rate(rows, col):
    return sum(1 for r in rows if r[col]) / len(rows) if rows else 0.0


def derive_join(key, case_fields, result_fields):
    def derive(cases, records):
        rows = []
        for cid, case in cases.items():
            result = records[cid]["result"]
            row = {key: cid}
            for name in case_fields:
                row[name] = case.get(name)
            for name in result_fields:
                row[name] = result.get(name)
            rows.append(row)
        return rows
    return derive
