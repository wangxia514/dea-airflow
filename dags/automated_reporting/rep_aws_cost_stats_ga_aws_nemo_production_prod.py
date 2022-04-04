# -*- coding: utf-8 -*-

"""
aws cost stats dag for ga-aws-nemo-production
"""

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from datetime import datetime as dt, timedelta
from infra.variables import REPORTING_IAM_REP_S3_SECRET
from infra.variables import REPORTING_DB_SECRET

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": False,
    "start_date": dt(2022, 4, 4),
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
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
    "rep_aws_cost_stats_prod_ga-aws-dea",
    description="DAG for aws cost stats prod ga-aws-dea",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval="0 14 * * *",  # daily at 1am AEDT
)

with dag:
    JOBS1 = [
        "echo AWS Usage job started: $(date)",
        "pip install ga-reporting-etls==1.15.0",
        "jsonresult=`python3 -c 'from nemo_reporting.aws_cost_stats import aws_cost_stats_ingestion; aws_cost_stats_ingestion.task()'`",
    ]
    aws_s3_cost_stats_ingestion = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS1)],
        name="aws_s3_cost_stats_ingestion",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="aws_s3_cost_stats_ingestion",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
        },
    )
    aws_s3_cost_stats_ingestion
