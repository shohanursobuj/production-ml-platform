"""Screenshot the running stack (Grafana, Prometheus, MLflow, CI) for the README.

Expects `docker compose up` plus a drift demo to have run; used by
.github/workflows/evidence.yml. Writes PNGs and the raw alert state to --out.
"""

import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

GRAFANA = "http://localhost:3000"
PROMETHEUS = "http://localhost:9090"
MLFLOW = "http://localhost:5000"
VIEWPORT = {"width": 1600, "height": 1000}


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def latest_mlflow_run() -> tuple[str, str]:
    experiment = get_json(
        f"{MLFLOW}/api/2.0/mlflow/experiments/get-by-name?experiment_name=sentiment"
    )["experiment"]
    request = urllib.request.Request(
        f"{MLFLOW}/api/2.0/mlflow/runs/search",
        data=json.dumps(
            {"experiment_ids": [experiment["experiment_id"]], "max_results": 1}
        ).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        run = json.load(response)["runs"][0]
    return experiment["experiment_id"], run["info"]["run_id"]


def shoot(page: Page, url: str, path: Path, wait_ms: int = 8000, full_page: bool = False) -> None:
    page.goto(url, wait_until="load", timeout=60_000)
    page.wait_for_timeout(wait_ms)
    page.screenshot(path=str(path), full_page=full_page)
    print(f"saved {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("evidence"))
    parser.add_argument("--ci-run-url", help="public URL of a green ci workflow run")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    alerts = get_json(f"{PROMETHEUS}/api/v1/alerts")["data"]["alerts"]
    (args.out / "alerts.json").write_text(json.dumps(alerts, indent=2) + "\n")

    psi_graph = f"{PROMETHEUS}/query?" + urllib.parse.urlencode(
        {"g0.expr": "ml_api_feature_drift_psi", "g0.tab": "graph", "g0.range_input": "30m"}
    )
    experiment_id, run_id = latest_mlflow_run()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)

        shoot(
            page,
            f"{GRAFANA}/d/ml-api/?orgId=1&from=now-30m&to=now&kiosk",
            args.out / "grafana-dashboard.png",
            wait_ms=12000,
        )

        page.goto(f"{PROMETHEUS}/alerts", wait_until="load")
        page.wait_for_timeout(3000)
        rule = page.get_by_text("FeatureDrift", exact=True).first
        if rule.count():
            rule.click()  # expand the rule to show the firing instance and its labels
            page.wait_for_timeout(1500)
        page.screenshot(path=str(args.out / "prometheus-alerts.png"), full_page=True)
        print(f"saved {args.out / 'prometheus-alerts.png'}")

        shoot(page, psi_graph, args.out / "prometheus-drift-psi.png", wait_ms=5000)
        shoot(
            page,
            f"{MLFLOW}/#/experiments/{experiment_id}/runs/{run_id}",
            args.out / "mlflow-run.png",
            wait_ms=8000,
        )
        if args.ci_run_url:
            shoot(page, args.ci_run_url, args.out / "ci-pipeline.png", wait_ms=6000)

        browser.close()


if __name__ == "__main__":
    main()
