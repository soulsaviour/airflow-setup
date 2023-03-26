#!/usr/bin/env bash
# Installs or upgrades Airflow with the pinned chart version.
#   scripts/install.sh                          # helm/values.yaml
#   VALUES=helm/values-local.yaml scripts/install.sh
set -euo pipefail

CHART_VERSION=1.22.0
NAMESPACE=${NAMESPACE:-airflow}
VALUES=${VALUES:-helm/values.yaml}

helm repo add apache-airflow https://airflow.apache.org --force-update >/dev/null
helm upgrade --install airflow apache-airflow/airflow \
  --version "$CHART_VERSION" \
  --namespace "$NAMESPACE" --create-namespace \
  -f "$VALUES" \
  --timeout 15m --wait "$@"
