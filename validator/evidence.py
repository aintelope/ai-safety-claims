"""Evidence behind a score table: freeze.yaml, freeze-cases.jsonl, trials.jsonl, raw-log/, adapter/.

The score table is a summary. The validator derives it again from the frozen cases and the trial records
(trials.jsonl, our format) and requires the two to agree, so a table cannot say more than the trials do.
The raw log is whatever the harness wrote, in any format; the repository keeps it whole up to
maxLocalLogBytes, otherwise its head and tail, and attempt.yaml rawLog pins the full file by sha256.
Hidden-suite cases are hashes only: the operator withholds secret fields and never publishes them.
"""

import gzip
import hashlib
import json
from pathlib import Path

from .tables import load_yaml

TRIALS = "trials.jsonl"
CASES = "freeze-cases.jsonl"
RAW = "raw-log"
MAX_ERRORS = 10


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def case_hash(case):
    """sha256 of the frozen case as frozen: without case_hash and without the withheld marker."""
    body = {k: v for k, v in case.items() if k not in ("case_hash", "withheld")}
    return hashlib.sha256(canonical(body).encode("utf-8")).hexdigest()


def withhold(case, fields):
    """Hidden-suite line: hash the full case, then drop the withheld fields."""
    full = dict(case)
    full["case_hash"] = case_hash(full)
    kept = {k: v for k, v in full.items() if k not in fields}
    kept["withheld"] = sorted(f for f in fields if f in case)
    return kept


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _datetime(s):
    import datetime as dt
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def _type_ok(value, spec):
    kind = spec["type"]
    if kind == "str":
        return isinstance(value, str)
    if kind == "bool":
        return isinstance(value, bool)
    if kind == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "enum":
        return value in spec["values"]
    if kind == "enum-list":
        return isinstance(value, list) and all(v in spec["values"] for v in value)
    if kind == "str-list":
        return isinstance(value, list) and all(isinstance(v, str) for v in value)
    if kind == "range":
        return (isinstance(value, list) and len(value) == 2
                and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value) and value[0] <= value[1])
    raise ValueError(f"unknown field type {kind}")


def check_fields(obj, fields, context, where, withheld=()):
    """Type-check obj against a cases/results field spec; requiredWhen is evaluated on context."""
    errors = []
    for name, spec in fields.items():
        if name in withheld:
            continue
        when = spec.get("requiredWhen")
        required = all(context.get(k) == v for k, v in when.items()) if when else not spec.get("optional")
        if obj.get(name) is None:
            if required:
                errors.append(f"{where}: {name} is missing")
            continue
        if not _type_ok(obj[name], spec):
            errors.append(f"{where}: {name} = {obj[name]!r} is not {spec['type']}"
                          + (f" in {spec['values']}" if "values" in spec else ""))
    return errors


def read_jsonl(path, opener=open):
    records, errors = [], []
    with opener(path, "rt", encoding="utf-8") as f:
        for n, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"{Path(path).name} line {n}: not JSON ({e.msg})")
                continue
            if not isinstance(obj, dict):
                errors.append(f"{Path(path).name} line {n}: not a JSON object")
                continue
            records.append((n, obj))
    return records, errors


def write_jsonl(path, records):
    Path(path).write_text("".join(canonical(r) + "\n" for r in records), encoding="utf-8")


def write_jsonl_gz(path, records):
    """Deterministic gzip (no timestamp), so regenerated files are byte-identical."""
    data = "".join(canonical(r) + "\n" for r in records).encode("utf-8")
    with open(path, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, filename="") as f:
        f.write(data)


def _capped(errors, what):
    extra = len(errors) - MAX_ERRORS
    return errors[:MAX_ERRORS] + ([f"{extra} more {what} errors"] if extra > 0 else [])


class Evidence:
    def __init__(self):
        self.problems = []         # reporting: missing or inconsistent evidence
        self.freeze_problems = []  # qualification: freeze order broken
        self.info = []
        self.rows = None           # derived score-table rows (when cases and trials are consistent)


def _cases_path(root, attempt_dir, attempt, manifest, ev):
    if attempt.get("challengeRun"):
        path = Path(root) / "challenge-runs" / attempt["challengeRun"] / CASES
        if not path.exists():
            ev.problems.append(f"challenge-runs/{attempt['challengeRun']}/{CASES} missing: the operator commits the "
                               "hidden suite's case ids and hashes before scoring")
            return None, True
        if manifest and file_sha256(path) != manifest.get("suiteHash"):
            ev.problems.append(f"challenge-runs/{attempt['challengeRun']}/{CASES} does not hash to the manifest suiteHash")
        return path, True
    path = attempt_dir / CASES
    if not path.exists():
        ev.problems.append(f"missing {CASES} (the frozen cases; `python -m validator hash-cases` fills case_hash)")
        return None, False
    return path, False


def check_raw_log(attempt_dir, attempt, limits):
    """Problems with raw-log/ and attempt.yaml rawLog. The raw format is not checked."""
    problems = []
    raw = attempt.get("rawLog")
    folder = attempt_dir / RAW
    if raw is None:
        if attempt.get("attemptType") == "run":
            problems.append("missing rawLog in attempt.yaml and the raw log under raw-log/ (whatever the harness "
                            "wrote; `python -m validator raw-log` copies or cuts it)")
        return problems
    files = sorted(p for p in folder.iterdir() if p.is_file()) if folder.is_dir() else []
    if raw["bytes"] <= limits["maxLocalLogBytes"]:
        if len(files) != 1:
            problems.append(f"raw-log/ must hold the one raw log file ({raw['bytes']} bytes fits the "
                            f"{limits['maxLocalLogBytes']}-byte limit)")
        elif files[0].stat().st_size != raw["bytes"] or file_sha256(files[0]) != raw["sha256"]:
            problems.append(f"raw-log/{files[0].name} does not match rawLog bytes and sha256")
    else:
        if not raw.get("url"):
            problems.append(f"rawLog: a raw log over {limits['maxLocalLogBytes']} bytes needs a url to the full file")
        n = limits["excerptBytes"]
        for part in ("head", "tail"):
            p = folder / part
            if not p.exists():
                problems.append(f"missing raw-log/{part} (the {part} {n} bytes of the full raw log)")
            elif p.stat().st_size != n:
                problems.append(f"raw-log/{part} is {p.stat().st_size} bytes, not {n}")
        others = [p.name for p in files if p.name not in ("head", "tail")]
        if others:
            problems.append(f"raw-log/ holds only head and tail for a large log, not {', '.join(others)}")
    return problems


def check(root, attempt_dir, attempt, contract, common, module, manifest, schema_errors):
    """Check the evidence files of one attempt or sketch. schema_errors(obj, name) -> [str]."""
    ev = Evidence()
    spec = contract["_columns"]
    limits = common["evidence"]

    freeze_path = attempt_dir / "freeze.yaml"
    freeze = None
    if not freeze_path.exists():
        ev.problems.append("missing freeze.yaml (what was fixed before scoring; commit it before the run)")
    else:
        freeze = load_yaml(freeze_path) or {}
        errors = schema_errors(freeze, "freeze.schema.json")
        ev.problems += errors
        if errors:
            freeze = None
        elif attempt.get("methodFreezeAt") and freeze["frozenAt"] != attempt["methodFreezeAt"]:
            ev.problems.append(f"freeze.yaml frozenAt {freeze['frozenAt']} differs from methodFreezeAt "
                               f"{attempt['methodFreezeAt']}")

    if attempt.get("attemptType") == "wrapped":
        adapter = attempt_dir / "adapter" / "adapter.yaml"
        if not adapter.exists():
            ev.problems.append("wrapped attempt: missing adapter/adapter.yaml (released data and the script that "
                               "turns it into the evidence files)")
        else:
            a = load_yaml(adapter) or {}
            errors = schema_errors(a, "adapter.schema.json")
            ev.problems += errors
            if not errors and not (attempt_dir / "adapter" / a["script"]).exists():
                ev.problems.append(f"adapter script adapter/{a['script']} not found")

    ev.problems += check_raw_log(attempt_dir, attempt, limits)
    if attempt.get("rawLog"):
        raw = attempt["rawLog"]
        ev.info.append(f"raw log: {raw['bytes']} bytes ({raw.get('format', 'format not stated')})"
                       + (f", full file at {raw['url']}" if raw.get("url") else ""))

    # Frozen cases.
    before = len(ev.problems)
    cases = {}
    path, hidden = _cases_path(root, attempt_dir, attempt, manifest, ev)
    if path is not None:
        lines, errors = read_jsonl(path)
        errors = list(errors)
        withholdable = {k for k, f in spec["cases"]["fields"].items() if f.get("withholdable")}
        n_withheld = 0
        for n, case in lines:
            where = f"{CASES} line {n}"
            cid = case.get("case_id")
            if not isinstance(cid, str) or not cid:
                errors.append(f"{where}: case_id is missing")
                continue
            if cid in cases:
                errors.append(f"{where}: case_id {cid} repeats")
            withheld = case.get("withheld") or []
            if withheld:
                n_withheld += 1
                if not hidden:
                    errors.append(f"{where}: only a hidden suite's cases may withhold fields")
                bad = [f for f in withheld if f not in withholdable]
                if bad:
                    errors.append(f"{where}: {', '.join(bad)} may not be withheld")
                if not isinstance(case.get("case_hash"), str) or len(case["case_hash"]) != 64:
                    errors.append(f"{where}: case_hash is missing")
            elif case.get("case_hash") != case_hash(case):
                errors.append(f"{where}: case_hash is missing or wrong (run `python -m validator hash-cases`)")
            errors += check_fields(case, spec["cases"]["fields"], case, where, withheld)
            check_case = getattr(module, "check_case", None)
            if check_case:
                errors += [f"{where}: {e}" for e in check_case(case)]
            cases[cid] = case
        if not lines:
            errors.append(f"{CASES} has no cases")
        ev.problems += _capped(errors, "case")
        rel = path.relative_to(root) if path.is_relative_to(root) else path.name
        ev.info.append(f"{len(cases)} frozen cases in {rel}" + (f" ({n_withheld} hash-only)" if n_withheld else ""))

    # Trial records (the extract).
    trials_path = attempt_dir / TRIALS
    records = {}
    errors = []
    if not trials_path.exists():
        ev.problems.append(f"missing {TRIALS} (one record per trial in the registry's format; "
                           "`python -m validator import-inspect` extracts it from an Inspect log)")
    else:
        lines, errors = read_jsonl(trials_path)
        errors = list(errors)
        trial_ids = set()
        run = attempt.get("attemptType") == "run"
        freeze_at = _datetime(freeze["frozenAt"]) if freeze else None
        check_trial = getattr(module, "check_trial", None)
        for n, rec in lines:
            where = f"{TRIALS} line {n}"
            schema = schema_errors(rec, "trial-record.schema.json")
            if schema:
                errors += [f"{where}: {e.split(': ', 1)[-1]}" for e in schema[:2]]
                continue
            if rec["trial_id"] in trial_ids:
                errors.append(f"{where}: trial_id {rec['trial_id']} repeats")
            trial_ids.add(rec["trial_id"])
            case = cases.get(rec["case_id"])
            if cases and case is None:
                errors.append(f"{where}: case_id {rec['case_id']} is not a frozen case")
                continue
            if case is not None and rec["case_hash"] != case["case_hash"]:
                errors.append(f"{where}: case_hash does not match the frozen case {rec['case_id']}")
            if rec["case_id"] in records:
                errors.append(f"{where}: a second trial for case {rec['case_id']}; this contract version scores "
                              "one trial per case")
            records[rec["case_id"]] = rec
            errors += check_fields(rec["result"], spec["results"]["fields"], {**(case or {}), **rec["result"]}, where)
            if check_trial and case is not None:
                errors += [f"{where}: {e}" for e in check_trial(case, rec["result"])]
            if run and not rec.get("started_at"):
                errors.append(f"{where}: started_at is required for run attempts")
            elif rec.get("started_at"):
                try:
                    started = _datetime(rec["started_at"])
                    if freeze_at and started < freeze_at:
                        ev.freeze_problems.append(f"trial {rec['trial_id']} started {rec['started_at']}, before the "
                                                  f"freeze at {freeze['frozenAt']}")
                    if attempt.get("publishedAt") and started.date().isoformat() > attempt["publishedAt"]:
                        errors.append(f"{where}: trial started after publishedAt {attempt['publishedAt']}")
                except (ValueError, TypeError):
                    errors.append(f"{where}: started_at {rec['started_at']!r} is not an ISO 8601 time")
        ev.info.append(f"{len(records)} trial records in {TRIALS}")
    ev.problems += _capped(errors, "trial")
    ev.freeze_problems = ev.freeze_problems[:MAX_ERRORS]

    if cases and records:
        scored = getattr(module, "scored", lambda case: True)
        unrun = [cid for cid, case in cases.items() if scored(case) and cid not in records]
        if unrun:
            ev.problems.append(f"{len(unrun)} frozen cases have no trial record (first: {', '.join(unrun[:3])})")
        if len(ev.problems) == before:
            # Cases and trials are consistent; other gaps (freeze.yaml, raw log) do not block derivation.
            ev.rows = module.derive(cases, records)
    return ev


def compare(table_rows, derived_rows, key):
    """Differences between the submitted score table and the table derived from the evidence."""
    have = {r[key]: r for r in table_rows}
    want = {r[key]: r for r in derived_rows}
    diffs = [f"{k}: in the score table but not derived from the trials" for k in sorted(set(have) - set(want))]
    diffs += [f"{k}: derived from the trials but missing in the score table" for k in sorted(set(want) - set(have))]
    for k in sorted(set(have) & set(want)):
        bad = [c for c in want[k] if have[k].get(c) != want[k][c]]
        if bad:
            diffs.append(f"{k}: " + ", ".join(f"{c} table {have[k].get(c)!r} vs trials {want[k][c]!r}" for c in bad))
    return diffs


def table_text(rows, columns):
    """score-table.csv text for derived rows, in the contract's column order."""
    import csv
    import io

    def cell(v):
        if v is None:
            return ""
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, list):
            return ";".join(map(str, v))
        return str(v)

    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(columns)
    for r in rows:
        w.writerow([cell(r.get(c)) for c in columns])
    return out.getvalue()
