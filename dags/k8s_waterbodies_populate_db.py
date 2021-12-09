"""
Populate the DEA Waterbodies interstitial DB with Conflux.

Supported configuration arguments:

dir
    Parquet or CSV directory. REQUIRED - no default.

drop
    Whether to drop the table first. Default False.

mode
    POPULATE or STACK.
"""
from datetime import datetime, timedelta

# import json

from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)

from textwrap import dedent

from infra.images import CONFLUX_UNSTABLE_IMAGE
from infra.podconfig import ONDEMAND_NODE_AFFINITY
from infra.variables import (
    AWS_DEFAULT_REGION,
    DB_PORT,
    WATERBODIES_DEV_USER_SECRET,
    WATERBODIES_DB_WRITER_SECRET,
)


# DAG CONFIGURATION
SECRETS = {
    "env_vars": {
        "WATERBODIES_DB_HOST": "pgbouncer",
        "WATERBODIES_DB_PORT": DB_PORT,
        "AWS_DEFAULT_REGION": AWS_DEFAULT_REGION,
    },
    # Lift secrets into environment variables
    "secrets": [
        Secret("env", "WATERBODIES_DB_NAME", WATERBODIES_DB_WRITER_SECRET, "database-name"),
        Secret("env", "WATERBODIES_DB_USER", WATERBODIES_DB_WRITER_SECRET, "postgres-username"),
        Secret("env", "WATERBODIES_DB_PASS", WATERBODIES_DB_WRITER_SECRET, "postgres-password"),
        Secret(
            "env",
            "AWS_ACCESS_KEY_ID",
            WATERBODIES_DEV_USER_SECRET,
            "AWS_ACCESS_KEY_ID",
        ),
        Secret(
            "env",
            "AWS_SECRET_ACCESS_KEY",
            WATERBODIES_DEV_USER_SECRET,
            "AWS_SECRET_ACCESS_KEY",
        ),
    ],
}
DEFAULT_ARGS = {
    "owner": "Matthew Alger",
    "depends_on_past": False,
    "start_date": datetime(2021, 6, 2),
    "email": ["matthew.alger@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "startup_timeout_seconds": 5 * 60,
    **SECRETS,
}

# THE DAG
dag = DAG(
    "k8s_waterbodies_populate_db",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,  # triggered only
    catchup=False,
    concurrency=1,
    tags=["k8s", "landsat", "waterbodies", "conflux"],
)


def k8s_stack(dag):
    cmd = [
        "bash",
        "-c",
        dedent(
            """
            if [ "POPULATE" = "{{ dag_run.conf.get("mode") }}" ]; then
                if [ "True" = "{{ dag_run.conf.get("drop", False) }}" ]; then
                    # drop the database
                    echo Dropping database...
                    dea-conflux stack --parquet-path {{ dag_run.conf["dir"] }} \
                        --mode waterbodies_db --drop
                else
                    dea-conflux stack --parquet-path {{ dag_run.conf["dir"] }} \
                        --mode waterbodies_db
                fi
            elif [ "STACK" = "{{ dag_run.conf.get("mode") }}" ]; then
                echo Stacking...
                dea-conflux db-to-csv --output {{ dag_run.conf["dir"] }} --jobs 64
            else
                echo No mode specified.
            fi
            """
        ),
    ]
    return KubernetesPodOperator(
        image=CONFLUX_UNSTABLE_IMAGE,
        dag=dag,
        name="waterbodies-populate-db",
        arguments=cmd,
        image_pull_policy="IfNotPresent",
        labels={"app": "waterbodies-populate-db"},
        get_logs=True,
        affinity=ONDEMAND_NODE_AFFINITY,
        is_delete_operator_pod=True,
        resources={
            "request_cpu": "2000m",
            "request_memory": "512Mi",
        },
        namespace="processing",
        task_id="waterbodies-populate-db",
    )


with dag:
    k8s_stack(dag)
