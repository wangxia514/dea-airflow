# -*- coding: utf-8 -*-

"""
Operational monitoring of ESA production systems
"""

# The DAG object; we'll need this to instantiate a DAG
from datetime import datetime, timedelta
import json

from airflow import DAG

from automated_reporting import k8s_secrets, utilities

ENV = "prod"
ETL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls:v2.11.0"
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
        + k8s_secrets.s3_secrets
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
        secrets=k8s_secrets.s3_secrets + k8s_secrets.db_secrets(ENV),
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
        "use_identifier": False,
        "days": 30,
        "sensors": [
            {
                "id": "s2a",
                "odc_code": "s2a_nrt_granule",
                "rep_code": "s2a_nrt_granule",
            },
            {
                "id": "s2b",
                "odc_code": "s2b_nrt_granule",
                "rep_code": "s2b_nrt_granule",
            },
        ],
    }
    ARDP_CONFIG = {
        "title": "AWS ARD P ODC",
        "source": "odc-nrt",
        "use_identifier": False,
        "days": 30,
        "sensors": [
            {
                "id": "s2a",
                "odc_code": "ga_s2am_ard_provisional_3",
                "rep_code": "ga_s2am_ard_provisional_3",
            },
            {
                "id": "s2b",
                "odc_code": "ga_s2bm_ard_provisional_3",
                "rep_code": "ga_s2bm_ard_provisional_3",
            },
        ],
    }

    COMPUTE_COMPLETENESS_TASK = [
        "echo Compute S2 L1 Completeness: $(date)",
        "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
        "esa-completeness",
    ]

    compute_s2_l1_completeness = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        task_id="compute_s2_l1_completeness",
        cmds=COMPUTE_COMPLETENESS_TASK,
        env_vars={
            "COMPLETENESS_CONFIG": json.dumps(L1_CONFIG),
            "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
        },
        secrets=k8s_secrets.aws_odc_secrets + k8s_secrets.db_secrets(ENV),
    )

    compute_s2_ard_completeness = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        task_id="compute_s2_ard_completeness",
        cmds=COMPUTE_COMPLETENESS_TASK,
        env_vars={
            "COMPLETENESS_CONFIG": json.dumps(ARD_CONFIG),
            "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
        },
        secrets=k8s_secrets.aws_odc_secrets + k8s_secrets.db_secrets(ENV),
    )

    compute_s2_ardp_completeness = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        task_id="compute_s2_ardp_completeness",
        cmds=COMPUTE_COMPLETENESS_TASK,
        env_vars={
            "COMPLETENESS_CONFIG": json.dumps(ARDP_CONFIG),
            "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
        },
        secrets=k8s_secrets.aws_odc_secrets + k8s_secrets.db_secrets(ENV),
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

    syn_l1_nrt_download >> syn_l1_nrt_ingestion
    (
        scihub_s2_acquisitions
        >> insert_s2_acquisitions
        >> [
            compute_s2_ard_completeness,
            compute_s2_ardp_completeness,
        ]
    )
    [syn_l1_nrt_ingestion, insert_s2_acquisitions] >> compute_s2_l1_completeness
