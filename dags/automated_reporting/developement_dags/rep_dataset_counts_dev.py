# -*- coding: utf-8 -*-

"""
Monitoring of dataset counts in NCI and AWS ODC
"""

from datetime import datetime, timedelta
import json

from airflow import DAG
from airflow.models import Variable

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
    f"rep_dataset_counts_{ENV}",
    description="DAG for counts of ODC datasets",
    tags=["reporting"] if ENV == "prod" else ["reporting_dev"],
    default_args=default_args,
    schedule_interval="@daily",
)

with dag:

    AWS_DATASET_COUNT_TASK = [
        "echo Compute S2 ODC Completeness: $(date)",
        "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
        "dataset-count",
    ]
    aws_product_ids = json.loads(Variable.get("rep_dataset_counts_aws"))
    aws_odc_tasks = [
        utilities.k8s_operator(
            dag=dag,
            image=ETL_IMAGE,
            task_id=f"dataset_counts-{product_id}-aws",
            cmds=AWS_DATASET_COUNT_TASK,
            env_vars={
                "PRODUCT": product_id,
                "PLATFORM": "aws",
                "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
            },
            secrets=k8s_secrets.aws_odc_secrets + k8s_secrets.db_secrets(ENV),
        )
        for product_id in aws_product_ids
    ]

    NCI_DATSET_COUNT_TASK = [
        "echo Compute S2 ODC Completeness: $(date)",
        "export ODC_DB_HOST=localhost",
        "export ODC_DB_PORT=54320",
        "dataset-count",
    ]
    nci_product_ids = json.loads(Variable.get("rep_dataset_counts_nci"))
    nci_odc_tasks = [
        utilities.k8s_operator(
            dag=dag,
            image=ETL_IMAGE,
            task_id=f"dataset_count-{product_id}-nci",
            cmds=utilities.NCI_TUNNEL_CMDS + NCI_DATSET_COUNT_TASK,
            env_vars={
                "PRODUCT": product_id,
                "PLATFORM": "nci",
                "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
            },
            secrets=k8s_secrets.nci_odc_secrets + k8s_secrets.db_secrets(ENV),
        )
        for product_id in nci_product_ids
    ]

    aws_odc_tasks + nci_odc_tasks
