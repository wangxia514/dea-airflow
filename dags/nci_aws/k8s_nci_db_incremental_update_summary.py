"""## DEA NCI prod database - Daily DAG to summarize datacube using incremental update-summary

This updates the Datacube Explorer summary extents of the NCI Datacube DB.
This is used by [Dev NCI Explorer](https://explorer-nci.dev.dea.ga.gov.au/)
and [Resto](https://github.com/jjrom/resto).

**Upstream dependency**
[K8s NCI DB Incremental Sync](/tree?dag_id=k8ds_nci_db_incremental_sync)
"""

import pendulum
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from airflow.kubernetes.secret import Secret
from airflow.operators.dummy_operator import DummyOperator
from datetime import datetime, timedelta
from infra.podconfig import ONDEMAND_NODE_AFFINITY
from infra.images import EXPLORER_UNSTABLE_IMAGE, EXPLORER_IMAGE
from infra.variables import DB_HOSTNAME, DB_PORT, SECRET_EXPLORER_NCI_WRITER_NAME
from infra.variables import AWS_DEFAULT_REGION

local_tz = pendulum.timezone("Australia/Canberra")

# Templated DAG arguments
DEFAULT_ARGS = {
    "owner": "Nikita Gandhi",
    "depends_on_past": False,
    "start_date": datetime(2020, 10, 3, tzinfo=local_tz),
    "email": ["nikita.gandhi@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "env_vars": {
        "AWS_DEFAULT_REGION": AWS_DEFAULT_REGION,
        "DB_HOSTNAME": DB_HOSTNAME,
        "DB_PORT": DB_PORT,
    },
    # Use K8S secrets to send DB Creds
    # Lift secrets into environment variables for datacube database connectivity
    # Use this db-users to run cubedash update-summary
    "secrets": [
        Secret("env", "DB_DATABASE", SECRET_EXPLORER_NCI_WRITER_NAME, "database-name"),
        Secret("env", "DB_USERNAME", SECRET_EXPLORER_NCI_WRITER_NAME, "postgres-username"),
        Secret("env", "DB_PASSWORD", SECRET_EXPLORER_NCI_WRITER_NAME, "postgres-password"),
    ],
}

dag = DAG(
    "k8s_nci_db_incremental_update_summary",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    catchup=False,
    concurrency=1,
    max_active_runs=1,
    tags=["k8s", "nci-explorer"],
    schedule_interval="45 1 * * *",    # every day 1:45AM
)

affinity = ONDEMAND_NODE_AFFINITY

with dag:
    START = DummyOperator(task_id="start")

    # Run update summary
    UPDATE_SUMMARY = KubernetesPodOperator(
        namespace="processing",
        image=EXPLORER_IMAGE,
        # Run `cubedash-gen --help` for explanations of each option+usage
        cmds=["cubedash-gen"],
        arguments=["--no-init-database", "--refresh-stats", "--minimum-scan-window", "4d", "--all"],
        labels={"step": "nci-db-incremental-update-summary"},
        name="nci-db-incremental-update-summary",
        task_id="nci-db-incremental-update-summary",
        get_logs=True,
        is_delete_operator_pod=True,
        affinity=affinity,
        # execution_timeout=timedelta(days=1),
    )

    # Task complete
    COMPLETE = DummyOperator(task_id="done")


    START >> UPDATE_SUMMARY
    UPDATE_SUMMARY >> COMPLETE
