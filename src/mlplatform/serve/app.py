"""Inference API.

Endpoints
  POST /predict  batch sentiment prediction
  GET  /healthz  liveness  (process is up)
  GET  /readyz   readiness (model loaded) — gates traffic during rollouts
  GET  /metrics  Prometheus: latency, throughput, errors, prediction mix, drift PSI
"""

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from pydantic import BaseModel, Field

from mlplatform import config
from mlplatform.drift import DriftMonitor

log = logging.getLogger("mlplatform.serve")

LATENCY_BUCKETS = (0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)


class PredictRequest(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=64)


class Prediction(BaseModel):
    label: str
    score: float


class PredictResponse(BaseModel):
    model_version: str
    predictions: list[Prediction]


class Metrics:
    """Own registry per app instance so tests can build apps independently."""

    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self.requests = Counter(
            "ml_api_requests", "HTTP requests", ["path", "status"], registry=self.registry
        )
        self.latency = Histogram(
            "ml_api_inference_seconds",
            "Model inference latency per request",
            buckets=LATENCY_BUCKETS,
            registry=self.registry,
        )
        self.predictions = Counter(
            "ml_api_predictions", "Predictions by label", ["label"], registry=self.registry
        )
        self.model_info = Gauge(
            "ml_api_model_info", "Loaded model version", ["version"], registry=self.registry
        )
        self.drift = Gauge(
            "ml_api_feature_drift_psi",
            "PSI of live traffic vs. training reference",
            ["feature"],
            registry=self.registry,
        )


def create_app(model_path: Path | None = None) -> FastAPI:
    metrics = Metrics()
    state: dict = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        path = model_path or config.MODEL_PATH
        artifact = joblib.load(path)
        state["pipeline"] = artifact["pipeline"]
        state["version"] = artifact["version"]
        state["drift"] = DriftMonitor(
            artifact["reference"], config.DRIFT_WINDOW, config.DRIFT_MIN_SAMPLES
        )
        metrics.model_info.labels(version=artifact["version"]).set(1)
        log.info("loaded model %s from %s", artifact["version"], path)
        yield
        state.clear()

    app = FastAPI(title="Sentiment inference API", lifespan=lifespan)

    @app.middleware("http")
    async def count_requests(request: Request, call_next):
        response = await call_next(request)
        if request.url.path != "/metrics":
            metrics.requests.labels(request.url.path, str(response.status_code)).inc()
        return response

    @app.post("/predict", response_model=PredictResponse)
    def predict(body: PredictRequest) -> PredictResponse:
        if "pipeline" not in state:
            raise HTTPException(503, "model not loaded")
        start = time.perf_counter()
        proba = state["pipeline"].predict_proba(body.texts)[:, 1]
        metrics.latency.observe(time.perf_counter() - start)

        predictions = []
        for p in proba:
            label = "positive" if p >= 0.5 else "negative"
            metrics.predictions.labels(label).inc()
            predictions.append(Prediction(label=label, score=round(float(p), 4)))

        state["drift"].observe(body.texts, proba)
        if scores := state["drift"].scores():
            for feature, value in scores.items():
                metrics.drift.labels(feature).set(value)

        return PredictResponse(model_version=state["version"], predictions=predictions)

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict:
        if "pipeline" not in state:
            raise HTTPException(503, "model not loaded")
        return {"status": "ready", "model_version": state["version"]}

    @app.get("/metrics")
    def prometheus_metrics() -> Response:
        return Response(generate_latest(metrics.registry), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
