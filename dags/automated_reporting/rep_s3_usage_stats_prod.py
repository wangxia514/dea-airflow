# -*- coding: utf-8 -*-

"""
aws usage stats dag prod
"""

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
from datetime import datetime as dt, timedelta
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
}

ENV = "prod"
ETL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls:v2.13.0"
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
        secrets=k8s_secrets.db_secrets(ENV) + k8s_secrets.iam_dea_secrets + k8s_secrets.s3_server_access_log_bucket,
    )
    aws_s3_usage_stats_ingestion
