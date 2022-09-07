# -*- coding: utf-8 -*-
"""
### Manage Reporting DB
This DAG is a scheduled run workflow to manage reporting DB backups in the S3 bucket `automated-reporting-db-dump`. The docker image used is automated-reporting_backup which can be found in the ECR. This is a simple docker image containing ubuntu + psql client + aws cli. The execution command is a shell script `manage_backup.sh` which can be found under folder `backup_restore_docker_scripts`. The DAG manages the s3 backup folder to contain only the last 30 days of backup at any point of time. It also ensures that the 1st day of the month backups are retained forever.
"""
# pylint: disable=C0301
# pylint: disable=W0104
# pylint: disable=E0401
from datetime import datetime as dt, timedelta
from airflow import DAG
from automated_reporting import k8s_secrets, utilities

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": False,
    "start_date": dt(2022, 5, 10),
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(days=1),
}

dag = DAG(
    "rep_manage_reporting_db_prod",
    doc_md=__doc__,
    description="Keep only 30 days manage and retain the monthly backups",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval="0 15 * * *",  # daily at 1am AEDT
)

BACKUP_RESTORE_IMAGE = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/automated-reporting-backup:latest"

with dag:
    manage_reporting_db = utilities.k8s_operator(
        dag=dag,
        image=BACKUP_RESTORE_IMAGE,
        cmds = [
            "sh /manage_backup.sh",
        ],
        task_id="manage_reporting_db",
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
        },
        secrets=k8s_secrets.s3_db_dump_bucket + k8s_secrets.iam_nemo_production_secrets,
    )
    manage_reporting_db
