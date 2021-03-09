"""
# Landsat Collection-3 indexing automation for odc db

DAG to periodically index/archive Landsat Collection-3 data.

This DAG uses k8s executors and in cluster with relevant tooling
and configuration installed.

"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.kubernetes.secret import Secret
from infra.variables import (
    C3_ALCHEMIST_ROLE,
    C3_FC_SQS_QUEUE_NAME,
    C3_WO_SQS_QUEUE_NAME,
    DB_DATABASE,
    DB_HOSTNAME,
    SECRET_ODC_WRITER_NAME,
)
from infra.images import INDEXER_IMAGE


DEFAULT_ARGS = {
    "owner": "Pin Jin",
    "depends_on_past": False,
    "start_date": datetime(2020, 10, 1),
    "email": ["pin.jin@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "env_vars": {
        "DB_HOSTNAME": DB_HOSTNAME,
        "DB_DATABASE": DB_DATABASE,
        "FC_SQS_INDEXING_QUEUE": C3_FC_SQS_QUEUE_NAME,
        "WO_SQS_INDEXING_QUEUE": C3_WO_SQS_QUEUE_NAME,
    },
    # Lift secrets into environment variables
    "secrets": [
        Secret(
            "env",
            "DB_USERNAME",
            SECRET_ODC_WRITER_NAME,
            "postgres-username",
        ),
        Secret(
            "env",
            "DB_PASSWORD",
            SECRET_ODC_WRITER_NAME,
            "postgres-password",
        ),
        Secret(
            "env",
            "AWS_DEFAULT_REGION",
            C3_ALCHEMIST_ROLE,
            "AWS_DEFAULT_REGION",
        ),
        Secret(
            "env",
            "AWS_ACCESS_KEY_ID",
            C3_ALCHEMIST_ROLE,
            "AWS_ACCESS_KEY_ID",
        ),
        Secret(
            "env",
            "AWS_SECRET_ACCESS_KEY",
            C3_ALCHEMIST_ROLE,
            "AWS_SECRET_ACCESS_KEY",
        ),
    ],
}

dag = DAG(
    "k8s_index_wo_fc_c3_odc",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval="0,30 * * * * *",
    catchup=False,
    tags=["k8s", "landsat_c3"],
)

with dag:
    for product in ["wo", "fc"]:
        INDEXING = KubernetesPodOperator(
            namespace="processing",
            image=INDEXER_IMAGE,
            image_pull_policy="IfNotPresent",
            arguments=[
                "bash",
                "-c",
                f"sqs-to-dc --stac --update-if-exists --allow-unsafe ${product.upper()}_SQS_INDEXING_QUEUE ga_ls_{product}_3",
            ],
            labels={"step": "sqs-dc-indexing"},
            name=f"datacube-index-{product}",
            task_id=f"indexing-task-{product}",
            get_logs=True,
            is_delete_operator_pod=True,
        )
