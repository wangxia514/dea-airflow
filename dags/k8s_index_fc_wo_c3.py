"""
# Landsat Collection-3 indexing automation

DAG to periodically index/archive Landsat Collection-3 data.

This DAG uses k8s executors and in cluster with relevant tooling
and configuration installed.

"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.kubernetes.secret import Secret
from airflow.operators.dummy_operator import DummyOperator

DEFAULT_ARGS = {
    "owner": "Alex Leith",
    "depends_on_past": False,
    "start_date": datetime(2020, 10, 1),
    "email": ["alex.leith@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "env_vars": {"DB_HOSTNAME": "db-writer", "DB_DATABASE": "sandbox"},
    # Lift secrets into environment variables
    "secrets": [
        Secret(
            "env",
            "DB_USERNAME",
            "ows-db",
            "postgres-username",
        ),
        Secret(
            "env",
            "DB_PASSWORD",
            "ows-db",
            "postgres-password",
        ),
        Secret(
            "env",
            "AWS_DEFAULT_REGION",
            "alchemist-c3-user-creds",
            "AWS_DEFAULT_REGION",
        ),
        Secret(
            "env",
            "AWS_ACCESS_KEY_ID",
            "alchemist-c3-user-creds",
            "AWS_ACCESS_KEY_ID",
        ),
        Secret(
            "env",
            "AWS_SECRET_ACCESS_KEY",
            "alchemist-c3-user-creds",
            "AWS_SECRET_ACCESS_KEY",
        ),
        Secret(
            "env",
            "FC_SQS_INDEXING_QUEUE",
            "alchemist-c3-user-creds",
            "FC_SQS_INDEXING_QUEUE",
        ),
        Secret(
            "env",
            "WO_SQS_INDEXING_QUEUE",
            "alchemist-c3-user-creds",
            "WO_SQS_INDEXING_QUEUE",
        ),
    ],
}

from infra.images import INDEXER_IMAGE

dag = DAG(
    "k8s_index_wo_fc_c3",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval="0,30 * * * * *",
    catchup=False,
    tags=["k8s", "landsat_c3"],
)

product_to_queue = {
    "ga_ls_wo_3": "WO_SQS_INDEXING_QUEUE",
    "ga_ls_fc_3": "FC_SQS_INDEXING_QUEUE",
}

with dag:
    for product, queue in product_to_queue.items():
        slug = product.replace("_", "-")
        INDEXING = KubernetesPodOperator(
            namespace="processing",
            image=INDEXER_IMAGE,
            image_pull_policy="IfNotPresent",
            arguments=[
                "bash",
                "-c",
                f"sqs-to-dc --stac --update-if-exists --allow-unsafe ${queue} {product}",
            ],
            labels={"step": "sqs-dc-indexing"},
            name=f"datacube-index-{slug}",
            task_id=f"indexing-task-{slug}",
            get_logs=True,
            is_delete_operator_pod=True,
        )

        INDEXING
