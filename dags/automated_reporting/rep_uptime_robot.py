# -*- coding: utf-8 -*-

"""
uptime robot dea dag
"""

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from datetime import datetime as dt, timedelta
from infra.variables import SARA_HISTORY_SECRET
from infra.variables import UPTIME_ROBOT_SECRET

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": False,
    "start_date": dt(2022, 2, 11),
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "secrets": [
        Secret("env", "DB_HOST", SARA_HISTORY_SECRET, "DB_HOST"),
        Secret("env", "DB_USER", SARA_HISTORY_SECRET, "DB_USER"),
        Secret("env", "DB_PASSWORD", SARA_HISTORY_SECRET, "DB_PASSWORD"),
        Secret("env", "API_KEY", UPTIME_ROBOT_SECRET, "API_KEY"),
    ],
}

dag = DAG(
    "uptime_robot_dea",
    description="DAG for uptime robot dea",
    tags=["reporting_dev"],
    default_args=default_args,
    schedule_interval="0 14 * * *",  # daily at 1am AEDT
)

with dag:
    JOBS1 = [
        "echo uptime robot processing dea started: $(date)",
        "pip install ga-reporting-etls==1.5.0",
        "jsonresult=`python3 -c 'from nemo_reporting.import uptime_robot.dea_uptime_robot_processing; dea_uptime_robot_processing.task()'`",
    ]
    uptime_robot_processing_dea = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS1)],
        name="uptime_robot_processing_dea",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="uptime_robot_processing_dea",
        get_logs=True,
        env_vars={
            "MONITORING_IDS": "784117804, 784122998, 784122995",
        },
    )
    uptime_robot_processing_dea
