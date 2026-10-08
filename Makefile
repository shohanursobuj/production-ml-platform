PY ?= .venv/bin/python
export PYTHONPATH := src

.PHONY: install test lint train gate serve loadgen drift-demo up down helm-rules helm-lint tf-validate

install:            ## create venv with dev dependencies
	python3 -m venv .venv && .venv/bin/pip install -r requirements/dev.txt

test:               ## unit + API tests (offline, synthetic data)
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check . && $(PY) -m ruff format --check .

train:              ## train on Rotten Tomatoes, write artifacts/
	$(PY) -m mlplatform.train

gate:               ## evaluation gate vs. thresholds and current champion
	$(PY) -m mlplatform.evaluate --candidate artifacts/metrics.json --champion models/champion.json

serve:              ## run the API locally on :8080
	$(PY) -m uvicorn mlplatform.serve.app:app --port 8080

loadgen:            ## replay held-out reviews against the API
	$(PY) scripts/loadgen.py --url http://localhost:8080

drift-demo:         ## send shifted traffic; watch PSI climb in Grafana
	$(PY) scripts/loadgen.py --url http://localhost:8080 --drift

up:                 ## API + MLflow + Prometheus + Grafana (run `make train` first)
	docker compose up --build -d

down:
	docker compose down

helm-rules:         ## regenerate the Helm PrometheusRule from monitoring/alerts.yml
	$(PY) scripts/gen_helm_rules.py

helm-lint:
	helm lint deploy/helm/ml-api --strict
	helm lint deploy/helm/ml-api --strict --set canary.enabled=true,monitoring.serviceMonitor=true,monitoring.prometheusRule=true

tf-validate:
	cd infra/terraform && terraform fmt -check && terraform init -backend=false -input=false && terraform validate
