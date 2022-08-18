"""
# Landsat Collection-3 indexing automation for odc db

DAG to periodically index/archive Landsat Collection-3 data.

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
    DB_DATABASE,
    DB_HOSTNAME,
    SECRET_ODC_WRITER_NAME,
    STATSD_HOST,
    STATSD_PORT,
)
from infra.variables import C3_BA_ALCHEMIST_SECRET
from infra.images import INDEXER_IMAGE
from infra.podconfig import ONDEMAND_NODE_AFFINITY


DEFAULT_ARGS = {
    "owner": "James O'Brien",
    "depends_on_past": False,
    "start_date": datetime(2020, 10, 1),
    "email": ["james.obrien@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "env_vars": {
        "DB_HOSTNAME": DB_HOSTNAME,
        "DB_DATABASE": DB_DATABASE,
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
            C3_BA_ALCHEMIST_SECRET,
            "AWS_DEFAULT_REGION",
        ),
        Secret(
            "env",
            "AWS_ACCESS_KEY_ID",
            C3_BA_ALCHEMIST_SECRET,
            "AWS_ACCESS_KEY_ID",
        ),
        Secret(
            "env",
            "AWS_SECRET_ACCESS_KEY",
            C3_BA_ALCHEMIST_SECRET,
            "AWS_SECRET_ACCESS_KEY",
        ),
        Secret(
            "env",
            "BURNS_SNS_INDEXING_QUEUE",
            C3_BA_ALCHEMIST_SECRET,
            "BURNS_SNS_INDEXING_QUEUE",
        ),
    ],
}

dag = DAG(
    "k8s_index_s2_derivatves_odc",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval="0,30 * * * * *",
    catchup=False,
    tags=["k8s", "burns_s2", "sentinel2_derivatives"],
)

with dag:
    # Burn Area based on s2 dataset
    for product in ["ba"]:
        INDEXING = KubernetesPodOperator(
            namespace="processing",
            image=INDEXER_IMAGE,
            image_pull_policy="IfNotPresent",
            arguments=[
                "bash",
                "-c",
                f"sqs-to-dc --stac --statsd-setting {STATSD_HOST}:{STATSD_PORT} --update-if-exists --allow-unsafe $BURNS_SNS_INDEXING_QUEUE ga_s2_{product}_provisional_3",
            ],
            labels={"step": "sqs-dc-indexing"},
            name=f"datacube-index-{product}",
            task_id=f"indexing-task-{product}",
            get_logs=True,
            affinity=ONDEMAND_NODE_AFFINITY,
            is_delete_operator_pod=True,
        )
