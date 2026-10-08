# Inference image. The trained artifact is baked in so an image tag == an exact model version:
# rollbacks are a tag change, and there is no model download on cold start.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src \
    MODEL_PATH=/app/artifacts/model.joblib

WORKDIR /app
COPY requirements/serve.txt requirements/serve.txt
RUN pip install -r requirements/serve.txt

COPY src/ src/
COPY artifacts/model.joblib artifacts/model.joblib

RUN useradd --uid 10001 --no-create-home app
USER 10001
EXPOSE 8080

CMD ["uvicorn", "mlplatform.serve.app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
