# -*- coding: utf-8 -*-

"""
marine ungrouped user stats dag
"""
# pylint: disable=C0301
# pylint: disable=W0104
# pylint: disable=E0401
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.dummy import DummyOperator
from automated_reporting import k8s_secrets, utilities

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": False,
    "start_date": datetime(2021, 9, 1),
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 90,
    "retry_delay": timedelta(days=1),
}
ENV = "prod"
ETL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls:v2.17.6"
)
dag = DAG(
    "rep_marine_monthly_prod",
    description="DAG for marine ungrouped user stats",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval="0 14 1 * *",
)


with dag:
    START = DummyOperator(task_id="marine-monthly-stats")
    fk1_ingestion = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo fk1 user stats ingestion: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "mkdir -p /airflow/xcom/",
            "user-stats-ingestion /airflow/xcom/return.json",
        ],
        xcom=True,
        task_id="fk1_ingestion",
        env_vars={
            "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
            "SCHEMA_TO_PROCESS"  : "marine",
            "PROJECT_TO_PROCESS" : "fk1"
        },
        secrets=k8s_secrets.db_secrets(ENV) + k8s_secrets.iam_rep_secrets + k8s_secrets.s3_automated_operation_bucket,
    )
    fk1_processing = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo fk1 user stats processing: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "user-stats-processing",
        ],
        task_id="fk1_processing",
        env_vars={
            "AGGREGATION_MONTHS": "{{ task_instance.xcom_pull(task_ids='fk4_ingestion') }}",
            "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
            "SCHEMA_TO_PROCESS" : "marine",
            "PROJECT_TO_PROCESS": "fk1"
        },
        secrets=k8s_secrets.db_secrets(ENV),
    )
    iy57_ingestion = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo iy57 user stats ingestion: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "mkdir -p /airflow/xcom/",
            "user-stats-ingestion /airflow/xcom/return.json",
        ],
        xcom=True,
        task_id="iy57_ingestion",
        env_vars={
            "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
            "SCHEMA_TO_PROCESS"  : "marine",
            "PROJECT_TO_PROCESS" : "iy57"
        },
        secrets=k8s_secrets.db_secrets(ENV) + k8s_secrets.iam_rep_secrets + k8s_secrets.s3_automated_operation_bucket,
    )
    iy57_processing = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo iy57 user stats processing: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "user-stats-processing",
        ],
        task_id="iy57_processing",
        env_vars={
            "AGGREGATION_MONTHS": "{{ task_instance.xcom_pull(task_ids='fk4_ingestion') }}",
            "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
            "SCHEMA_TO_PROCESS" : "marine",
            "PROJECT_TO_PROCESS": "iy57"
        },
        secrets=k8s_secrets.db_secrets(ENV),
    )
    pw31_ingestion = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo pw31 user stats ingestion: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "mkdir -p /airflow/xcom/",
            "user-stats-ingestion /airflow/xcom/return.json",
        ],
        xcom=True,
        task_id="pw31_ingestion",
        env_vars={
            "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
            "SCHEMA_TO_PROCESS"  : "marine",
            "PROJECT_TO_PROCESS" : "pw31"
        },
        secrets=k8s_secrets.db_secrets(ENV) + k8s_secrets.iam_rep_secrets + k8s_secrets.s3_automated_operation_bucket,
    )
    pw31_processing = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo pw31 user stats processing: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "user-stats-processing",
        ],
        task_id="pw31_processing",
        env_vars={
            "AGGREGATION_MONTHS": "{{ task_instance.xcom_pull(task_ids='fk4_ingestion') }}",
            "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
            "SCHEMA_TO_PROCESS" : "marine",
            "PROJECT_TO_PROCESS": "pw31"
        },
        secrets=k8s_secrets.db_secrets(ENV),
    )
    elvis_ingestion = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo Elvis ingestion processing: $(date)",
            "parse-uri $REP_DB_URI /tmp/env; source /tmp/env",
            "marine-elvis-ingestion",
        ],
        task_id="elvis_ingestion",
        env_vars={
            "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
        },
        secrets=k8s_secrets.db_secrets(ENV) + k8s_secrets.s3_automated_operation_bucket + k8s_secrets.iam_rep_secrets,
    )
    START >> fk1_ingestion >> fk1_processing
    START >> iy57_ingestion >> iy57_processing
    START >> pw31_ingestion >> pw31_processing
    START >> elvis_ingestion
