# -*- coding: utf-8 -*-

"""
check nci conn dat
"""
from airflow import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator
from datetime import datetime

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "start_date": datetime(2020, 3, 12),
    "retries": 0,
    "timeout": 1200,  # For running SSH Commands
    "email_on_failure": True,
    "email": "ramkumar.ramagopalan@ga.gov.au",
}

dag = DAG(
    "test_nci_conn_dev",
    default_args=default_args,
    schedule_interval=None,
    tags=["dev"],
)

with dag:
    JOBS2 = [
        "result=`cat /scratch/v10/usage_reports/ga_storage_usage_latest.csv`",
        "mkdir -p /airflow/xcom/; echo $jsonresult > /airflow/xcom/return.json",
    ]
    print_ga_storage_task = SSHOperator(
        task_id="print_storage_file",
        ssh_conn_id="lpgs_gadi",
        command=JOBS2,
        do_xcom_push=True,
    )
    print_ga_storage_task
