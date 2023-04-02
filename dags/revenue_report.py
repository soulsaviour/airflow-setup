"""Weekly revenue report, refreshed whenever orders_daily updates daily_revenue.

Scheduled on the daily_revenue asset rather than a clock, so it runs as soon
as fresh data lands and never against a half-loaded day.
"""

import pendulum
from airflow.sdk import Variable, dag, task

from orders_lib.assets import DAILY_REVENUE
from orders_lib.report import render_report

QUERY = """
    SELECT region, SUM(orders), SUM(revenue)
    FROM daily_revenue
    WHERE day > current_date - 7
    GROUP BY region
    ORDER BY SUM(revenue) DESC
"""


@dag(
    schedule=[DAILY_REVENUE],
    start_date=pendulum.datetime(2026, 10, 1, tz="UTC"),
    catchup=False,
    tags=["orders", "reporting"],
)
def revenue_report():
    @task
    def build_report() -> str:
        from airflow.providers.postgres.hooks.postgres import PostgresHook

        rows = PostgresHook(postgres_conn_id="analytics").get_records(QUERY)
        return render_report(rows, generated_on=pendulum.now("UTC").to_date_string())

    @task
    def publish(report: str) -> None:
        from airflow.providers.amazon.aws.hooks.s3 import S3Hook

        today = pendulum.now("UTC").to_date_string()
        S3Hook(aws_conn_id="aws_default").load_string(
            report,
            key=f"reports/revenue-{today}.md",
            bucket_name=Variable.get("reports_bucket"),
            replace=True,
        )

    publish(build_report())


revenue_report()
