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
from airflow.operators.subdag_operator import SubDagOperator
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


def load_subdag(parent_dag_name, child_dag_name, args, config_task_name):
    """
    Make us a subdag to hide all the sub tasks
    """
    key_name = 'return_value'
    subdag = DAG(
        dag_id=f"{parent_dag_name}.{child_dag_name}", default_args=args, catchup=False
    )

    config = "{{{{ task_instance.xcom_pull(dag_id='{}', task_ids='{}',key_id='{}') }}}}".format(
        parent_dag_name, config_task_name, key_name
    )

    try:
        config = json.loads(config)
    except json.decoder.JSONDecodeError:
        config = {}

    filename = config.get('file1')
    metrics_task = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS2)],
        name="write-xcom",
        do_xcom_push=True,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="metrics_collector",
        get_logs=True,
        env_vars={
                "INVENTORY_FILE": "{{ filename }}",
        },
    )

    return subdag


with dag:
    JOBS1 = [
        "echo AWS Storage job started: $(date)",
        "pip install ga-reporting-etls==1.2.19",
        "jsonresult=`python3 -c 'from nemo_reporting.aws_storage_stats import downloadinventory; downloadinventory.task()'`",
        "mkdir -p /airflow/xcom/; echo $jsonresult > /airflow/xcom/return.json",
    ]
    JOBS2 = [
        "echo AWS Storage job started: $(date)",
        "pip install ga-reporting-etls==1.2.19",
        "jsonresult=`python3 -c 'from nemo_reporting.aws_storage_stats import process; process.calc_size_and_count()'`",
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
            "GOOGLE_ANALYTICS_CREDENTIALS": Variable.get("google_analytics"),
        },
    )
    INDEX = SubDagOperator(
        task_id='metrics_collector',
        subdag=load_subdag('aws_storage_stats', 'metrics_collector', default_args, 'get_inventory_files'),
        default_args=default_args,
        dag=dag,
    )
    k8s_task_download_inventory >> INDEX
