#!/usr/bin/env python3
"""The mutation gate: compute the score and fail below a threshold.

A mutant is *killed* when the test suite fails against it, and *survived*
when the suite still passes - which means the mutant is a change no test
noticed.

Two things this script refuses to do:

* Score a partial run. The score is computed from mutmut's own recorded
  per-mutant results, and a run in which not every generated mutant has a
  result is reported as INCOMPLETE rather than as a number.
* Count a timeout as a kill. A mutant that made the suite hang was
  *detected* in a sense, but the tests did not fail - it neither proves
  nor disproves that the behaviour is covered, so it counts against the
  score and is reported separately.

Usage:
    python scripts/mutation_gate.py [--min-score 80] [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MUTANTS = ROOT / "mutants" / "src"

# A mutant definition looks like: def xǁClassǁmethod__mutmut_3(self, ...)
MUTANT_DEF = re.compile(r"^\s*def x.+__mutmut_\d+\(", re.M)

# pytest exits 1 when a test fails. That is a kill.
PYTEST_FAILED = 1

# mutmut kills a worker that overruns its wall-time limit with SIGXCPU,
# and the `timeout` command exits 33. Neither is a clean kill.
TIMEOUT_CODES = {-24, 33, 124, 137}


def total_mutants() -> int:
    """How many mutants mutmut generated."""
    if not MUTANTS.exists():
        return 0
    total = 0
    for path in MUTANTS.rglob("*.py"):
        total += len(MUTANT_DEF.findall(path.read_text()))
    return total


def tree_mutant_names() -> set[str]:
    """The mangled names of the mutants in the generated tree.

    A mutant is named ``xǁClassǁmethod__mutmut_3`` in the tree, and
    mutmut records it under the full dotted path in the ``.meta`` file.
    Comparing the two tells us whether the recorded results belong to
    *this* source or to a different version of it.
    """
    names: set[str] = set()
    for path in MUTANTS.rglob("*.py"):
        try:
            text = path.read_text()
        except OSError:
            continue
        for match in re.finditer(r"^\s*def (x.+?__mutmut_\d+)\(", text, re.M):
            names.add(match.group(1))
    return names


def recorded_results() -> tuple[int, int, int, Counter, int]:
    """Tally the recorded results.

    Returns ``(tested, killed, timed_out, other, orphans)``. mutmut records
    each mutant's pytest exit code in the ``.meta`` file beside the
    mutated module: ``None`` means it has not been run yet, ``0`` means the
    tests still passed (the mutant SURVIVED), ``1`` means the tests failed
    (the mutant was KILLED), and the timeout codes mean the worker was
    killed for overrunning.

    ``orphans`` counts results recorded for mutants that are not in the
    tree - which means the results are from a different version of the
    source, and cannot be scored against this one.
    """
    known = tree_mutant_names()
    tested = 0
    killed = 0
    timed_out = 0
    orphans = 0
    other: Counter = Counter()
    for meta in MUTANTS.rglob("*.meta"):
        try:
            data = json.loads(meta.read_text())
        except (OSError, ValueError):
            continue
        for key, code in (data.get("exit_code_by_key") or {}).items():
            if code is None:
                continue
            if known and key.split(".")[-1] not in known:
                orphans += 1
                continue
            tested += 1
            if code == 0:
                continue  # survived
            if code == PYTEST_FAILED:
                killed += 1
            elif code in TIMEOUT_CODES:
                timed_out += 1
            else:
                other[code] += 1
    return tested, killed, timed_out, other, orphans


def survivors() -> list[str]:
    """The mutants the test suite failed to kill, as mutmut reports them."""
    result = subprocess.run(
        [str(ROOT / ".venv" / "bin" / "mutmut"), "results"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return [
        line.split(":")[0].strip()
        for line in result.stdout.splitlines()
        if "survived" in line
    ]


def stale_results() -> list[tuple[str, list[str]]]:
    """Recorded results that belong to a different version of the source.

    mutmut records a hash of every function it mutated. If the source has
    changed since the run, the hashes no longer match and the verdicts
    describe mutations of code that is no longer there. Two runs sharing
    the ``mutants/`` directory can produce exactly that, and the mutant
    *names* are the same in both, so only the hashes reveal it.
    """
    try:
        from mutmut.mutation.file_mutation import compute_function_hashes
    except ImportError:  # pragma: no cover - mutmut is always present here
        return []

    stale: list[tuple[str, list[str]]] = []
    for meta_path in sorted(MUTANTS.rglob("*.meta")):
        relative = meta_path.relative_to(MUTANTS)
        source_path = ROOT / "src" / relative.with_suffix("")
        if not source_path.exists():
            continue
        try:
            data = json.loads(meta_path.read_text())
        except (OSError, ValueError):
            continue
        recorded = data.get("hash_by_function_name") or {}
        if not recorded:
            continue
        try:
            current = compute_function_hashes(source_path.read_text())
        except SyntaxError:
            continue
        differing = [key for key, value in recorded.items() if current.get(key) != value]
        if differing:
            stale.append((str(relative), differing))
    return stale


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-score", type=float, default=80.0, help="minimum score, 0-100")
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = parser.parse_args()

    total = total_mutants()
    if total == 0:
        print("no mutants found - run `mutmut run` first", file=sys.stderr)
        return 2

    tested, killed, timed_out, other, orphans = recorded_results()
    stale = stale_results()
    if stale:
        detail = ", ".join(f"{name} ({len(keys)} functions)" for name, keys in stale[:5])
        message = (
            f"mutation results are STALE: {len(stale)} modules were mutated from a "
            f"different version of the source ({detail}). The source has changed "
            "since the run. Delete mutants/ and run again."
        )
        if args.json:
            print(json.dumps({"complete": False, "total": total, "stale": [s[0] for s in stale]}))
        else:
            print(message)
        print(message, file=sys.stderr)
        return 2
    if orphans:
        message = (
            f"mutation results do not match the source: {orphans} recorded results "
            "are for mutants that are not in this tree. Two runs shared the "
            "mutants/ directory. Delete mutants/ and run again."
        )
        if args.json:
            print(json.dumps({"complete": False, "total": total, "orphans": orphans}))
        else:
            print(message)
        print(message, file=sys.stderr)
        return 2
    if tested < total:
        message = (
            f"mutation run is INCOMPLETE: {tested}/{total} mutants have a result. "
            "A partial run is not a score."
        )
        if args.json:
            print(json.dumps({"complete": False, "total": total, "tested": tested, "killed": killed}))
        else:
            print(message)
        print(message, file=sys.stderr)
        return 2

    alive = survivors()
    score = (killed / total) * 100.0

    if args.json:
        print(
            json.dumps(
                {
                    "complete": True,
                    "total": total,
                    "killed": killed,
                    "survivors": len(alive),
                    "timed_out": timed_out,
                    "other": dict(other),
                    "score": round(score, 2),
                }
            )
        )
    else:
        print(f"mutation score: {score:.2f}%  ({killed}/{total} killed, {len(alive)} survived)")
        if timed_out:
            print(f"  {timed_out} timed out - not counted as kills")
        if other:
            print(f"  {sum(other.values())} ended with an unusual exit code: {dict(other)}")
        if alive:
            by_function: dict[str, int] = {}
            for name in alive:
                key = re.sub(r"__mutmut_\d+$", "", name.split(".")[-1])
                by_function[key] = by_function.get(key, 0) + 1
            print("worst offenders:")
            for key, count in sorted(by_function.items(), key=lambda item: -item[1])[:15]:
                print(f"  {count:4d}  {key}")

    if score < args.min_score:
        print(
            f"FAIL: mutation score {score:.2f}% is below the {args.min_score:.2f}% floor",
            file=sys.stderr,
        )
        return 1
    print(f"PASS: mutation score {score:.2f}% meets the {args.min_score:.2f}% floor")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
