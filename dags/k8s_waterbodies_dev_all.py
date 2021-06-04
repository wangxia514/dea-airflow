"""
DEA Waterbodies processing on dev.

DAG to run the "all" workflow of DEA Waterbodies.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator

from textwrap import dedent

from infra.images import WATERBODIES_UNSTABLE_IMAGE

from infra.variables import (
    DB_DATABASE,
    DB_READER_HOSTNAME,
    AWS_DEFAULT_REGION,
    DB_PORT,
)
from infra.podconfig import ONDEMAND_NODE_AFFINITY

# DAG CONFIGURATION
DEFAULT_ARGS = {
    "owner": "Matthew Alger",
    "depends_on_past": False,
    "start_date": datetime(2021, 6, 2),
    "email": ["matthew.alger@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "env_vars": {
        "DB_HOSTNAME": DB_READER_HOSTNAME,
        "DB_DATABASE": DB_DATABASE,
        "DB_PORT": DB_PORT,
        "AWS_DEFAULT_REGION": AWS_DEFAULT_REGION,
    },
    # Lift secrets into environment variables
    "secrets": [
        Secret("env", "DB_USERNAME", 'odc-reader', "postgres-username"),
        Secret("env", "DB_USERNAME", 'odc-reader', "postgres-password"),
        Secret(
            "env",
            "AWS_ACCESS_KEY_ID",
            "waterbodies-dev-user-creds",
            "AWS_ACCESS_KEY_ID",
        ),
        Secret(
            "env",
            "AWS_SECRET_ACCESS_KEY",
            "waterbodies-dev-user-creds",
            "AWS_SECRET_ACCESS_KEY",
        ),
    ],
}

# parallel --delay 5 --retries 3 --load 100%  --colsep ',' python -m dea_waterbodies.make_time_series ::: $CONFIG,--part,{1..24},--chunks,$NCHUNKS

WATERBODIES_BASH_COMMAND = "-mdea_waterbodies.make_time_series --part={part} --chunks={n_chunks}"

# THE DAG
dag = DAG(
    "k8s_waterbodies_dev_all",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,  # triggered only
    catchup=False,
    tags=["k8s", "landsat", "waterbodies"],
)

with dag:
    n_chunks = 24
    for part in range(1, n_chunks + 1):
        # https://airflow.apache.org/docs/apache-airflow/1.10.12/_api/airflow/contrib/operators/
        # kubernetes_pod_operator/index.html#airflow.contrib.operators.kubernetes_pod_operator.KubernetesPodOperator
        WATERBODIES_ALL_PART = KubernetesPodOperator(
            image=WATERBODIES_UNSTABLE_IMAGE,
            name="waterbodies-all",
            cmds="python",
            arguments=WATERBODIES_BASH_COMMAND.format(part=part, n_chunks=n_chunks).split(' '),
            image_pull_policy="IfNotPresent",
            labels={"step": "waterbodies-dev-all-{part}".format(part=part)},
            get_logs=True,
            affinity=ONDEMAND_NODE_AFFINITY,
            is_delete_operator_pod=True,
            namespace="processing",
            task_id="waterbodies-all-task",
        )
