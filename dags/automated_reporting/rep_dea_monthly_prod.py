# -*- coding: utf-8 -*-

"""
dea ungrouped user stats dag
"""
# pylint: disable=C0301
# pylint: disable=W0104
# pylint: disable=E0401
from datetime import datetime, timedelta
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from airflow.operators.dummy import DummyOperator
from infra.variables import SARA_HISTORY_SECRET_MASTER

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": True,
    "start_date": datetime(2022, 9, 1),
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 90,
    "retry_delay": timedelta(days=1),
    "secrets": [
        Secret("env", "ACCESS_KEY", SARA_HISTORY_SECRET_MASTER, "ACCESS_KEY"),
        Secret("env", "SECRET_KEY", SARA_HISTORY_SECRET_MASTER, "SECRET_KEY"),
        Secret("env", "DB_HOST", SARA_HISTORY_SECRET_MASTER, "DB_HOST"),
        Secret("env", "DB_USER", SARA_HISTORY_SECRET_MASTER, "DB_USER"),
        Secret("env", "DB_PASSWORD", SARA_HISTORY_SECRET_MASTER, "DB_PASSWORD"),
    ],
}

dag = DAG(
    "rep_dea_monthly_prod",
    description="DAG for dea ungrouped user stats",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval="0 14 1 * *",
)


with dag:
    JOBS1 = [
        "echo fk4 user stats ingestion: $(date)",
        "pip install ga-reporting-etls==1.4.4",
        "jsonresult=`python3 -c 'from nemo_reporting.user_stats import fk4_user_stats_ingestion; fk4_user_stats_ingestion.task()'`",
        "mkdir -p /airflow/xcom/; echo $jsonresult > /airflow/xcom/return.json",
    ]
    JOBS2 = [
        "echo fk4 user stats processing: $(date)",
        "pip install ga-reporting-etls==1.4.4",
        "jsonresult=`python3 -c 'from nemo_reporting.user_stats import fk4_user_stats_processing; fk4_user_stats_processing.task()'`",
    ]
    JOBS3 = [
        "echo rs0 user stats ingestion: $(date)",
        "pip install ga-reporting-etls==1.4.4",
        "jsonresult=`python3 -c 'from nemo_reporting.user_stats import rs0_user_stats_ingestion; rs0_user_stats_ingestion.task()'`",
        "mkdir -p /airflow/xcom/; echo $jsonresult > /airflow/xcom/return.json",
    ]
    JOBS4 = [
        "echo rs0 user stats processing: $(date)",
        "pip install ga-reporting-etls==1.4.4",
        "jsonresult=`python3 -c 'from nemo_reporting.user_stats import rs0_user_stats_processing; rs0_user_stats_processing.task()'`",
    ]
    START = DummyOperator(task_id="dea-ungrouped-user-stats")
    fk4_ingestion = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS1)],
        name="write-xcom",
        do_xcom_push=True,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="fk4_ingestion",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
            "FILE_TO_PROCESS": "fk4",
        },
    )
    fk4_processing = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS2)],
        name="fk4_processing",
        do_xcom_push=False,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="fk4_processing",
        get_logs=True,
        env_vars={
            "AGGREGATION_MONTHS" : "{{ task_instance.xcom_pull(task_ids='fk4_ingestion') }}",
            "EXECUTION_DATE": "{{ ds }}",
        },
    )
    rs0_ingestion = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS3)],
        name="write-xcom",
        do_xcom_push=True,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="rs0_ingestion",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
            "FILE_TO_PROCESS": "rs0",
        },
    )
    rs0_processing = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS4)],
        name="rs0_processing",
        do_xcom_push=False,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="rs0_processing",
        get_logs=True,
        env_vars={
            "AGGREGATION_MONTHS" : "{{ task_instance.xcom_pull(task_ids='rs0_ingestion') }}",
            "EXECUTION_DATE": "{{ ds }}",
        },
    )
    START >> fk4_ingestion >> fk4_processing
    START >> rs0_ingestion >> rs0_processing
