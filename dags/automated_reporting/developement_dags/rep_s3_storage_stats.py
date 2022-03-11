# -*- coding: utf-8 -*-

"""
aws storage stats dag
"""

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.operators.python_operator import PythonOperator
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from datetime import datetime as dt, timedelta
import json
from infra.variables import REPORTING_IAM_DEA_S3_SECRET
from infra.variables import REPORTING_DB_DEV_SECRET
from infra.variables import AWS_STORAGE_STATS_POD_COUNT

REPORTING_PACKAGE = 1.7.10

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": False,
    "start_date": dt(2021, 12, 19),
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "secrets": [
        Secret("env", "ACCESS_KEY", REPORTING_IAM_DEA_S3_SECRET, "ACCESS_KEY"),
        Secret("env", "SECRET_KEY", REPORTING_IAM_DEA_S3_SECRET, "SECRET_KEY"),
        Secret("env", "DB_HOST", REPORTING_DB_DEV_SECRET, "DB_HOST"),
        Secret("env", "DB_NAME", REPORTING_DB_DEV_SECRET, "DB_NAME"),
        Secret("env", "DB_PORT", REPORTING_DB_DEV_SECRET, "DB_PORT"),
        Secret("env", "DB_USER", REPORTING_DB_DEV_SECRET, "DB_USER"),
        Secret("env", "DB_PASSWORD", REPORTING_DB_DEV_SECRET, "DB_PASSWORD"),
    ],
}

dag = DAG(
    "rep_aws_storage_stats_dev",
    description="DAG for aws storage stats",
    tags=["reporting_dev"],
    default_args=default_args,
    schedule_interval="0 14 * * *",  # daily at 1am AEDT
)


def aggregate_metrics_from_collections(task_instance):
    """ pull metrics from the colletors, aggregate and xcom_push """
    # Do a xcompull from 10 collectors based on the pod count
    latest_size_dict = {}
    old_size_dict = {}
    latest_count_dict = {}
    old_count_dict = {}

    for i in range(1, int(AWS_STORAGE_STATS_POD_COUNT) + 1):
        task_id = f"collection{i}"
        collection_metrics = task_instance.xcom_pull(task_ids=task_id)
        collection_metrics_v2 = str(collection_metrics).replace("'", '"')
        data = json.loads(collection_metrics_v2)
        # Get non zero elements of latest size
        for key, value in data["latestsize"].items():
            if float(value) > 0.0:
                if key in latest_size_dict:
                    latest_size_dict[key] = latest_size_dict[key] + float(value)
                else:
                    latest_size_dict[key] = float(value)
        # Get non zero elements of latest count
        for key, value in data["latestcount"].items():
            if float(value) > 0.0:
                if key in latest_count_dict:
                    latest_count_dict[key] = latest_count_dict[key] + float(value)
                else:
                    latest_count_dict[key] = float(value)
        # Get non zero elements of old size
        for key, value in data["oldsize"].items():
            if float(value) > 0.0:
                if key in old_size_dict:
                    old_size_dict[key] = old_size_dict[key] + float(value)
                else:
                    old_size_dict[key] = float(value)
        # Get non zero elements of old size
        for key, value in data["oldcount"].items():
            if float(value) > 0.0:
                if key in old_count_dict:
                    old_count_dict[key] = old_count_dict[key] + float(value)
                else:
                    old_count_dict[key] = float(value)
    # totalsizelatest = data["totalsizelatest"]
    # totalsizeold = data["totalsizeold"]
    # totalcountlatest = data["totalcountlatest"]
    # totalcountold = data["totalcountold"]
    result = {}
    result["latestsize"] = latest_size_dict
    result["latestcount"] = latest_count_dict
    result["oldsize"] = old_size_dict
    result["oldcount"] = old_count_dict
    json_result = json.dumps(result)
    task_instance.xcom_push(key="metrics", value=json_result)
    # Now do a xcom push of the final result


with dag:
    JOBS1 = [
        "echo AWS Storage job started: $(date)",
        f"pip install ga-reporting-etls=={REPORTING_PACKAGE}",
        "jsonresult=`python3 -c 'from nemo_reporting.aws_storage_stats import downloadinventory; downloadinventory.task()'`",
        "mkdir -p /airflow/xcom/; echo $jsonresult > /airflow/xcom/return.json",
    ]
    JOBS2 = [
        "echo AWS Storage job started: $(date)",
        f"pip install ga-reporting-etls=={REPORTING_PACKAGE}",
        "jsonresult=`python3 -c 'from nemo_reporting.aws_storage_stats import process; process.calc_size_and_count()'`",
        "mkdir -p /airflow/xcom/; echo $jsonresult > /airflow/xcom/return.json",
    ]
    JOBS3 = [
        "echo AWS Storage job started: $(date)",
        f"pip install ga-reporting-etls=={REPORTING_PACKAGE}",
        "jsonresult=`python3 -c 'from nemo_reporting.aws_storage_stats import etl; etl.task()'`",
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
            "EXECUTION_DATE": "{{ ds }}",
        },
    )

    aggregate_metrics = PythonOperator(
        task_id="aggregate_metrics",
        python_callable=aggregate_metrics_from_collections,
        provide_context=True,
    )

    push_to_db = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS3)],
        name="write-xcom",
        do_xcom_push=True,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="push_to_db",
        get_logs=True,
        env_vars={
            "METRICS" : "{{ task_instance.xcom_pull(task_ids='aggregate_metrics', key='metrics') }}",
            "EXECUTION_DATE": "{{ ds }}",
        },
    )

    # k8s_task_download_inventory >> metrics_task1 >> metrics_task2 >> metrics_task3
    metrics_tasks = {}
    for i in range(1, int(AWS_STORAGE_STATS_POD_COUNT) + 1):
        counter = str(i)
        metrics_tasks[i] = KubernetesPodOperator(
            namespace="processing",
            image="python:3.8-slim-buster",
            arguments=["bash", "-c", " &&\n".join(JOBS2)],
            name="write-xcom",
            do_xcom_push=True,
            is_delete_operator_pod=True,
            in_cluster=True,
            task_id=f"collection{i}",
            get_logs=True,
            env_vars={
                "INVENTORY_FILE" : "{{ task_instance.xcom_pull(task_ids='get_inventory_files', key='return_value') }}",
                "COUNTER" : counter,
            },
        )
        k8s_task_download_inventory >> metrics_tasks[i] >> aggregate_metrics >> push_to_db
