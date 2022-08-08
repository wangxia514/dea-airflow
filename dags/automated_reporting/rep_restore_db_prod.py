# -*- coding: utf-8 -*-
"""
### Restore Reporting DB
This DAG is a scheduled run workflow to restore reporting DB into the DEV instance. The docker image used is automated-reporting-backup from the ECR. This is a simple docker image containing ubuntu + psql client + aws cli. The execution command is a shell script `restore.sh` which can be found under folder `backup_restore_docker_scripts`. RDS develop instance details fetched from kubernetes secrets including username and password. The DAG restores the s3 backup folder onto develop instance based on the date input. e.g. {"EXECUTION_DATE":"2022-08-06"}
"""
# pylint: disable=C0301
# pylint: disable=W0104
# pylint: disable=E0401

from datetime import datetime as dt
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from airflow.operators.dummy import DummyOperator
from infra.variables import REPORTING_IAM_NEMO_PROD_SECRET
from infra.variables import REPORTING_DB_DEV_SECRET

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends": False,
    "start_date": dt(2022, 6, 7),
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "secrets": [
        Secret("env", "AWS_ACCESS_KEY_ID", REPORTING_IAM_NEMO_PROD_SECRET, "ACCESS_KEY"),
        Secret("env", "AWS_SECRET_ACCESS_KEY", REPORTING_IAM_NEMO_PROD_SECRET, "SECRET_KEY"),
        Secret("env", "DB_HOST", REPORTING_DB_DEV_SECRET, "DB_HOST"),
        Secret("env", "DB_NAME", REPORTING_DB_DEV_SECRET, "DB_NAME"),
        Secret("env", "DB_USER", REPORTING_DB_DEV_SECRET, "DB_USER"),
        Secret("env", "PGPASSWORD", REPORTING_DB_DEV_SECRET, "DB_PASSWORD")
    ],
}

dag = DAG(
    "rep_restore_reporting_db_prod",
    doc_md=__doc__,
    description="Restore develop db",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval=None
)

BACKUP_RESTORE_IMAGE = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/automated-reporting-backup:latest"

with dag:
    JOBS1 = [
        "echo db restore started: $(date)",
        "sh /restore.sh",
    ]
    restore_reporting_db_landsat = KubernetesPodOperator(
        namespace="processing",
        image=BACKUP_RESTORE_IMAGE,
        arguments=["bash", "-c", " &&\n".join(JOBS1)],
        name="restore_reporting_db_landsat",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="restore_reporting_db_landsat",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ params.EXECUTION_DATE }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "AWS_PAGER": "",
            "REPORTING_BUCKET": "automated-reporting-db-dump",
            "SCHEMA": "landsat",
        },
    )
    restore_reporting_db_dea = KubernetesPodOperator(
        namespace="processing",
        image=BACKUP_RESTORE_IMAGE,
        arguments=["bash", "-c", " &&\n".join(JOBS1)],
        name="restore_reporting_db_dea",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="restore_reporting_db_dea",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ params.EXECUTION_DATE }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "AWS_PAGER": "",
            "REPORTING_BUCKET": "automated-reporting-db-dump",
            "SCHEMA": "dea",
        },
    )
    restore_reporting_db_cophub = KubernetesPodOperator(
        namespace="processing",
        image=BACKUP_RESTORE_IMAGE,
        arguments=["bash", "-c", " &&\n".join(JOBS1)],
        name="restore_reporting_db_cophub",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="restore_reporting_db_cophub",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ params.EXECUTION_DATE }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "AWS_PAGER": "",
            "REPORTING_BUCKET": "automated-reporting-db-dump",
            "SCHEMA": "cophub",
        },
    )
    restore_reporting_db_marine = KubernetesPodOperator(
        namespace="processing",
        image=BACKUP_RESTORE_IMAGE,
        arguments=["bash", "-c", " &&\n".join(JOBS1)],
        name="restore_reporting_db_marine",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="restore_reporting_db_marine",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ params.EXECUTION_DATE }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "AWS_PAGER": "",
            "REPORTING_BUCKET": "automated-reporting-db-dump",
            "SCHEMA": "marine",
        },
    )
    restore_reporting_db_nci = KubernetesPodOperator(
        namespace="processing",
        image=BACKUP_RESTORE_IMAGE,
        arguments=["bash", "-c", " &&\n".join(JOBS1)],
        name="restore_reporting_db_nci",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="restore_reporting_db_nci",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ params.EXECUTION_DATE }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "AWS_PAGER": "",
            "REPORTING_BUCKET": "automated-reporting-db-dump",
            "SCHEMA": "nci",
        },
    )
    restore_reporting_db_public = KubernetesPodOperator(
        namespace="processing",
        image=BACKUP_RESTORE_IMAGE,
        arguments=["bash", "-c", " &&\n".join(JOBS1)],
        name="restore_reporting_db_public",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="restore_reporting_db_public",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ params.EXECUTION_DATE }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "AWS_PAGER": "",
            "REPORTING_BUCKET": "automated-reporting-db-dump",
            "SCHEMA": "public",
        },
    )
    START = DummyOperator(task_id="restore-reporting-db")
    START >> restore_reporting_db_landsat
    START >> restore_reporting_db_dea
    START >> restore_reporting_db_cophub
    START >> restore_reporting_db_marine
    START >> restore_reporting_db_nci
    START >> restore_reporting_db_public
