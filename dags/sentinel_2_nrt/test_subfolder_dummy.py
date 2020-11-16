"""
Fetch wagl NRT ancillary.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.operators.dummy_operator import DummyOperator



default_args = {
    "owner": "Pin Jin",
    "depends_on_past": False,
    "start_date": datetime(2020, 9, 28),
    "email": ["pin.jin@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=30),
}

pipeline = DAG(
    "subdir_test",
    doc_md=__doc__,
    default_args=default_args,
    description="testing dagbag",
    concurrency=1,
    max_active_runs=1,
    catchup=False,
    params={},
    schedule_interval=None,
    tags=["dag bag"],
)

with pipeline:

    START = DummyOperator(task_id="start")
