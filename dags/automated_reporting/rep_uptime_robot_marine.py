# -*- coding: utf-8 -*-

"""
uptime robot marine dag
"""
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from datetime import datetime as dt, timedelta
from infra.variables import REPORTING_DB_SECRET
from infra.variables import REPORTING_UPTIME_API_SECRET

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": False,
    "start_date": dt(2022, 2, 22),
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(days=1),
    "secrets": [
        Secret("env", "API_KEY", REPORTING_UPTIME_API_SECRET, "API_KEY"),
        Secret("env", "DB_HOST", REPORTING_DB_SECRET, "DB_HOST"),
        Secret("env", "DB_NAME", REPORTING_DB_SECRET, "DB_NAME"),
        Secret("env", "DB_PORT", REPORTING_DB_SECRET, "DB_PORT"),
        Secret("env", "DB_USER", REPORTING_DB_SECRET, "DB_USER"),
        Secret("env", "DB_PASSWORD", REPORTING_DB_SECRET, "DB_PASSWORD"),
    ],
}

dag = DAG(
    "rep_uptime_robot_marine_prod",
    description="DAG for uptime robot marine",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval="0 14 * * *",  # daily at 1am AEDT
)

with dag:
    JOBS1 = [
        "echo uptime robot processing marine started: $(date)",
        "pip install ga-reporting-etls==1.7.10",
        "jsonresult=`python3 -c 'from nemo_reporting.uptime_robot import marine_uptime_robot_processing; marine_uptime_robot_processing.task()'`",
    ]
    uptime_robot_processing_marine = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS1)],
        name="uptime_robot_processing_marine",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="uptime_robot_processing_marine",
        get_logs=True,
        env_vars={
            "MONITORING_IDS": "785233301, 785236465, 785236456, 785233316, 785233317, 785233343, 785233341, 785251927, 785251954, 785252068, 785252069, 790085518",
            "EXECUTION_DATE": "{{ ds }}",
        },
    )
    uptime_robot_processing_marine
