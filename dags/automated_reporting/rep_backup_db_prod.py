# -*- coding: utf-8 -*-
"""
### Backup Reporting DB
This DAG is a scheduled run workflow to backup reporting DB into the nemo production account on a daily basis. The docker image used is ramagopr123/psql_client which can be found in the dockerhub. This is a simple docker image containing ubuntu + psql client + aws cli. The execution command is a pg_dump with RDS master instance details fetched from kubernetes secrets including username and password. The DAG is done as a single task per schema and done in parallel.
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
        Secret("env", "AWS_ACCESS_KEY_ID", REPORTING_IAM_NEMO_PROD_SECRET, "ACCESS_KEY"),
        Secret("env", "AWS_SECRET_ACCESS_KEY", REPORTING_IAM_NEMO_PROD_SECRET, "SECRET_KEY"),
        Secret("env", "DB_HOST", REPORTING_DB_SECRET, "DB_HOST"),
        Secret("env", "DB_NAME", REPORTING_DB_SECRET, "DB_NAME"),
        Secret("env", "DB_USER", REPORTING_DB_SECRET, "DB_USER"),
        Secret("env", "PGPASSWORD", REPORTING_DB_SECRET, "DB_PASSWORD"),
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
    JOBSLANDSAT = [
        "echo db backup started: $(date)",
        "pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -n landsat | aws s3 cp --storage-class STANDARD_IA --sse aws:kms - s3://$REPORTING_BUCKET/$EXECUTION_DATE/landsat-dump.sql",
    ]
    JOBSDEA = [
        "echo db backup started: $(date)",
        "pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -n dea | aws s3 cp --storage-class STANDARD_IA --sse aws:kms - s3://$REPORTING_BUCKET/$EXECUTION_DATE/dea-dump.sql",
    ]
    JOBSCOPHUB = [
        "echo db backup started: $(date)",
        "pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -n cophub | aws s3 cp --storage-class STANDARD_IA --sse aws:kms - s3://$REPORTING_BUCKET/$EXECUTION_DATE/cophub-dump.sql",
    ]
    JOBSMARINE = [
        "echo db backup started: $(date)",
        "pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -n marine | aws s3 cp --storage-class STANDARD_IA --sse aws:kms - s3://$REPORTING_BUCKET/$EXECUTION_DATE/marine-dump.sql",
    ]
    JOBSNCI = [
        "echo db backup started: $(date)",
        "pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -n nci | aws s3 cp --storage-class STANDARD_IA --sse aws:kms - s3://$REPORTING_BUCKET/$EXECUTION_DATE/nci-dump.sql",
    ]
    JOBSPUBLIC = [
        "echo db backup started: $(date)",
        "pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -n public | aws s3 cp --storage-class STANDARD_IA --sse aws:kms - s3://$REPORTING_BUCKET/$EXECUTION_DATE/public-dump.sql",
    ]
    backup_reporting_db_landsat = KubernetesPodOperator(
        namespace="processing",
        image="ramagopr123/psql_client",
        arguments=["bash", "-c", " &&\n".join(JOBSLANDSAT)],
        name="backup_reporting_db_landsat",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="backup_reporting_db_landsat",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "AWS_PAGER": "",
            "REPORTING_BUCKET": "automated-reporting-db-dump",
        },
    )
    backup_reporting_db_dea = KubernetesPodOperator(
        namespace="processing",
        image="ramagopr123/psql_client",
        arguments=["bash", "-c", " &&\n".join(JOBSDEA)],
        name="backup_reporting_db_dea",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="backup_reporting_db_dea",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "AWS_PAGER": "",
            "REPORTING_BUCKET": "automated-reporting-db-dump",
        },
    )
    backup_reporting_db_cophub = KubernetesPodOperator(
        namespace="processing",
        image="ramagopr123/psql_client",
        arguments=["bash", "-c", " &&\n".join(JOBSCOPHUB)],
        name="backup_reporting_db_cophub",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="backup_reporting_db_cophub",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "AWS_PAGER": "",
            "REPORTING_BUCKET": "automated-reporting-db-dump",
        },
    )
    backup_reporting_db_marine = KubernetesPodOperator(
        namespace="processing",
        image="ramagopr123/psql_client",
        arguments=["bash", "-c", " &&\n".join(JOBSMARINE)],
        name="backup_reporting_db_marine",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="backup_reporting_db_marine",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "AWS_PAGER": "",
            "REPORTING_BUCKET": "automated-reporting-db-dump",
        },
    )
    backup_reporting_db_nci = KubernetesPodOperator(
        namespace="processing",
        image="ramagopr123/psql_client",
        arguments=["bash", "-c", " &&\n".join(JOBSNCI)],
        name="backup_reporting_db_nci",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="backup_reporting_db_nci",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "AWS_PAGER": "",
            "REPORTING_BUCKET": "automated-reporting-db-dump",
        },
    )
    backup_reporting_db_public = KubernetesPodOperator(
        namespace="processing",
        image="ramagopr123/psql_client",
        arguments=["bash", "-c", " &&\n".join(JOBSPUBLIC)],
        name="backup_reporting_db_public",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="backup_reporting_db_public",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "AWS_PAGER": "",
            "REPORTING_BUCKET": "automated-reporting-db-dump",
        },
    )
    START = DummyOperator(task_id="backup-reporting-db")
    START >> backup_reporting_db_landsat
    START >> backup_reporting_db_dea
    START >> backup_reporting_db_cophub
    START >> backup_reporting_db_marine
    START >> backup_reporting_db_nci
    START >> backup_reporting_db_public
