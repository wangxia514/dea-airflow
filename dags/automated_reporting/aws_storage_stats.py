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
from airflow.operators.python_operator import PythonOperator
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


def get_dictionary(**context):
    """ pulls xcom json file
    print("inventory files json from xcom pull")
    print(inventory_files_json)
    inventory_files = str(inventory_files_json).replace("'", '"')
    inventory_files_dict = json.loads(inventory_files)
    print(inventory_files_dict)
    return inventory_files_dict
    inventory_files_json = ("{{ task_instance.xcom_pull(task_ids='get_inventory_files', key='return_value') }}")
    xcom_data = context['ti'].xcom_pull(task_ids='get_inventory_files', key='return_value')
    """
    task_instance = context['task_instance']
    xcom_data = task_instance.xcom_pull(task_ids='get_inventory_files')
    print("xcom data is getting printed")
    print(xcom_data)
    return xcom_data


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
        "pip install ga-reporting-etls==1.2.22",
        "jsonresult=`python3 -c 'from nemo_reporting.aws_storage_stats import downloadinventory; downloadinventory.task()'`",
        "mkdir -p /airflow/xcom/; echo $jsonresult > /airflow/xcom/return.json",
    ]
    JOBS2 = [
        "echo AWS Storage job started: $(date)",
        "pip install ga-reporting-etls==1.2.22",
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
    inventory_files_dict = PythonOperator(task_id='inv_files_dictionary', python_callable=get_dictionary, provide_context=True)
    metrics_task = {}
    for counter in range(1, int(AWS_STORAGE_STATS_POD_COUNT) + 1):
        inventory_file = "{{ task_instance.xcom_pull(task_ids='get_inventory_files', key='return_value')['metrics_collector_" + str(counter) + "'] }}"
        metrics_task[counter] = KubernetesPodOperator(
            namespace="processing",
            image="python:3.8-slim-buster",
            arguments=["bash", "-c", " &&\n".join(JOBS2)],
            name="write-xcom",
            do_xcom_push=True,
            is_delete_operator_pod=True,
            in_cluster=True,
            task_id=f"metrics_collector{counter}",
            get_logs=True,
            env_vars={
                "INVENTORY_FILE" : inventory_file
            },
        )
        k8s_task_download_inventory >> inventory_files_dict >> metrics_task[counter]
