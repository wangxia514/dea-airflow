# -*- coding: utf-8 -*-

"""
aws cost stats dag for ga-aws-dea-dev
"""

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from datetime import datetime as dt, timedelta
from infra.variables import REPORTING_IAM_DEA_DEV_SECRET
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
        Secret("env", "ACCESS_KEY", REPORTING_IAM_DEA_DEV_SECRET, "ACCESS_KEY"),
        Secret("env", "SECRET_KEY", REPORTING_IAM_DEA_DEV_SECRET, "SECRET_KEY"),
        Secret("env", "DB_HOST", REPORTING_DB_SECRET, "DB_HOST"),
        Secret("env", "DB_NAME", REPORTING_DB_SECRET, "DB_NAME"),
        Secret("env", "DB_PORT", REPORTING_DB_SECRET, "DB_PORT"),
        Secret("env", "DB_USER", REPORTING_DB_SECRET, "DB_USER"),
        Secret("env", "DB_PASSWORD", REPORTING_DB_SECRET, "DB_PASSWORD"),
    ],
}

dag = DAG(
    "rep_aws_cost_stats_prod_ga_aws_dea_dev",
    description="DAG for aws cost stats prod ga-aws-dea-dev",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval="0 14 * * *",  # daily at 1am AEDT
)

ETL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls:v2.4.4"
)

with dag:
    JOBS1 = [
        "echo AWS Cost Stats job started: $(date)",
        "aws-cost-ingestion",
    ]
    aws_s3_cost_stats_ingestion = KubernetesPodOperator(
        namespace="processing",
        image=ETL_IMAGE,
        arguments=["bash", "-c", " &&\n".join(JOBS1)],
        name="aws_s3_cost_stats_ingestion",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="aws_s3_cost_stats_ingestion",
        get_logs=True,
        env_vars={
            "REPORTING_DATE": "{{ ds }}",
        },
        execution_timeout=timedelta(minutes=30),
    )
    aws_s3_cost_stats_ingestion
