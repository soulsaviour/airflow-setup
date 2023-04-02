"""Loads the DAG folder the way Airflow does and checks the result.

Needs Airflow installed (CI installs it); skipped otherwise.
"""

from pathlib import Path

import pytest

pytest.importorskip("airflow")
from airflow.dag_processing.dagbag import DagBag  # noqa: E402

DAGS = Path(__file__).parent.parent / "dags"


@pytest.fixture(scope="module")
def dagbag():
    return DagBag(dag_folder=str(DAGS), include_examples=False)


def test_no_import_errors(dagbag):
    assert dagbag.import_errors == {}


def test_expected_dags(dagbag):
    assert set(dagbag.dag_ids) == {"orders_daily", "revenue_report"}


def test_orders_daily(dagbag):
    dag = dagbag.dags["orders_daily"]
    assert dag.catchup is False
    assert dag.max_active_runs == 1
    assert sorted(dag.task_ids) == ["load", "summarise_orders"]
    assert dag.get_task("load").upstream_task_ids == {"summarise_orders"}
    assert all(task.retries == 2 for task in dag.tasks)
    outlets = [asset.uri for asset in dag.get_task("load").outlets]
    assert outlets == ["postgres://analytics/public/daily_revenue"]


def test_revenue_report_waits_for_daily_revenue(dagbag):
    dag = dagbag.dags["revenue_report"]
    assert type(dag.timetable).__name__ == "AssetTriggeredTimetable"
    assert dag.get_task("publish").upstream_task_ids == {"build_report"}


def test_every_dag_has_tags_and_no_catchup(dagbag):
    for dag in dagbag.dags.values():
        assert dag.tags, f"{dag.dag_id} has no tags"
        assert dag.catchup is False, f"{dag.dag_id} would backfill on deploy"
