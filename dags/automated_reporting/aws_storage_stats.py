# -*- coding: utf-8 -*-

"""
aws storage stats dag
"""

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)

from datetime import datetime as dt, timedelta
from airflow.models import Variable
from infra.variables import AWS_STATS_SECRET
import json

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": False,
    "start_date": dt.now() - timedelta(hours=1),
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "secrets": [
        Secret("env", "ACCESS_KEY", AWS_STATS_SECRET, "ACCESS_KEY"),
        Secret("env", "SECRET_KEY", AWS_STATS_SECRET, "SECRET_KEY"),
    ],
}

dag = DAG(
    "aws_storage_stats",
    description="DAG for aws storage stats",
    tags=["aws_storage_stats"],
    default_args=default_args,
    schedule_interval=None,
)

INVENTORY_FILES_JSON = (
    "{{ task_instance.xcom_pull(task_ids='get_inventory_files', key='return_value') }}"
)
with dag:
    JOBS1 = [
        "echo AWS Storage job started: $(date)",
        "pip install ga-reporting-etls==1.2.19",
        "jsonresult=`python3 -c 'from nemo_reporting.aws_storage_stats import downloadinventory; downloadinventory.task()'`",
        "mkdir -p /airflow/xcom/; echo $jsonresult > /airflow/xcom/return.json",
    ]
    k8s_task_download_inventory = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS1)],
        name="write-xcom",
        do_xcom_push=True,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="get_inventory_files",
        get_logs=True,
        env_vars={
            "GOOGLE_ANALYTICS_CREDENTIALS": Variable.get("google_analytics"),
        },
    )
    JOBS2 = [
        "echo AWS Storage job started: $(date)",
        "pip install ga-reporting-etls==1.2.19",
        "jsonresult=`python3 -c 'from nemo_reporting.aws_storage_stats import process; process.task()'`",
    ]
    metrics_task = {}
    json_dict = json.loads(INVENTORY_FILES_JSON)
    for i in range(1, len(json_dict)):
        task_id_key = f"calc_metrics_file{i}"
        file = json_dict[f"'file{i}'"]
        metrics_task[task_id_key] = KubernetesPodOperator(
            namespace="processing",
            image="python:3.8-slim-buster",
            arguments=["bash", "-c", " &&\n".join(JOBS2)],
            name="write-xcom",
            do_xcom_push=True,
            is_delete_operator_pod=True,
            in_cluster=True,
            task_id=task_id_key,
            get_logs=True,
            env_vars={
                "INVENTORY_FILE": "{{ file }}",
            },
        )
        k8s_task_download_inventory >> metrics_task[task_id_key]
