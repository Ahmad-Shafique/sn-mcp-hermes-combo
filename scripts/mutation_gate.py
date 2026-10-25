#!/usr/bin/env python3
"""The mutation gate: compute the score and fail below a threshold.

``mutmut results`` lists the survivors. The total comes from the mutated
source tree, which holds one copy of every mutant it generated.

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


def survivors() -> list[str]:
    """The mutants the test suite failed to kill."""
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

    alive = survivors()
    killed = total - len(alive)
    score = (killed / total) * 100.0

    if args.json:
        print(json.dumps({"total": total, "killed": killed, "survivors": len(alive), "score": round(score, 2)}))
    else:
        print(f"mutation score: {score:.2f}%  ({killed}/{total} killed, {len(alive)} survived)")
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
