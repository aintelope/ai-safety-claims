"""Export everything the site shows as one JSON file: contracts (every version), shared rules, outcomes,
and sketch dry runs. The site renders this file and computes nothing itself."""

import json
import subprocess
from pathlib import Path

from . import contribute
from .engine import REPO, build_outcomes, load_common, load_contracts, load_registry

DEFAULT_REPOSITORY = "https://github.com/aintelope/ai-safety-claims"


def _git(*args):
    try:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _repository():
    url = _git("remote", "get-url", "origin") or ""
    if url.startswith("git@github.com:"):
        url = "https://github.com/" + url.split(":", 1)[1]
    url = url.removesuffix(".git")
    return url if url.startswith("https://github.com/") else DEFAULT_REPOSITORY


def _contract(contract, outcome):
    out = {k: v for k, v in contract.items() if not k.startswith("_")}
    out["file"] = f"market-contracts/{contract['market']}/contract-v{contract['version']}.yaml"
    columns = contract["_columns"]
    out["scoreTable"] = {"unit": columns.get("unit"), "columns": columns.get("columns", {}),
                         "cases": columns.get("cases"), "results": columns.get("results")}
    out["outcome"] = outcome
    return out


def build_export():
    contracts = load_contracts()
    outcomes = build_outcomes(REPO)
    by_market = {}
    for (market, version), contract in sorted(contracts.items()):
        outcome = outcomes.get(f"{market}-v{version}.json")
        by_market.setdefault(market, []).append(_contract(contract, outcome))
    markets = []
    for market, versions in sorted(by_market.items()):
        latest = max(versions, key=lambda v: v["version"])
        markets.append({"market": market, "number": int(market.split("-")[1]), "title": latest["title"],
                        "latestVersion": latest["version"], "versions": versions})

    sketches = []
    base = REPO / "sketches"
    for d in sorted(p for p in base.iterdir() if p.is_dir()) if base.exists() else []:
        report = contribute.dry_run(d, REPO)
        attempt = contribute.load_yaml(d / "attempt.yaml") if (d / "attempt.yaml").exists() else {}
        sketches.append({"id": d.name, "market": attempt.get("market"), "contractVersion": attempt.get("contractVersion"),
                         "attemptType": attempt.get("attemptType"), "submitter": attempt.get("submitter"),
                         "filedAt": attempt.get("filedAt"), "notes": attempt.get("notes"),
                         "report": report.summary()})

    return {
        "repository": _repository(),
        "commit": _git("rev-parse", "HEAD"),
        "registry": load_registry(),
        "sharedRules": load_common(),
        "markets": markets,
        "sketches": sketches,
    }


def write_export(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_export(), indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    print(f"wrote {path}")
    return 0
