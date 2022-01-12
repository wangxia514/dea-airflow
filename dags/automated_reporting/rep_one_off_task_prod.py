# -*- coding: utf-8 -*-

"""
Automated Reporting - ASB - Google Analytics
"""

import json
from datetime import datetime as dt, timedelta

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from airflow.models import Variable
from infra import connections as infra_connections
from automated_reporting.utilities import helpers
from airflow.hooks.base_hook import BaseHook
from airflow.kubernetes.secret import Secret

from infra.variables import SECRET_ODC_READER_NAME, DB_HOSTNAME, DB_PORT

REP_CONN_STR = Variable.get("db_rep_secret")
ODC_CONN_STR = json.dumps(
    helpers.parse_connection(
        BaseHook.get_connection(infra_connections.DB_ODC_READER_CONN)
    )
)

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt(2020, 6, 15),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": False,
    "retries": 0,
    "secrets": [
        Secret("env", "ODC_DB_USER", SECRET_ODC_READER_NAME, "postgres-username"),
        Secret("env", "ODC_DB_PASSWORD", SECRET_ODC_READER_NAME, "postgres-password"),
    ],
}

dag = DAG(
    "rep_one_off_task_prod",
    description="DAG for running one off tasks",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval=None,
)

with dag:

    # fmt: off
    JOBS = [
        "echo Reporting task started: $(date)",
        f"pip install ga-reporting-etls",
        "echo $ODC_DB_HOST",
        "python3 -m nemo_reporting.$MODULE",
        "echo Reporting task completed: $(date)",
    ]

    task = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS)],
        name="one_off_task",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="one_off_task",
        get_logs=True,
        env_vars={
            "ODC_DB_HOST": DB_HOSTNAME,
            "ODC_DB_PORT": DB_PORT,
            "KWARGS": "{{dag_run.conf['kwargs']}}",
            "MODULE": "{{dag_run.conf['module']}}",
            "EXECUTION_DATE": "{{ ds }}"
        }
    )
