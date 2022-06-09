# -*- coding: utf-8 -*-

"""
manage reporting DB backups
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
        "date_diff=30",
        "BACKUP_DELETE_DATE=$(date --date=""${EXECUTION_DATE} -${date_diff} day"" +%Y-%m-%d)",
        "day=`echo $BACKUP_DELETE_DATE | cut -f3 -d'-'`",
        "if [ '$day' != '01' ]",
        "then",
        "    aws s3 rm s3://automated-reporting-db-dump/$BACKUP_DELETE_DATE/ --recursive",
        "fi",
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
