"""Usage:
  python -m validator build           write market-outcomes/ from the tree
  python -m validator check           fail if those files differ from what build would write
  python -m validator test [--update] run examples/scenarios and the statistics tests
  python -m validator export [--out site/src/data/registry.json]
                                      everything the site shows, as one JSON file

Contributors:
  python -m validator new --market market-04 --submitter you --slug my-eval [--type wrapped] [--from-fixture m04-yes]
                                      start sketches/<submitter>-<today>-<slug>/ (from a fixture: copy its files)
  python -m validator dry-run <dir>   list what a sketch or attempt still misses, without deciding anything
  python -m validator submit <dir> [--allow-not-qualifying]
                                      move a sketch to submitted-attempts/ if the dry run allows it

Evidence (see shared-rules/common-v1.yaml, evidence):
  python -m validator hash-cases <freeze-cases.jsonl>     fill in case_hash on every case
  python -m validator import-inspect <inspect log> --cases <freeze-cases.jsonl> --out <trials.jsonl>
                                      [--system-version V] [--scorer NAME ...]
  python -m validator raw-log <file> --attempt <dir> [--url URL] [--format F] [--update-attempt]
                                      keep the raw log (whole, or head and tail); print or write rawLog
  python -m validator derive-table <dir>                  write score-table.csv from the cases and trials
  python -m validator verify-log <dir> [--file F]         maintainers: check the full raw log
  python -m validator rerun-adapter <dir> --source F      maintainers: rerun a wrapped attempt's adapter

Maintainers:
  python -m validator adjudicate pending
  python -m validator adjudicate start <attempt-id> --maintainer you
  python -m validator adjudicate set <attempt-id> <check-id> pass|fail|unsettled --note "..." --maintainer you
"""

import argparse
import contextlib
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

from . import contribute, logtools
from .engine import REPO, BuildError, build_outcomes, check_sketches, dump, load_common
from .stats import clopper_pearson_upper

OUT = REPO / "market-outcomes"


def expected_files():
    outcomes = build_outcomes(REPO)
    return {OUT / name: dump(obj) for name, obj in outcomes.items()}


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
    check_sketches(REPO)
    files = expected_files()
    bad = [str(p.relative_to(REPO)) for p, text in files.items()
           if not p.exists() or p.read_text(encoding="utf-8") != text]
    bad += [str(p.relative_to(REPO)) for p in OUT.glob("*.json") if p not in files]
    if bad:
        print("out of date (run python -m validator build): " + ", ".join(bad))
        return 1
    print(f"ok: {len(files)} outcome files match the validator")
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


def test_contribute():
    """new -> dry-run -> submit guards -> adjudicate guards, in a scratch tree."""
    with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
        root = Path(tmp)
        blank = contribute.new_sketch("market-01", "tester", "blank", "run", root=root)
        rep = contribute.dry_run(blank, root)
        assert any("missing publishedAt" in b for b in rep.blocking) and rep.qualification
        assert contribute.submit(blank, root=root) == 1 and blank.exists()
        copied = contribute.new_sketch("market-04", "tester", "copy", "run", from_fixture="m04-yes", root=root)
        rep = contribute.dry_run(copied, root)
        assert any("copied from a fixture" in b for b in rep.blocking)
        assert any("identical to fixture rows" in b for b in rep.blocking)
        assert any("fictional fixture values" in b for b in rep.blocking)
        assert contribute.submit(copied, allow_not_qualifying=True, root=root) == 1 and copied.exists()
        try:
            contribute.adjudicate_start(copied.name, "maintainer", root=root)
            raise AssertionError("a sketch was adjudicated")
        except SystemExit as e:
            assert "sketch" in str(e)
    print("ok: sketch guards (new, dry-run, submit, adjudicate)")


def _scenario_copy(tmp, name):
    root = Path(tmp) / "scenario"
    shutil.copytree(REPO / "examples" / "scenarios" / name, root)
    return root, next((root / "submitted-attempts").iterdir())


def _reason(root):
    outcome = next(iter(build_outcomes(root, only_markets_with_attempts=True).values()))
    return outcome["attempts"][0]["reason"], outcome["attempts"][0]["details"]


def test_evidence():
    """Tampering with the evidence is caught; the tools reproduce what the fixtures hold."""
    # A score table that says more than the trials.
    with tempfile.TemporaryDirectory() as tmp:
        root, d = _scenario_copy(tmp, "m04-case-gap-no")
        table = d / "score-table.csv"
        table.write_text(table.read_text(encoding="utf-8").replace(
            "g-002,genuine,authority-change,false,false,false", "g-002,genuine,authority-change,false,false,true"),
            encoding="utf-8")
        reason, details = _reason(root)
        assert reason == "reporting-insufficient" and any("disagrees with the trials" in x for x in details), details
    # A trial that started before the freeze.
    with tempfile.TemporaryDirectory() as tmp:
        root, d = _scenario_copy(tmp, "m04-yes")
        trials = d / "trials.jsonl"
        lines = trials.read_text(encoding="utf-8").splitlines()
        lines[0] = lines[0].replace('"started_at":"2027-08-01T09:00:00Z"', '"started_at":"2027-07-01T09:00:00Z"')
        trials.write_text("\n".join(lines) + "\n", encoding="utf-8")
        reason, details = _reason(root)
        assert reason == "qualification-failed" and any("before the freeze" in x for x in details), details
    # A frozen case edited after the trials ran.
    with tempfile.TemporaryDirectory() as tmp:
        root, d = _scenario_copy(tmp, "m04-yes")
        cases = d / "freeze-cases.jsonl"
        cases.write_text(cases.read_text(encoding="utf-8").replace("held-out task set P-g-000", "easier probe", 1),
                         encoding="utf-8")
        reason, details = _reason(root)
        assert reason == "reporting-insufficient" and any("case_hash" in x for x in details), details
    # Raw log over the local limit: head and tail only, url required.
    with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
        from .evidence import check_raw_log, file_sha256
        big = Path(tmp) / "big.log"
        big.write_bytes(b"x" * 50 + b"y" * 50)
        attempt_dir = Path(tmp) / "a"
        attempt_dir.mkdir()
        limits = {"maxLocalLogBytes": 40, "excerptBytes": 20}
        logtools.load_common = lambda: {"evidence": limits}
        try:
            logtools.keep_raw_log(big, attempt_dir, url="https://example.org/big.log")
            raw = {"sha256": file_sha256(big), "bytes": 100, "url": "https://example.org/big.log"}
            attempt = {"attemptType": "run", "rawLog": raw}
            assert check_raw_log(attempt_dir, attempt, limits) == []
            assert (attempt_dir / "raw-log" / "tail").read_bytes() == b"y" * 20
            (attempt_dir / "attempt.yaml").write_text(yaml.safe_dump({"rawLog": raw}), encoding="utf-8")
            assert logtools.verify_log(attempt_dir, big) == 0
            assert check_raw_log(attempt_dir, {"attemptType": "run", "rawLog": {**raw, "url": None}}, limits)
        finally:
            logtools.load_common = load_common
    # Tools reproduce the fixtures: the full raw log, the wrapped adapter, and an Inspect extract.
    with contextlib.redirect_stdout(io.StringIO()):
        d = next((REPO / "examples/scenarios/m04-capture-no/submitted-attempts").iterdir())
        assert logtools.verify_log(d, d / "raw-log" / "harness.log") == 0
        scenario = REPO / "examples/scenarios/m04-wrapped-other"
        d = scenario / "submitted-attempts" / "example-filer-2027-11-02-wrap-jones-2027"
        assert logtools.rerun_adapter(d, scenario / "sources" / "jones-2027-episodes.csv") == 0
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "trials.jsonl"
            inspect = REPO / "examples" / "inspect"
            assert logtools.import_inspect(inspect / "corrections-mockllm.json", inspect / "freeze-cases.jsonl", out) == 0
            records = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
            assert [r["result"] for r in records] == [{"persisted_after_reset": True, "uptake": True},
                                                      {"sham_succeeded": False}], records
    # derive-table writes exactly the fixtures' score tables.
    with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
        for scenario in sorted((REPO / "examples" / "scenarios").iterdir()):
            root = Path(tmp) / scenario.name
            shutil.copytree(scenario, root)
            for d in sorted((root / "submitted-attempts").glob("*")) if (root / "submitted-attempts").exists() else []:
                want = (d / "score-table.csv").read_text(encoding="utf-8")
                logtools.derive_table(d, root)
                assert (d / "score-table.csv").read_text(encoding="utf-8") == want, d.name
    print("ok: evidence (table vs trials, freeze timing, case hashes, raw log, adapter rerun, Inspect extract, "
          "derive-table)")


def cmd_test(update):
    test_stats()
    test_forbidden_field()
    test_contribute()
    test_evidence()
    failures = 0
    for scenario in sorted((REPO / "examples" / "scenarios").iterdir()):
        if not scenario.is_dir():
            continue
        outcomes = build_outcomes(scenario, only_markets_with_attempts=True)
        expected_dir = scenario / "expected-outcomes"
        got = {name: dump(obj) for name, obj in outcomes.items()}
        # Sketches never feed an outcome; their dry-run reports are fixed like outcome files.
        sketches = scenario / "sketches"
        for d in sorted(sketches.iterdir()) if sketches.exists() else []:
            got[f"dry-run-{d.name}.txt"] = contribute.dry_run(d, scenario).render()
        if update:
            shutil.rmtree(expected_dir, ignore_errors=True)
            expected_dir.mkdir()
            for name, text in got.items():
                (expected_dir / name).write_text(text, encoding="utf-8")
            print(f"updated {scenario.name}")
            continue
        want = {p.name: p.read_text(encoding="utf-8") for p in expected_dir.iterdir()}
        if got != want:
            failures += 1
            print(f"FAIL {scenario.name}")
        else:
            summary = ", ".join([f"{o['market']} {o['outcome']}" for o in outcomes.values()]
                                + [f"{len(got) - len(outcomes)} sketch dry runs"] * (len(got) > len(outcomes)))
            print(f"ok: {scenario.name} ({summary})")
    return 1 if failures else 0


def _parser():
    p = argparse.ArgumentParser(prog="python -m validator", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    sub.add_parser("check")
    ex = sub.add_parser("export")
    ex.add_argument("--out", default=str(REPO / "site" / "src" / "data" / "registry.json"))
    t = sub.add_parser("test")
    t.add_argument("--update", action="store_true")
    n = sub.add_parser("new")
    n.add_argument("--market", required=True)
    n.add_argument("--submitter", required=True)
    n.add_argument("--slug", required=True)
    n.add_argument("--type", default="run", dest="attempt_type")
    n.add_argument("--from-fixture", help="<scenario> or <scenario>/<attempt-id> under examples/scenarios")
    d = sub.add_parser("dry-run")
    d.add_argument("dir")
    s = sub.add_parser("submit")
    s.add_argument("dir")
    s.add_argument("--allow-not-qualifying", action="store_true")
    h = sub.add_parser("hash-cases")
    h.add_argument("file")
    i = sub.add_parser("import-inspect")
    i.add_argument("log")
    i.add_argument("--cases", required=True)
    i.add_argument("--out", required=True)
    i.add_argument("--system-version")
    i.add_argument("--scorer", action="append")
    r = sub.add_parser("raw-log")
    r.add_argument("file")
    r.add_argument("--attempt", required=True)
    r.add_argument("--url")
    r.add_argument("--format")
    r.add_argument("--update-attempt", action="store_true")
    dt_ = sub.add_parser("derive-table")
    dt_.add_argument("dir")
    v = sub.add_parser("verify-log")
    v.add_argument("dir")
    v.add_argument("--file")
    ra = sub.add_parser("rerun-adapter")
    ra.add_argument("dir")
    ra.add_argument("--source", required=True)
    a = sub.add_parser("adjudicate").add_subparsers(dest="action", required=True)
    a.add_parser("pending")
    st = a.add_parser("start")
    st.add_argument("attempt")
    st.add_argument("--maintainer", required=True)
    se = a.add_parser("set")
    se.add_argument("attempt")
    se.add_argument("check")
    se.add_argument("verdict", choices=["pass", "fail", "unsettled"])
    se.add_argument("--note", required=True)
    se.add_argument("--maintainer", required=True)
    return p


def main(argv):
    args = _parser().parse_args(argv)
    try:
        if args.cmd == "build":
            return cmd_build()
        if args.cmd == "check":
            return cmd_check()
        if args.cmd == "export":
            from .export import write_export
            return write_export(args.out)
        if args.cmd == "test":
            return cmd_test(args.update)
        if args.cmd == "new":
            contribute.new_sketch(args.market, args.submitter, args.slug, args.attempt_type, args.from_fixture)
            return 0
        if args.cmd == "dry-run":
            report = contribute.dry_run(Path(args.dir))
            print(report.render(), end="")
            return 1 if report.blocking else 0
        if args.cmd == "submit":
            return contribute.submit(Path(args.dir), args.allow_not_qualifying)
        if args.cmd == "hash-cases":
            return logtools.hash_cases(Path(args.file))
        if args.cmd == "import-inspect":
            return logtools.import_inspect(args.log, args.cases, args.out, args.system_version, args.scorer)
        if args.cmd == "raw-log":
            return logtools.keep_raw_log(args.file, args.attempt, args.url, args.format, args.update_attempt)
        if args.cmd == "derive-table":
            return logtools.derive_table(args.dir)
        if args.cmd == "verify-log":
            return logtools.verify_log(args.dir, args.file)
        if args.cmd == "rerun-adapter":
            return logtools.rerun_adapter(args.dir, args.source)
        if args.action == "pending":
            return contribute.adjudicate_pending()
        if args.action == "start":
            return contribute.adjudicate_start(args.attempt, args.maintainer)
        return contribute.adjudicate_set(args.attempt, args.check, args.verdict, args.note, args.maintainer)
    except BuildError as e:
        print(f"error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
