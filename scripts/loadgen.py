"""Send traffic to the API. `--drift` sends inputs unlike the training data so you can watch
ml_api_feature_drift_psi climb in Grafana and the FeatureDrift alert fire.

    PYTHONPATH=src python scripts/loadgen.py --url http://localhost:8080
    PYTHONPATH=src python scripts/loadgen.py --url http://localhost:8080 --drift
"""

import argparse
import json
import random
import urllib.request

from mlplatform.data import load_split


def drifted(text: str) -> str:
    """Simulate an upstream change: clients start sending whole pasted documents."""
    return " ".join([text] * 3)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8080")
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--drift", action="store_true")
    args = parser.parse_args()

    texts = load_split("test")["text"].tolist()  # held-out reviews: same distribution as training
    for i in range(args.requests):
        batch = random.sample(texts, args.batch)
        if args.drift:
            batch = [drifted(t) for t in batch]
        request = urllib.request.Request(
            f"{args.url}/predict",
            data=json.dumps({"texts": batch}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            if i == 0:
                print(response.read().decode())
    print(f"sent {args.requests} requests")


if __name__ == "__main__":
    main()
