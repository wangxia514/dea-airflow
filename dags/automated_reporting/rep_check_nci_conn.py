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
    print_ga_storage_task = SSHOperator(
        task_id="print_storage_file",
        ssh_conn_id="lpgs_gadi",
        command="cat /scratch/v10/usage_reports/ga_storage_usage_latest.csv",
        do_xcom_push=True,
    )
    run_lquota_task = SSHOperator(
        task_id="run_lquota_task",
        ssh_conn_id="lpgs_gadi",
        command="lquota -—no-pretty-print",
    )
    print_ga_storage_task >> run_lquota_task
