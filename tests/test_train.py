import json

import joblib


def test_training_writes_self_describing_artifact(trained):
    out, metrics = trained
    artifact = joblib.load(out / "model.joblib")
    assert set(artifact) == {"pipeline", "version", "reference"}
    assert set(artifact["reference"]) == {"text_length", "positive_score"}
    assert json.loads((out / "metrics.json").read_text()) == metrics


def test_model_learns_the_synthetic_task(trained):
    _, metrics = trained
    assert metrics["accuracy"] > 0.95
    assert metrics["latency_ms_p95"] > 0
