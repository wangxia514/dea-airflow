"""
# Sentinel-2_nrt Streamline Indexing from SQS

DAG to periodically index Sentinel-2 NRT data.

This DAG uses k8s executors and in cluster with relevant tooling
and configuration installed.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator

from infra.images import INDEXER_IMAGE
from infra.variables import (
    DB_DATABASE,
    DB_HOSTNAME,
    SECRET_ODC_WRITER_NAME,
    AWS_DEFAULT_REGION,
)
from infra.sqs_queues import SQS_QUEUE_NAME
from infra.iam_roles import INDEXING_ROLE
from infra.pools import DEA_NEWDATA_PROCESSING_POOL
from dea_public_data_sns_indexing.env_cfg import (
    NRT_PRODUCTS,
    NRT_PATHS,
)
from infra.podconfig import ONDEMAND_NODE_AFFINITY

INDEXER_IMAGE = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/opendatacube/datacube-index:0.0.20"

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
        "DB_PORT": "5432",
        "AWS_DEFAULT_REGION": AWS_DEFAULT_REGION,
    },
    # Lift secrets into environment variables
    "secrets": [
        Secret("env", "DB_USERNAME", SECRET_ODC_WRITER_NAME, "postgres-username"),
        Secret("env", "DB_PASSWORD", SECRET_ODC_WRITER_NAME, "postgres-password"),
    ],
}

record_path_list_with_prefix = [f"--record-path '{path}'" for path in NRT_PATHS]
index_product_string = " ".join(NRT_PRODUCTS)
record_path_string = " ".join(record_path_list_with_prefix)


INDEXING_BASH_COMMAND = [
    "bash",
    "-c",
    f"sqs-to-dc --skip-lineage --allow-unsafe {SQS_QUEUE_NAME} '{index_product_string}' {record_path_string}",
]


# THE DAG
dag = DAG(
    "dea_public_data_sns_streamline_indexing",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval="0 */1 * * *",  # hourly
    # schedule_interval=None,  # for testing
    catchup=False,
    max_active_runs=1,
    tags=["k8s", "sentinel-2", "streamline-indexing"],
    params={"labels": {"env": "dev"}},
)

with dag:
    INDEXING = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        image_pull_policy="IfNotPresent",
        annotations={"iam.amazonaws.com/role": INDEXING_ROLE},
        arguments=INDEXING_BASH_COMMAND,
        labels={"app": "dag_s2_nrt_streamline"},
        name="datacube-index",
        task_id="streamline-indexing-task",
        get_logs=True,
        pool=DEA_NEWDATA_PROCESSING_POOL,
        affinity=ONDEMAND_NODE_AFFINITY,
        is_delete_operator_pod=True,
        log_events_on_failure=True,
    )
