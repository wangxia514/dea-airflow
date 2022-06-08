"""
DEA Waterbodies processing using Conflux schedule run.

This DAG will call another waterbodies processing DAG every day.

"""


from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

DEFAULT_ARGS = {
    "owner": "Sai Ma",
    "depends_on_past": False,
    "start_date": datetime(2021, 6, 2),
    "email": ["sai.ma@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "startup_timeout_seconds": 5 * 60
}


# THE DAG
dag = DAG(
    "k8s_waterbodies_conflux_schedule_run",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=timedelta(minutes=15),
    catchup=False,
    concurrency=128,
    tags=["k8s", "landsat", "waterbodies", "conflux", "Work In Progress"],
)

with dag:
    trigger = TriggerDagRunOperator(
        task_id="k8s_waterbodies_conflux_schedule_run",
        trigger_dag_id="k8s_waterbodies_conflux_dev",
        dag=dag,
    )