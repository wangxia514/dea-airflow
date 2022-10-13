# -*- coding: utf-8 -*-

"""
cophub monthly dag for prod
"""

# The DAG object; we'll need this to instantiate a DAG
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.dummy import DummyOperator
from automated_reporting import k8s_secrets, utilities

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": False,
    "start_date": datetime(2022, 3, 1),
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 90,
    "retry_delay": timedelta(days=1),
}

ENV = "prod"
ETL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls:v2.16.0"
)

dag = DAG(
    "rep_cophub_monthly_prod",
    description="DAG for sara history ingestion and processing",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval="0 14 1 * *",
)

with dag:
    START = DummyOperator(task_id="nci-monthly-stats")
    sara_history_ingestion = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo Sara history ingestion started: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "sara-history-ingestion",
        ],
        task_id="sara_history_ingestion",
        env_vars={
            "REPORTING_MONTH": "{{  dag_run.data_interval_start | ds }}",
        },
        secrets=k8s_secrets.db_secrets(ENV) + k8s_secrets.s3_automated_operation_bucket + k8s_secrets.iam_rep_secrets
    )
    sara_history_processing = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo Sara history processing: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "sara-history-processing",
        ],
        task_id="sara_history_processing",
        env_vars={
            "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
        },
        secrets=k8s_secrets.db_secrets(ENV)
    )
    archie_ingestion = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo Archie ingestion started: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "archie-ingestion",
        ],
        task_id="archie_ingestion",
        env_vars={
            "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
        },
        secrets=k8s_secrets.db_secrets(ENV) + k8s_secrets.s3_automated_operation_bucket + k8s_secrets.iam_rep_secrets
    )
    archie_processing_sattoesa = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo Archie processing - SatToEsa started: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "archie-latency sat_to_esa",
        ],
        task_id="archie_processing_sattoesa",
        env_vars={
            "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
        },
        secrets=k8s_secrets.db_secrets(ENV)
    )
    archie_processing_esatoncitask = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo Archie processing - EsaToNciTask started: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "archie-latency esa_to_nci",
        ],
        task_id="archie_processing_esatoncitask",
        env_vars={
            "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
        },
        secrets=k8s_secrets.db_secrets(ENV)
    )
    archie_processing_esatoncis1task = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo Archie processing - EsaToNciS1Task started: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "archie-latency esa_to_nci_s1",
        ],
        task_id="archie_processing_esatoncis1task",
        env_vars={
            "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
        },
        secrets=k8s_secrets.db_secrets(ENV)
    )
    archie_processing_esatoncis2task = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo Archie processing - EsaToNciS2Task started: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "archie-latency esa_to_nci_s2",
        ],
        task_id="archie_processing_esatoncis2task",
        env_vars={
            "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
        },
        secrets=k8s_secrets.db_secrets(ENV)
    )
    archie_processing_esatoncis3task = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo Archie processing - EsaToNciS3Task started: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "archie-latency esa_to_nci_s3",
        ],
        task_id="archie_processing_esatoncis3task",
        env_vars={
            "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
        },
        secrets=k8s_secrets.db_secrets(ENV)
    )
    archie_processing_downloads = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo Archie processing - Downloads started: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "archie-download-volume",
        ],
        task_id="archie_processing_downloads",
        env_vars={
            "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
        },
        secrets=k8s_secrets.db_secrets(ENV)
    )
    fj7_disk_usage = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo FJ7 disk usage download and processing: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "jsonresult=`python3 -c 'from reporting_etls.fj7_storage import fj7_disk_usage; fj7_disk_usage.task()'`",
        ],
        task_id="fj7_disk_usage",
        env_vars={
            "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
        },
        secrets=k8s_secrets.db_secrets(ENV) + k8s_secrets.iam_rep_secrets
    )
    fj7_ungrouped_user_stats_ingestion = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo FJ7 user stats ingestion: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "mkdir -p /airflow/xcom/",
            "user-stats-ingestion /airflow/xcom/return.json",
        ],
        xcom=True,
        task_id="fj7_ungrouped_user_stats_ingestion",
        env_vars={
            "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
            "SCHEMA_TO_PROCESS": "cophub",
            "PROJECT_TO_PROCESS": "fj7",
        },
        secrets=k8s_secrets.db_secrets(ENV) + k8s_secrets.iam_rep_secrets + k8s_secrets.s3_automated_operation_bucket
    )
    fj7_ungrouped_user_stats_processing = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo FJ7 user stats processing: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "user-stats-processing",
        ],
        task_id="fj7_ungrouped_user_stats_processing",
        env_vars={
            "AGGREGATION_MONTHS": "{{ task_instance.xcom_pull(task_ids='fj7_ungrouped_user_stats_ingestion') }}",
            "REPORTING_MONTH": "{{ dag_run.data_interval_start | ds }}",
            "SCHEMA_TO_PROCESS" : "cophub",
            "PROJECT_TO_PROCESS": "fj7"
        },
        secrets=k8s_secrets.db_secrets(ENV) + k8s_secrets.iam_rep_secrets
    )
    START >> sara_history_ingestion >> sara_history_processing
    START >> fj7_ungrouped_user_stats_ingestion >> fj7_ungrouped_user_stats_processing
    START >> archie_ingestion
    START >> fj7_disk_usage
    archie_ingestion >> archie_processing_sattoesa
    archie_ingestion >> archie_processing_esatoncitask
    archie_ingestion >> archie_processing_esatoncis1task
    archie_ingestion >> archie_processing_esatoncis2task
    archie_ingestion >> archie_processing_esatoncis3task
    archie_ingestion >> archie_processing_downloads
