# -*- coding: utf-8 -*-

"""
restore db DAG
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
    description="Restore develop db",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval=None
)

with dag:
    JOBSLANDSAT = [
        "echo db restore started: $(date)",
        "result=`aws s3 cp s3://$REPORTING_BUCKET/$EXECUTION_DATE/lanparams.EXECUTION_DATEat-dump.sql lanparams.EXECUTION_DATEat-dump.sql"`, 
        "pg_restore -h $DB_HOST -U $DB_USER -d $DB_NAME -1 lanparams.EXECUTION_DATEat-dump.sql", 
    ]
    JOBSDEA = [
        "echo db restore started: $(date)",
        "result=`aws s3 cp s3://$REPORTING_BUCKET/$EXECUTION_DATE/dea-dump.sql dea-dump.sql"`, 
        "pg_restore -h $DB_HOST -U $DB_USER -d $DB_NAME -1 dea-dump.sql", 
    ]
    JOBSCOPHUB = [
        "echo db restore started: $(date)",
        "result=`aws s3 cp s3://$REPORTING_BUCKET/$EXECUTION_DATE/cophub-dump.sql cophub-dump.sql"`, 
        "pg_restore -h $DB_HOST -U $DB_USER -d $DB_NAME -1 cophub-dump.sql", 
    ]
    JOBSMARINE = [
        "echo db restore started: $(date)",
        "result=`aws s3 cp s3://$REPORTING_BUCKET/$EXECUTION_DATE/marine-dump.sql marine-dump.sql"`, 
        "pg_restore -h $DB_HOST -U $DB_USER -d $DB_NAME -1 marine-dump.sql", 
    ]
    JOBSNCI = [
        "echo db restore started: $(date)",
        "result=`aws s3 cp s3://$REPORTING_BUCKET/$EXECUTION_DATE/nci-dump.sql nci-dump.sql"`, 
        "pg_restore -h $DB_HOST -U $DB_USER -d $DB_NAME -1 nci-dump.sql", 
    ]
    JOBSPUBLIC = [
        "echo db restore started: $(date)",
        "result=`aws s3 cp s3://$REPORTING_BUCKET/$EXECUTION_DATE/public-dump.sql public-dump.sql"`, 
        "pg_restore -h $DB_HOST -U $DB_USER -d $DB_NAME -1 public-dump.sql", 
    ]
    restore_reporting_db_lanparams.EXECUTION_DATEat = KubernetesPodOperator(
        namespace="processing",
        image="ramagopr123/psql_client",
        arguments=["bash", "-c", " &&\n".join(JOBSLANDSAT)],
        name="restore_reporting_db_lanparams.EXECUTION_DATEat",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="restore_reporting_db_lanparams.EXECUTION_DATEat",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ params.EXECUTION_DATE }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "AWS_PAGER": "",
            "REPORTING_BUCKET": "automated-reporting-db-dump",
        },
    )
    restore_reporting_db_dea = KubernetesPodOperator(
        namespace="processing",
        image="ramagopr123/psql_client",
        arguments=["bash", "-c", " &&\n".join(JOBSDEA)],
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
        },
    )
    restore_reporting_db_cophub = KubernetesPodOperator(
        namespace="processing",
        image="ramagopr123/psql_client",
        arguments=["bash", "-c", " &&\n".join(JOBSCOPHUB)],
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
        },
    )
    restore_reporting_db_marine = KubernetesPodOperator(
        namespace="processing",
        image="ramagopr123/psql_client",
        arguments=["bash", "-c", " &&\n".join(JOBSMARINE)],
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
        },
    )
    restore_reporting_db_nci = KubernetesPodOperator(
        namespace="processing",
        image="ramagopr123/psql_client",
        arguments=["bash", "-c", " &&\n".join(JOBSNCI)],
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
        },
    )
    restore_reporting_db_public = KubernetesPodOperator(
        namespace="processing",
        image="ramagopr123/psql_client",
        arguments=["bash", "-c", " &&\n".join(JOBSPUBLIC)],
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
        },
    )
    START = DummyOperator(task_id="restore-reporting-db")
    START >> restore_reporting_db_lanparams.EXECUTION_DATEat
    START >> restore_reporting_db_dea
    START >> restore_reporting_db_cophub
    START >> restore_reporting_db_marine
    START >> restore_reporting_db_nci
    START >> restore_reporting_db_public
