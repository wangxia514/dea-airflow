"""
# Collection-3 indexing automation

DAG to periodically index/archive Collection-3 data.

This DAG uses k8s executors and in cluster with relevant tooling
and configuration installed.

"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from airflow.kubernetes.secret import Secret
from infra.variables import (
    DB_HOSTNAME,
    ALCHEMIST_C3_USER_SECRET,
    SECRET_ODC_WRITER_NAME,
)
from infra.podconfig import ONDEMAND_NODE_AFFINITY
from infra.images import INDEXER_IMAGE

DEFAULT_ARGS = {
    "owner": "Alex Leith",
    "depends_on_past": False,
    "start_date": datetime(2020, 10, 1),
    "email": ["alex.leith@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "env_vars": {
        "DB_HOSTNAME": DB_HOSTNAME,
    },
    # Lift secrets into environment variables
    "secrets": [
        Secret(
            "env",
            "DB_DATABASE",
            SECRET_ODC_WRITER_NAME,
            "database-name",
        ),
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
            ALCHEMIST_C3_USER_SECRET,
            "AWS_DEFAULT_REGION",
        ),
        Secret(
            "env",
            "AWS_ACCESS_KEY_ID",
            ALCHEMIST_C3_USER_SECRET,
            "AWS_ACCESS_KEY_ID",
        ),
        Secret(
            "env",
            "AWS_SECRET_ACCESS_KEY",
            ALCHEMIST_C3_USER_SECRET,
            "AWS_SECRET_ACCESS_KEY",
        ),
        Secret(
            "env",
            "FC_SQS_INDEXING_QUEUE",
            ALCHEMIST_C3_USER_SECRET,
            "FC_SQS_INDEXING_QUEUE",
        ),
        Secret(
            "env",
            "WO_SQS_INDEXING_QUEUE",
            ALCHEMIST_C3_USER_SECRET,
            "WO_SQS_INDEXING_QUEUE",
        ),
        Secret(
            "env",
            "S2_NRT_WO_SQS_INDEXING_QUEUE",
            ALCHEMIST_C3_USER_SECRET,
            "S2_NRT_WO_SQS_INDEXING_QUEUE",
        ),
        Secret(
            "env",
            "S2_WO_SQS_INDEXING_QUEUE",
            ALCHEMIST_C3_USER_SECRET,
            "S2_WO_SQS_INDEXING_QUEUE",
        ),
    ],
}


dag = DAG(
    "k8s_index_wo_fc_c3",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval="0 */1 * * *",
    catchup=False,
    tags=["k8s", "landsat_c3"],
)

queue_to_product = {
    "WO_SQS_INDEXING_QUEUE": "ga_ls_wo_3",
    "FC_SQS_INDEXING_QUEUE": "ga_ls_fc_3",
    "S2_NRT_WO_SQS_INDEXING_QUEUE": "ga_s2_wo_3",
    "S2_WO_SQS_INDEXING_QUEUE": "ga_s2_wo_3",
}

with dag:
    for queue, product in queue_to_product.items():
        slug = product.replace("_", "-")
        INDEXING = KubernetesPodOperator(
            namespace="processing",
            image=INDEXER_IMAGE,
            image_pull_policy="IfNotPresent",
            arguments=[
                "bash",
                "-c",
                "sqs-to-dc --stac "  # continue
                f"--update-if-exists --allow-unsafe ${queue} {product}",
            ],
            labels={"step": "sqs-dc-indexing"},
            name=f"datacube-index-{queue}",
            task_id=f"indexing-task-{queue}",
            get_logs=True,
            affinity=ONDEMAND_NODE_AFFINITY,
            is_delete_operator_pod=True,
        )

        INDEXING
