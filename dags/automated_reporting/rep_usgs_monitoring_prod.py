"""
# Run tasks to monitor USGS NRT Products

This DAG
 * Connects to USGS M2M API to determine USGS Inventory
 * Inserts data into reporting DB, in both hg and landsat schemas
 * Runs completeness and latency checks
 * Inserts summary completeness and latency reporting data
 * Inserts completeness data for each wrs path row
"""
import json
from datetime import datetime as dt, timedelta, timezone

from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)

from infra.variables import REPORTING_ODC_DB_SECRET
from infra.variables import REPORTING_DB_SECRET
from infra.variables import REPORTING_USGSM2M_API_SECRET
from infra.variables import REPORTING_AIRFLOW_S3_SECRET

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt(2022, 7, 22, 0, 0, 0, tzinfo=timezone.utc),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "secrets": [
        Secret("env", "S3_ACCESS_KEY", REPORTING_AIRFLOW_S3_SECRET, "ACCESS_KEY"),
        Secret("env", "S3_BUCKET", REPORTING_AIRFLOW_S3_SECRET, "BUCKET"),
        Secret("env", "S3_SECRET_KEY", REPORTING_AIRFLOW_S3_SECRET, "SECRET_KEY"),
        Secret("env", "DB_HOST", REPORTING_DB_SECRET, "DB_HOST"),
        Secret("env", "DB_NAME", REPORTING_DB_SECRET, "DB_NAME"),
        Secret("env", "DB_PORT", REPORTING_DB_SECRET, "DB_PORT"),
        Secret("env", "DB_USER", REPORTING_DB_SECRET, "DB_USER"),
        Secret("env", "DB_PASSWORD", REPORTING_DB_SECRET, "DB_PASSWORD"),
        Secret("env", "ODC_DB_HOST", REPORTING_ODC_DB_SECRET, "DB_HOST"),
        Secret("env", "ODC_DB_NAME", REPORTING_ODC_DB_SECRET, "DB_NAME"),
        Secret("env", "ODC_DB_PORT", REPORTING_ODC_DB_SECRET, "DB_PORT"),
        Secret("env", "ODC_DB_USER", REPORTING_ODC_DB_SECRET, "DB_USER"),
        Secret("env", "ODC_DB_PASSWORD", REPORTING_ODC_DB_SECRET, "DB_PASSWORD"),
        Secret("env", "M2M_USER", REPORTING_USGSM2M_API_SECRET, "M2M_USER"),
        Secret("env", "M2M_PASSWORD", REPORTING_USGSM2M_API_SECRET, "M2M_PASSWORD"),
    ],
}

ETL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls:v2.4.4"
)

dag = DAG(
    "rep_usgs_monitoring_prod",
    description="DAG for completeness and latency metric on USGS rapid mapping products",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval=timedelta(minutes=15),
)

with dag:

    usgs_aquisitions_job = [
        "echo DEA USGS Acquisitions job started: $(date)",
        "mkdir -p /airflow/xcom/",
        "usgs-acquisitions /airflow/xcom/return.json",
    ]
    usgs_acquisitions = KubernetesPodOperator(
        namespace="processing",
        image=ETL_IMAGE,
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
            "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
        },
    )

    usgs_inserts_job = [
        "echo DEA USGS Insert Acquisitions job started: $(date)",
        "usgs-inserts",
    ]
    usgs_inserts = KubernetesPodOperator(
        namespace="processing",
        image=ETL_IMAGE,
        arguments=["bash", "-c", " &&\n".join(usgs_inserts_job)],
        name="usgs-inserts",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="usgs-inserts",
        get_logs=True,
        env_vars={
            "USGS_ACQ_XCOM": "{{ task_instance.xcom_pull(task_ids='usgs-acquisitions', key='return_value') }}",
        },
    )

    usgs_inserts_hg_l0_job = [
        "echo DEA USGS Insert Acquisitions job started: $(date)",
        "usgs-inserts-hg-l0",
    ]
    usgs_inserts_hg_l0 = KubernetesPodOperator(
        namespace="processing",
        image=ETL_IMAGE,
        arguments=["bash", "-c", " &&\n".join(usgs_inserts_hg_l0_job)],
        name="usgs-inserts-hg-l0",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="usgs-inserts-hg-l0",
        get_logs=True,
        env_vars={
            "USGS_ACQ_XCOM": "{{ task_instance.xcom_pull(task_ids='usgs-acquisitions', key='return_value') }}",
        },
    )

    usgs_l1_completness_ls8_product = {
        "s3_code": "L8C2",
        "acq_code": "LC8%",
        "rep_code": "usgs_ls8c_level1_nrt_c2",
    }
    usgs_completeness_l1_job = [
        "echo DEA USGS Insert Acquisitions job started: $(date)",
        "mkdir -p /airflow/xcom/",
        "usgs-l1-completeness /airflow/xcom/return.json",
    ]
    usgs_ls8_l1_completeness = KubernetesPodOperator(
        namespace="processing",
        image=ETL_IMAGE,
        arguments=["bash", "-c", " &&\n".join(usgs_completeness_l1_job)],
        name="usgs-completeness-l1",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="usgs-completeness-l1",
        get_logs=True,
        do_xcom_push=True,
        env_vars={
            "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
            "DAYS": "30",
            "PRODUCT": json.dumps(usgs_l1_completness_ls8_product),
        },
    )

    usgs_ard_completness_ls8_product = {
        "odc_code": "ga_ls8c_ard_provisional_3",
        "acq_code": "LC8%",
    }
    usgs_completeness_ard_job = [
        "echo DEA USGS Insert Acquisitions job started: $(date)",
        "usgs-ard-completeness",
    ]
    usgs_ls8_ard_completeness = KubernetesPodOperator(
        namespace="processing",
        image=ETL_IMAGE,
        arguments=["bash", "-c", " &&\n".join(usgs_completeness_ard_job)],
        name="usgs-completeness-ard",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="usgs-completeness-ard",
        get_logs=True,
        env_vars={
            "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
            "DAYS": "30",
            "PRODUCT": json.dumps(usgs_ard_completness_ls8_product),
        },
    )

    usgs_currency_job = [
        "echo DEA USGS Insert Acquisitions job started: $(date)",
        "usgs-currency-from-completeness",
    ]
    usgs_ls8_l1_currency = KubernetesPodOperator(
        namespace="processing",
        image=ETL_IMAGE,
        arguments=["bash", "-c", " &&\n".join(usgs_currency_job)],
        name="usgs-currency-ls8-l1",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="usgs-currency-ls8-l1",
        get_logs=True,
        env_vars={
            "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
            "USGS_COMPLETENESS_XCOM": "{{ task_instance.xcom_pull(task_ids='usgs-completeness-l1', key='return_value') }}",
        },
    )

    usgs_acquisitions >> usgs_inserts
    usgs_inserts >> usgs_ls8_ard_completeness
    usgs_inserts >> usgs_ls8_l1_completeness >> usgs_ls8_l1_currency
    usgs_acquisitions >> usgs_inserts_hg_l0
