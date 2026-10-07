"""Turn contracts, attempts, challenge runs, and adjudication into market outcome files.

Order of checks for one attempt (the first failing step names the reason):
  1. reporting-insufficient  files, schemas, columns, links
  2. late-evidence / late-filing  evidence public after resolve-by; filed after the window
  3. qualification-failed    sample floors, coverage, freeze order, adversarial route thresholds
  4. judged-not-qualifying   a maintainer check is "fail"
  5. unresolved-judgment     a maintainer check is missing or "unsettled"
  6. bars-met / substantive-bar-failed
Metrics are reported whenever the score table parses, so partial attempts stay visible.
"""

import datetime as dt
import json
from pathlib import Path

import jsonschema

from .markets import MODULES
from .tables import TableError, forbidden_keys, load_yaml, parse_table

REPO = Path(__file__).resolve().parent.parent


class BuildError(Exception):
    """The tree cannot be evaluated at all; CI must fail."""


def _schema(name):
    with open(REPO / "schemas" / name, encoding="utf-8") as f:
        return json.load(f)


def _schema_errors(obj, name):
    validator = jsonschema.Draft202012Validator(_schema(name))
    return [f"{name}: {'/'.join(map(str, e.path)) or '(root)'}: {e.message}"
            for e in sorted(validator.iter_errors(obj), key=lambda e: list(e.path))]


def _date(s):
    return dt.date.fromisoformat(s)


def _datetime(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def load_common():
    return load_yaml(REPO / "shared-rules" / "common-v1.yaml")


def load_registry():
    return load_yaml(REPO / "registry.yaml")


def load_contracts():
    contracts = {}
    for path in sorted((REPO / "market-contracts").glob("market-*/contract-v*.yaml")):
        contract = load_yaml(path)
        errors = _schema_errors(contract, "contract.schema.json")
        if errors:
            raise BuildError(f"{path}: " + "; ".join(errors))
        columns = load_yaml(path.parent / "required-columns.yaml")
        if columns.get("contractVersion") != contract["version"]:
            raise BuildError(f"{path.parent}/required-columns.yaml does not match contract version {contract['version']}")
        if contract["market"] not in MODULES:
            raise BuildError(f"{contract['market']}: no validator module")
        contract["_columns"] = columns
        contracts[(contract["market"], contract["version"])] = contract
    return contracts


def _threshold_ok(item, value):
    if "equals" in item:
        return value == item["equals"]
    ok = True
    if "min" in item:
        ok = ok and value >= item["min"]
    if "max" in item:
        ok = ok and value <= item["max"]
    return ok


def _apply(items, metrics):
    results = {}
    for item in items:
        value = metrics[item["id"]]
        results[item["id"]] = {"value": round(value, 4) if isinstance(value, float) else value,
                               "ok": _threshold_ok(item, value)}
    return results


def _route_ok(route, common):
    """Mechanical thresholds of the three serious-adversarial routes."""
    rules = common["seriousAdversarialEvaluation"]["routes"]
    kind = route["route"]
    if kind == "red-teams":
        r, groups = rules["red-teams"], route["redTeams"]["groups"]
        orgs = {g["organization"] for g in groups}
        ok = (len(groups) >= r["minGroups"] and len(orgs) >= r["minOrganizations"]
              and all(g["expertHours"] >= r["minHoursEach"] for g in groups))
        return ok, f"{len(groups)} groups, {len(orgs)} organizations, min hours {min((g['expertHours'] for g in groups), default=0)}"
    if kind == "bounty":
        r, b = rules["bounty"], route["bounty"]
        days = (_date(b["closedAt"]) - _date(b["openedAt"])).days
        ok = b["usd"] >= r["minUsd"] and days >= r["minDaysOpen"] and b["qualifyingSubmissions"] >= r["minQualifyingSubmissions"]
        return ok, f"USD {b['usd']}, {days} days open, {b['qualifyingSubmissions']} qualifying submissions"
    r, g = rules["generator"], route["generator"]
    found = g["plantedWeaknessesFound"] / g["plantedWeaknesses"]
    ok = found >= r["minPlantedFound"] and g["independentExpertHours"] >= r["minIndependentHours"]
    return ok, f"found {g['plantedWeaknessesFound']}/{g['plantedWeaknesses']} planted weaknesses, {g['independentExpertHours']} independent hours"


def human_check_ids(contract, attempt_type, common):
    checks = list(common["humanChecks"]["all"])
    if attempt_type == "wrapped":
        checks += common["humanChecks"]["wrapped"]
    if contract["adversarialBudget"] == "serious":
        checks += common["humanChecks"]["serious"]
    checks += contract["humanChecks"]
    return [c["id"] for c in checks]


def window_closes(contract, common):
    return _date(contract["resolveBy"]) + dt.timedelta(days=common["deadlines"]["windowDays"])


def evaluate_attempt(root, attempt_dir, attempt, contract, common, all_attempt_ids):
    rec = {"id": attempt_dir.name, "attemptType": attempt.get("attemptType"), "submitter": attempt.get("submitter"),
           "publishedAt": attempt.get("publishedAt"), "qualifying": False, "barsMet": None, "reason": None,
           "details": [], "metrics": {}, "qualification": {}, "bars": {}, "human": {}}

    def stop(reason, *details):
        rec["reason"] = reason
        rec["details"].extend(details)
        return rec

    # 1. Reporting: schemas, files, table, links.
    problems = list(_schema_errors(attempt, "attempt.schema.json"))
    if attempt.get("id") != attempt_dir.name:
        problems.append("attempt.yaml id does not equal the directory name")
    if not attempt_dir.name.startswith(f"{attempt.get('submitter')}-{attempt.get('filedAt')}-"):
        problems.append("attempt id must be {submitter}-{filedAt}-{slug}")
    if attempt.get("attemptType") not in contract["attemptTypes"]:
        problems.append(f"attemptType {attempt.get('attemptType')!r} not allowed by this contract")
    for name in contract["requiredFiles"]:
        if not (attempt_dir / name).exists():
            problems.append(f"missing {name}")
    for dep in attempt.get("dependsOnAttempts", []):
        if dep not in all_attempt_ids:
            problems.append(f"dependsOnAttempts: {dep} not found")

    route = None
    if contract["adversarialBudget"] == "serious" and (attempt_dir / "adversarial-route.yaml").exists():
        route = load_yaml(attempt_dir / "adversarial-route.yaml")
        problems += _schema_errors(route, "adversarial-route.schema.json")

    if contract["adversarialBudget"] == "serious" and route is None:
        problems.append("serious adversarial budget: missing adversarial-route.yaml")

    manifest = None
    if attempt.get("attemptType") in contract["hiddenSuite"]["requiredFor"] and not attempt.get("challengeRun"):
        problems.append("this contract requires challengeRun for this attempt type")
    if attempt.get("challengeRun"):
        manifest_path = root / "challenge-runs" / attempt["challengeRun"] / "suite-manifest.yaml"
        if not manifest_path.exists():
            problems.append(f"challenge run {attempt['challengeRun']} has no suite-manifest.yaml")
        else:
            manifest = load_yaml(manifest_path)
            problems += _schema_errors(manifest, "suite-manifest.schema.json")
            if manifest.get("market") != contract["market"]:
                problems.append("suite manifest is for a different market")
            if manifest.get("suiteHash") != attempt.get("hiddenSuiteHash"):
                problems.append("hiddenSuiteHash does not match the suite manifest")

    rows = []
    table_path = attempt_dir / "score-table.csv"
    if table_path.exists():
        rows, table_errors, _ = parse_table(table_path, contract["_columns"])
        problems += [f"score-table.csv {e}" for e in table_errors]
        if not table_errors:
            try:
                metrics = MODULES[contract["market"]].compute(rows)
                rec["metrics"] = {k: round(v, 4) if isinstance(v, float) else v for k, v in metrics.items()}
                rec["qualification"] = _apply(contract["qualification"], metrics)
                rec["bars"] = _apply(contract["bars"], metrics)
                rec["barsMet"] = all(b["ok"] for b in rec["bars"].values())
            except TableError as e:
                problems.append(f"score-table.csv {e}")
    if problems:
        return stop("reporting-insufficient", *problems)

    # 2. Dates.
    cutoff = _date(contract["resolveBy"])
    if _date(attempt["publishedAt"]) > cutoff:
        return stop("late-evidence", f"publishedAt {attempt['publishedAt']} is after resolve-by {contract['resolveBy']}")
    if manifest and _date(manifest["releasedAt"]) > cutoff:
        return stop("late-evidence", f"hidden suite released {manifest['releasedAt']}, after resolve-by")
    if _date(attempt["filedAt"]) > window_closes(contract, common):
        return stop("late-filing", f"filedAt {attempt['filedAt']} is after the window closed")

    # 3. Mechanical qualification.
    failed = [f"{k} = {v['value']}" for k, v in rec["qualification"].items() if not v["ok"]]
    if manifest and contract["hiddenSuite"]["postFreezeBuiltAfterMethodFreeze"] and attempt["attemptType"] == "run":
        built = manifest.get("postFreezeBuiltAt")
        if not built or _datetime(built) <= _datetime(attempt["methodFreezeAt"]):
            failed.append(f"post-freeze part built at {built}, not after method freeze {attempt['methodFreezeAt']}")
    if contract["adversarialBudget"] == "serious":
        ok, summary = _route_ok(route, common)
        rec["qualification"]["adversarial-route"] = {"value": f"{route['route']}: {summary}", "ok": ok}
        if not ok:
            failed.append(f"adversarial route below the common-rule thresholds ({summary})")
    if failed:
        return stop("qualification-failed", *failed)

    # 4-5. Maintainer adjudication.
    adj_path = root / "adjudication" / contract["market"] / f"{attempt_dir.name}.yaml"
    needed = human_check_ids(contract, attempt["attemptType"], common)
    adj = None
    if adj_path.exists():
        adj = load_yaml(adj_path)
        errors = _schema_errors(adj, "adjudication.schema.json")
        if errors:
            raise BuildError(f"{adj_path}: " + "; ".join(errors))
        if adj["attempt"] != attempt_dir.name or adj["market"] != contract["market"] or adj["contractVersion"] != contract["version"]:
            raise BuildError(f"{adj_path}: attempt, market, or contractVersion does not match")
    verdicts = {cid: (adj["checks"].get(cid, {}).get("verdict", "missing") if adj else "missing") for cid in needed}
    rec["human"] = verdicts
    fails = [cid for cid, v in verdicts.items() if v == "fail"]
    if fails:
        return stop("judged-not-qualifying", *[f"{cid}: {adj['checks'][cid]['note']}" for cid in fails])
    open_checks = [cid for cid, v in verdicts.items() if v != "pass"]
    if open_checks:
        return stop("unresolved-judgment", *[f"{cid}: {verdicts[cid]}" for cid in open_checks])

    # 6. Bars.
    rec["qualifying"] = True
    if rec["barsMet"]:
        rec["reason"] = "bars-met"
    else:
        rec["reason"] = "substantive-bar-failed"
        rec["details"] = [f"{k} = {v['value']}" for k, v in rec["bars"].items() if not v["ok"]]
    return rec


def _check_submitted_files(attempt_dir):
    """Hard error if a submitter set an outcome field anywhere."""
    for path in sorted(attempt_dir.rglob("*.yaml")):
        found = forbidden_keys(load_yaml(path))
        if found:
            raise BuildError(f"{path}: submitters may not set {sorted(found)}")
    table = attempt_dir / "score-table.csv"
    if table.exists():
        with open(table, encoding="utf-8") as f:
            header = set(f.readline().strip().split(","))
        found = header & {"qualifying", "barsMet", "outcome", "reason"}
        if found:
            raise BuildError(f"{table}: submitters may not set {sorted(found)}")


def build_outcomes(root, only_markets_with_attempts=False):
    """Return {filename: outcome dict} for every contract (or only those with attempts)."""
    root = Path(root)
    common, registry, contracts = load_common(), load_registry(), load_contracts()
    attempts_dir = root / "submitted-attempts"
    attempt_dirs = sorted(p for p in attempts_dir.iterdir() if p.is_dir()) if attempts_dir.exists() else []
    loaded = []
    for d in attempt_dirs:
        if not (d / "attempt.yaml").exists():
            raise BuildError(f"{d}: missing attempt.yaml")
        _check_submitted_files(d)
        attempt = load_yaml(d / "attempt.yaml")
        key = (attempt.get("market"), attempt.get("contractVersion"))
        if key not in contracts:
            raise BuildError(f"{d}: no contract {key[0]} version {key[1]}")
        loaded.append((d, attempt, key))
    all_ids = {d.name for d, _, _ in loaded}

    outcomes = {}
    for key, contract in sorted(contracts.items()):
        mine = [(d, a) for d, a, k in loaded if k == key]
        if only_markets_with_attempts and not mine:
            continue
        if contract["outcomes"] != ["YES", "NO", "OTHER"]:
            raise BuildError(f"{contract['market']}: only three-way contracts are implemented")
        records = [evaluate_attempt(root, d, a, contract, common, all_ids) for d, a in mine]
        qualifying = [r for r in records if r["qualifying"]]
        if any(r["barsMet"] for r in qualifying):
            outcome, reason = "YES", "qualifying-attempt-met-bars"
        elif qualifying:
            outcome, reason = "NO", "every-qualifying-attempt-missed-bars"
        else:
            outcome, reason = "OTHER", "no-qualifying-attempt"
        result = {
            "market": contract["market"],
            "contractVersion": contract["version"],
            "contractStatus": contract["status"],
            "resolutionSource": bool(registry["resolutionSource"]),
            "title": contract["title"],
            "outcomes": contract["outcomes"],
            "evidenceCutoff": contract["resolveBy"],
            "windowCloses": window_closes(contract, common).isoformat(),
            "outcome": outcome,
            "reason": reason,
            "attempts": records,
        }
        schema_errors = _schema_errors(result, "market-outcome.schema.json")
        if schema_errors:
            raise BuildError("generated outcome fails its schema: " + "; ".join(schema_errors))
        outcomes[f"{contract['market']}-v{contract['version']}.json"] = result
    return outcomes


def dump(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
