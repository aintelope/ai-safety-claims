"""Example adapter for a wrapped Market 1 attempt: released per-system CSV -> evidence files.

Usage: python m01_csv.py <released.csv> <output dir>
Writes freeze-cases.jsonl and trials.jsonl. Standard library only, so a maintainer can rerun it.
Expected columns: system_id, families, components, response_statistic, min_change, no_effect_low,
no_effect_high, adversarial_subset, components_named, certificate, certificate_correct, method_output.
List columns are semicolon-separated. A system without all four freeze fields is copied unscored.
"""

import csv
import hashlib
import json
import sys
from pathlib import Path


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def items(s):
    return [x for x in s.split(";") if x]


def main(source, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    cases, records = [], []
    with open(source, newline="", encoding="utf-8") as f:
        for n, row in enumerate(csv.DictReader(f), start=2):
            case = {"case_id": row["system_id"], "families": items(row["families"]),
                    "adversarial_subset": row["adversarial_subset"] == "true", "freeze_complete": False}
            if row["components"] and row["response_statistic"] and row["min_change"] and row["no_effect_low"]:
                case.update(freeze_complete=True, components=items(row["components"]),
                            components_count=len(items(row["components"])),
                            response_statistic=row["response_statistic"], min_change=float(row["min_change"]),
                            no_effect_range=[float(row["no_effect_low"]), float(row["no_effect_high"])])
            case["case_hash"] = hashlib.sha256(canonical(case).encode("utf-8")).hexdigest()
            cases.append(case)
            if not case["freeze_complete"]:
                continue
            named = items(row["components_named"])
            result = {"components_named": named, "components_named_listed": len(set(named) & set(case["components"])),
                      "certificate": row["certificate"]}
            if row["certificate"] == "complete":
                result["certificate_correct"] = row["certificate_correct"] == "true"
            records.append({"trial_id": f"t-{case['case_id']}", "case_id": case["case_id"],
                            "case_hash": case["case_hash"], "system": {"name": "boundary method", "version": "as published"},
                            "scorer": {"name": "authors-released-labels", "version": "as published"},
                            "output": row["method_output"], "result": result, "source": f"{Path(source).name} line {n}"})
    (out / "freeze-cases.jsonl").write_text("".join(canonical(c) + "\n" for c in cases), encoding="utf-8")
    (out / "trials.jsonl").write_text("".join(canonical(r) + "\n" for r in records), encoding="utf-8")


if __name__ == "__main__":
    main(*sys.argv[1:3])
