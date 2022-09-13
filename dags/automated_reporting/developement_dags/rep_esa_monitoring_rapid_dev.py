# -*- coding: utf-8 -*-

"""
Operational monitoring of ESA production systems
"""

# The DAG object; we'll need this to instantiate a DAG
from datetime import datetime, timedelta
import json

from airflow import DAG

from automated_reporting import k8s_secrets, utilities

ENV = "dev"
ETL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls-dev:latest"
)

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": datetime(2022, 3, 1),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": True if ENV == "prod" else False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    f"rep_esa_monitoring_{ENV}",
    description="DAG ESA production monitoring",
    tags=["reporting"] if ENV == "prod" else ["reporting_dev"],
    default_args=default_args,
    schedule_interval="*/15 * * * *",
)

with dag:

    SCIHUB_ACQS_TASK = [
        "echo Get SCIHUB acquisitions: $(date)",
        "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
        "mkdir -p /airflow/xcom/",
        "esa-acquisitions /airflow/xcom/return.json",
    ]
    scihub_s2_acquisitions = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        task_id="scihub_s2_acquisitions",
        xcom=True,
        task_concurrency=1,
        cmds=SCIHUB_ACQS_TASK,
        env_vars={
            "ACQUISITION_DAYS": "{{ dag_run.conf['acquisition_days'] | default(3) }}",
            "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
        },
        secrets=k8s_secrets.scihub_secrets
        + k8s_secrets.s3_automated_operation_bucket
        + k8s_secrets.iam_rep_secrets
        + k8s_secrets.db_secrets(ENV),
    )

    INSERT_ACQS_TASK = [
        "echo Insert S2 acquisitions: $(date)",
        "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
        "esa-inserts",
    ]
    insert_s2_acquisitions = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        task_id="insert_s2_acquisitions",
        cmds=INSERT_ACQS_TASK,
        env_vars={
            "S2_ACQ_XCOM": "{{ task_instance.xcom_pull(task_ids='scihub_s2_acquisitions', key='return_value') }}",
        },
        secrets=k8s_secrets.s3_automated_operation_bucket
        + k8s_secrets.iam_rep_secrets
        + k8s_secrets.db_secrets(ENV),
    )

    syn_l1_nrt_download = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo syn_l1_nrt_download job started: $(date)",
            "mkdir -p /airflow/xcom/",
            "syn_l1_nrt_downloads /airflow/xcom/return.json",
        ],
        task_id="syn_l1_nrt_download",
        xcom=True,
        env_vars={
            "QUEUE_NAME": "dea-sandbox-eks-automated-reporting-sqs",
        },
        secrets=k8s_secrets.sqs_secrets,
    )

    syn_l1_nrt_ingestion = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo syn_l1_nrt_ingestion job started: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "syn_l1_nrt_ingestion",
        ],
        task_id="syn_l1_nrt_ingestion",
        env_vars={
            "METRICS": "{{ task_instance.xcom_pull(task_ids='syn_l1_nrt_download') }}",
        },
        secrets=k8s_secrets.db_secrets(ENV),
    )

    SQS_COMPLETENESS_TASK = [
        "echo Compute S2 L1 Completeness(SQS): $(date)",
        "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
        "esa-sqs-completeness",
    ]
    SQS_PRODUCT_DEFS = [
        {
            "environment": "aws-sqs",
            "use_identifier": True,
            "reporting_id": "esa_s2a_msi_l1c",
            "platform": "s2a",
        },
        {
            "environment": "aws-sqs",
            "use_identifier": True,
            "reporting_id": "esa_s2b_msi_l1c",
            "platform": "s2b",
        },
    ]

    sqs_tasks = [
        utilities.k8s_operator(
            dag=dag,
            image=ETL_IMAGE,
            task_id=f"completeness-{product_def['reporting_id']}",
            cmds=SQS_COMPLETENESS_TASK,
            env_vars={
                "PRODUCT": json.dumps(product_def),
                "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
                "DAYS": "30",
            },
            secrets=k8s_secrets.db_secrets(ENV),
        )
        for product_def in SQS_PRODUCT_DEFS
    ]

    ODC_COMPLETENESS_TASK = [
        "echo Compute S2 Completeness: $(date)",
        "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
        "esa-odc-completeness",
    ]
    ODC_PRODUCT_DEFS = [
        {
            "product_id": "s2a_nrt_granule",
            "reporting_id": "s2a_nrt_granule",
            "environment": "aws-odc",
            "platform": "s2a",
        },
        {
            "product_id": "s2b_nrt_granule",
            "reporting_id": "s2b_nrt_granule",
            "environment": "aws-odc",
            "platform": "s2b",
        },
        {
            "product_id": "ga_s2am_ard_provisional_3",
            "reporting_id": "ga_s2am_ard_provisional_3",
            "environment": "aws-odc",
            "platform": "s2a",
        },
        {
            "product_id": "ga_s2bm_ard_provisional_3",
            "reporting_id": "ga_s2bm_ard_provisional_3",
            "environment": "aws-odc",
            "platform": "s2b",
        },
        {
            "product_id": "ga_s2_ba_provisional_3",
            "reporting_id": "ga_s2_ba_provisional_3",
            "environment": "aws-odc",
            "platform": "s2",
        },
    ]

    odc_tasks = [
        utilities.k8s_operator(
            dag=dag,
            image=ETL_IMAGE,
            task_id=f"completeness-{product_def['reporting_id']}",
            cmds=SQS_COMPLETENESS_TASK,
            env_vars={
                "PRODUCT": json.dumps(product_def),
                "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
                "DAYS": "30",
            },
            secrets=k8s_secrets.aws_odc_secrets + k8s_secrets.db_secrets(ENV),
        )
        for product_def in ODC_PRODUCT_DEFS
    ]

    syn_l1_nrt_download >> syn_l1_nrt_ingestion
    scihub_s2_acquisitions >> insert_s2_acquisitions
    [syn_l1_nrt_ingestion, insert_s2_acquisitions] >> (sqs_tasks + odc_tasks)
