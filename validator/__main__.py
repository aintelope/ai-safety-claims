"""Usage:
  python -m validator build           write market-outcomes/ and ui/index.html from the tree
  python -m validator check           fail if those files differ from what build would write
  python -m validator test [--update] run examples/scenarios and the statistics tests
"""

import shutil
import sys
import tempfile
from pathlib import Path

from .engine import REPO, BuildError, build_outcomes, dump, load_registry
from .stats import clopper_pearson_upper
from .ui import render

OUT = REPO / "market-outcomes"
UI = REPO / "ui" / "index.html"


def expected_files():
    outcomes = build_outcomes(REPO)
    files = {OUT / name: dump(obj) for name, obj in outcomes.items()}
    files[UI] = render(outcomes, load_registry())
    return files


def cmd_build():
    files = expected_files()
    for stale in OUT.glob("*.json"):
        if stale not in files:
            stale.unlink()
    for path, text in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path.relative_to(REPO)}")
    return 0


def cmd_check():
    files = expected_files()
    bad = [str(p.relative_to(REPO)) for p, text in files.items()
           if not p.exists() or p.read_text(encoding="utf-8") != text]
    bad += [str(p.relative_to(REPO)) for p in OUT.glob("*.json") if p not in files]
    if bad:
        print("out of date (run python -m validator build): " + ", ".join(bad))
        return 1
    print(f"ok: {len(files) - 1} outcome files and ui/index.html match the validator")
    return 0


def test_stats():
    # Zero failures in 50 units: 1 - 0.05^(1/50).
    assert abs(clopper_pearson_upper(0, 50) - (1 - 0.05 ** (1 / 50))) < 1e-6
    # Appendix H, Market 19 example: 3 of 120 accepted, six stacks -> about 8.3%.
    assert abs(clopper_pearson_upper(3, 120, 1 - 0.05 / 6) - 0.083) < 0.001
    assert clopper_pearson_upper(5, 5) == 1.0
    print("ok: statistics")


def test_forbidden_field():
    source = REPO / "examples" / "scenarios" / "m04-yes"
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "scenario"
        shutil.copytree(source, root)
        attempt = next((root / "submitted-attempts").iterdir()) / "attempt.yaml"
        attempt.write_text(attempt.read_text(encoding="utf-8") + "outcome: YES\n", encoding="utf-8")
        try:
            build_outcomes(root, only_markets_with_attempts=True)
        except BuildError as e:
            assert "may not set" in str(e)
            print("ok: submitter-set outcome field is rejected")
            return
    raise AssertionError("a submitter-set outcome field was not rejected")


def cmd_test(update):
    test_stats()
    test_forbidden_field()
    failures = 0
    for scenario in sorted((REPO / "examples" / "scenarios").iterdir()):
        if not scenario.is_dir():
            continue
        outcomes = build_outcomes(scenario, only_markets_with_attempts=True)
        expected_dir = scenario / "expected-outcomes"
        if update:
            shutil.rmtree(expected_dir, ignore_errors=True)
            expected_dir.mkdir()
            for name, obj in outcomes.items():
                (expected_dir / name).write_text(dump(obj), encoding="utf-8")
            print(f"updated {scenario.name}")
            continue
        got = {name: dump(obj) for name, obj in outcomes.items()}
        want = {p.name: p.read_text(encoding="utf-8") for p in expected_dir.glob("*.json")}
        if got != want:
            failures += 1
            print(f"FAIL {scenario.name}")
        else:
            summary = ", ".join(f"{o['market']} {o['outcome']}" for o in outcomes.values())
            print(f"ok: {scenario.name} ({summary})")
    return 1 if failures else 0


def main(argv):
    if not argv or argv[0] not in ("build", "check", "test"):
        print(__doc__)
        return 2
    try:
        if argv[0] == "build":
            return cmd_build()
        if argv[0] == "check":
            return cmd_check()
        return cmd_test("--update" in argv)
    except BuildError as e:
        print(f"error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
