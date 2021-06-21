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
    AWS_DEFAULT_REGION,
)
from infra.sqs_queues import LS_C3_WO_SUMMARY_QUEUE
from infra.pools import DEA_NEWDATA_PROCESSING_POOL
from infra.iam_roles import DB_DUMP_S3_ROLE

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
        "AWS_DEFAULT_REGION": AWS_DEFAULT_REGION,
    },
    # Lift secrets into environment variables
    "secrets": [
        Secret("env", "DB_USERNAME", SECRET_ODC_READER_NAME, "postgres-username"),
        Secret("env", "DB_PASSWORD", SECRET_ODC_READER_NAME, "postgres-password"),
    ],
}

# annual summary input is the daily WOfS
PRODUCT_NAME = "ga_ls_wo_3"
FREQUENCY = "annual" # if we split the summary of WOfS summaries task in another DAG, this value could be a hardcode value

# only grab 2009 data to speed up test, the search expression may open to the user later
CACHE_AND_UPLOADING_BASH_COMMAND = [
    "bash",
    "-c",
    f"odc-stats save-tasks '{PRODUCT_NAME}' --year=2009 --grid au-30 --frequency '{FREQUENCY}' ga_ls_wo_3_'{FREQUENCY}'.db",
    "&&", 
    f"s3 cp ga_ls_wo_3_'{FREQUENCY}'.db s3://dea-dev-stats-processing/dbs/ga_ls_wo_3_'{FREQUENCY}_test_from_airflow'.db",
]

SUBIT_TASKS_BASH_COMMAND = [
    "bash",
    "-c",
    f"odc-stats publish-tasks ga_ls_wo_3_'{FREQUENCY}'.db queue '{LS_C3_WO_SUMMARY_QUEUE}'",
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

    START = DummyOperator(task_id="start-stats-tasks")

    CACHEING = KubernetesPodOperator(
        namespace="processing",
        image=STAT_IMAGE,
        image_pull_policy="IfNotPresent",
        arguments=CACHE_AND_UPLOADING_BASH_COMMAND,
        annotations={"iam.amazonaws.com/role": DB_DUMP_S3_ROLE},
        labels={"step": "task-to-sqs"},
        name="datacube-stats",
        task_id="submit-stat-task",
        get_logs=True,
        affinity=ONDEMAND_NODE_AFFINITY,
        is_delete_operator_pod=True,
    )

    COMPLETE = DummyOperator(task_id="tasks-stats-complete")

    START >> CACHEING >> COMPLETE
