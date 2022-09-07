# -*- coding: utf-8 -*-
"""
### Restore Reporting DB
This DAG is a scheduled run workflow to restore reporting DB into the DEV instance. The docker image used is automated-reporting-backup from the ECR. This is a simple docker image containing ubuntu + psql client + aws cli. The execution command is a shell script `restore.sh` which can be found under folder `backup_restore_docker_scripts`. RDS develop instance details fetched from kubernetes secrets including username and password. The DAG restores the s3 backup folder onto develop instance based on the date input. e.g. {"EXECUTION_DATE":"2022-08-06"}
"""
# pylint: disable=C0301
# pylint: disable=W0104
# pylint: disable=E0401

from ctypes import util
from datetime import datetime as dt
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from airflow.operators.dummy import DummyOperator
from infra.variables import REPORTING_DB_DEV_SECRET
from automated_reporting import k8s_secrets, utilities

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends": False,
    "start_date": dt(2022, 6, 7),
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "secrets": [
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
    restore_reporting_db_landsat = utilities.k8s_operator(
        dag=dag,
        image=BACKUP_RESTORE_IMAGE,
        cmds = [
            "echo db restore started: $(date)",
            "sh /restore.sh",
        ],
        task_id="restore_reporting_db_landsat",
        env_vars={
            "EXECUTION_DATE": "{{ params.EXECUTION_DATE }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "AWS_PAGER": "",
            "SCHEMA": "landsat",
        },
        secrets=k8s_secrets.s3_db_dump_bucket + k8s_secrets.iam_nemo_production_secrets,
    )
    restore_reporting_db_dea = utilities.k8s_operator(
        dag=dag,
        image=BACKUP_RESTORE_IMAGE,
        cmds = [
            "echo db restore started: $(date)",
            "sh /restore.sh",
        ],
        task_id="restore_reporting_db_dea",
        env_vars={
            "EXECUTION_DATE": "{{ params.EXECUTION_DATE }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "AWS_PAGER": "",
            "SCHEMA": "dea",
        },
        secrets=k8s_secrets.s3_db_dump_bucket + k8s_secrets.iam_nemo_production_secrets,
    )
    restore_reporting_db_cophub = utilities.k8s_operator(
        dag=dag,
        image=BACKUP_RESTORE_IMAGE,
        cmds = [
            "echo db restore started: $(date)",
            "sh /restore.sh",
        ],
        task_id="restore_reporting_db_cophub",
        env_vars={
            "EXECUTION_DATE": "{{ params.EXECUTION_DATE }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "AWS_PAGER": "",
            "SCHEMA": "cophub",
        },
        secrets=k8s_secrets.s3_db_dump_bucket + k8s_secrets.iam_nemo_production_secrets,
    )
    restore_reporting_db_marine = utilities.k8s_operator(
        dag=dag,
        image=BACKUP_RESTORE_IMAGE,
        cmds = [
            "echo db restore started: $(date)",
            "sh /restore.sh",
        ],
        task_id="restore_reporting_db_marine",
        env_vars={
            "EXECUTION_DATE": "{{ params.EXECUTION_DATE }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "AWS_PAGER": "",
            "SCHEMA": "marine",
        },
        secrets=k8s_secrets.s3_db_dump_bucket + k8s_secrets.iam_nemo_production_secrets,
    )
    restore_reporting_db_nci = utilities.k8s_operator(
        dag=dag,
        image=BACKUP_RESTORE_IMAGE,
        cmds = [
            "echo db restore started: $(date)",
            "sh /restore.sh",
        ],
        task_id="restore_reporting_db_nci",
        env_vars={
            "EXECUTION_DATE": "{{ params.EXECUTION_DATE }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "AWS_PAGER": "",
            "SCHEMA": "nci",
        },
        secrets=k8s_secrets.s3_db_dump_bucket + k8s_secrets.iam_nemo_production_secrets,
    )
    restore_reporting_db_public = utilities.k8s_operator(
        dag=dag,
        image=BACKUP_RESTORE_IMAGE,
        cmds = [
            "echo db restore started: $(date)",
            "sh /restore.sh",
        ],
        task_id="restore_reporting_db_public",
        env_vars={
            "EXECUTION_DATE": "{{ params.EXECUTION_DATE }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "AWS_PAGER": "",
            "SCHEMA": "public",
        },
        secrets=k8s_secrets.s3_db_dump_bucket + k8s_secrets.iam_nemo_production_secrets,
    )
    START = DummyOperator(task_id="restore-reporting-db")
    START >> restore_reporting_db_landsat
    START >> restore_reporting_db_dea
    START >> restore_reporting_db_cophub
    START >> restore_reporting_db_marine
    START >> restore_reporting_db_nci
    START >> restore_reporting_db_public
