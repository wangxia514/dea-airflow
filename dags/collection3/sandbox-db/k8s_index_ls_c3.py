"""
# Landsat Collection-3 indexing automation

DAG to periodically index/archive Landsat Collection-3 data.

This DAG uses k8s executors and in cluster with relevant tooling
and configuration installed.

This DAG takes following input parameters from `k8s_index_ls_c3_config` variable:

 * `index_sqs_queue`: Name of the SQS queue for indexing
 * `archive_sqs_queue`: Name of the SQS queue for archiving
 * `db_hostname`: Name of the DB host
 * `db_database`: Name of the DB

"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from airflow.operators.dummy import DummyOperator
from infra.variables import (
    C3_INDEXING_USER_SECRET,
    DB_SANDBOX_DATABASE,
    DB_SANDBOX_USER_SECRET,
    DB_HOSTNAME,
)
from infra.podconfig import ONDEMAND_NODE_AFFINITY

from infra.images import INDEXER_IMAGE


DEFAULT_ARGS = {
    "owner": "Damien Ayers",
    "depends_on_past": False,
    "start_date": datetime(2020, 6, 1),
    "email": ["damien.ayers@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "index_sqs_queue": "{{ var.json.k8s_index_ls_c3_config.index_sqs_queue }}",
    "archive_sqs_queue": "{{ var.json.k8s_index_ls_c3_config.archive_sqs_queue }}",
    "products": "ga_ls5t_ard_3 ga_ls7e_ard_3 ga_ls8c_ard_3",
    "env_vars": {
        "DB_HOSTNAME": DB_HOSTNAME,
        "DB_DATABASE": DB_SANDBOX_DATABASE,
    },
    # Lift secrets into environment variables
    "secrets": [
        Secret(
            "env",
            "DB_USERNAME",
            DB_SANDBOX_USER_SECRET,
            "postgres-username",
        ),
        Secret(
            "env",
            "DB_PASSWORD",
            DB_SANDBOX_USER_SECRET,
            "postgres-password",
        ),
        Secret(
            "env",
            "AWS_DEFAULT_REGION",
            C3_INDEXING_USER_SECRET,
            "AWS_DEFAULT_REGION",
        ),
        Secret(
            "env",
            "AWS_ACCESS_KEY_ID",
            C3_INDEXING_USER_SECRET,
            "AWS_ACCESS_KEY_ID",
        ),
        Secret(
            "env",
            "AWS_SECRET_ACCESS_KEY",
            C3_INDEXING_USER_SECRET,
            "AWS_SECRET_ACCESS_KEY",
        ),
    ],
}


dag = DAG(
    "k8s_index_ls_c3",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval="0 */1 * * *",
    catchup=False,
    tags=["k8s", "landsat_c3"],
)

with dag:
    START = DummyOperator(task_id="start-tasks")

    INDEXING = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        image_pull_policy="Always",
        arguments=[
            "sqs-to-dc",
            "--stac",
            "--skip-lineage",
            dag.default_args["index_sqs_queue"],
            dag.default_args["products"],
        ],
        labels={"step": "sqs-dc-indexing"},
        name="datacube-index",
        task_id="indexing-task",
        get_logs=True,
        affinity=ONDEMAND_NODE_AFFINITY,
        is_delete_operator_pod=True,
    )

    ARCHIVING = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        image_pull_policy="Always",
        arguments=[
            "sqs-to-dc",
            "--archive",
            dag.default_args["archive_sqs_queue"],
            dag.default_args["products"],
        ],
        labels={"step": "sqs-dc-archiving"},
        name="datacube-archive",
        task_id="archiving-task",
        get_logs=True,
        affinity=ONDEMAND_NODE_AFFINITY,
        is_delete_operator_pod=True,
    )

    COMPLETE = DummyOperator(task_id="tasks-complete")

    START >> INDEXING >> COMPLETE
    START >> ARCHIVING >> COMPLETE
