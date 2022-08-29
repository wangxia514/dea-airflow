# -*- coding: utf-8 -*-

"""
dea ungrouped user stats dag
"""
# pylint: disable=C0301
# pylint: disable=W0104
# pylint: disable=E0401
from datetime import datetime, timedelta
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.operators.dummy import DummyOperator
from dags.automated_reporting import utilities, k8s_secrets
from infra.variables import REPORTING_IAM_REP_S3_SECRET

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": True,
    "start_date": datetime(2021, 9, 1),
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 90,
    "retry_delay": timedelta(days=1),
    "secrets": [
        Secret("env", "ACCESS_KEY", REPORTING_IAM_REP_S3_SECRET, "ACCESS_KEY"),
        Secret("env", "SECRET_KEY", REPORTING_IAM_REP_S3_SECRET, "SECRET_KEY"),
    ],
}

dag = DAG(
    "rep_dea_monthly_prod",
    description="DAG for dea ungrouped user stats",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval="0 14 1 * *",
)

ENV="prod"
ETL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls:v2.4.4"
)

with dag:
    START = DummyOperator(task_id="dea-ungrouped-user-stats")
    fk4_ingestion = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo fk4 user stats ingestion: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "jsonresult=`python3 -c 'from nemo_reporting.user_stats import fk4_user_stats_ingestion; fk4_user_stats_ingestion.task()'`",
            "mkdir -p /airflow/xcom/; echo $jsonresult > /airflow/xcom/return.json",
        ],
        xcom=True,
        task_id="fk4_ingestion",
        env_vars={
            "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
            "FILE_TO_PROCESS": "fk4",
        },
        secrets=k8s_secrets.db_secrets(ENV)
    )
    fk4_processing = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
        "echo fk4 user stats processing: $(date)",
        "parse-uri $REP_DB_URI /tmp/env; source /tmp/env",
        "jsonresult=`python3 -c 'from nemo_reporting.user_stats import fk4_user_stats_processing; fk4_user_stats_processing.task()'`",
        ],
        task_id="fk4_processing",
        env_vars={
            "AGGREGATION_MONTHS": "{{ task_instance.xcom_pull(task_ids='fk4_ingestion') }}",
            "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
        },
        secrets=k8s_secrets.db_secrets(ENV)
    )
    START >> fk4_ingestion >> fk4_processing
