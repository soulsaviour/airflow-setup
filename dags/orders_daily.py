"""Daily revenue per region from the orders export in S3.

Reads s3://<orders_bucket>/orders/<date>.csv, keeps completed orders and
writes one row per region to daily_revenue in the analytics database.
Re-running a day replaces that day's rows, so retries and backfills are safe.
"""

import pendulum
from airflow.sdk import Asset, Variable, dag, task

from orders_lib.transform import parse_orders, summarise

DAILY_REVENUE = Asset("postgres://analytics/public/daily_revenue")


@dag(
    schedule="@daily",
    start_date=pendulum.datetime(2026, 10, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": pendulum.duration(minutes=5)},
    tags=["orders", "etl"],
)
def orders_daily():
    @task
    def summarise_orders(ds=None) -> dict:
        # Provider imports stay inside tasks so DAG parsing stays fast.
        from airflow.providers.amazon.aws.hooks.s3 import S3Hook

        csv_text = S3Hook(aws_conn_id="aws_default").read_key(
            key=f"orders/{ds}.csv", bucket_name=Variable.get("orders_bucket")
        )
        summary, rejected = summarise(parse_orders(csv_text))
        if not summary:
            raise ValueError(f"no completed orders in the export for {ds}")
        return {
            "rejected": rejected,
            "rows": [
                {"region": r.region, "orders": r.orders, "revenue": str(r.revenue)} for r in summary
            ],
        }

    @task(outlets=[DAILY_REVENUE])
    def load(result: dict, ds=None) -> None:
        from airflow.providers.postgres.hooks.postgres import PostgresHook

        rows = [(ds, r["region"], r["orders"], r["revenue"]) for r in result["rows"]]
        conn = PostgresHook(postgres_conn_id="analytics").get_conn()
        try:
            with conn, conn.cursor() as cur:
                cur.execute("DELETE FROM daily_revenue WHERE day = %s", (ds,))
                cur.executemany(
                    "INSERT INTO daily_revenue (day, region, orders, revenue)"
                    " VALUES (%s, %s, %s, %s)",
                    rows,
                )
        finally:
            conn.close()
        print(f"loaded {len(rows)} regions for {ds}, rejected {result['rejected']} rows")

    load(summarise_orders())


orders_daily()
