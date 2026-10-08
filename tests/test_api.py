def test_predict_returns_labels_and_version(client):
    texts = ["a superb and moving film", "dull, tedious plot"]
    response = client.post("/predict", json={"texts": texts})
    assert response.status_code == 200
    body = response.json()
    assert [p["label"] for p in body["predictions"]] == ["positive", "negative"]
    assert body["model_version"]


def test_rejects_empty_and_oversized_batches(client):
    assert client.post("/predict", json={"texts": []}).status_code == 422
    assert client.post("/predict", json={"texts": ["x"] * 65}).status_code == 422


def test_probes(client):
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").json()["status"] == "ready"


def test_metrics_expose_latency_predictions_and_drift(client):
    for _ in range(5):
        client.post("/predict", json={"texts": ["great film"] * 4})
    text = client.get("/metrics").text
    for name in [
        "ml_api_inference_seconds_bucket",
        'ml_api_predictions_total{label="positive"}',
        'ml_api_requests_total{path="/predict",status="200"}',
        "ml_api_model_info",
        'ml_api_feature_drift_psi{feature="text_length"}',
    ]:
        assert name in text, name
