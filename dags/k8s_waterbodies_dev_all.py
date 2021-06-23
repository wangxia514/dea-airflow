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
    WATERBODIES_DEV_USER_SECRET,
    SECRET_ODC_READER_NAME,
)

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
        Secret("env", "DB_USERNAME", SECRET_ODC_READER_NAME, "postgres-username"),
        Secret("env", "DB_PASSWORD", SECRET_ODC_READER_NAME, "postgres-password"),
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

# Kubernetes autoscaling group affinity
affinity = {
    "nodeAffinity": {
        "requiredDuringSchedulingIgnoredDuringExecution": {
            "nodeSelectorTerms": [
                {
                    "matchExpressions": [
                        {
                            "key": "nodegroup",
                            "operator": "In",
                            "values": [
                                "r5-4xl-waterbodies",
                            ],
                        }
                    ]
                }
            ]
        }
    }
}

# This is the original waterbodies command:
# parallel --delay 5 --retries 3 --load 100%  --colsep ',' python -m dea_waterbodies.make_time_series ::: $CONFIG,--part,{1..24},--chunks,$NCHUNKS

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
    n_chunks = 12
    for part in range(1, n_chunks + 1):
        # https://airflow.apache.org/docs/apache-airflow/1.10.12/_api/airflow/contrib/operators/
        # kubernetes_pod_operator/index.html#airflow.contrib.operators.kubernetes_pod_operator.KubernetesPodOperator

        cmd = [
            "bash",
            "-c",
            dedent(
                """
                echo "Using dea-waterbodies image {image}"
                wget https://raw.githubusercontent.com/GeoscienceAustralia/dea-waterbodies/stable/ts_configs/{conf} -O config.ini
                cat config.ini
                python -m dea_waterbodies.make_time_series config.ini --part={part} --chunks={n_chunks}
                """.format(image=WATERBODIES_UNSTABLE_IMAGE,
                           part=part, n_chunks=n_chunks,
                           conf='{{ dag_run.conf.get("config_name", "config_moree_test") }}')
            ),
        ]
        KubernetesPodOperator(
            image=WATERBODIES_UNSTABLE_IMAGE,
            name="waterbodies-all",
            arguments=cmd,
            image_pull_policy="IfNotPresent",
            labels={"step": "waterbodies-dev-all-{part}".format(part=part)},
            get_logs=True,
            affinity=affinity,
            is_delete_operator_pod=True,
            resources={
                "request_cpu": "1000m",
                "request_memory": "500Mi",
            },
            namespace="processing",
            task_id="waterbodies-all-task-{part}".format(part=part),
        )
