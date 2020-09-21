"""
# Sentinel-2_nrt Indexing from SQS

DAG to periodically index Sentinel-2 NRT data.

This DAG uses k8s executors and in cluster with relevant tooling
and configuration installed.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.kubernetes.volume import Volume
from airflow.kubernetes.volume_mount import VolumeMount
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator

from textwrap import dedent

import kubernetes.client.models as k8s

from sentinel_2_nrt.images import INDEXER_IMAGE, CREATION_DT_PATCHER_IMAGE
from env_var.infra import (
    DB_DATABASE,
    DB_HOSTNAME,
    SECRET_OWS_NAME,
    SECRET_AWS_NAME,
    INDEXING_ROLE,
)
from sentinel_2_nrt.env_cfg import (
    SQS_QUEUE_NAME,
    INDEXING_PRODUCTS,
)

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
    },
    # Lift secrets into environment variables
    "secrets": [
        Secret("env", "DB_USERNAME", SECRET_OWS_NAME, "postgres-username"),
        Secret("env", "DB_PASSWORD", SECRET_OWS_NAME, "postgres-password"),
        Secret("env", "AWS_DEFAULT_REGION", SECRET_AWS_NAME, "AWS_DEFAULT_REGION"),
    ],
}


INDEXING_BASH_COMMAND = [
    "bash",
    "-c",
    dedent(
        """
            sqs-to-dc %s "%s" --skip-lineage --allow-unsafe --record-path "L2/sentinel-2-nrt/S2MSIARD/*/*/ARD-METADATA.yaml" --limit 1;
        """
    )
    % (SQS_QUEUE_NAME, INDEXING_PRODUCTS),
]

CREATION_DT_PATCH_COMMAND = [
    "bash",
    "-c",
    dedent(
        """
            for product in %s; do
                python3 creation_dt_patch.py --product $product --apply-patch;
            done;
        """
    )
    % (INDEXING_PRODUCTS),
]


# THE DAG
dag = DAG(
    "sentinel_2_nrt_indexing",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval="0 */1 * * *",  # hourly
    # schedule_interval=None,  # for testing
    catchup=False,
    tags=["k8s", "sentinel-2"],
)

with dag:
    INDEXING = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        image_pull_policy="IfNotPresent",
        annotations={"iam.amazonaws.com/role": INDEXING_ROLE},
        arguments=INDEXING_BASH_COMMAND,
        labels={"step": "sqs-to-rds"},
        name="datacube-index",
        task_id="indexing-task",
        get_logs=True,
        is_delete_operator_pod=True,
    )

    PATCH = KubernetesPodOperator(
        namespace="processing",
        image=CREATION_DT_PATCHER_IMAGE,
        image_pull_policy="IfNotPresent",
        arguments=CREATION_DT_PATCH_COMMAND,
        labels={"step": "add-creation-dt"},
        name="nrt-creation-dt",
        task_id="creation-dt-task",
        get_logs=True,
        is_delete_operator_pod=True,
    )

    INDEXING >> PATCH
