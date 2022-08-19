# -*- coding: utf-8 -*-
"""
aws cost stats dag for ga-aws-dea
"""
# The DAG object; we'll need this to instantiate a DAG
from datetime import datetime as dt
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from infra.variables import REPORTING_IAM_SQS_SECRET

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": False,
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "start_date": dt(2022, 8, 17),
    "secrets": [
        Secret("env", "ACCESS_KEY", REPORTING_IAM_SQS_SECRET, "ACCESS_KEY"),
        Secret("env", "SECRET_KEY", REPORTING_IAM_SQS_SECRET, "SECRET_KEY"),
    ],
}

dag = DAG(
    "rep_usgs_l1_nrt_downloads",
    description="DAG for usgs_l1_nrt_downloads dev",
    tags=["reporting_dev"],
    default_args=default_args,
    schedule_interval=None,
)

ETL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls-dev:latest"
)

with dag:
    JOBS1 = [
        "echo usgs-l1-nrt-downloads job started: $(date)",
        "mkdir -p /airflow/xcom/",
        "usgs-l1-nrt-downloads /airflow/xcom/return.json",
    ]
    usgs_l1_nrt_downloads = KubernetesPodOperator(
        namespace="processing",
        image=ETL_IMAGE,
        arguments=["bash", "-c", " &&\n".join(JOBS1)],
        name="usgs_l1_nrt_downloads",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="usgs_l1_nrt_downloads",
        get_logs=True,
        env_vars={
            "QUEUE_NAME": "automated-reporting-ls-l1-nrt",
        }
    )
    usgs_l1_nrt_downloads
