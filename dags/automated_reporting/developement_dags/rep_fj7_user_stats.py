# -*- coding: utf-8 -*-

"""
fj7 dag
"""

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from datetime import datetime, timedelta
from infra.variables import SARA_HISTORY_SECRET

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": True,
    "start_date": datetime(2021, 10, 1),
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 90,
    "retry_delay": timedelta(days=1),
    "secrets": [
        Secret("env", "ACCESS_KEY", SARA_HISTORY_SECRET, "ACCESS_KEY"),
        Secret("env", "SECRET_KEY", SARA_HISTORY_SECRET, "SECRET_KEY"),
        Secret("env", "DB_HOST", SARA_HISTORY_SECRET, "DB_HOST"),
        Secret("env", "DB_USER", SARA_HISTORY_SECRET, "DB_USER"),
        Secret("env", "DB_PASSWORD", SARA_HISTORY_SECRET, "DB_PASSWORD"),
    ],
}

dag = DAG(
    "rep_fj7_ungrouped_user_stats",
    description="DAG for fj7 ungrouped user stats",
    tags=["reporting_dev"],
    default_args=default_args,
    schedule_interval="0 14 1 * *",
)


with dag:
    JOBS1 = [
        "echo fj7 user stats ingestion: $(date)",
        "pip install ga-reporting-etls==1.4.2",
        "jsonresult=`python3 -c 'from nemo_reporting.user_stats import fj7_user_stats_ingestion; fj7_user_stats_ingestion.task()'`",
        "mkdir -p /airflow/xcom/; echo $jsonresult > /airflow/xcom/return.json",
    ]
    JOBS2 = [
        "echo fj7 user stats processing: $(date)",
        "pip install ga-reporting-etls==1.4.2",
        "jsonresult=`python3 -c 'from nemo_reporting.user_stats import fj7_user_stats_processing; fj7_user_stats_processing.task()'`",
    ]
    fj7_ingestion = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS1)],
        name="write-xcom",
        do_xcom_push=True,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="fj7_ingestion",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
            "FILE_TO_PROCESS": "fj7",
        },
    )
    fj7_processing = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS2)],
        name="fj7_processing",
        do_xcom_push=False,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="fj7_processing",
        get_logs=True,
        env_vars={
            "AGGREGATION_MONTHS" : "{{ task_instance.xcom_pull(task_ids='fj7_ingestion') }}",
            "EXECUTION_DATE": "{{ ds }}",
        },
    )
    fj7_ingestion >> fj7_processing
