"""Tools for the evidence files: hash cases, keep a raw log, verify it against its URL, extract trials from
an Inspect log, and rerun a wrapped attempt's adapter. None of these run in CI."""

import json
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from .engine import load_common
from .evidence import CASES, RAW, TRIALS, canonical, case_hash, file_sha256, read_jsonl, write_jsonl
from .tables import load_yaml


def hash_cases(path):
    """Fill in case_hash on every line that withholds nothing. Hash-only lines keep the operator's hash."""
    lines, errors = read_jsonl(path)
    if errors:
        raise SystemExit("; ".join(errors))
    out = []
    for _, case in lines:
        if not case.get("withheld"):
            case["case_hash"] = case_hash(case)
        out.append(case)
    write_jsonl(path, out)
    print(f"hashed {len(out)} cases in {path}")
    return 0


def keep_raw_log(source, attempt_dir, url=None, fmt=None, update_attempt=False):
    """Copy the raw log into raw-log/ (whole, or head and tail) and print the rawLog block for attempt.yaml,
    or write it there with update_attempt (attempt.yaml is rewritten; comments are lost)."""
    limits = load_common()["evidence"]
    source, folder = Path(source), Path(attempt_dir) / RAW
    size = source.stat().st_size
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    if size <= limits["maxLocalLogBytes"]:
        shutil.copy(source, folder / source.name)
    else:
        n = limits["excerptBytes"]
        with open(source, "rb") as f:
            (folder / "head").write_bytes(f.read(n))
            f.seek(size - n)
            (folder / "tail").write_bytes(f.read(n))
        if not url:
            print(f"note: {size} bytes is over {limits['maxLocalLogBytes']}; publish the full file and add its url")
    block = {"sha256": file_sha256(source), "bytes": size, "format": fmt or source.suffix.lstrip(".") or "raw"}
    if url:
        block["url"] = url
    if update_attempt:
        import yaml
        path = Path(attempt_dir) / "attempt.yaml"
        attempt = load_yaml(path) or {}
        attempt["rawLog"] = block
        path.write_text(yaml.safe_dump(attempt, sort_keys=False, width=100), encoding="utf-8")
        print(f"wrote rawLog to {path}")
    else:
        print("add to attempt.yaml:\nrawLog:\n" + "".join(f"  {k}: {json.dumps(v)}\n" for k, v in block.items()), end="")
    return 0


def derive_table(attempt_dir, root=None):
    """Write score-table.csv from freeze-cases.jsonl and trials.jsonl (what the validator would derive)."""
    from .engine import REPO, _schema_errors, load_contracts
    from .evidence import check, table_text
    from .markets import MODULES
    attempt_dir = Path(attempt_dir).resolve()
    root = Path(root or REPO)
    attempt = load_yaml(attempt_dir / "attempt.yaml") or {}
    contract = load_contracts().get((attempt.get("market"), attempt.get("contractVersion")))
    if contract is None:
        raise SystemExit(f"no contract {attempt.get('market')} version {attempt.get('contractVersion')}")
    manifest = None
    if attempt.get("challengeRun"):
        manifest = load_yaml(root / "challenge-runs" / attempt["challengeRun"] / "suite-manifest.yaml")
    ev = check(root, attempt_dir, attempt, contract, load_common(), MODULES[contract["market"]], manifest,
               _schema_errors)
    if ev.rows is None:
        raise SystemExit("cannot derive the table yet:\n  " + "\n  ".join(ev.problems))
    columns = list(contract["_columns"]["columns"])
    (attempt_dir / "score-table.csv").write_text(table_text(ev.rows, columns), encoding="utf-8")
    print(f"wrote {attempt_dir / 'score-table.csv'} ({len(ev.rows)} rows)")
    return 0


def verify_log(attempt_dir, local_file=None):
    """Fetch the full raw log (or use a local copy), check sha256 and size, and that raw-log/ matches it."""
    attempt_dir = Path(attempt_dir)
    raw = (load_yaml(attempt_dir / "attempt.yaml") or {}).get("rawLog")
    if not raw:
        raise SystemExit("attempt.yaml has no rawLog")
    limits = load_common()["evidence"]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(local_file) if local_file else Path(tmp) / "raw"
        if not local_file:
            if not raw.get("url"):
                raise SystemExit("rawLog has no url; the local copy is the whole log")
            print(f"fetching {raw['url']}")
            with urllib.request.urlopen(raw["url"]) as r, open(path, "wb") as f:
                shutil.copyfileobj(r, f)
        problems = []
        if file_sha256(path) != raw["sha256"]:
            problems.append("sha256 of the full log differs from rawLog")
        if path.stat().st_size != raw["bytes"]:
            problems.append(f"full log is {path.stat().st_size} bytes, rawLog says {raw['bytes']}")
        data = path.read_bytes()
        folder = attempt_dir / RAW
        if raw["bytes"] <= limits["maxLocalLogBytes"]:
            files = [p for p in folder.iterdir() if p.is_file()] if folder.is_dir() else []
            if len(files) != 1 or files[0].read_bytes() != data:
                problems.append("raw-log/ is not a copy of the full log")
        else:
            n = limits["excerptBytes"]
            if (folder / "head").read_bytes() != data[:n] or (folder / "tail").read_bytes() != data[-n:]:
                problems.append("raw-log/head or raw-log/tail is not the head or tail of the full log")
    for p in problems:
        print(f"FAIL {p}")
    if not problems:
        print("ok: the full raw log matches rawLog and raw-log/")
    return 1 if problems else 0


# ---------------------------------------------------------------------------------------------------------
# Inspect

def _read_inspect(path):
    """(header, samples) as plain dicts. Uses inspect_ai if installed (any log format), else reads the file:
    .json directly, .eval as a zip (Zstandard entries need Python 3.14+ or inspect_ai)."""
    try:
        from inspect_ai.log import read_eval_log
        log = read_eval_log(str(path))
        header = log.model_dump(mode="json", exclude={"samples"})
        return header, [s.model_dump(mode="json") for s in (log.samples or [])]
    except ImportError:
        pass
    if str(path).endswith(".json"):
        log = json.loads(Path(path).read_text(encoding="utf-8"))
        return log, log.get("samples") or []
    try:
        with zipfile.ZipFile(path) as z:
            header = json.loads(z.read("header.json"))
            samples = [json.loads(z.read(n)) for n in sorted(z.namelist()) if n.startswith("samples/")]
    except NotImplementedError:
        raise SystemExit(f"{path} uses Zstandard compression: install inspect_ai or use Python 3.14+")
    return header, samples


def import_inspect(log_path, cases_path, out, system_version=None, scorers=None):
    """Extract trials.jsonl from an Inspect log. A sample's case is metadata.case_id (else its id); its
    result is the metadata of the named scorers (all if none named) plus metadata.result. The Inspect file
    itself is the raw log: keep it with `validator raw-log`."""
    header, samples = _read_inspect(log_path)
    lines, errors = read_jsonl(cases_path)
    if errors:
        raise SystemExit("; ".join(errors))
    cases = {c["case_id"]: c for _, c in lines}
    ev = header["eval"]
    version = f"inspect_ai {ev.get('packages', {}).get('inspect_ai', '?')}, task {ev['task']} v{ev.get('task_version', 0)}"
    log_sha = file_sha256(log_path)
    records, problems = [], []
    for s in samples:
        meta = s.get("metadata") or {}
        cid = str(meta.get("case_id", s["id"]))
        if cid not in cases:
            problems.append(f"sample {s['id']}: case {cid} is not in {cases_path}")
            continue
        chosen = {k: v for k, v in (s.get("scores") or {}).items() if not scorers or k in scorers}
        result = {}
        for score in chosen.values():
            result.update(score.get("metadata") or {})
        result.update(meta.get("result") or {})
        rec = {"trial_id": f"{s['id']}-e{s.get('epoch', 1)}", "case_id": cid, "case_hash": cases[cid]["case_hash"],
               "system": {"name": ev["model"], "version": system_version or ev["model"]},
               "scorer": {"name": "+".join(sorted(chosen)) or "none", "version": version},
               "result": result, "raw_ref": f"sample {s['id']} epoch {s.get('epoch', 1)}",
               "harness": {"name": "inspect_ai", "eval_id": ev.get("eval_id"), "log_sha256": log_sha}}
        started = s.get("started_at") or (header.get("stats") or {}).get("started_at")
        finished = s.get("completed_at") or (header.get("stats") or {}).get("completed_at")
        if started:
            rec["started_at"] = started
        if finished:
            rec["finished_at"] = finished
        if not cases[cid].get("withheld"):
            rec["input"] = s.get("input")
        rec["output"] = (s.get("output") or {}).get("completion")
        records.append(rec)
    for p in problems:
        print(f"skipped: {p}")
    write_jsonl(out, records)
    print(f"wrote {len(records)} trials to {out}; keep {log_path} as the raw log (`validator raw-log`)")
    return 1 if problems else 0


# ---------------------------------------------------------------------------------------------------------
# Wrapped attempts

def rerun_adapter(attempt_dir, source):
    """Rerun adapter/<script> on a local copy of the released data and compare its output with the
    attempt's freeze-cases.jsonl and trials.jsonl. This executes the submitter's script."""
    attempt_dir = Path(attempt_dir)
    adapter = load_yaml(attempt_dir / "adapter" / "adapter.yaml")
    if file_sha256(source) != adapter["source"]["sha256"]:
        raise SystemExit("the source file's sha256 differs from adapter.yaml")
    print(f"running adapter/{adapter['script']} (submitted code; read it first)")
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([sys.executable, "-I", str(attempt_dir / "adapter" / adapter["script"]), str(Path(source).resolve()), tmp],
                       check=True, cwd=tmp)
        problems = [f"{name} differs from the adapter's output" for name in (CASES, TRIALS)
                    if (Path(tmp) / name).read_bytes() != (attempt_dir / name).read_bytes()]
    for p in problems:
        print(f"FAIL {p}")
    if not problems:
        print(f"ok: the adapter reproduces {CASES} and {TRIALS}")
    return 1 if problems else 0


__all__ = ["hash_cases", "keep_raw_log", "verify_log", "import_inspect", "rerun_adapter", "canonical"]
