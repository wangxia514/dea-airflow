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
from infra.variables import AWS_STATS_SECRET
from infra.variables import AWS_STORAGE_STATS_POD_COUNT

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

with dag:
    JOBS1 = [
        "echo AWS Storage job started: $(date)",
        "pip install ga-reporting-etls==1.2.23",
        "jsonresult=`python3 -c 'from nemo_reporting.aws_storage_stats import downloadinventory; downloadinventory.task()'`",
        "mkdir -p /airflow/xcom/; echo $jsonresult > /airflow/xcom/return.json",
    ]
    JOBS2 = [
        "echo AWS Storage job started: $(date)",
        "pip install ga-reporting-etls==1.2.23",
        "jsonresult=`python3 -c 'from nemo_reporting.aws_storage_stats import process; process.printvar()'`",
        "mkdir -p /airflow/xcom/; echo '{\"status\": \"success\"}' > /airflow/xcom/return.json",
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
            "POD_COUNT": AWS_STORAGE_STATS_POD_COUNT,
        },
    )
    metrics_task = {}
    metrics_task[1] = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS2)],
        name="write-xcom",
        do_xcom_push=True,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="metrics_collector1",
        get_logs=True,
        env_vars={
            "INVENTORY_FILE" : "abc",
        },
    )
    metrics_task[2] = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS2)],
        name="write-xcom",
        do_xcom_push=True,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="metrics_collector2",
        get_logs=True,
        env_vars={
            "INVENTORY_FILE" : "{{ task_instance.xcom_pull(task_ids='get_inventory_files', key='return_value')['metrics_collector_2'] }}",
        },
    )
    metrics_task[3] = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS2)],
        name="write-xcom",
        do_xcom_push=True,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="metrics_collector3",
        get_logs=True,
        env_vars={
            "INVENTORY_FILE" : "{{ task_instance.xcom_pull(task_ids='get_inventory_files', key='return_value')['metrics_collector_3'] }}",
        },
    )
    metrics_task[4] = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS2)],
        name="write-xcom",
        do_xcom_push=True,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="metrics_collector4",
        get_logs=True,
        env_vars={
            "INVENTORY_FILE" : "{{ task_instance.xcom_pull(task_ids='get_inventory_files', key='return_value')['metrics_collector_4'] }}",
        },
    )
    metrics_task[5] = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS2)],
        name="write-xcom",
        do_xcom_push=True,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="metrics_collector5",
        get_logs=True,
        env_vars={
            "INVENTORY_FILE" : "{{ task_instance.xcom_pull(task_ids='get_inventory_files', key='return_value')['metrics_collector_5'] }}",
        },
    )
    metrics_task[6] = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS2)],
        name="write-xcom",
        do_xcom_push=True,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="metrics_collector6",
        get_logs=True,
        env_vars={
            "INVENTORY_FILE" : "{{ task_instance.xcom_pull(task_ids='get_inventory_files', key='return_value')['metrics_collector_6'] }}",
        },
    )
    metrics_task[7] = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS2)],
        name="write-xcom",
        do_xcom_push=True,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="metrics_collector7",
        get_logs=True,
        env_vars={
            "INVENTORY_FILE" : "{{ task_instance.xcom_pull(task_ids='get_inventory_files', key='return_value')['metrics_collector_7'] }}",
        },
    )
    metrics_task[8] = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS2)],
        name="write-xcom",
        do_xcom_push=True,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="metrics_collector8",
        get_logs=True,
        env_vars={
            "INVENTORY_FILE" : "{{ task_instance.xcom_pull(task_ids='get_inventory_files', key='return_value')['metrics_collector_8'] }}",
        },
    )
    metrics_task[9] = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS2)],
        name="write-xcom",
        do_xcom_push=True,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="metrics_collector9",
        get_logs=True,
        env_vars={
            "INVENTORY_FILE" : "{{ task_instance.xcom_pull(task_ids='get_inventory_files', key='return_value')['metrics_collector_9'] }}",
        },
    )
    metrics_task[10] = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS2)],
        name="write-xcom",
        do_xcom_push=True,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="metrics_collector10",
        get_logs=True,
        env_vars={
            "INVENTORY_FILE" : "{{ task_instance.xcom_pull(task_ids='get_inventory_files', key='return_value')['metrics_collector_10'] }}",
        },
    )
    k8s_task_download_inventory >> metrics_task[1]
    # k8s_task_download_inventory >> [metrics_task[1], metrics_task[2], metrics_task[3], metrics_task[4], metrics_task[5], metrics_task[6], metrics_task[7], metrics_task[8], metrics_task[9], metrics_task[10]]
