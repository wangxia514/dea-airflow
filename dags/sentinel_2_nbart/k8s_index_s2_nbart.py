"""
# Sentinel-3 indexing automation

DAG to periodically index/archive Sentinel-2 NBART data.

This DAG uses k8s executors and in cluster with relevant tooling
and configuration installed.

"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.operators.dummy_operator import DummyOperator

DEFAULT_ARGS = {
    "owner": "Kieran Ricardo",
    "depends_on_past": False,
    "start_date": datetime(2020, 6, 1),
    "email": ["kieran.ricardo@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "index_sqs_queue": "{{ var.json.k8s_index_s2_nbart_config.index_sqs_queue }}",
    "products": "s2a_ard_granule s2b_ard_granule",
    "env_vars": {
        "DB_HOSTNAME": "db-writer",
    },
    # Lift secrets into environment variables
    "secrets": [
        Secret(
            "env",
            "DB_DATABASE",
            "odc-writer",
            "database-name",
        ),
        Secret(
            "env",
            "DB_USERNAME",
            "odc-writer",
            "postgres-username",
        ),
        Secret(
            "env",
            "DB_PASSWORD",
            "odc-writer",
            "postgres-password",
        ),
        Secret(
            "env",
            "AWS_DEFAULT_REGION",
            "processing-aws-creds-dev",
            "AWS_DEFAULT_REGION",
        ),
        Secret(
            "env",
            "AWS_ACCESS_KEY_ID",
            "processing-aws-creds-dev",
            "AWS_ACCESS_KEY_ID",
        ),
        Secret(
            "env",
            "AWS_SECRET_ACCESS_KEY",
            "processing-aws-creds-dev",
            "AWS_SECRET_ACCESS_KEY",
        ),
    ],
}

from infra.images import INDEXER_IMAGE

dag = DAG(
    "k8s_index_s2_nbart",
    default_args=DEFAULT_ARGS,
    schedule_interval="0 */1 * * *",
    catchup=False,
    tags=["k8s", "s2_nbart"],
)

with dag:
    START = DummyOperator(task_id="start-tasks")

    INDEXING = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        image_pull_policy="Always",
        arguments=[
            "git clone https://github.com/opendatacube/odc-tools.git;",
            "./odc-tools/scripts/dev-install.sh;",
            "sqs-to-dc",
            "--stac",
            "--skip-lineage",
            "--absolute",
            dag.default_args["index_sqs_queue"],
            dag.default_args["products"],
        ],
        labels={"step": "sqs-dc-indexing"},
        name="datacube-index",
        task_id="indexing-task",
        get_logs=True,
        is_delete_operator_pod=True,
    )

    COMPLETE = DummyOperator(task_id="tasks-complete")

    START >> INDEXING >> COMPLETE
