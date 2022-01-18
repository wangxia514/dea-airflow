# -*- coding: utf-8 -*-

"""
sara_history dag
"""

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from datetime import datetime as dt, timedelta
from infra.variables import SARA_HISTORY_SECRET
from airflow.operators.dummy_operator import DummyOperator

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": False,
    "start_date": dt.now() - timedelta(hours=1),
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 90,
    "retry_delay": timedelta(minutes=1440),
    "secrets": [
        Secret("env", "ACCESS_KEY", SARA_HISTORY_SECRET, "ACCESS_KEY"),
        Secret("env", "SECRET_KEY", SARA_HISTORY_SECRET, "SECRET_KEY"),
        Secret("env", "DB_HOST", SARA_HISTORY_SECRET, "DB_HOST"),
        Secret("env", "DB_USER", SARA_HISTORY_SECRET, "DB_USER"),
        Secret("env", "DB_PASSWORD", SARA_HISTORY_SECRET, "DB_PASSWORD"),
    ],
}

dag = DAG(
    "rep_sara_history",
    description="DAG for nci monthly stats",
    tags=["reporting_dev"],
    default_args=default_args,
    schedule_interval="0 1 1 * *",
)


with dag:
    JOBS1 = [
        "echo AWS Storage job started: $(date)",
        "pip install ga-reporting-etls==1.2.53",
        "jsonresult=`python3 -c 'from nemo_reporting.sara_history import sara_history_ingestion; sara_history_ingestion.task()'`",
    ]
    JOBS2 = [
        "echo AWS Storage job started: $(date)",
        "pip install ga-reporting-etls==1.2.53",
        "jsonresult=`python3 -c 'from nemo_reporting.sara_history import sara_history_processing; sara_history_processing.task()'`",
    ]
    JOBS3 = [
        "echo archie ingestion started: $(date)",
        "pip install ga-reporting-etls==1.2.57",
        "jsonresult=`python3 -c 'from nemo_reporting.archie import archie_ingestion; archie_ingestion.task()'`",
    ]
    JOBS4 = [
        "echo archie processing - SatToEsa started: $(date)",
        "pip install ga-reporting-etls==1.2.57",
        "jsonresult=`python3 -c 'from nemo_reporting.archie import archie_processing; archie_processing.SatToEsaTask()'`",
    ]
    JOBS5 = [
        "echo archie processing - EsaToNciTask started: $(date)",
        "pip install ga-reporting-etls==1.2.57",
        "jsonresult=`python3 -c 'from nemo_reporting.archie import archie_processing; archie_processing.EsaToNciTask()'`",
    ]
    JOBS6 = [
        "echo archie processing - EsaToNciS1Task started: $(date)",
        "pip install ga-reporting-etls==1.2.57",
        "jsonresult=`python3 -c 'from nemo_reporting.archie import archie_processing; archie_processing.EsaToNciS1Task()'`",
    ]
    JOBS7 = [
        "echo archie processing - EsaToNciS2Task started: $(date)",
        "pip install ga-reporting-etls==1.2.57",
        "jsonresult=`python3 -c 'from nemo_reporting.archie import archie_processing; archie_processing.EsaToNciS2Task()'`",
    ]
    JOBS8 = [
        "echo archie processing - EsaToNciS3Task started: $(date)",
        "pip install ga-reporting-etls==1.2.57",
        "jsonresult=`python3 -c 'from nemo_reporting.archie import archie_processing; archie_processing.EsaToNciS3Task()'`",
    ]
    JOBS9 = [
        "echo archie processing - Downloads started: $(date)",
        "pip install ga-reporting-etls==1.2.57",
        "jsonresult=`python3 -c 'from nemo_reporting.archie import archie_processing; archie_processing.Downloads()'`",
    ]
    START = DummyOperator(task_id="nci-monthly-stats") 
    sara_history_ingestion = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS1)],
        name="sara_history_ingestion",
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
        name="sara_history_processing",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="sara_history_processing",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
        },
    )
    archie_ingestion = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS3)],
        name="archie_ingestion",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="archie_ingestion",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
        },
    )
    archie_processing_sattoesa = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS4)],
        name="archie_processing_sattoesa",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="archie_processing_sattoesa",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
        },
    )
    archie_processing_esatoncitask = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS5)],
        name="archie_processing_esatoncitask",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="archie_processing_esatoncitask",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
        },
    )
    archie_processing_esatoncis1task = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS6)],
        name="archie_processing_EsaToNciS1Task",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="archie_processing_EsaToNciS1Task",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
        },
    )
    archie_processing_esatoncis2task = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS7)],
        name="archie_processing_esatoncis2task",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="archie_processing_esatoncis2task",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
        },
    )
    archie_processing_esatoncis3task = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS8)],
        name="archie_processing_esatoncis3task",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="archie_processing_esatoncis3task",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
        },
    )
    archie_processing_downloads = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS9)],
        name="archie_processing_downloads",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="archie_processing_downloads",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
        },
    )
    START >> sara_history_ingestion >> sara_history_processing
    START >> archie_ingestion
    archie_ingestion >> archie_processing_sattoesa
    archie_ingestion >> archie_processing_esatoncitask
    archie_ingestion >> archie_processing_esatoncis1task
    archie_ingestion >> archie_processing_esatoncis2task
    archie_ingestion >> archie_processing_esatoncis3task
    archie_ingestion >> archie_processing_downloads
