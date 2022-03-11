# -*- coding: utf-8 -*-

"""
Operational monitoring of ESA production systems
"""

# The DAG object; we'll need this to instantiate a DAG
from datetime import datetime, timedelta
import json

from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from airflow.hooks.base_hook import BaseHook
from airflow.models import Variable

from automated_reporting.utilities import helpers
from infra import connections as infra_connections

REP_CONN_STR = Variable.get("db_rep_secret")
SCIHUB_CREDENTIALS_STR = Variable.get("copernicus_api_password")
S3_CREDENTIALS_STR = Variable.get("reporting_s3_secret")
ODC_CONN_STR = json.dumps(
    helpers.parse_connection(
        BaseHook.get_connection(infra_connections.DB_ODC_READER_CONN)
    )
)

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": datetime(2022, 3, 1),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "rep_esa_monitoring_prod",
    description="DAG ESA production monitoring",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval=timedelta(minutes=15),
)

with dag:

    SCIHUB_ACQS_TASK = [
        "echo Get SCIHUB acquisitions: $(date)",
        "pip install ga-reporting-etls",
        "mkdir -p /airflow/xcom/",
        "python3 -c 'from nemo_reporting.esa_monitoring import s2_acquisitions; \
            s2_acquisitions.task_env(json_output=\"/airflow/xcom/return.json\")'",
    ]
    scihub_s2_acquisitions = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(SCIHUB_ACQS_TASK)],
        name="scihub_s2_acquisitions",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="scihub_s2_acquisitions",
        get_logs=True,
        task_concurrency=1,
        do_xcom_push=True,
        env_vars={
            "SCIHUB_CREDENTIALS": SCIHUB_CREDENTIALS_STR,
            "S3_CREDENTIALS": S3_CREDENTIALS_STR,
            "DB_CREDS": REP_CONN_STR,
            "ACQUISITION_DAYS": "{{ dag_run.conf['acquisition_days'] | default(3) }}",
            "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
        },
    )

    INSERT_ACQS_TASK = [
        "echo Insert S2 acquisitions: $(date)",
        "pip install ga-reporting-etls",
        "python3 -c 'from nemo_reporting.esa_monitoring import s2_inserts; s2_inserts.task_env()'",
    ]
    insert_s2_acquisitions = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(INSERT_ACQS_TASK)],
        name="insert_s2_acquisitions",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="insert_s2_acquisitions",
        get_logs=True,
        env_vars={
            "S3_CREDENTIALS": S3_CREDENTIALS_STR,
            "DB_CREDS": REP_CONN_STR,
            "S2_ACQ_XCOM": "{{ task_instance.xcom_pull(task_ids='scihub_s2_acquisitions', key='return_value') }}",
        },
    )

    L1_CONFIG = {
        "title": "AWS L1 SQS",
        "source": "sqs",
        "use_identifier": True,
        "days": 30,
        "sensors": [
            {"id": "s2a", "pipeline": "S2A_MSIL1C", "rep_code": "esa_s2a_msi_l1c"},
            {"id": "s2b", "pipeline": "S2B_MSIL1C", "rep_code": "esa_s2b_msi_l1c"},
        ],
    }
    ARD_CONFIG = {
        "title": "AWS ARD ODC",
        "source": "odc-nrt",
        "use_identifier": True,
        "days": 30,
        "sensors": [
            {
                "id": "s2a",
                "odc_code": "s2a_nrt_granule",
                "rep_code": "ga_s2a_msi_ard_c3",
            },
            {
                "id": "s2b",
                "odc_code": "s2b_nrt_granule",
                "rep_code": "ga_s2b_msi_ard_c3",
            },
        ],
    }
    COMPUTE_COMPLETENESS_TASK = [
        "echo Compute S2 L1 Completeness: $(date)",
        "pip install ga-reporting-etls",
        "python3 -c 'from nemo_reporting.esa_monitoring import s2_completeness; s2_completeness.task_env()'",
    ]
    compute_s2_l1_completeness = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(COMPUTE_COMPLETENESS_TASK)],
        name="compute_s2_l1_completeness",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="compute_s2_l1_completeness",
        get_logs=True,
        env_vars={
            "COMPLETENESS_CONFIG": json.dumps(L1_CONFIG),
            "S3_CREDENTIALS": S3_CREDENTIALS_STR,
            "DB_CREDS": REP_CONN_STR,
            "ODC_CREDS": ODC_CONN_STR,
        },
    )
    compute_s2_ard_completeness = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(COMPUTE_COMPLETENESS_TASK)],
        name="compute_s2_ard_completeness",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="compute_s2_ard_completeness",
        get_logs=True,
        env_vars={
            "COMPLETENESS_CONFIG": json.dumps(ARD_CONFIG),
            "S3_CREDENTIALS": S3_CREDENTIALS_STR,
            "DB_CREDS": REP_CONN_STR,
            "ODC_CREDS": ODC_CONN_STR,
        },
    )

    (
        scihub_s2_acquisitions
        >> insert_s2_acquisitions
        >> [compute_s2_l1_completeness, compute_s2_ard_completeness]
    )
