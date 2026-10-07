"""YAML loading and score-table parsing."""

import csv

import yaml

# Submitters never author these; a submitted file containing them is a build error.
FORBIDDEN_KEYS = {"qualifying", "barsMet", "outcome", "reason"}


class TableError(ValueError):
    """A score table is present but structurally unusable."""


class _Loader(yaml.SafeLoader):
    pass


# Keep dates as strings so they compare and round-trip exactly as written.
_Loader.yaml_implicit_resolvers = {
    key: [(tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:timestamp"]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.load(f, Loader=_Loader)


def forbidden_keys(obj):
    """Return forbidden keys found anywhere in a loaded YAML object."""
    found = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in FORBIDDEN_KEYS:
                found.add(key)
            found |= forbidden_keys(value)
    elif isinstance(obj, list):
        for item in obj:
            found |= forbidden_keys(item)
    return found


def _convert(raw, col):
    kind = col["type"]
    if kind == "str":
        return raw
    if kind == "int":
        return int(raw)
    if kind == "bool":
        if raw not in ("true", "false"):
            raise ValueError(f"expected true or false, got {raw!r}")
        return raw == "true"
    if kind == "enum":
        if raw not in col["values"]:
            raise ValueError(f"{raw!r} not in {col['values']}")
        return raw
    if kind == "enum-list":
        items = [x.strip() for x in raw.split(";") if x.strip()]
        bad = [x for x in items if x not in col["values"]]
        if bad:
            raise ValueError(f"{bad} not in {col['values']}")
        return items
    raise ValueError(f"unknown column type {kind}")


def parse_table(path, spec):
    """Parse score-table.csv against required-columns.yaml. Returns (rows, errors, forbidden)."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        raw_rows = list(reader)
    forbidden = FORBIDDEN_KEYS & set(header)
    columns = spec["columns"]
    missing = [name for name in columns if name not in header]
    if missing:
        return [], [f"missing columns: {', '.join(missing)}"], forbidden
    rows, errors = [], []
    for line, raw_row in enumerate(raw_rows, start=2):
        row = {}
        for name, col in columns.items():
            raw = (raw_row.get(name) or "").strip()
            when = col.get("requiredWhen")
            required = all(row.get(k) == v for k, v in when.items()) if when else True
            if raw == "":
                if required:
                    errors.append(f"line {line}: {name} is empty")
                row[name] = None
                continue
            try:
                row[name] = _convert(raw, col)
            except ValueError as e:
                errors.append(f"line {line}: {name}: {e}")
                row[name] = None
        rows.append(row)
    if not rows:
        errors.append("score table has no rows")
    return rows, errors, forbidden
