"""
# Sentinel-2_nrt Batch Indexing From S3

DAG to periodically index Sentinel-2 NRT data.

This DAG uses k8s executors and in cluster with relevant tooling
and configuration installed.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from textwrap import dedent

from infra.images import INDEXER_IMAGE
from infra.variables import (
    DB_DATABASE,
    DB_HOSTNAME,
    SECRET_ODC_WRITER_NAME,
    AWS_DEFAULT_REGION,
)
from infra.pools import DEA_NEWDATA_PROCESSING_POOL
from infra.podconfig import ONDEMAND_NODE_AFFINITY
from sentinel_2_nrt.env_cfg import (
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
        "DB_PORT": "5432",
        "AWS_DEFAULT_REGION": AWS_DEFAULT_REGION,
    },
    # Lift secrets into environment variables
    "secrets": [
        Secret("env", "DB_USERNAME", SECRET_ODC_WRITER_NAME, "postgres-username"),
        Secret("env", "DB_PASSWORD", SECRET_ODC_WRITER_NAME, "postgres-password"),
    ],
}


uri_list = []
for n in range(1, 8):  # cover an entire week
    uri_date = (datetime.today() - timedelta(days=n)).strftime("%Y-%m-%d")
    URI = f"s3://dea-public-data/L2/sentinel-2-nrt/S2MSIARD/{uri_date}/**/ARD-METADATA.yaml"
    uri_list.append(URI)

uri_string = " ".join(uri_list)

INDEXING_BASH_COMMAND = [
    "bash",
    "-c",
    dedent(
        """
            for uri in %s; do
               s3-to-dc $uri "%s" --skip-lineage --no-sign-request;
            done
        """
    )
    % (uri_string, " ".join(INDEXING_PRODUCTS)),
]


# THE DAG
dag = DAG(
    "sentinel_2_nrt_batch_indexing",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval="0 6 * * *",  # 11pm
    catchup=False,
    max_active_runs=1,
    tags=["k8s", "sentinel-2", "batch-indexing"],
)

with dag:
    INDEXING = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        image_pull_policy="IfNotPresent",
        arguments=INDEXING_BASH_COMMAND,
        labels={"step": "s3-to-rds"},
        name="datacube-index",
        task_id="batch-indexing-task",
        get_logs=True,
        affinity=ONDEMAND_NODE_AFFINITY,
        is_delete_operator_pod=True,
        pool=DEA_NEWDATA_PROCESSING_POOL,
    )
