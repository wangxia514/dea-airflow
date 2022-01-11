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
import json

REP_CONN_STR = Variable.get("db_rep_secret")
ODC_CONN_STR = json.dumps(
    helpers.parse_connection(
        BaseHook.get_connection(infra_connections.DB_ODC_READER_CONN)
    )
)
REPORTING_PACKAGE_VERSION = "1.1.8"

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt(2020, 6, 15),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=60),
}

dag = DAG(
    "rep_one_off_task_prod",
    description="DAG for running one off tasks",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval=None,
)

with dag:

    CONF_STR = {{dag_run.conf}}  # pylint: disable-msg=E0602

    # fmt: off
    JOBS = [
        "echo Reporting task started: $(date)",
        f"pip install ga-reporting-etls=={REPORTING_PACKAGE_VERSION}",
        "echo $CONF",
        "python3 -m nemo_reporting.{{ dag_run.conf['module'] }}",
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
            "REP_CONN": REP_CONN_STR,
            "ODC_CONN": ODC_CONN_STR,
            "CONF": CONF_STR,
            "EXECUTION_DATE": "{{ ds }}",
        }
    )
