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
    JOBS1 = [
        "echo db backup started: $(date)",
        "pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -n marine",
        "aws sts get-caller-identity",
        # | aws s3 cp --storage-class STANDARD_IA --sse aws:kms - s3://$REPORTING_BUCKET/$EXECUTION_DATE/marine-dump.sql.gz",
    ]
    backup_reporting_db = KubernetesPodOperator(
        namespace="processing",
        image="ramagopr123/psql_client",
        arguments=["bash", "-c", " &&\n".join(JOBS1)],
        name="backup_reporting_db",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="backup_reporting_db",
        get_logs=True,
        env_vars={
            "EXECUTION_DATE": "{{ ds }}",
            "AWS_DEFAULT_REGION": "ap-southeast-2",
            "AWS_PAGER": "",
            "REPORTING_BUCKET": "automated-reporting-db-dump",
        },
    )
    backup_reporting_db
