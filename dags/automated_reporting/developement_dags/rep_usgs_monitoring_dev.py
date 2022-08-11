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
from datetime import datetime as dt, timedelta

from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)

REPORTING_DB_SECRET = "reporting-db-dev"
ETL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls-dev:latest"
)

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt.now() - timedelta(hours=1),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "secrets": [
        Secret("env", "S3_ACCESS_KEY", "reporting-airflow", "ACCESS_KEY"),
        Secret("env", "S3_BUCKET", "reporting-airflow", "BUCKET"),
        Secret("env", "S3_SECRET_KEY", "reporting-airflow", "SECRET_KEY"),
        Secret("env", "DB_HOST", REPORTING_DB_SECRET, "DB_HOST"),
        Secret("env", "DB_NAME", REPORTING_DB_SECRET, "DB_NAME"),
        Secret("env", "DB_PORT", REPORTING_DB_SECRET, "DB_PORT"),
        Secret("env", "DB_USER", REPORTING_DB_SECRET, "DB_USER"),
        Secret("env", "DB_PASSWORD", REPORTING_DB_SECRET, "DB_PASSWORD"),
        Secret("env", "ODC_DB_HOST", "reporting-odc-db", "DB_HOST"),
        Secret("env", "ODC_DB_NAME", "reporting-odc-db", "DB_NAME"),
        Secret("env", "ODC_DB_PORT", "reporting-odc-db", "DB_PORT"),
        Secret("env", "ODC_DB_USER", "reporting-odc-db", "DB_USER"),
        Secret("env", "ODC_DB_PASSWORD", "reporting-odc-db", "DB_PASSWORD"),
        Secret("env", "M2M_USER", "reporting-usgsm2m-api", "M2M_USER"),
        Secret("env", "M2M_PASSWORD", "reporting-usgsm2m-api", "M2M_PASSWORD"),
    ],
}

dag = DAG(
    "rep_usgs_monitoring_dev",
    description="DAG for completeness and latency metric on USGS rapid mapping products",
    tags=["reporting-dev"],
    default_args=default_args,
    schedule_interval="*/15 * * * *",
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
            "CATEGORY": "nrt",
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

    usgs_l1_completness_ls8_product = dict(
        scene_prefix="LC8%", acq_categories=("RT",), rep_code="usgs_ls8c_level1_nrt_c2"
    )
    usgs_completeness_l1_job = [
        "echo DEA USGS Insert Acquisitions job started: $(date)",
        "mkdir -p /airflow/xcom/",
        "usgs-l1-completeness /airflow/xcom/return.json",
    ]
    usgs_ls8_l1_completeness = KubernetesPodOperator(
        namespace="processing",
        image=ETL_IMAGE,
        arguments=["bash", "-c", " &&\n".join(usgs_completeness_l1_job)],
        name="usgs-completeness-ls8-l1",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="usgs-completeness-ls8-l1",
        get_logs=True,
        do_xcom_push=True,
        env_vars={
            "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
            "DAYS": "30",
            "PRODUCT": json.dumps(usgs_l1_completness_ls8_product),
        },
    )

    usgs_l1_completness_ls9_product = dict(
        scene_prefix="LC9%",
        acq_categories=("T1", "T2"),
        rep_code="usgs_ls9c_level1_nrt_c2",
    )
    usgs_ls9_l1_completeness = KubernetesPodOperator(
        namespace="processing",
        image=ETL_IMAGE,
        arguments=["bash", "-c", " &&\n".join(usgs_completeness_l1_job)],
        name="usgs-completeness-ls9-l1",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="usgs-completeness-ls9-l1",
        get_logs=True,
        do_xcom_push=True,
        env_vars={
            "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
            "DAYS": "30",
            "PRODUCT": json.dumps(usgs_l1_completness_ls9_product),
        },
    )

    usgs_ard_completness_ls8_product = dict(
        odc_code="ga_ls8c_ard_provisional_3", acq_code="LC8%", acq_categories=("RT",)
    )
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
            "USGS_COMPLETENESS_XCOM": "{{ task_instance.xcom_pull(task_ids='usgs-completeness-ls8-l1', key='return_value') }}",
        },
    )
    usgs_ls9_l1_currency = KubernetesPodOperator(
        namespace="processing",
        image=ETL_IMAGE,
        arguments=["bash", "-c", " &&\n".join(usgs_currency_job)],
        name="usgs-currency-ls9-l1",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="usgs-currency-ls9-l1",
        get_logs=True,
        env_vars={
            "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
            "USGS_COMPLETENESS_XCOM": "{{ task_instance.xcom_pull(task_ids='usgs-completeness-ls9-l1', key='return_value') }}",
        },
    )

    usgs_acquisitions >> usgs_inserts
    usgs_inserts >> usgs_ls8_ard_completeness
    usgs_inserts >> usgs_ls8_l1_completeness >> usgs_ls8_l1_currency
    usgs_inserts >> usgs_ls9_l1_completeness >> usgs_ls9_l1_currency
    usgs_acquisitions >> usgs_inserts_hg_l0
