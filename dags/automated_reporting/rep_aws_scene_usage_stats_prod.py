# -*- coding: utf-8 -*-

"""
aws scene usage stats dag
"""

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.operators.dummy import DummyOperator
from datetime import datetime as dt, timedelta
from infra.variables import REPORTING_IAM_DEA_S3_SECRET
from automated_reporting import k8s_secrets, utilities

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": False,
    "start_date": dt(2022, 4, 29),
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

dag = DAG(
    "rep_aws_scene_usage_stats_prod",
    description="DAG for aws scene usage stats prod",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval="0 14 * * *",  # daily at 1am AEDT
)

ENV = "prod"
ETL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls:v2.4.4"
)


with dag:
    START = DummyOperator(task_id="aws-scene-usage-stats")
    aws_s3_year_wise_scene_usage_ingestion = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo year-wise scene usage ingestion processing: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "s3-usage-year-ingestion",
        ],
        task_id="aws_s3_year_wise_scene_usage_ingestion",
        env_vars={
            "REPORTING_BUCKET": "s3-server-access-logs-schedule",
        },
        secrets=k8s_secrets.db_secrets(ENV)
    )
    aws_s3_region_wise_scene_usage_ingestion = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo region-wise scene usage ingestion processing: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "s3-usage-region-ingestion",
        ],
        task_id="aws_s3_region_wise_scene_usage_ingestion",
        env_vars={
            "REPORTING_BUCKET": "s3-server-access-logs-schedule",
        },
        secrets=k8s_secrets.db_secrets(ENV)
    )
    aws_s3_ip_requester_wise_scene_usage_ingestion = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo ip-requester-wise scene usage ingestion processing: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "s3-usage-ip-requester-ingestion",
        ],
        task_id="aws_s3_ip_requester_wise_scene_usage_ingestion",
        env_vars={
            "REPORTING_BUCKET": "s3-server-access-logs-schedule",
        },
        secrets=k8s_secrets.db_secrets(ENV)
    )
    START >> aws_s3_year_wise_scene_usage_ingestion
    START >> aws_s3_region_wise_scene_usage_ingestion
    START >> aws_s3_ip_requester_wise_scene_usage_ingestion
