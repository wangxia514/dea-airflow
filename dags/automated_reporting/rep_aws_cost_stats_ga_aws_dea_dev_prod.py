# -*- coding: utf-8 -*-

"""
aws cost stats dag for ga-aws-dea-dev
"""

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
from datetime import datetime as dt, timedelta
from automated_reporting import k8s_secrets, utilities

default_args = {
    "owner": utilities.REPORTING_OWNERS,
    "depends_on_past": False,
    "start_date": dt(2022, 4, 4),
    "email": utilities.REPORTING_ADMIN_EMAILS,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "rep_aws_cost_stats_prod_ga_aws_dea_dev",
    description="DAG for aws cost stats prod ga-aws-dea-dev",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval="0 14 * * *",  # daily at 1am AEDT
)

ENV = "prod"
ETL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls:v2.13.0"
)

with dag:
    aws_s3_cost_stats_ingestion = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo AWS Cost Stats job started: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "aws-cost-ingestion",
        ],
        task_id="aws_s3_cost_stats_ingestion",
        env_vars={
            "REPORTING_DATE": "{{ ds }}",
        },
        secrets=k8s_secrets.db_secrets(ENV) + k8s_secrets.iam_dea_dev_secrets,
    )
    aws_s3_cost_stats_ingestion
