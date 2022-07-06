"""
# Simple latency metric on nrt products: AWS ODC -> AIRFLOW -> Reporting DB

This DAG extracts latest timestamp values for a list of products in AWS ODC. It:
 * Connects to AWS ODC.
 * Runs multiple tasks (1 per product type) querying the latest timestamps for each from AWS ODC.
 * Inserts a summary of latest timestamps into the landsat.derivative_latency table in reporting DB.

"""

from datetime import datetime as dt
from datetime import timedelta
import pendulum

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from datetime import datetime as dt, timedelta
from infra.variables import REPORTING_DB_SECRET
from infra.variables import REPORTING_ODC_DB_SECRET
# Tasks
utc_tz = pendulum.timezone("UTC")

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt(2021, 9, 22, tzinfo=utc_tz),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "secrets": [
        Secret("env", "REP_DB_HOST", REPORTING_DB_SECRET, "DB_HOST"),
        Secret("env", "REP_DB_NAME", REPORTING_DB_SECRET, "DB_NAME"),
        Secret("env", "REP_DB_PORT", REPORTING_DB_SECRET, "DB_PORT"),
        Secret("env", "REP_DB_USER", REPORTING_DB_SECRET, "DB_USER"),
        Secret("env", "REP_DB_PASSWORD", REPORTING_DB_SECRET, "DB_PASSWORD"),
        Secret("env", "ODC_DB_HOST", REPORTING_ODC_DB_SECRET, "DB_HOST"),
        Secret("env", "ODC_DB_NAME", REPORTING_ODC_DB_SECRET, "DB_DB_NAME"),
        Secret("env", "ODC_DB_PORT", REPORTING_ODC_DB_SECRET, "DB_DB_PORT"),
        Secret("env", "ODC_DB_USER", REPORTING_ODC_DB_SECRET, "DB_USER"),
        Secret("env", "ODC_DB_PASSWORD", REPORTING_ODC_DB_SECRET, "DB_PASSWORD"),
    ],
}

dag = DAG(
    "rep_nrt_simple_latency_prod",
    description="DAG for simple latency metric on nrt products: AWS ODC -> AIRFLOW -> Live Reporting DB",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval=timedelta(minutes=15),
)

with dag:
    JOBS1 = [
        "echo Check DB started: $(date)",
        "pip install simple-latency==1.0.1",
        "check-db",
    ]
    JOBS2 = [
        "echo ODC Latency task started: $(date)",
        "pip install simple-latency==1.0.1",
        "odc-latency",
    ]
    JOBS3 = [
        "echo SNS Latency task started: $(date)",
        "pip install simple-latency==1.0.1",
        "sns-latency",
    ]
    products_list = [
        "s2a_nrt_granule",
        "s2b_nrt_granule",
        "ga_s2_wo_3",
        "ga_ls7e_ard_provisional_3",
        "ga_ls8c_ard_provisional_3",
        "ga_s2am_ard_provisional_3",
        "ga_s2bm_ard_provisional_3",
        "ga_s2_ba_provisional_3"
    ]

    check_db = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS1)],
        name="write-xcom",
        do_xcom_push=False,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="check-db",
        get_logs=True,
    )
    odc_tasks = {}
    for i in range(0, len(products_list)):
        odc_tasks[i] = KubernetesPodOperator(
            namespace="processing",
            image="python:3.8-slim-buster",
            arguments=["bash", "-c", " &&\n".join(JOBS2)],
            name="write-xcom",
            do_xcom_push=False,
            is_delete_operator_pod=True,
            in_cluster=True,
            task_id=f"odc-latency_{products_list[i]}",
            get_logs=True,
            env_vars={
                "PRODUCT_NAME" : products_list[i],
                "DAYS" : 30,
            },
        )
        check_db >> odc_tasks[i]
    sns_tasks = {}
    sns_list = [("S2A_MSIL1C", "esa_s2a_msi_l1c"), ("S2B_MSIL1C", "esa_s2b_msi_l1c")]
    for i in range(0, len(sns_list)):
        sns_tasks[i] = KubernetesPodOperator(
            namespace="processing",
            image="python:3.8-slim-buster",
            arguments=["bash", "-c", " &&\n".join(JOBS3)],
            name="write-xcom",
            do_xcom_push=False,
            is_delete_operator_pod=True,
            in_cluster=True,
            task_id=f"sns-latency_{sns_list[i]}",
            get_logs=True,
            env_vars={
                "PIPELINE" : sns_list[i][0],
                "PRODUCT_ID": sns_list[i][1],
            },
        )
        check_db >> sns_tasks[i]
