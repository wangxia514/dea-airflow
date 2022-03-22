# -*- coding: utf-8 -*-

"""
marine ungrouped user stats dag
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
from airflow.models import Variable

from infra.variables import REPORTING_IAM_REP_S3_SECRET
from infra.variables import REPORTING_DB_SECRET

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": True,
    "start_date": datetime(2021, 9, 1),
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
    "rep_elvis_dev",
    description="DAG for testing marine monthly stats jobs",
    tags=["reporting_dev"],
    default_args=default_args,
    schedule_interval="0 14 1 * *",
)

with dag:
    JOBS7 = [
        "echo Elvis ingestion processing: $(date)",
        "pip install ga-reporting-etls==1.10.1",
        "marine-elvis-ingestion",
    ]
    START = DummyOperator(task_id="marine-monthly-stats")
    elvis_ingestion = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS7)],
        name="elvis_ingestion",
        do_xcom_push=False,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="elvis_ingestion",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
            "REPORTING_BUCKET": Variable.get("reporting_s3_bucket"),
        },
    )
    START >> elvis_ingestion
