# -*- coding: utf-8 -*-

"""
Operational monitoring of ESA production systems
"""

# The DAG object; we'll need this to instantiate a DAG
from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)

from airflow.models import Variable

REP_CONN_STR = Variable.get("db_rep_secret")
SCIHUB_CREDENTIALS_STR = Variable.get("copernicus_api_password")
S3_CREDENTIALS_STR = Variable.get("reporting_s3_secret")

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": datetime(2022, 3, 1),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "rep_esa_monitoring_prod",
    description="DAG ESA production monitoring",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval=timedelta(minutes=15),
)

with dag:

    SCIHUB_ACQS_TASK = [
        "echo Get SCIHUB acquisitions: $(date)",
        "pip install ga-reporting-etls",
        "mkdir -p /airflow/xcom/",
        "python3 -c 'from nemo_reporting.esa_monitoring import s2_acquisitions; \
            s2_acquisitions.task_env(json_output=\"/airflow/xcom/return.json\")'",
    ]
    scihub_s2_acquisitions = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(SCIHUB_ACQS_TASK)],
        name="scihub_s2_acquisitions",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="scihub_s2_acquisitions",
        get_logs=True,
        task_concurrency=1,
        do_xcom_push=True,
        env_vars={
            "SCIHUB_CREDENTIALS": SCIHUB_CREDENTIALS_STR,
            "S3_CREDENTIALS": S3_CREDENTIALS_STR,
            "DB_CREDS": REP_CONN_STR,
            "EXECUTION_DATE": "{{  dag_run.end_date | ts  }}",
        },
    )

    INSERT_ACQS_TASK = [
        "echo Insert S2 acquisitions: $(date)",
        "pip install ga-reporting-etls",
        "jsonresult=`python3 -c 'from nemo_reporting.esa_monitoring import s2_inserts; s2_inserts.task_env()'`",
        "mkdir -p /airflow/xcom/; echo $jsonresult > /airflow/xcom/return.json",
    ]
    insert_s2_acquisitions = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(INSERT_ACQS_TASK)],
        name="insert_s2_acquisitions",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="insert_s2_acquisitions",
        get_logs=True,
        env_vars={
            "S3_CREDENTIALS": S3_CREDENTIALS_STR,
            "DB_CREDS": REP_CONN_STR,
            "S2_ACQ_XCOM": "{{ task_instance.xcom_pull(task_ids='scihub_s2_acquisitions', key='return_value') }}",
        },
    )

    scihub_s2_acquisitions >> insert_s2_acquisitions
