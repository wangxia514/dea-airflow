# -*- coding: utf-8 -*-

"""
aws usage stats dag prod
"""

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
from airflow.kubernetes.secret import Secret
from datetime import datetime as dt, timedelta
from infra.variables import REPORTING_IAM_DEA_S3_SECRET
from automated_reporting import k8s_secrets, utilities

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": False,
    "start_date": dt(2022, 3, 19),
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "secrets": [
        Secret("env", "ACCESS_KEY", REPORTING_IAM_DEA_S3_SECRET, "ACCESS_KEY"),
        Secret("env", "SECRET_KEY", REPORTING_IAM_DEA_S3_SECRET, "SECRET_KEY"),
    ],
}

ENV = "prod"
ETL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls:v2.4.4"
)

dag = DAG(
    "rep_aws_usage_stats_prod",
    description="DAG for aws usage stats prod",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval="0 14 * * *",  # daily at 1am AEDT
)

with dag:
    aws_s3_usage_stats_ingestion = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo AWS Usage job started: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "aws-usage-ingestion",
        ],
        task_id="aws_s3_usage_stats_ingestion",
        env_vars={
            "REPORTING_BUCKET": "s3-server-access-logs-schedule",
        },
        secrets=k8s_secrets.db_secrets(ENV),
    )
    aws_s3_usage_stats_ingestion
