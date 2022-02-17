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
from infra.variables import SARA_HISTORY_SECRET_MASTER
from infra.variables import UPTIME_ROBOT_SECRET

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": False,
    "start_date": dt(2022, 2, 11),
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(days=1),
    "secrets": [
        Secret("env", "DB_HOST", SARA_HISTORY_SECRET_MASTER, "DB_HOST"),
        Secret("env", "DB_USER", SARA_HISTORY_SECRET_MASTER, "DB_USER"),
        Secret("env", "DB_PASSWORD", SARA_HISTORY_SECRET_MASTER, "DB_PASSWORD"),
        Secret("env", "API_KEY", UPTIME_ROBOT_SECRET, "API_KEY"),
    ],
}

dag = DAG(
    "uptime_robot_marine_prod",
    description="DAG for uptime robot marine",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval="0 14 * * *",  # daily at 1am AEDT
)

with dag:
    JOBS1 = [
        "echo uptime robot processing marine started: $(date)",
        "pip install ga-reporting-etls==1.5.3",
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
