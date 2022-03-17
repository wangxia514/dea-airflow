# -*- coding: utf-8 -*-

"""
cophub monthly dag for prod
"""

# The DAG object; we'll need this to instantiate a DAG
from datetime import datetime, timedelta
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from airflow.operators.dummy import DummyOperator
from infra.variables import REPORTING_IAM_REP_S3_SECRET
from infra.variables import REPORTING_DB_SECRET

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": False,
    "start_date": datetime(2022, 3, 1),
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 90,
    "retry_delay": timedelta(days=1),
    "secrets": [
        Secret("env", "ACCESS_KEY", REPORTING_IAM_REP_S3_SECRET, "ACCESS_KEY"),
        Secret("env", "SECRET_KEY", REPORTING_IAM_REP_S3_SECRET, "SECRET_KEY"),
        Secret("env", "DB_HOST", REPORTING_DB_SECRET, "DB_HOST"),
        Secret("env", "DB_NAME", REPORTING_DB_SECRET, "DB_NAME"),
        Secret("env", "DB_PORT", REPORTING_DB_SECRET, "DB_PORT"),
        Secret("env", "DB_USER", REPORTING_DB_SECRET, "DB_USER"),
        Secret("env", "DB_PASSWORD", REPORTING_DB_SECRET, "DB_PASSWORD"),
    ],
}

dag = DAG(
    "rep_cophub_monthly_prod",
    description="DAG for sara history ingestion and processing",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval="0 14 1 * *",
)

with dag:
    JOBS1 = [
        "echo Sara history ingestion started: $(date)",
        "pip install ga-reporting-etls==1.8.7",
        "jsonresult=`python3 -c 'from nemo_reporting.sara_history import sara_history_ingestion; sara_history_ingestion.task()'`",
    ]
    JOBS2 = [
        "echo Sara history processing: $(date)",
        "pip install ga-reporting-etls==1.8.7",
        "jsonresult=`python3 -c 'from nemo_reporting.sara_history import sara_history_processing; sara_history_processing.task()'`",
    ]
    JOBS3 = [
        "echo Archie ingestion started: $(date)",
        "pip install ga-reporting-etls==1.8.7",
        "jsonresult=`python3 -c 'from nemo_reporting.archie import archie_ingestion; archie_ingestion.task()'`",
    ]
    JOBS4 = [
        "echo Archie processing - SatToEsa started: $(date)",
        "pip install ga-reporting-etls==1.8.7",
        "jsonresult=`python3 -c 'from nemo_reporting.archie import archie_processing; archie_processing.SatToEsaTask()'`",
    ]
    JOBS5 = [
        "echo Archie processing - EsaToNciTask started: $(date)",
        "pip install ga-reporting-etls==1.8.7",
        "jsonresult=`python3 -c 'from nemo_reporting.archie import archie_processing; archie_processing.EsaToNciTask()'`",
    ]
    JOBS6 = [
        "echo Archie processing - EsaToNciS1Task started: $(date)",
        "pip install ga-reporting-etls==1.8.7",
        "jsonresult=`python3 -c 'from nemo_reporting.archie import archie_processing; archie_processing.EsaToNciS1Task()'`",
    ]
    JOBS7 = [
        "echo Archie processing - EsaToNciS2Task started: $(date)",
        "pip install ga-reporting-etls==1.8.7",
        "jsonresult=`python3 -c 'from nemo_reporting.archie import archie_processing; archie_processing.EsaToNciS2Task()'`",
    ]
    JOBS8 = [
        "echo Archie processing - EsaToNciS3Task started: $(date)",
        "pip install ga-reporting-etls==1.8.7",
        "jsonresult=`python3 -c 'from nemo_reporting.archie import archie_processing; archie_processing.EsaToNciS3Task()'`",
    ]
    JOBS9 = [
        "echo Archie processing - Downloads started: $(date)",
        "pip install ga-reporting-etls==1.8.7",
        "jsonresult=`python3 -c 'from nemo_reporting.archie import archie_processing; archie_processing.DownloadsTask()'`",
    ]
    JOBS10 = [
        "echo FJ7 disk usage download and processing: $(date)",
        "pip install ga-reporting-etls==1.8.7",
        "jsonresult=`python3 -c 'from nemo_reporting.fj7_storage import fj7_disk_usage; fj7_disk_usage.task()'`",
    ]
    JOBS11 = [
        "echo FJ7 user stats ingestion: $(date)",
        "pip install ga-reporting-etls==1.8.7",
        "jsonresult=`python3 -c 'from nemo_reporting.user_stats import fj7_user_stats_ingestion; fj7_user_stats_ingestion.task()'`",
        "mkdir -p /airflow/xcom/; echo $jsonresult > /airflow/xcom/return.json",
    ]
    JOBS12 = [
        "echo FJ7 user stats processing: $(date)",
        "pip install ga-reporting-etls==1.8.7",
        "jsonresult=`python3 -c 'from nemo_reporting.user_stats import fj7_user_stats_processing; fj7_user_stats_processing.task()'`",
    ]
    START = DummyOperator(task_id="nci-monthly-stats")
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
        name="archie_processing_esatoncis1task",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="archie_processing_esatoncis1task",
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
    fj7_disk_usage = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS10)],
        name="fj7_disk_usage",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="fj7_disk_usage",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
        },
    )
    fj7_ungrouped_user_stats_ingestion = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS11)],
        name="write-xcom",
        do_xcom_push=True,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="fj7_ungrouped_user_stats_ingestion",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
            "FILE_TO_PROCESS": "fj7",
        },
    )
    fj7_ungrouped_user_stats_processing = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS12)],
        name="fj7_ungrouped_user_stats_processing",
        do_xcom_push=False,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="fj7_ungrouped_user_stats_processing",
        get_logs=True,
        env_vars={
            "AGGREGATION_MONTHS": "{{ task_instance.xcom_pull(task_ids='fj7_ungrouped_user_stats_ingestion') }}",
            "EXECUTION_DATE": "{{ ds }}",
        },
    )
    START >> sara_history_ingestion >> sara_history_processing
    START >> fj7_ungrouped_user_stats_ingestion >> fj7_ungrouped_user_stats_processing
    START >> archie_ingestion
    START >> fj7_disk_usage
    archie_ingestion >> archie_processing_sattoesa
    archie_ingestion >> archie_processing_esatoncitask
    archie_ingestion >> archie_processing_esatoncis1task
    archie_ingestion >> archie_processing_esatoncis2task
    archie_ingestion >> archie_processing_esatoncis3task
    archie_ingestion >> archie_processing_downloads
