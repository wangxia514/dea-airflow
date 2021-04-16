"""## DEA NCI prod database - Daily DAG to summarize datacube using incremental update-summary

This updates the Datacube Explorer summary extents of the NCI Datacube DB.
This is used by [NCI Explorer](https://explorer.dea.ga.gov.au/)
and [Resto](https://github.com/jjrom/resto).

**Upstream dependency**
[K8s NCI DB Incremental Sync](/tree?dag_id=k8ds_nci_db_incremental_sync)
"""

import pendulum
from airflow import DAG
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.kubernetes.secret import Secret
from airflow.operators.dummy_operator import DummyOperator
from datetime import datetime, timedelta
from infra.podconfig import ONDEMAND_NODE_AFFINITY
from infra.images import EXPLORER_UNSTABLE_IMAGE, EXPLORER_IMAGE

local_tz = pendulum.timezone("Australia/Canberra")

# Templated DAG arguments
DB_HOSTNAME = "db-writer"

DEFAULT_ARGS = {
    "owner": "Nikita Gandhi",
    "depends_on_past": False,
    "start_date": datetime(2021, 3, 30, tzinfo=local_tz),
    "email": ["nikita.gandhi@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "env_vars": {
        "AWS_DEFAULT_REGION": "ap-southeast-2",
        "DB_HOSTNAME": DB_HOSTNAME,
        "DB_PORT": "5432",
    },
    # Use K8S secrets to send DB Creds
    # Lift secrets into environment variables for datacube database connectivity
    # Use this db-users to run cubedash update-summary
    "secrets": [
        Secret("env", "DB_DATABASE", "explorer-nci-writer", "database-name"),
        Secret("env", "DB_USERNAME", "explorer-nci-writer", "postgres-username"),
        Secret("env", "DB_PASSWORD", "explorer-nci-writer", "postgres-password"),
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
        arguments=["-v", "--no-init-database", "--refresh-stats", "--minimum-scan-window", "4d", "--all"],
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