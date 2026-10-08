import random

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from mlplatform.serve.app import create_app
from mlplatform.train import train

POSITIVE = ["great", "wonderful", "brilliant", "moving", "delightful", "superb", "charming"]
NEGATIVE = ["awful", "boring", "dull", "terrible", "tedious", "clumsy", "lifeless"]
FILLER = ["the", "film", "plot", "acting", "was", "really", "story", "cast", "and"]


def _sentences(n: int, seed: int) -> pd.DataFrame:
    """Small synthetic sentiment dataset so tests run offline and in seconds."""
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        label = i % 2
        vocab = POSITIVE if label else NEGATIVE
        words = rng.sample(FILLER, 4) + rng.sample(vocab, 2)
        rng.shuffle(words)
        rows.append({"text": " ".join(words), "label": label})
    return pd.DataFrame(rows)


@pytest.fixture(scope="session")
def trained(tmp_path_factory):
    out = tmp_path_factory.mktemp("artifacts")
    metrics = train(_sentences(400, seed=1), _sentences(200, seed=2), out)
    return out, metrics


@pytest.fixture
def client(trained, monkeypatch):
    monkeypatch.setattr("mlplatform.config.DRIFT_MIN_SAMPLES", 10)
    out, _ = trained
    with TestClient(create_app(out / "model.joblib")) as c:
        yield c
