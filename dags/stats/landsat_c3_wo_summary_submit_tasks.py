"""
# Landsat Collection-3 WOfS yearly summary tasks to SQS

DAG to manually submit WOfS yearly summary task on Landsat Collection-3.

This DAG uses k8s executors and in submit tasks to SQS with relevant tooling
and configuration installed.
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.operators.dummy_operator import DummyOperator

from infra.images import STAT_IMAGE
from infra.variables import (
    DB_DATABASE,
    DB_HOSTNAME,
    SECRET_ODC_READER_NAME,
    PROCESSING_STATS_USER_SECRET
)
from infra.sqs_queues import LS_C3_WO_SUMMARY_QUEUE
from infra.pools import DEA_NEWDATA_PROCESSING_POOL

from infra.podconfig import ONDEMAND_NODE_AFFINITY

# DAG CONFIGURATION
DEFAULT_ARGS = {
    "owner": "Sai Ma",
    "depends_on_past": False,
    "start_date": datetime(2021, 6, 14),
    "email": ["sai.ma@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "env_vars": {
        # We need the DB access to get the Tasks from ODC
        "DB_HOSTNAME": DB_HOSTNAME,
        "DB_DATABASE": DB_DATABASE,
        "DB_PORT": "5432",
    },
    # Lift secrets into environment variables
    "secrets": [
        Secret("env", "DB_USERNAME", SECRET_ODC_READER_NAME, "postgres-username"),
        Secret("env", "DB_PASSWORD", SECRET_ODC_READER_NAME, "postgres-password"),
        Secret(
            "env",
            "AWS_DEFAULT_REGION",
            PROCESSING_STATS_USER_SECRET,
            "AWS_DEFAULT_REGION",
        ),
        Secret(
            "env",
            "AWS_ACCESS_KEY_ID",
            PROCESSING_STATS_USER_SECRET,
            "AWS_ACCESS_KEY_ID",
        ),
        Secret(
            "env",
            "AWS_SECRET_ACCESS_KEY",
            PROCESSING_STATS_USER_SECRET,
            "AWS_SECRET_ACCESS_KEY",
        )
    ],
}

# annual summary input is the daily WOfS
PRODUCT_NAME = "ga_ls_wo_3"
FREQUENCY = "annual" # if we split the summary of WOfS summaries task in another DAG, this value could be a hardcode value
LS_C3_WO_SUMMARY_QUEUE_NAME = LS_C3_WO_SUMMARY_QUEUE.split("/")[-1]

# only grab 2009 data to speed up test, the search expression may open to the user later
CACHE_AND_UPLOADING_BASH_COMMAND = [
    f"odc-stats save-tasks {PRODUCT_NAME} --year=2009 --grid au-30 --frequency {FREQUENCY} ga_ls_wo_3_{FREQUENCY}.db && ls -lh && " \
    f"aws s3 cp ga_ls_wo_3_{FREQUENCY}.db s3://dea-dev-stats-processing/dbs/ga_ls_wo_3_{FREQUENCY}_test_from_airflow.db",
]

# Test CMD in JupyterHub: odc-stats publish-tasks s3://dea-dev-stats-processing/dbs/ga_ls_wo_3_annual_test_from_airflow.db queue=dea-dev-eks-stats-kk ":1"
# Only submit single message to do the test
SUBIT_TASKS_BASH_COMMAND = [
    f"sleep 600 && odc-stats publish-tasks s3://dea-dev-stats-processing/dbs/ga_ls_wo_3_{FREQUENCY}_test_from_airflow.db queue=dea-dev-eks-stats-kk ':1'",
]

# THE DAG
dag = DAG(
    "landset_c3_wo_summary_submit_tasks",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,  # manually trigger it every year
    catchup=False,
    tags=["k8s", "ls-c3-wofs-summary", "submit-stat-task"],
    params={"labels": {"env": "dev"}},
)

with dag:

    START = DummyOperator(task_id="start-stats-submit-tasks")

    CACHEING = KubernetesPodOperator(
        namespace="processing",
        image=STAT_IMAGE,
        image_pull_policy="IfNotPresent",
        cmds=["bash", "-c"],
        arguments=CACHE_AND_UPLOADING_BASH_COMMAND,
        labels={"step": "task-to-s3"},
        name="datacube-stats",
        task_id="cache-stat-tasks",
        get_logs=True,
        affinity=ONDEMAND_NODE_AFFINITY,
        is_delete_operator_pod=True,
    )

    SUBMITTING = KubernetesPodOperator(
        namespace="processing",
        image=STAT_IMAGE,
        image_pull_policy="IfNotPresent",
        cmds=["bash", "-c"],
        arguments=SUBIT_TASKS_BASH_COMMAND,
        labels={"step": "task-to-sqs"},
        name="datacube-stats",
        task_id="submit-stat-tasks",
        get_logs=True,
        affinity=ONDEMAND_NODE_AFFINITY,
        is_delete_operator_pod=True,
    )

    COMPLETE = DummyOperator(task_id="complete-stats-submit-tasks")

    START >> CACHEING >> SUBMITTING >> COMPLETE
