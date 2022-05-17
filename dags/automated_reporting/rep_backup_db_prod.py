from datetime import datetime as dt, timedelta
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from infra.variables import REPORTING_IAM_NEMO_PROD_SECRET
from infra.variables import REPORTING_DB_SECRET

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
        Secret("env", "ACCESS_KEY", REPORTING_IAM_NEMO_PROD_SECRET, "ACCESS_KEY"),
        Secret("env", "SECRET_KEY", REPORTING_IAM_NEMO_PROD_SECRET, "SECRET_KEY"),
        Secret("env", "DB_HOST", REPORTING_DB_SECRET, "DB_HOST"),
        Secret("env", "DB_NAME", REPORTING_DB_SECRET, "DB_NAME"),
        Secret("env", "DB_PORT", REPORTING_DB_SECRET, "DB_PORT"),
        Secret("env", "DB_USER", REPORTING_DB_SECRET, "DB_USER"),
        Secret("env", "DB_PASSWORD", REPORTING_DB_SECRET, "DB_PASSWORD"),
    ],
}

dag = DAG(
    "rep_backup_reporting_db_prod",
    description="Create daily backups for reporting db prod",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval="0 14 * * *",  # daily at 1am AEDT
)

with dag:
    JOBS1 = [
        "echo db backup started: $(date)",
        "pip install ga-reporting-etls==1.22.0",
        "jsonresult=`apt-get update; apt-get install -y  postgresql; python3 -c 'from nemo_reporting.backup_restore_db import backup; backup.backup_task()'`",
    ]
    backup_reporting_db = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS1)],
        name="backup_reporting_db",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="backup_reporting_db",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
        },
    )
    backup_reporting_db
