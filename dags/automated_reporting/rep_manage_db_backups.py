# -*- coding: utf-8 -*-
"""
### Manage Reporting DB
This DAG is a scheduled run workflow to manage reporting DB backups in the S3 bucket `automated-reporting-db-dump`. The docker image used is ramagopr123/psql_client which can be found in the dockerhub. This is a simple docker image containing ubuntu + psql client + aws cli. The execution command is a shell script `manage_backup.sh` which can be found under folder `backup_restore_docker_scripts`. The DAG manages the s3 backup folder to contain only the last 30 days of backup at any point of time. It also ensures that the 1st day of the month backups are retained forever. 
"""
# pylint: disable=C0301
# pylint: disable=W0104
# pylint: disable=E0401
from datetime import datetime as dt, timedelta
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from infra.variables import REPORTING_IAM_NEMO_PROD_SECRET

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": False,
    "start_date": dt(2022, 5, 10),
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(days=1),
    "secrets": [
        Secret("env", "AWS_ACCESS_KEY_ID", REPORTING_IAM_NEMO_PROD_SECRET, "ACCESS_KEY"),
        Secret("env", "AWS_SECRET_ACCESS_KEY", REPORTING_IAM_NEMO_PROD_SECRET, "SECRET_KEY"),
    ],
}

dag = DAG(
    "rep_manage_reporting_db_prod",
    description="Keep only 30 days manage and retain the monthly backups",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval="0 15 * * *",  # daily at 1am AEDT
)

with dag:
    JOBS1 = [
        "sh /manage_backup.sh",
    ]
    manage_reporting_db = KubernetesPodOperator(
        namespace="processing",
        image="ramagopr123/psql_client",
        arguments=["bash", "-c", " &&\n".join(JOBS1)],
        name="manage_reporting_db",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="manage_reporting_db",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "REPORTING_BUCKET": "automated-reporting-db-dump",
        },
    )
    manage_reporting_db
