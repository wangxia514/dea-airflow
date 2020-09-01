"""
# Explorer cubedash-gen refresh-stats
"""

from airflow import DAG
from datetime import datetime, timedelta
from airflow.operators.dummy_operator import DummyOperator

from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.kubernetes.secret import Secret
from airflow.operators.subdag_operator import SubDagOperator
from sentinel_2_nrt.subdag_ows_views import ows_update_extent_subdag

from sentinel_2_nrt.env_cfg import DB_DATABASE, SECRET_EXPLORER_NAME, SECRET_AWS_NAME

DAG_NAME = "utility_ows-update-extent"

# DAG CONFIGURATION
DEFAULT_ARGS = {
    "owner": "Pin Jin",
    "depends_on_past": False,
    "start_date": datetime(2020, 6, 14),
    "email": ["pin.jin@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "env_vars": {
        # TODO: Pass these via templated params in DAG Run
        "DB_HOSTNAME": "db-writer",
        "DB_DATABASE": DB_DATABASE,
    },
    # Lift secrets into environment variables
    "secrets": [
        Secret("env", "AWS_DEFAULT_REGION", SECRET_AWS_NAME, "AWS_DEFAULT_REGION"),
    ],
}


# THE DAG
dag = DAG(
    dag_id=DAG_NAME,
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval="0 */1 * * *",
    catchup=False,
    tags=["k8s", "ows"],
)

with dag:
    OWS_UPDATE_EXTENTS = SubDagOperator(
        task_id="run-ows-update-ranges",
        subdag=ows_update_extent_subdag(DAG_NAME, "run-ows-update-ranges", DEFAULT_ARGS, "{{ dag_run.conf.products }}"),
    )

    START = DummyOperator(task_id="start_ows_update_ranges")

    COMPLETE = DummyOperator(task_id="all_done")

    START >> OWS_UPDATE_EXTENTS
    OWS_UPDATE_EXTENTS >> COMPLETE
