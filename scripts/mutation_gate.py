#!/usr/bin/env python3
"""The mutation gate: compute the score and fail below a threshold.

A mutant is *killed* when the test suite fails against it, and *survived*
when the suite still passes - which means the mutant is a change no test
noticed.

The score is computed from mutmut's own recorded results, not from a
count-minus-survivors guess, so an unfinished run can never be mistaken for
a perfect one.

Usage:
    python scripts/mutation_gate.py [--min-score 80] [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MUTANTS = ROOT / "mutants" / "src"

# A mutant definition looks like: def xǁClassǁmethod__mutmut_3(self, ...)
MUTANT_DEF = re.compile(r"^\s*def x.+__mutmut_\d+\(", re.M)


def total_mutants() -> int:
    """How many mutants mutmut generated."""
    if not MUTANTS.exists():
        return 0
    total = 0
    for path in MUTANTS.rglob("*.py"):
        total += len(MUTANT_DEF.findall(path.read_text()))
    return total


def recorded_results() -> tuple[int, int]:
    """How many mutants have a result, and how many of those were killed.

    mutmut records each mutant's pytest exit code in the ``.meta`` file
    beside the mutated module: ``None`` means it has not been run yet,
    ``0`` means the tests still passed (the mutant SURVIVED), anything else
    means the tests failed (the mutant was KILLED).
    """
    tested = 0
    killed = 0
    for meta in MUTANTS.rglob("*.meta"):
        try:
            data = json.loads(meta.read_text())
        except (OSError, ValueError):
            continue
        for code in (data.get("exit_code_by_key") or {}).values():
            if code is None:
                continue
            tested += 1
            if code != 0:
                killed += 1
    return tested, killed


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-score", type=float, default=80.0, help="minimum score, 0-100")
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = parser.parse_args()

    total = total_mutants()
    if total == 0:
        print("no mutants found - run `mutmut run` first", file=sys.stderr)
        return 2

    tested, killed = recorded_results()
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
    score = (killed / tested) * 100.0

    if args.json:
        print(
            json.dumps(
                {
                    "complete": True,
                    "total": total,
                    "killed": killed,
                    "survivors": len(alive),
                    "score": round(score, 2),
                }
            )
        )
    else:
        print(f"mutation score: {score:.2f}%  ({killed}/{tested} killed, {len(alive)} survived)")
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
