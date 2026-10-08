"""Train the sentiment model and write a self-describing artifact.

The artifact bundles the sklearn pipeline, a version string, and the drift reference
profile, so the serving image needs nothing else to run and monitor itself.
"""

import argparse
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.pipeline import Pipeline

from mlplatform import drift
from mlplatform.config import ARTIFACT_DIR

# Chosen by a small sweep on the validation split; the gate scores on the held-out test split.
PARAMS = {"ngram_range": (1, 2), "min_df": 1, "C": 8.0}


def build_pipeline(params: dict = PARAMS) -> Pipeline:
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=params["ngram_range"], min_df=params["min_df"], sublinear_tf=True
                ),
            ),
            ("clf", LogisticRegression(C=params["C"], max_iter=1000)),
        ]
    )


def single_request_latency_ms(pipeline: Pipeline, texts, n: int = 200) -> float:
    """p95 latency of one-text predictions — what a single API request actually pays."""
    timings = []
    for text in list(texts)[:n]:
        start = time.perf_counter()
        pipeline.predict_proba([text])
        timings.append((time.perf_counter() - start) * 1000)
    return float(np.percentile(timings, 95))


def model_version() -> str:
    sha = (os.getenv("GIT_SHA") or "local")[:7]
    return f"{datetime.now(UTC):%Y%m%d%H%M}-{sha}"


def train(train_df, eval_df, out_dir: Path = ARTIFACT_DIR) -> dict:
    pipeline = build_pipeline()
    pipeline.fit(train_df["text"], train_df["label"])

    proba = pipeline.predict_proba(eval_df["text"])[:, 1]
    preds = (proba >= 0.5).astype(int)
    version = model_version()
    metrics = {
        "model_version": version,
        "accuracy": round(accuracy_score(eval_df["label"], preds), 4),
        "f1": round(f1_score(eval_df["label"], preds), 4),
        "roc_auc": round(roc_auc_score(eval_df["label"], proba), 4),
        "latency_ms_p95": round(single_request_latency_ms(pipeline, eval_df["text"]), 3),
        "n_train": len(train_df),
        "n_eval": len(eval_df),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "pipeline": pipeline,
            "version": version,
            "reference": drift.reference_profile(eval_df["text"], proba),
        },
        out_dir / "model.joblib",
    )
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    log_to_mlflow(metrics, out_dir)
    return metrics


def log_to_mlflow(metrics: dict, out_dir: Path) -> None:
    """Track the run in MLflow when a tracking server is configured (e.g. `make up`)."""
    if not os.getenv("MLFLOW_TRACKING_URI"):
        return
    import mlflow

    mlflow.set_experiment("sentiment")
    with mlflow.start_run(run_name=metrics["model_version"]):
        mlflow.log_params({k: str(v) for k, v in PARAMS.items()})
        mlflow.log_metrics({k: v for k, v in metrics.items() if isinstance(v, float)})
        mlflow.log_artifacts(str(out_dir))


def main() -> None:
    from mlplatform.data import load_split

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ARTIFACT_DIR)
    args = parser.parse_args()

    metrics = train(load_split("train"), load_split("test"), args.out)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
