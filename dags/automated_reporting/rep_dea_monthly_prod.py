# -*- coding: utf-8 -*-

"""
dea ungrouped user stats dag
"""
# pylint: disable=C0301
# pylint: disable=W0104
# pylint: disable=E0401
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.dummy import DummyOperator
from automated_reporting import utilities, k8s_secrets

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": True,
    "start_date": datetime(2021, 9, 1),
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 90,
    "retry_delay": timedelta(days=1),
}

dag = DAG(
    "rep_dea_monthly_prod",
    description="DAG for dea ungrouped user stats",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval="0 14 1 * *",
)

ENV = "prod"
ETL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls:v2.17.4"
)

with dag:
    START = DummyOperator(task_id="dea-ungrouped-user-stats")
    fk4_ingestion = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo fk4 user stats ingestion: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "mkdir -p /airflow/xcom/",
            "user-stats-ingestion /airflow/xcom/return.json",
        ],
        xcom=True,
        task_id="fk4_ingestion",
        env_vars={
            "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
            "SCHEMA_TO_PROCESS"  : "dea",
            "PROJECT_TO_PROCESS" : "fk4"
        },
        secrets=k8s_secrets.db_secrets(ENV) + k8s_secrets.iam_rep_secrets + k8s_secrets.s3_automated_operation_bucket,
    )
    fk4_processing = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo fk4 user stats processing: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "user-stats-processing",
        ],
        task_id="fk4_processing",
        env_vars={
            "AGGREGATION_MONTHS": "{{ task_instance.xcom_pull(task_ids='fk4_ingestion') }}",
            "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
            "SCHEMA_TO_PROCESS" : "dea",
            "PROJECT_TO_PROCESS": "fk4"
        },
        secrets=k8s_secrets.db_secrets(ENV),
    )
    START >> fk4_ingestion >> fk4_processing
