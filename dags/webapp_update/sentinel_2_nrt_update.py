"""
# Sentinel-2_nrt update views automation

This DAG uses k8s executors and in cluster with relevant tooling
and configuration installed.
"""

from airflow import DAG
from datetime import datetime, timedelta

from airflow.kubernetes.secret import Secret
from subdags.subdag_ows_views import ows_update_operator
from subdags.subdag_explorer_summary import explorer_refresh_operator
from infra.variables import (
    DB_DATABASE,
    DB_HOSTNAME,
    AWS_DEFAULT_REGION,
)

DAG_NAME = "webapp_update"

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
        "DB_HOSTNAME": DB_HOSTNAME,
        "DB_DATABASE": DB_DATABASE,
        "AWS_DEFAULT_REGION": AWS_DEFAULT_REGION,
    },
}


# THE DAG
dag = DAG(
    dag_id=DAG_NAME,
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval="0 */6 * * *",  # every 6 hours
    catchup=False,
    tags=["k8s", "ows-update", "explorer-update"],
)


with dag:

    OWS_UPDATE_EXTENTS = ows_update_operator(dag=dag)

    EXPLORER_SUMMARY = explorer_refresh_operator()
