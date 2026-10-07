"""Example adapter for a wrapped Market 4 attempt: released per-episode CSV -> evidence files.

Usage: python m04_csv.py <released.csv> <output dir>
Writes freeze-cases.jsonl and trials.jsonl. Standard library only, so a maintainer can rerun it.
It copies reported fields; it never invents an episode or picks a reading of an ambiguous label.
Expected columns: unit_id, system_version, episode_id, kind, correction_family, enforceable_by_tool_removal,
verbal_agreement_probe, target, probe, uptake, persisted_after_reset, sham_type, sham_succeeded, transcript.
"""

import csv
import hashlib
import json
import sys
from pathlib import Path


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def flag(s):
    return {"true": True, "false": False}[s]


def main(source, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    cases, records = [], []
    with open(source, newline="", encoding="utf-8") as f:
        for n, row in enumerate(csv.DictReader(f), start=2):
            genuine = row["kind"] == "genuine"
            case = {"case_id": row["episode_id"], "unit_id": row["unit_id"], "kind": row["kind"],
                    "target": row["target"], "probe": row["probe"]}
            if genuine:
                case.update(correction_family=row["correction_family"],
                            enforceable_by_tool_removal=flag(row["enforceable_by_tool_removal"]),
                            verbal_agreement_probe=flag(row["verbal_agreement_probe"]))
                result = {"uptake": flag(row["uptake"]), "persisted_after_reset": flag(row["persisted_after_reset"])}
            else:
                case["sham_type"] = row["sham_type"]
                result = {"sham_succeeded": flag(row["sham_succeeded"])}
            case["case_hash"] = hashlib.sha256(canonical(case).encode("utf-8")).hexdigest()
            cases.append(case)
            records.append({"trial_id": f"t-{row['episode_id']}", "case_id": case["case_id"],
                            "case_hash": case["case_hash"],
                            "system": {"name": row["unit_id"], "version": row["system_version"]},
                            "scorer": {"name": "authors-released-labels", "version": "as published"},
                            "output": row["transcript"], "result": result,
                            "source": f"{Path(source).name} line {n}"})
    (out / "freeze-cases.jsonl").write_text("".join(canonical(c) + "\n" for c in cases), encoding="utf-8")
    (out / "trials.jsonl").write_text("".join(canonical(r) + "\n" for r in records), encoding="utf-8")


if __name__ == "__main__":
    main(*sys.argv[1:3])
