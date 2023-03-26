#!/usr/bin/env bash
# Creates the secrets helm/values.yaml expects. Run once per cluster; existing
# secrets are left alone so keys never change underneath Airflow.
#
#   METADATA_DB_URI='postgresql://airflow:...@db.example.com:5432/airflow' scripts/create-secrets.sh
set -euo pipefail

NAMESPACE=${NAMESPACE:-airflow}
: "${METADATA_DB_URI:?set METADATA_DB_URI to the metadata database connection URI}"

kubectl get namespace "$NAMESPACE" >/dev/null 2>&1 || kubectl create namespace "$NAMESPACE"

create() {
  local name=$1 key=$2 value=$3
  if kubectl -n "$NAMESPACE" get secret "$name" >/dev/null 2>&1; then
    echo "exists: $name"
  else
    kubectl -n "$NAMESPACE" create secret generic "$name" --from-literal="$key=$value" >/dev/null
    echo "created: $name"
  fi
}

random_key() { openssl rand -base64 32 | tr '+/' '-_'; }

create airflow-metadata-db connection "$METADATA_DB_URI"
create airflow-fernet-key fernet-key "$(random_key)"
create airflow-api-secret-key api-secret-key "$(random_key)"
create airflow-jwt-secret jwt-secret "$(random_key)"
create airflow-webserver-secret-key webserver-secret-key "$(random_key)"
