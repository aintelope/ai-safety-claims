"""Contributor helpers: start a sketch, dry-run it against its contract, submit it, and record adjudication.

A sketch is an attempt folder under sketches/ instead of submitted-attempts/. It has the same files and
schemas; the outcome files never read it. Submitting is a plain move of the folder, guarded by a dry run.
"""

import datetime as dt
import shutil
import subprocess
from pathlib import Path

import yaml

from .engine import (REPO, _apply, _date, _datetime, _exercised, _route_ok, _schema, _schema_errors,
                     human_check_ids, load_common, load_contracts)
from . import evidence
from .markets import MODULES
from .tables import TableError, forbidden_keys, load_yaml, parse_table

SKETCHES = "sketches"
SUBMITTED = "submitted-attempts"
FIXTURES = REPO / "examples" / "scenarios"
FIXTURE_MARK = "# Copied from fixture"
FIXTURE_HOST = "example.org"


def _today():
    return dt.date.today().isoformat()


def _latest_contract(market):
    versions = [c for (m, _), c in load_contracts().items() if m == market]
    if not versions:
        raise SystemExit(f"no contract for {market}")
    return max(versions, key=lambda c: c["version"])


def _need(item):
    if "equals" in item:
        return f"= {item['equals']}"
    parts = []
    if "min" in item:
        parts.append(f">= {item['min']}")
    if "max" in item:
        parts.append(f"<= {item['max']}")
    return " and ".join(parts)


def _check_texts(contract, common):
    texts = {}
    for group in common["humanChecks"].values():
        texts.update({c["id"]: c["text"] for c in group})
    texts.update({c["id"]: c["text"] for c in contract["humanChecks"]})
    return texts


# ---------------------------------------------------------------------------------------------------------
# Skeletons: commented YAML generated from the schemas, so a sketch starts with the real structure.

def _hint(prop):
    if "enum" in prop:
        return " | ".join(map(str, prop["enum"]))
    hint = prop.get("type", "value")
    if "pattern" in prop:
        hint += f" matching {prop['pattern']}"
    return hint


def _skeleton(schema, indent=0, first_prefix=None):
    """Commented lines; deleting the leading '# ' leaves valid, correctly indented YAML."""
    pad = " " * indent
    lines = []
    for key, prop in schema.get("properties", {}).items():
        lead = first_prefix if (first_prefix is not None and not lines) else pad
        required = " (required)" if key in schema.get("required", []) else ""
        about = f"  # {prop['description']}" if "description" in prop else ""
        if prop.get("type") == "object" and "properties" in prop:
            lines.append(f"# {lead}{key}:{required and '  #' + required}{about}")
            lines += _skeleton(prop, indent + 2)
        elif prop.get("type") == "array" and "properties" in prop.get("items", {}):
            lines.append(f"# {lead}{key}:{required and '  #' + required}{about}")
            lines += _skeleton(prop["items"], indent + 4, first_prefix=pad + "  - ")
        else:
            lines.append(f"# {lead}{key}: <{_hint(prop)}>{required}{about}")
    return lines


def _write_attempt_yaml(path, known, header):
    schema = _schema("attempt.schema.json")
    skip = set(known) | ({"wrapped"} if known["attemptType"] != "wrapped" else set())
    rest = {"properties": {k: v for k, v in schema["properties"].items() if k not in skip},
            "required": schema["required"]}
    text = header + yaml.safe_dump(known, sort_keys=False, width=100)
    text += "# Fill in what you have; `python -m validator dry-run` lists what is still missing.\n"
    text += "\n".join(_skeleton(rest)) + "\n"
    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------------------------------------
# new

def new_sketch(market, submitter, slug, attempt_type, from_fixture=None, root=REPO):
    contract = _latest_contract(market)
    if attempt_type not in contract["attemptTypes"]:
        raise SystemExit(f"{market} allows attempt types {contract['attemptTypes']}, not {attempt_type}")
    attempt_id = f"{submitter}-{_today()}-{slug}"
    target = Path(root) / SKETCHES / attempt_id
    for where in (SKETCHES, SUBMITTED):
        if (Path(root) / where / attempt_id).exists():
            raise SystemExit(f"{where}/{attempt_id} already exists")
    known = {"id": attempt_id, "market": market, "contractVersion": contract["version"],
             "attemptType": attempt_type, "submitter": submitter, "filedAt": _today()}

    if from_fixture:
        source = _fixture_attempt(from_fixture, market)
        shutil.copytree(source, target)
        mark = (f"{FIXTURE_MARK} {source.relative_to(REPO)}. Every value below is fictional: replace it with\n"
                f"# your own, then delete this line. Submitting is refused while it is here.\n")
        attempt = load_yaml(target / "attempt.yaml")
        attempt.update(known)
        (target / "attempt.yaml").write_text(mark + yaml.safe_dump(attempt, sort_keys=False, width=100),
                                             encoding="utf-8")
        for path in target.glob("*.yaml"):
            if path.name != "attempt.yaml":
                body = path.read_text(encoding="utf-8").replace("# Fictional fixture.\n", "")
                path.write_text(mark + body, encoding="utf-8")
    else:
        target.mkdir(parents=True)
        _write_attempt_yaml(target / "attempt.yaml", known, f"# Sketch for {market} contract v{contract['version']}.\n")
        columns = contract["_columns"]["columns"]
        (target / "score-table.csv").write_text(",".join(columns) + "\n", encoding="utf-8")
        freeze = ("# What was fixed before any case was scored. Commit this file and freeze-cases.jsonl before the\n"
                  "# run: the commit date is the public record of the freeze. frozenAt equals methodFreezeAt.\n")
        freeze += "\n".join(_skeleton(_schema("freeze.schema.json"))) + "\n"
        (target / "freeze.yaml").write_text(freeze, encoding="utf-8")
        (target / evidence.CASES).write_text("", encoding="utf-8")
        if contract["adversarialBudget"] == "serious":
            text = ("# Which serious-adversarial route the evaluation used (shared-rules/common-v1.yaml).\n"
                    "# Keep `route` and the one matching block.\n")
            text += "\n".join(_skeleton(_schema("adversarial-route.schema.json"))) + "\n"
            (target / "adversarial-route.yaml").write_text(text, encoding="utf-8")
    print(f"created {target.relative_to(root)}")
    print(f"score-table.csv columns: {contract['_columns']['market']} required-columns.yaml "
          f"(one row per {contract['_columns'].get('unit', 'unit')})")
    fields = ", ".join(contract["_columns"]["cases"]["fields"])
    print(f"{evidence.CASES}: one JSON object per case with case_id and {fields}; then `python -m validator "
          f"hash-cases`. After the run: {evidence.TRIALS} (`import-inspect` extracts it) and the raw log "
          f"(`raw-log`).")
    print(f"next: python -m validator dry-run {target.relative_to(root)}")
    return target


def _fixture_attempt(spec, market):
    """spec is <scenario> or <scenario>/<attempt-id>."""
    scenario, _, attempt_id = spec.partition("/")
    base = FIXTURES / scenario / SUBMITTED
    if not base.is_dir():
        raise SystemExit(f"no fixture scenario {scenario} (see examples/scenarios/)")
    candidates = [d for d in sorted(base.iterdir()) if d.is_dir() and (not attempt_id or d.name == attempt_id)]
    candidates = [d for d in candidates if load_yaml(d / "attempt.yaml").get("market") == market]
    if len(candidates) != 1:
        names = ", ".join(d.name for d in candidates) or "none"
        raise SystemExit(f"fixture {spec}: need exactly one {market} attempt, found {names}")
    return candidates[0]


# ---------------------------------------------------------------------------------------------------------
# dry-run

class Report:
    """blocking: must be fixed before submitting. qualification: the attempt would not qualify.
    maintainer: human checks recorded after submission. preview: bar values, not a result."""

    def __init__(self, attempt_dir):
        self.attempt_dir = attempt_dir
        self.blocking, self.qualification, self.coverage, self.maintainer, self.preview = [], [], [], [], []
        self.evidence = []
        self.met = []

    @property
    def status(self):
        return ("not ready to submit" if self.blocking else
                "ready to submit, but would not qualify" if self.qualification else
                "ready to submit; qualification now depends on the maintainer checks")

    def summary(self):
        """The report as data, for the site."""
        return {"status": self.status, "blocking": self.blocking, "qualification": self.qualification,
                "evidence": self.evidence, "coverage": self.coverage, "met": self.met,
                "maintainer": self.maintainer, "preview": self.preview}

    def render(self):
        out = [f"dry run: {self.attempt_dir.name}"]
        sections = [("Fix before submitting", self.blocking), ("Missing for a qualifying attempt", self.qualification),
                    ("Evidence", self.evidence), ("Coverage so far", self.coverage),
                    ("Qualification thresholds already met", self.met),
                    ("Maintainer checks after submission", self.maintainer),
                    ("Bar preview (not a result; bars decide YES or NO only for a qualifying attempt)", self.preview)]
        for title, items in sections:
            if items:
                out.append(f"\n{title}:")
                out += [f"  - {i}" for i in items]
        out.append(f"\nstatus: {self.status} ({len(self.blocking)} blocking, {len(self.qualification)} qualification gaps)")
        return "\n".join(out) + "\n"


def _fixture_rows():
    rows = set()
    for where in (SUBMITTED, SKETCHES):
        for table in FIXTURES.glob(f"*/{where}/*/score-table.csv"):
            rows.update(table.read_text(encoding="utf-8").splitlines()[1:])
    return rows


def _fixture_hashes():
    """case_hash values in fixture case files: a sketch reusing them still has fictional cases."""
    found = set()
    for path in FIXTURES.glob(f"**/{evidence.CASES}"):
        lines, _ = evidence.read_jsonl(path)
        found.update(c.get("case_hash") for _, c in lines)
    return found


def _strings(obj):
    if isinstance(obj, dict):
        for value in obj.values():
            yield from _strings(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _strings(item)
    elif isinstance(obj, str):
        yield obj


def _fixture_strings():
    """Fictional names and URLs used in the fixtures (they all contain 'example')."""
    found = set()
    for path in FIXTURES.glob("*/**/*.yaml"):
        found.update(v for v in _strings(load_yaml(path)) if "example" in v)
    return found


def dry_run(attempt_dir, root=REPO):
    attempt_dir = Path(attempt_dir).resolve()
    rep = Report(attempt_dir)
    path = attempt_dir / "attempt.yaml"
    if not path.exists():
        rep.blocking.append("no attempt.yaml (start one with `python -m validator new`)")
        return rep
    attempt = load_yaml(path) or {}
    contracts, common = load_contracts(), load_common()
    contract = contracts.get((attempt.get("market"), attempt.get("contractVersion")))
    if contract is None:
        rep.blocking.append(f"no contract {attempt.get('market')} version {attempt.get('contractVersion')}")
        return rep

    # Files and fields.
    for p in sorted(attempt_dir.rglob("*.yaml")):
        found = forbidden_keys(load_yaml(p))
        if found:
            rep.blocking.append(f"{p.name}: submitters may not set {sorted(found)}")
        if FIXTURE_MARK in p.read_text(encoding="utf-8"):
            rep.blocking.append(f"{p.name}: still marked as copied from a fixture")
    descriptions = _schema("attempt.schema.json")["properties"]
    for err in _schema_errors(attempt, "attempt.schema.json"):
        if "is a required property" in err:
            field = err.split("'")[1]
            about = descriptions.get(field, {}).get("description", "")
            rep.blocking.append(f"attempt.yaml: missing {field}" + (f" ({about})" if about else ""))
        else:
            rep.blocking.append(err)
    fixture_strings = _fixture_strings()
    for p in sorted(attempt_dir.glob("*.yaml")):
        leftovers = sorted({v for v in _strings(load_yaml(p)) if v in fixture_strings or FIXTURE_HOST in v})
        if leftovers:
            rep.blocking.append(f"{p.name}: fictional fixture values left: {', '.join(leftovers)}")
    if attempt.get("id") != attempt_dir.name:
        rep.blocking.append("attempt.yaml id does not equal the directory name")
    if not attempt_dir.name.startswith(f"{attempt.get('submitter')}-{attempt.get('filedAt')}-"):
        rep.blocking.append("directory name must be {submitter}-{filedAt}-{slug}")
    if attempt.get("attemptType") not in contract["attemptTypes"]:
        rep.blocking.append(f"attemptType {attempt.get('attemptType')!r} not allowed by this contract")
    for name in contract["requiredFiles"]:
        if not (attempt_dir / name).exists():
            rep.blocking.append(f"missing file {name}")

    route = None
    route_path = attempt_dir / "adversarial-route.yaml"
    if contract["adversarialBudget"] == "serious" and route_path.exists():
        route = load_yaml(route_path)
        errors = _schema_errors(route, "adversarial-route.schema.json") if route else ["adversarial-route.yaml is empty"]
        rep.blocking += errors
        if errors:
            route = None

    manifest = None
    if attempt.get("attemptType") in contract["hiddenSuite"]["requiredFor"] and not attempt.get("challengeRun"):
        rep.blocking.append("this contract needs a challengeRun (a hidden suite from an independent challenge operator)")
    if attempt.get("challengeRun"):
        manifest_path = Path(root) / "challenge-runs" / attempt["challengeRun"] / "suite-manifest.yaml"
        if manifest_path.exists():
            manifest = load_yaml(manifest_path)
            if manifest.get("suiteHash") != attempt.get("hiddenSuiteHash"):
                rep.blocking.append("hiddenSuiteHash does not match the suite manifest")
        else:
            rep.blocking.append(f"challenge run {attempt['challengeRun']} has no suite-manifest.yaml")

    # Dates.
    if attempt.get("publishedAt") and _valid_date(attempt["publishedAt"]) and \
            _date(attempt["publishedAt"]) > _date(contract["resolveBy"]):
        rep.blocking.append(f"publishedAt {attempt['publishedAt']} is after resolve-by {contract['resolveBy']}: "
                            "the evidence would not count")

    # Score table.
    table = attempt_dir / "score-table.csv"
    metrics = None
    if table.exists():
        rows, errors, forbidden = parse_table(table, contract["_columns"])
        if forbidden:
            rep.blocking.append(f"score-table.csv: submitters may not set {sorted(forbidden)}")
        fixture_rows = _fixture_rows()
        copied = sum(1 for line in table.read_text(encoding="utf-8").splitlines()[1:] if line in fixture_rows)
        if copied:
            rep.blocking.append(f"score-table.csv: {copied} rows are identical to fixture rows")
    cases_file = attempt_dir / evidence.CASES
    if cases_file.exists():
        lines, _ = evidence.read_jsonl(cases_file)
        reused = sum(1 for _, c in lines if c.get("case_hash") in _fixture_hashes())
        if reused:
            rep.blocking.append(f"{evidence.CASES}: {reused} cases are fixture cases")
        if errors:
            rep.blocking += [f"score-table.csv {e}" for e in errors[:10]]
            if len(errors) > 10:
                rep.blocking.append(f"score-table.csv: {len(errors) - 10} more row errors")
        else:
            try:
                metrics = MODULES[contract["market"]].compute(rows)
            except TableError as e:
                rep.blocking.append(f"score-table.csv {e}")
    ev = evidence.check(root, attempt_dir, attempt, contract, common, MODULES[contract["market"]], manifest,
                        _schema_errors)
    rep.blocking += ev.problems
    rep.qualification += ev.freeze_problems
    rep.evidence += ev.info
    if ev.rows is not None and metrics is not None:
        diffs = evidence.compare(rows, ev.rows, MODULES[contract["market"]].KEY)
        rep.blocking += [f"score table disagrees with the trials: {d}" for d in diffs[:10]]
        if not diffs:
            rep.evidence.append("score table matches the table derived from the frozen cases and trials")
    if metrics is None:
        rep.qualification.append("no usable score table yet, so the sample-size and coverage floors cannot be checked: "
                                 + ", ".join(f"{q['id']} {_need(q)}" for q in contract["qualification"]))
    else:
        checks = {q["id"]: q for q in contract["qualification"]}
        results = _apply(contract["qualification"], metrics)
        for bar_id, res in _exercised(contract["bars"], metrics).items():
            checks[bar_id] = {"text": "at least one case for this bar", "min": 1}
            results[bar_id] = res
        for cid, res in results.items():
            line = f"{cid}: {res['value']} (need {_need(checks[cid])})"
            (rep.met if res["ok"] else rep.qualification).append(line)
        coverage = getattr(MODULES[contract["market"]], "coverage", None)
        if coverage:
            rep.coverage += coverage(rows)
        for bar_id, res in _apply(contract["bars"], metrics).items():
            bar = next(b for b in contract["bars"] if b["id"] == bar_id)
            if "exercisedBy" in bar and metrics[bar["exercisedBy"]] < 1:
                rep.preview.append(f"{bar_id}: not exercised (no cases yet)")
            else:
                rep.preview.append(f"{bar_id}: {res['value']} (bar {_need(bar)}, {'met' if res['ok'] else 'missed'})")

    if manifest and contract["hiddenSuite"]["postFreezeBuiltAfterMethodFreeze"] and attempt.get("methodFreezeAt"):
        built = manifest.get("postFreezeBuiltAt")
        if not built or _datetime(built) <= _datetime(attempt["methodFreezeAt"]):
            rep.qualification.append(f"post-freeze part built at {built}, not after method freeze {attempt['methodFreezeAt']}")
    if contract["adversarialBudget"] == "serious":
        if route is None:
            rep.qualification.append("serious adversarial evaluation: no valid adversarial-route.yaml yet")
        else:
            ok, summary = _route_ok(route, common)
            (rep.met if ok else rep.qualification).append(f"adversarial route {route['route']}: {summary}")

    texts = _check_texts(contract, common)
    rep.maintainer = [f"{cid}: {texts[cid]}" for cid in human_check_ids(contract, attempt.get("attemptType"), common)]
    return rep


def _valid_date(s):
    try:
        _date(s)
        return True
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------------------------------------
# submit

def _tracked(path, root):
    result = subprocess.run(["git", "ls-files", "--error-unmatch", str(path)], cwd=root,
                            capture_output=True, text=True)
    return result.returncode == 0


def submit(attempt_dir, allow_not_qualifying=False, root=REPO):
    attempt_dir = Path(attempt_dir).resolve()
    root = Path(root).resolve()
    if attempt_dir.parent != root / SKETCHES:
        raise SystemExit(f"submit moves a folder from {SKETCHES}/ to {SUBMITTED}/; {attempt_dir} is not in {SKETCHES}/")
    rep = dry_run(attempt_dir, root)
    print(rep.render())
    if rep.blocking:
        print("refused: fix the items under 'Fix before submitting' first.")
        return 1
    if rep.qualification and not allow_not_qualifying:
        print("refused: this attempt would not qualify, so it stays a sketch. If it records a published result "
              "that really misses the floors and should be on file, rerun with --allow-not-qualifying.")
        return 1
    target = root / SUBMITTED / attempt_dir.name
    if target.exists():
        print(f"refused: {target.relative_to(root)} already exists")
        return 1
    target.parent.mkdir(exist_ok=True)
    if _tracked(attempt_dir / "attempt.yaml", root):
        subprocess.run(["git", "mv", str(attempt_dir), str(target)], cwd=root, check=True)
    else:
        shutil.move(str(attempt_dir), str(target))
    print(f"moved to {target.relative_to(root)}. Open a pull request; CI recomputes the outcome and a maintainer "
          "records the checks listed above.")
    return 0


# ---------------------------------------------------------------------------------------------------------
# adjudicate

def _submitted(attempt_id, root):
    d = Path(root) / SUBMITTED / attempt_id
    if not (d / "attempt.yaml").exists():
        if (Path(root) / SKETCHES / attempt_id).exists():
            raise SystemExit(f"{attempt_id} is a sketch; sketches are not adjudicated")
        raise SystemExit(f"no attempt {SUBMITTED}/{attempt_id}")
    return d, load_yaml(d / "attempt.yaml")


def _adjudication(attempt_id, root):
    d, attempt = _submitted(attempt_id, root)
    contract = load_contracts()[(attempt["market"], attempt["contractVersion"])]
    common = load_common()
    path = Path(root) / "adjudication" / attempt["market"] / f"{attempt_id}.yaml"
    record = load_yaml(path) if path.exists() else None
    return attempt, contract, common, path, record


def _guard_maintainer(attempt, maintainer):
    if maintainer == attempt.get("submitter"):
        raise SystemExit(f"{maintainer} submitted this attempt and may not adjudicate it (GOVERNANCE.md, Conflicts)")


def _save(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    errors = _schema_errors(record, "adjudication.schema.json")
    if errors:
        raise SystemExit("; ".join(errors))
    path.write_text(yaml.safe_dump(record, sort_keys=False, width=100), encoding="utf-8")


def adjudicate_start(attempt_id, maintainer, root=REPO):
    attempt, contract, common, path, record = _adjudication(attempt_id, root)
    _guard_maintainer(attempt, maintainer)
    print("Conflicts: do not adjudicate an attempt you operated or authored, one by your employer, or one in a "
          "market where you hold a position (GOVERNANCE.md).")
    record = record or {"attempt": attempt_id, "market": attempt["market"], "contractVersion": attempt["contractVersion"],
                        "maintainer": maintainer, "decidedAt": _today(), "checks": {}}
    texts = _check_texts(contract, common)
    for cid in human_check_ids(contract, attempt["attemptType"], common):
        record["checks"].setdefault(cid, {"verdict": "unsettled", "note": "Not reviewed yet."})
    _save(path, record)
    print(f"wrote {path.relative_to(root)}")
    for cid, check in record["checks"].items():
        print(f"  {check['verdict']:9} {cid}: {texts.get(cid, '(not a check for this attempt)')}")
    return 0


def adjudicate_set(attempt_id, check_id, verdict, note, maintainer, root=REPO):
    attempt, contract, common, path, record = _adjudication(attempt_id, root)
    _guard_maintainer(attempt, maintainer)
    needed = human_check_ids(contract, attempt["attemptType"], common)
    if check_id not in needed:
        raise SystemExit(f"{check_id} is not a check for this attempt; checks: {', '.join(needed)}")
    if verdict not in ("pass", "fail", "unsettled"):
        raise SystemExit("verdict must be pass, fail, or unsettled")
    if not note.strip():
        raise SystemExit("a note naming the evidence reviewed is required")
    if record is None:
        raise SystemExit(f"no adjudication file yet; run `python -m validator adjudicate start {attempt_id}` first")
    if record["maintainer"] != maintainer:
        raise SystemExit(f"this record belongs to maintainer {record['maintainer']}")
    record["checks"][check_id] = {"verdict": verdict, "note": note.strip()}
    record["decidedAt"] = _today()
    _save(path, record)
    print(f"{attempt_id}: {check_id} = {verdict}")
    return 0


def adjudicate_pending(root=REPO):
    common, contracts = load_common(), load_contracts()
    base = Path(root) / SUBMITTED
    open_count = 0
    for d in sorted(p for p in base.iterdir() if p.is_dir()) if base.exists() else []:
        attempt = load_yaml(d / "attempt.yaml")
        contract = contracts.get((attempt.get("market"), attempt.get("contractVersion")))
        if contract is None:
            continue
        path = Path(root) / "adjudication" / attempt["market"] / f"{d.name}.yaml"
        checks = load_yaml(path)["checks"] if path.exists() else {}
        pending = [cid for cid in human_check_ids(contract, attempt.get("attemptType"), common)
                   if checks.get(cid, {}).get("verdict") != "pass" and checks.get(cid, {}).get("verdict") != "fail"]
        if pending:
            open_count += 1
            print(f"{d.name} ({attempt['market']}): {', '.join(pending)}")
    if not open_count:
        print("no pending checks")
    return 0
