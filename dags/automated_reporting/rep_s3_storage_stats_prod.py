# -*- coding: utf-8 -*-

"""
aws storage stats dag
"""

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.operators.python_operator import PythonOperator
from datetime import datetime as dt, timedelta
from infra.variables import REPORTING_IAM_DEA_S3_SECRET
from automated_reporting import k8s_secrets, utilities
from infra.variables import AWS_STORAGE_STATS_POD_COUNT
import json

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": False,
    "start_date": dt(2021, 12, 1),
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "secrets": [
        Secret("env", "ACCESS_KEY", REPORTING_IAM_DEA_S3_SECRET, "ACCESS_KEY"),
        Secret("env", "SECRET_KEY", REPORTING_IAM_DEA_S3_SECRET, "SECRET_KEY"),
    ],
}

dag = DAG(
    "rep_aws_storage_stats_prod",
    description="DAG for aws storage stats",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval="0 14 * * *",  # daily at 1am AEDT
)

ENV = "prod"
ETL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls:v2.4.4"
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
    k8s_task_download_inventory = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo AWS Storage job started - download: $(date)",
            "parse-uri $REP_DB_URI /tmp/env; source /tmp/env",
            "mkdir -p /airflow/xcom/",
            "aws-storage-download /airflow/xcom/return.json",
        ] ,
        xcom=True,
        task_id="get_inventory_files",
        env_vars={
            "POD_COUNT": AWS_STORAGE_STATS_POD_COUNT,
            "REPORTING_BUCKET": "dea-public-data-inventory",
            "REPORTING_DATE": "{{ ds }}",
        },
        secrets=k8s_secrets.db_secrets(ENV)
    )

    aggregate_metrics = PythonOperator(
        task_id="aggregate_metrics",
        python_callable=aggregate_metrics_from_collections,
        provide_context=True,
    )

    push_to_db = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo AWS Storage job started - ingestion to db: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "aws-storage-ingestion",
        ],
        task_id="push_to_db",
        env_vars={
            "METRICS" : "{{ task_instance.xcom_pull(task_ids='aggregate_metrics', key='metrics') }}",
            "REPORTING_BUCKET": "dea-public-data-inventory",
            "REPORTING_DATE": "{{ ds }}",
        },
        secrets=k8s_secrets.db_secrets(ENV)
    )

    # k8s_task_download_inventory >> metrics_task1 >> metrics_task2 >> metrics_task3
    metrics_tasks = {}
    for i in range(1, int(AWS_STORAGE_STATS_POD_COUNT) + 1):
        counter = str(i)
        metrics_tasks[i] = utilities.k8s_operator(
            dag=dag,
            image=ETL_IMAGE,
            cmds=[
                "echo AWS Storage job started - process: $(date)",
                "parse-uri $REP_DB_URI /tmp/env; source /tmp/env",
                "mkdir -p /airflow/xcom/",
                "aws-storage-process /airflow/xcom/return.json",
            ],
            xcom=True,
            task_id=f"collection{i}",
            env_vars={
                "INVENTORY_FILE" : "{{ task_instance.xcom_pull(task_ids='get_inventory_files', key='return_value') }}",
                "REPORTING_BUCKET": "dea-public-data-inventory",
                "COUNTER" : counter,
            },
            secrets=k8s_secrets.db_secrets(ENV)
        )
        k8s_task_download_inventory >> metrics_tasks[i] >> aggregate_metrics >> push_to_db
