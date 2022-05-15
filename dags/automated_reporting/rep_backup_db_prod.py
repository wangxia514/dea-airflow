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
    backup_cmd_dea = "pg_dump -Z 9 -h $DB_HOST -U $DB_USER -d $DB_NAME -n dea | aws s3 cp --storage-class STANDARD_IA --sse aws:kms - s3://automated-reporting-db-dump/${EXECUTION_DATE}/dea-dump.sql.gz"
    backup_cmd_cophub = "pg_dump -Z 9 -h $DB_HOST -U $DB_USER -d $DB_NAME -n cophub | aws s3 cp --storage-class STANDARD_IA --sse aws:kms - s3://automated-reporting-db-dump/${EXECUTION_DATE}/cophub-dump.sql.gz"
    backup_cmd_landsat = "pg_dump -Z 9 -h $DB_HOST -U $DB_USER -d $DB_NAME -n landsat | aws s3 cp --storage-class STANDARD_IA --sse aws:kms - s3://automated-reporting-db-dump/${EXECUTION_DATE}/landsat-dump.sql.gz"
    backup_cmd_marine = "pg_dump -Z 9 -h $DB_HOST -U $DB_USER -d $DB_NAME -n marine | aws s3 cp --storage-class STANDARD_IA --sse aws:kms - s3://automated-reporting-db-dump/${EXECUTION_DATE}/marine-dump.sql.gz"
    backup_cmd_nci = "pg_dump -Z 9 -h $DB_HOST -U $DB_USER -d $DB_NAME -n nci | aws s3 cp --storage-class STANDARD_IA --sse aws:kms - s3://automated-reporting-db-dump/${EXECUTION_DATE}/nci-dump.sql.gz"
    backup_cmd_public = "pg_dump -Z 9 -h $DB_HOST -U $DB_USER -d $DB_NAME -n public | aws s3 cp --storage-class STANDARD_IA --sse aws:kms - s3://automated-reporting-db-dump/${EXECUTION_DATE}/public-dump.sql.gz"
    backup_dea = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", backup_cmd_dea,
        name="backup_dea",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="backup_dea",
        get_logs=True,
        env_vars={"EXECUTION_DATE": "{{ ds }}", },
    )
    backup_cophub = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", backup_cmd_cophub,
        name="backup_cophub",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="backup_cophub",
        get_logs=True,
        env_vars={"EXECUTION_DATE": "{{ ds }}", },
    )
    backup_landsat = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", backup_cmd_landsat,
        name="backup_landsat",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="backup_landsat",
        get_logs=True,
        env_vars={"EXECUTION_DATE": "{{ ds }}", },
    )
    backup_marine = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", backup_cmd_marine,
        name="backup_marine",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="backup_marine",
        get_logs=True,
        env_vars={"EXECUTION_DATE": "{{ ds }}", },
    )
    backup_nci = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", backup_cmd_nci,
        name="backup_marine",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="backup_nci",
        get_logs=True,
        env_vars={"EXECUTION_DATE": "{{ ds }}", },
    )
    backup_public = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", backup_cmd_public,
        name="backup_marine",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="backup_public",
        get_logs=True,
        env_vars={"EXECUTION_DATE": "{{ ds }}", },
    )
    START = DummyOperator(task_id="backup-db")
    START >> backup_dea
    START >> backup_cophub
    START >> backup_landsat
    START >> backup_marine
    START >> backup_nci
    START >> backup_public
