"""Regenerate the Helm PrometheusRule from monitoring/alerts.yml so both alert sets match."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEADER = """{{- if .Values.monitoring.prometheusRule }}
# Generated from monitoring/alerts.yml (make helm-rules). Do not edit by hand.
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: {{ include "ml-api.fullname" . }}
  labels:
    {{- include "ml-api.labels" . | nindent 4 }}
spec:
  groups:"""


def main() -> None:
    body = (ROOT / "monitoring/alerts.yml").read_text().split("groups:", 1)[1]
    # Escape Prometheus templating ({{ $value }}) so Helm passes it through untouched.
    body = re.sub(r"\{\{(.*?)\}\}", lambda m: '{{ "{{" }}' + m.group(1) + '{{ "}}" }}', body)
    indented = "\n".join(("  " + line) if line.strip() else line for line in body.splitlines())
    out = ROOT / "deploy/helm/ml-api/templates/prometheusrule.yaml"
    out.write_text(HEADER + indented + "\n{{- end }}\n")


if __name__ == "__main__":
    main()
