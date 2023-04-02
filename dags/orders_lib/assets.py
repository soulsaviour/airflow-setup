"""Assets shared between DAGs. Import them from here, never from another DAG
file: importing a DAG module defines its DAG a second time."""

from airflow.sdk import Asset

DAILY_REVENUE = Asset("postgres://analytics/public/daily_revenue")
