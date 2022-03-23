"""
# Bulk Index ALL Sentinel-2 ARD Data in `dea-public-data`

This DAG runs weekly, attempting to index all the Sentinel-2 ARD data
we have in s3://dea-public-data/ .

In theory, this shouldn't be necessary, as we're indexing from SQS message queues
and watch for failed indexing in the Dead-letter queue. In practice, this is
a simple method to make sure we haven't missed anything.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from infra.variables import DB_HOSTNAME, SECRET_ODC_WRITER_NAME
from infra.images import INDEXER_IMAGE

DEFAULT_ARGS = {
    "owner": "Damien Ayers",
    "depends_on_past": False,
    "start_date": datetime(2020, 6, 14),
    "email": ["damien.ayers@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "products": "s2a_ard_granule s2b_ard_granule",
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
    ],
}


dag = DAG(
    "k8s_index_s2_nbart_backlog",
    default_args=DEFAULT_ARGS,
    schedule_interval="@weekly",
    catchup=False,
    tags=["k8s", "s2", "ard"],
)

with dag:
    for year in range(2015, datetime.now().year + 1):
        for i, quarter in enumerate(["0[123]", "0[456]", "0[789]", "1[012]"]):
            INDEXING = KubernetesPodOperator(
                namespace="processing",
                image=INDEXER_IMAGE,
                image_pull_policy="Always",
                arguments=[
                    "s3-to-dc",
                    "--skip-lineage",
                    "--allow-unsafe",
                    "--update-if-exists",
                    "--no-sign-request",
                    "s3://dea-public-data/baseline/s2[ab]_ard_granule/"
                    + f"{year}-{quarter}"
                    + "-*/*/eo3-ARD-METADATA.odc-metadata.yaml",
                    dag.default_args["products"],
                ],
                labels={"step": "s3-dc-indexing"},
                name="datacube-index",
                task_id=f"indexing-task-{year}-Q{i+1}",
                get_logs=True,
                is_delete_operator_pod=True,
            )
