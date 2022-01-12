# -*- coding: utf-8 -*-

"""
sara_history dag for prod
"""

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from datetime import datetime as dt, timedelta
from infra.variables import SARA_HISTORY_SECRET_MASTER

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": False,
    "start_date": dt.now() - timedelta(hours=1),
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
    "rep_sara_history",
    description="DAG for sara history ingestion and processing",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval="0 14 1 * *",
)


with dag:
    JOBS1 = [
        "echo AWS Storage job started: $(date)",
        "pip install ga-reporting-etls==1.2.54",
        "jsonresult=`python3 -c 'from nemo_reporting.sara_history import sara_history_ingestion; sara_history_ingestion.task()'`",
    ]
    JOBS2 = [
        "echo AWS Storage job started: $(date)",
        "pip install ga-reporting-etls==1.2.54",
        "jsonresult=`python3 -c 'from nemo_reporting.sara_history import sara_history_processing; sara_history_processing.task()'`",
    ]
    sara_history_ingestion = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS1)],
        name="sarra-history-ingestion",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="sara_history_ingestion",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
        },
    )
    sara_history_processing = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS2)],
        name="sara-history-processing",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="sara_history_processing",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
        },
    )
    sara_history_ingestion >> sara_history_processing
