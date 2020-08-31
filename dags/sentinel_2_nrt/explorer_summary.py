"""
# Explorer cubedash-gen refresh-stats
"""

from airflow import DAG
from textwrap import dedent
from datetime import datetime, timedelta
from airflow.operators.dummy_operator import DummyOperator

from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.kubernetes.secret import Secret
from sentinel_2_nrt.env_cfg import INDEXING_PRODUCTS
from sentinel_2_nrt.images import EXPLORER_IMAGE
from sentinel_2_nrt.env_cfg import DB_DATABASE, SECRET_EXPLORER_NAME, SECRET_AWS_NAME


EXPLORER_BASH_COMMAND = [
    "bash",
    "-c",
    dedent("""
        for product in %s; do
            cubedash-gen --no-init-database --refresh-stats --force-refresh $product;
        done;
    """)%(INDEXING_PRODUCTS)
]

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
        "DB_HOSTNAME": "db-writer",
        "DB_DATABASE": DB_DATABASE,
    },
    # Lift secrets into environment variables
    "secrets": [
        Secret("env", "AWS_DEFAULT_REGION", SECRET_AWS_NAME, "AWS_DEFAULT_REGION"),
    ],
}

EXPLORER_SECRETS = [
    Secret("env", "DB_USERNAME", SECRET_EXPLORER_NAME, "postgres-username"),
    Secret("env", "DB_PASSWORD", SECRET_EXPLORER_NAME, "postgres-password")
]

# THE DAG
dag = DAG(
    "explorer-refresh-stats",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval="0 */1 * * *",
    catchup=False,
    tags=["k8s", "explorer"],
)

with dag:
    EXPLORER_SUMMARY = KubernetesPodOperator(
        namespace="processing",
        image=EXPLORER_IMAGE,
        arguments=EXPLORER_BASH_COMMAND,
        secrets=EXPLORER_SECRETS,
        labels={"step": "explorer-refresh-stats"},
        name="explorer-summary",
        task_id="explorer-summary-task",
        get_logs=True,
        is_delete_operator_pod=True,
    )

    START = DummyOperator(task_id="start_sentinel_2_nrt")

    COMPLETE = DummyOperator(task_id="all_done")

    START >> EXPLORER_SUMMARY
    EXPLORER_SUMMARY >> COMPLETE