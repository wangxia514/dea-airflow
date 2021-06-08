"""
# Sentinel-3 indexing automation

DAG to bulk index Sentinel-2 NBART data.

This DAG uses k8s executors and in cluster with relevant tooling
and configuration installed.

"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.operators.dummy_operator import DummyOperator
from infra.variables import DB_HOSTNAME, SECRET_ODC_WRITER_NAME
from infra.images import INDEXER_IMAGE

DEFAULT_ARGS = {
    "owner": "Kieran Ricardo",
    "depends_on_past": False,
    "email": ["kieran.ricardo@ga.gov.au"],
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
    schedule_interval=None,
    catchup=False,
    tags=["k8s", "s2_nbart"],
)

with dag:
    for year in range(2015, 2018): # TODO: update year range when all metadata fixed
        for quarter in ["0[123]", "0[456]", "0[789]", "1[012]"]:

            INDEXING = KubernetesPodOperator(
                namespace="processing",
                image=INDEXER_IMAGE,
                image_pull_policy="Always",
                arguments=[
                    "s3-to-dc",
                    "--skip-lineage",
                    f"s3://dea-public-data/baseline/s2[ab]_ard_granule/{year}-{quarter}-*/*/eo3-ARD-METADATA.yaml",
                    dag.default_args["products"],
                ],
                labels={"step": "s3-dc-indexing"},
                name="datacube-index",
                task_id=f"indexing-task-{year}-{quarter}",
                get_logs=True,
                is_delete_operator_pod=True,
            )
