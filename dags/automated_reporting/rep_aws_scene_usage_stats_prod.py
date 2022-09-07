# -*- coding: utf-8 -*-

"""
aws scene usage stats dag
"""

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
from airflow.operators.dummy import DummyOperator
from datetime import datetime as dt, timedelta
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
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls:v2.10.0"
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
        secrets=k8s_secrets.db_secrets(ENV) + k8s_secrets.s3_server_access_log_bucket + k8s_secrets.iam_dea_secrets,
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
        secrets=k8s_secrets.db_secrets(ENV) + k8s_secrets.s3_server_access_log_bucket + k8s_secrets.iam_dea_secrets,
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
        secrets=k8s_secrets.db_secrets(ENV) + + k8s_secrets.s3_server_access_log_bucket + k8s_secrets.iam_dea_secrets,
    )
    START >> aws_s3_year_wise_scene_usage_ingestion
    START >> aws_s3_region_wise_scene_usage_ingestion
    START >> aws_s3_ip_requester_wise_scene_usage_ingestion
