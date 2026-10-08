"""Input / output drift detection with the Population Stability Index (PSI).

At training time we store a reference profile (quantile bins + bin fractions) for each
monitored feature. At serving time a rolling window of live values is binned the same way
and compared against the reference. Rule of thumb: PSI < 0.1 stable, 0.1–0.2 moderate,
> 0.2 significant shift worth a retrain.
"""

from collections import deque

import numpy as np

N_BINS = 10
EPS = 1e-4


def features(texts, proba) -> dict[str, np.ndarray]:
    """Monitored features: input length (data drift) and positive score (prediction drift)."""
    return {
        "text_length": np.array([len(t) for t in texts], dtype=float),
        "positive_score": np.asarray(proba, dtype=float),
    }


def _fractions(values: np.ndarray, edges: list[float]) -> np.ndarray:
    counts = np.bincount(np.searchsorted(edges, values, side="right"), minlength=len(edges) + 1)
    return counts / max(len(values), 1)


def build_profile(values: np.ndarray, n_bins: int = N_BINS) -> dict:
    edges = np.unique(np.quantile(values, np.linspace(0, 1, n_bins + 1)[1:-1])).tolist()
    return {"edges": edges, "fractions": _fractions(values, edges).tolist()}


def reference_profile(texts, proba) -> dict[str, dict]:
    return {name: build_profile(values) for name, values in features(texts, proba).items()}


def psi(reference: np.ndarray, current: np.ndarray) -> float:
    reference = np.clip(np.asarray(reference, dtype=float), EPS, None)
    current = np.clip(np.asarray(current, dtype=float), EPS, None)
    return float(np.sum((current - reference) * np.log(current / reference)))


class DriftMonitor:
    """Keeps a rolling window of live feature values and scores them against the reference."""

    def __init__(self, reference: dict[str, dict], window: int, min_samples: int):
        self.reference = reference
        self.min_samples = min_samples
        self.values = {name: deque(maxlen=window) for name in reference}

    def observe(self, texts, proba) -> None:
        for name, values in features(texts, proba).items():
            self.values[name].extend(values.tolist())

    def scores(self) -> dict[str, float] | None:
        """PSI per feature, or None until the window holds enough samples to be meaningful."""
        if min(len(v) for v in self.values.values()) < self.min_samples:
            return None
        return {
            name: psi(ref["fractions"], _fractions(np.array(self.values[name]), ref["edges"]))
            for name, ref in self.reference.items()
        }
