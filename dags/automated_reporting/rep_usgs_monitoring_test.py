"""
# Run tasks to monitor USGS NRT Products

This DAG
 * Connects to USGS M2M API to determine USGS Inventory
 * Inserts data into reporting DB, in both hg and landsat schemas
 * Runs completeness and latency checks
 * Inserts summary completeness and latency reporting data
 * Inserts completeness data for each wrs path row
"""
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from airflow.operators.dummy import DummyOperator
from datetime import datetime as dt, timedelta
from infra.variables import REPORTING_ODC_DB_SECRET
from infra.variables import REPORTING_DB_DEV_SECRET
from infra.variables import REPORTING_USGSM2M_API_SECRET

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt.now() - timedelta(hours=1),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": False,              ##UPDATE IN PROD
    "email_on_retry": False,
    "retries": 1,                           ##UPDATE IN PROD
    "retry_delay": timedelta(minutes=5),
        "secrets": [
        Secret("env", "DB_HOST", REPORTING_DB_DEV_SECRET, "DB_HOST"),
        Secret("env", "DB_NAME", REPORTING_DB_DEV_SECRET, "DB_NAME"),
        Secret("env", "DB_PORT", REPORTING_DB_DEV_SECRET, "DB_PORT"),
        Secret("env", "DB_USER", REPORTING_DB_DEV_SECRET, "DB_USER"),
        Secret("env", "DB_PASSWORD", REPORTING_DB_DEV_SECRET, "DB_PASSWORD"),
        Secret("env", "ODC_DB_HOST", REPORTING_ODC_DB_SECRET, "DB_HOST"),
        Secret("env", "ODC_DB_NAME", REPORTING_ODC_DB_SECRET, "DB_NAME"),
        Secret("env", "ODC_DB_PORT", REPORTING_ODC_DB_SECRET, "DB_PORT"),
        Secret("env", "ODC_DB_USER", REPORTING_ODC_DB_SECRET, "DB_USER"),
        Secret("env", "ODC_DB_PASSWORD", REPORTING_ODC_DB_SECRET, "DB_PASSWORD"),
        Secret("env", "M2M_USER", REPORTING_USGSM2M_API_SECRET, "M2M_USER"),
        Secret("env", "M2M_PASSWORD", REPORTING_USGSM2M_API_SECRET, "M2M_PASSWORD"),
    ],
}

dag = DAG(
    "rep_usgs_monitoring_test",             ##UPDATE IN PROD
    description="DAG for completeness and latency metric on USGS L1 C2 nrt product",
    tags=["reporting-dev"],                 ##UPDATE IN PROD
    default_args=default_args,
    schedule_interval=timedelta(minutes=15),
)

with dag:


    usgs_aquisitions_job = [
        "echo DEA USGS Acquisitions job started: $(date)",
        "pip install ga-reporting-etls==2.3.1",
        "mkdir -p /airflow/xcom/",
        "usgs-acquisitions /airflow/xcom/return.json"
    ]

    usgs_acquisitions = KubernetesPodOperator(
                namespace="processing",
                image="python:3.8-slim-buster",
                arguments=["bash", "-c", " &&\n".join(usgs_aquisitions_job)],
                name="usgs-acquisitions",
                is_delete_operator_pod=True,
                in_cluster=True,
                task_id="usgs-acquisitions",
                get_logs=True,
                do_xcom_push=True,
                task_concurrency=1,
                env_vars={
                    "DAYS": "{{ dag_run.conf['acquisition_days'] | default(3) }}",
                    "PRODUCT_IDS": "landsat_etm_c2_l1,landsat_ot_c2_l1",
                    "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}"
                }
    )
