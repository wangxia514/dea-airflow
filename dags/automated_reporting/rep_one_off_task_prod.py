# -*- coding: utf-8 -*-

"""
Automated Reporting - A task to run one-off tasks in the k8s cluster
"""

from datetime import datetime as dt

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from airflow.kubernetes.secret import Secret

from automated_reporting import utilities

from infra.variables import SECRET_ODC_READER_NAME, DB_HOSTNAME, DB_PORT, DB_DATABASE

default_args = {
    "owner": utilities.REPORTING_OWNERS,
    "depends_on_past": False,
    "start_date": dt(2020, 6, 15),
    "email": utilities.REPORTING_ADMIN_EMAILS,
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
        "pip install ga-reporting-etls",
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
            "ODC_DB_DBNAME": DB_DATABASE,
            "KWARGS": "{{dag_run.conf['kwargs']}}",
            "MODULE": "{{dag_run.conf['module']}}",
            "EXECUTION_DATE": "{{ ds }}"
        }
    )
