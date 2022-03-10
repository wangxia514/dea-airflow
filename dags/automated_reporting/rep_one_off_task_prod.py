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

from infra.variables import REPORTING_ODC_DB_SECRET

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt(2020, 6, 15),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": False,
    "retries": 0,
    "secrets": [
        Secret("env", "ODC_DB_HOST", REPORTING_ODC_DB_SECRET, "DB_HOST"),
        Secret("env", "ODC_DB_NAME", REPORTING_ODC_DB_SECRET, "DB_NAME"),
        Secret("env", "ODC_DB_PORT", REPORTING_ODC_DB_SECRET, "DB_PORT"),
        Secret("env", "ODC_DB_USER", REPORTING_ODC_DB_SECRET, "DB_USER"),
        Secret("env", "ODC_DB_PASSWORD", REPORTING_ODC_DB_SECRET, "DB_PASSWORD"),
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
            "KWARGS": "{{dag_run.conf['kwargs']}}",
            "MODULE": "{{dag_run.conf['module']}}",
            "EXECUTION_DATE": "{{ ds }}"
        }
    )
