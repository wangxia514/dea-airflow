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
    "start_date": datetime(2022, 9, 10),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": True if ENV == "prod" else False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    f"rep_esa_monitoring_daily_{ENV}",
    description="DAG ESA production monitoring",
    tags=["reporting"] if ENV == "prod" else ["reporting_dev"],
    default_args=default_args,
    schedule_interval="@daily",
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

    AWS_ODC_COMPLETENESS_TASK = [
        "echo Compute S2 ODC Completeness: $(date)",
        "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
        "esa-odc-completeness",
    ]
    AWS_ODC_PRODUCT_DEFS = [
        {
            "product_id": "s2a_ard_granule",
            "reporting_id": "s2a_ard_granule",
            "environment": "aws-odc",
            "platform": "s2a",
        },
        {
            "product_id": "s2b_ard_granule",
            "reporting_id": "s2b_ard_granule",
            "environment": "aws-odc",
            "platform": "s2b",
        },
    ]

    aws_odc_tasks = [
        utilities.k8s_operator(
            dag=dag,
            image=ETL_IMAGE,
            task_id=f"completeness-{product_def['reporting_id']}",
            cmds=AWS_ODC_COMPLETENESS_TASK,
            env_vars={
                "PRODUCT": json.dumps(product_def),
                "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
                "DAYS": "30",
            },
            secrets=k8s_secrets.aws_odc_secrets + k8s_secrets.db_secrets(ENV),
        )
        for product_def in AWS_ODC_PRODUCT_DEFS
    ]

    NCI_ODC_COMPLETENESS_TASK = [
        "echo Compute S2 ODC Completeness: $(date)",
        "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
        "export ODC_DB_HOST=localhost",
        "export ODC_DB_PORT=54320",
        "esa-odc-completeness",
    ]
    NCI_ODC_PRODUCT_DEFS = [
        {
            "product_id": "s2a_level1c_granule",
            "reporting_id": "s2a_level1c_granule-nci",
            "environment": "nci-odc",
            "platform": "s2a",
        },
        {
            "product_id": "s2b_level1c_granule",
            "reporting_id": "s2b_level1c_granule-nci",
            "environment": "nci-odc",
            "platform": "s2b",
        },
        {
            "product_id": "s2a_ard_granule",
            "reporting_id": "s2a_ard_granule-nci",
            "environment": "nci-odc",
            "platform": "s2a",
        },
        {
            "product_id": "s2b_ard_granule",
            "reporting_id": "s2b_ard_granule-nci",
            "environment": "nci-odc",
            "platform": "s2b",
        },
        {
            "product_id": "ga_s2am_ard_3",
            "reporting_id": "ga_s2am_ard_3-nci",
            "environment": "nci-odc",
            "platform": "s2a",
        },
        {
            "product_id": "ga_s2bm_ard_3",
            "reporting_id": "ga_s2bm_ard_3-nci",
            "environment": "nci-odc",
            "platform": "s2b",
        },
    ]

    nci_odc_tasks = [
        utilities.k8s_operator(
            dag=dag,
            image=ETL_IMAGE,
            task_id=f"completeness-{product_def['reporting_id']}",
            cmds=utilities.NCI_TUNNEL_CMDS + NCI_ODC_COMPLETENESS_TASK,
            env_vars={
                "PRODUCT": json.dumps(product_def),
                "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
                "DAYS": "30",
            },
            secrets=k8s_secrets.nci_odc_secrets + k8s_secrets.db_secrets(ENV),
        )
        for product_def in NCI_ODC_PRODUCT_DEFS
    ]

    scihub_s2_acquisitions >> insert_s2_acquisitions >> [aws_odc_tasks, nci_odc_tasks]
