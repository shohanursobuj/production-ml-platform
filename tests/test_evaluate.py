from mlplatform.evaluate import gate

GOOD = {"accuracy": 0.79, "roc_auc": 0.88, "latency_ms_p95": 0.4}


def test_good_candidate_passes():
    assert gate(GOOD) == []


def test_floor_and_latency_ceiling_block():
    failures = gate({**GOOD, "accuracy": 0.60, "latency_ms_p95": 50.0})
    assert len(failures) == 2


def test_regression_against_champion_blocks():
    champion = {**GOOD, "accuracy": 0.82}
    assert any("regresses champion" in f for f in gate(GOOD, champion))


def test_small_noise_against_champion_is_tolerated():
    champion = {**GOOD, "accuracy": 0.795}
    assert gate(GOOD, champion) == []
