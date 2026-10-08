import os
from pathlib import Path

ARTIFACT_DIR = Path(os.getenv("ARTIFACT_DIR", "artifacts"))
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
MODEL_PATH = Path(os.getenv("MODEL_PATH", ARTIFACT_DIR / "model.joblib"))

# Drift monitoring: PSI is computed over a rolling window of recent requests.
DRIFT_WINDOW = int(os.getenv("DRIFT_WINDOW", "500"))
DRIFT_MIN_SAMPLES = int(os.getenv("DRIFT_MIN_SAMPLES", "100"))
