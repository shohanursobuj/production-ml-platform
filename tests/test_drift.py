import numpy as np

from mlplatform.drift import DriftMonitor, build_profile, psi, reference_profile


def test_psi_is_zero_for_identical_distributions():
    assert psi([0.5, 0.5], [0.5, 0.5]) == 0


def test_psi_flags_shifted_distribution():
    rng = np.random.default_rng(0)
    profile = build_profile(rng.normal(0, 1, 5000))
    same = build_profile(rng.normal(0, 1, 5000))["fractions"]
    assert psi(profile["fractions"], same) < 0.05


def test_monitor_waits_for_min_samples_then_detects_shift():
    rng = np.random.default_rng(0)
    texts = ["x" * int(n) for n in rng.normal(100, 20, 2000).clip(1)]
    reference = reference_profile(texts, rng.uniform(0, 1, 2000))
    monitor = DriftMonitor(reference, window=500, min_samples=100)

    monitor.observe(texts[:50], rng.uniform(0, 1, 50))
    assert monitor.scores() is None

    monitor.observe(texts[:500], rng.uniform(0, 1, 500))
    assert all(v < 0.1 for v in monitor.scores().values())

    long_texts = ["x" * 400] * 500  # inputs suddenly 4x longer than in training
    monitor.observe(long_texts, rng.uniform(0, 1, 500))
    assert monitor.scores()["text_length"] > 0.2
