"""Evaluation gate: block promotion unless the candidate clears absolute thresholds
and does not regress against the current champion.

Exit code 0 = promote, 1 = block. Used by CI and by the retraining workflow.
"""

import argparse
import json
import sys
from pathlib import Path

# Floors / ceilings every candidate must meet regardless of the champion.
MIN = {"accuracy": 0.77, "roc_auc": 0.85}
MAX = {"latency_ms_p95": 10.0}
# How much worse than the champion a candidate may be on quality metrics.
MAX_REGRESSION = 0.01


def gate(candidate: dict, champion: dict | None = None) -> list[str]:
    failures = []
    for metric, floor in MIN.items():
        if candidate[metric] < floor:
            failures.append(f"{metric} {candidate[metric]} < floor {floor}")
    for metric, ceiling in MAX.items():
        if candidate[metric] > ceiling:
            failures.append(f"{metric} {candidate[metric]} > ceiling {ceiling}")
    if champion:
        for metric in MIN:
            if candidate[metric] < champion[metric] - MAX_REGRESSION:
                failures.append(
                    f"{metric} {candidate[metric]} regresses champion {champion[metric]} "
                    f"by more than {MAX_REGRESSION}"
                )
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, default=Path("artifacts/metrics.json"))
    parser.add_argument("--champion", type=Path, help="metrics.json of the model in production")
    args = parser.parse_args()

    candidate = json.loads(args.candidate.read_text())
    champion = json.loads(args.champion.read_text()) if args.champion else None

    print(f"{'metric':<16}{'candidate':>12}{'champion':>12}")
    for metric in [*MIN, *MAX]:
        print(f"{metric:<16}{candidate[metric]:>12}{(champion or {}).get(metric, '-'):>12}")

    failures = gate(candidate, champion)
    if failures:
        print("\nGATE FAILED:\n  " + "\n  ".join(failures))
        sys.exit(1)
    print("\nGATE PASSED")


if __name__ == "__main__":
    main()
