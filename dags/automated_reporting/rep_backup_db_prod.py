# -*- coding: utf-8 -*-
"""
### Backup Reporting DB
This DAG is a scheduled run workflow to backup reporting DB into the nemo production account on a daily basis. The docker image used is BACKUP_RESTORE_IMAGE which can be found in the ECR. This is a simple docker image containing ubuntu + psql client + aws cli. The execution command is a pg_dump with RDS master instance details fetched from kubernetes secrets including username and password. The DAG is done as a single task per schema and done in parallel.
* `landsat`
* `dea`
* `cophub`
* `marine`
* `nci`
* `public`
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
from airflow.operators.dummy import DummyOperator
from infra.variables import REPORTING_DB_SECRET
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
    "secrets": [
        Secret("env", "DB_HOST", REPORTING_DB_SECRET, "DB_HOST"),
        Secret("env", "DB_NAME", REPORTING_DB_SECRET, "DB_NAME"),
        Secret("env", "DB_USER", REPORTING_DB_SECRET, "DB_USER"),
        Secret("env", "PGPASSWORD", REPORTING_DB_SECRET, "DB_PASSWORD"),
    ],
}

dag = DAG(
    "rep_backup_reporting_db_prod",
    doc_md=__doc__,
    description="Create daily backups for reporting db prod",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval="0 14 * * *",  # daily at 1am AEDT
)

BACKUP_RESTORE_IMAGE = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/automated-reporting-backup:latest"

with dag:
    backup_reporting_db_landsat = utilities.k8s_operator(
        dag=dag,
        image=BACKUP_RESTORE_IMAGE,
        cmds=[
            "echo db backup started: $(date)",
            "pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -n landsat | aws s3 cp --storage-class STANDARD_IA --sse aws:kms - s3://$S3_BUCKET/$EXECUTION_DATE/landsat-dump.sql",
        ],
        task_id="backup_reporting_db_landsat",
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "AWS_PAGER": "",
        },
        secrets=k8s_secrets.s3_db_dump_bucket + k8s_secrets.iam_nemo_production_secrets,
    )
    backup_reporting_db_dea = utilities.k8s_operator(
        dag=dag,
        image=BACKUP_RESTORE_IMAGE,
        cmds=[
            "echo db backup started: $(date)",
            "pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -n dea | aws s3 cp --storage-class STANDARD_IA --sse aws:kms - s3://$S3_BUCKET/$EXECUTION_DATE/dea-dump.sql",
        ],
        task_id="backup_reporting_db_dea",
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "AWS_PAGER": "",
        },
        secrets=k8s_secrets.s3_db_dump_bucket + k8s_secrets.iam_nemo_production_secrets,
    )
    backup_reporting_db_cophub = utilities.k8s_operator(
        dag=dag,
        image=BACKUP_RESTORE_IMAGE,
        cmds = [
            "echo db backup started: $(date)",
            "pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -n cophub | aws s3 cp --storage-class STANDARD_IA --sse aws:kms - s3://$S3_BUCKET/$EXECUTION_DATE/cophub-dump.sql",
        ],
        task_id="backup_reporting_db_cophub",
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "AWS_PAGER": "",
        },
        secrets=k8s_secrets.s3_db_dump_bucket + k8s_secrets.iam_nemo_production_secrets,
    )
    backup_reporting_db_marine = KubernetesPodOperator(
        dag=dag,
        image=BACKUP_RESTORE_IMAGE,
        cmds = [
            "echo db backup started: $(date)",
            "pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -n marine | aws s3 cp --storage-class STANDARD_IA --sse aws:kms - s3://$S3_BUCKET/$EXECUTION_DATE/marine-dump.sql",
        ],
        task_id="backup_reporting_db_marine",
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "AWS_PAGER": "",
        },
        secrets=k8s_secrets.s3_db_dump_bucket + k8s_secrets.iam_nemo_production_secrets,
    )
    backup_reporting_db_nci = utilities.k8s_operator(
        dag=dag,
        image=BACKUP_RESTORE_IMAGE,
        cmds = [
            "echo db backup started: $(date)",
            "pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -n nci | aws s3 cp --storage-class STANDARD_IA --sse aws:kms - s3://$S3_BUCKET/$EXECUTION_DATE/nci-dump.sql",
        ],
        task_id="backup_reporting_db_nci",
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "AWS_PAGER": "",
        },
        secrets=k8s_secrets.s3_db_dump_bucket + k8s_secrets.iam_nemo_production_secrets,
    )
    backup_reporting_db_public = utilities.k8s_operator(
        dag=dag,
        image=BACKUP_RESTORE_IMAGE,
        cmds = [
            "echo db backup started: $(date)",
            "pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -n public | aws s3 cp --storage-class STANDARD_IA --sse aws:kms - s3://$S3_BUCKET/$EXECUTION_DATE/public-dump.sql",
        ],
        task_id="backup_reporting_db_public",
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "AWS_PAGER": "",
        },
        secrets=k8s_secrets.s3_db_dump_bucket + k8s_secrets.iam_nemo_production_secrets,
    )
    START = DummyOperator(task_id="backup-reporting-db")
    START >> backup_reporting_db_landsat
    START >> backup_reporting_db_dea
    START >> backup_reporting_db_cophub
    START >> backup_reporting_db_marine
    START >> backup_reporting_db_nci
    START >> backup_reporting_db_public
