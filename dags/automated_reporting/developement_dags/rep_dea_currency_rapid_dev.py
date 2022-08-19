# -*- coding: utf-8 -*-
"""
DEA Currency Dags
"""

# The DAG object; we'll need this to instantiate a DAG
# pylint: skip-file
from datetime import datetime as dt, timedelta

from airflow import DAG
from airflow.operators.dummy import DummyOperator

from automated_reporting import k8s_secrets, utilities

ENV = "dev"
ETL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls-dev:latest"
)

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt.now() - timedelta(hours=1),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": True if ENV == "prod" else False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

rapid_dag = DAG(
    f"rep_dea_currency_rapid_{ENV}",
    description="DAG for currency of dea products (run 15mins)",
    tags=["reporting"] if ENV == "prod" else ["reporting_dev"],
    default_args=default_args,
    schedule_interval="*/15 * * * *",
)

with rapid_dag:

    START_RAPID = DummyOperator(task_id="dea-currency-rapid")

    # Product list to extract the metric for, could potentially be part of dag configuration and managed in airflow UI?
    rapid_odc_products_list = [
        "s2a_nrt_granule",
        "s2b_nrt_granule",
        "ga_ls8c_ard_provisional_3",
        "ga_s2am_ard_provisional_3",
        "ga_s2bm_ard_provisional_3",
        "ga_s2_wo_3",
        "ga_s2_ba_provisional_3",
    ]
    AWS_ODC_CURRENCY_JOB = [
        "echo DEA AWS ODC Currency job started: $(date)",
        "odc-currency",
    ]
    rapid_aws_odc_tasks = [
        utilities.k8s_operator(
            dag=rapid_dag,
            image=ETL_IMAGE,
            task_id=f"aws-odc_{product_id}",
            cmds=AWS_ODC_CURRENCY_JOB,
            env_vars={
                "PRODUCT_ID": product_id,
                "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
                "DAYS": "30",
            },
            secrets=k8s_secrets.db_secrets(ENV) + k8s_secrets.aws_odc_secrets,
        )
        for product_id in rapid_odc_products_list
    ]

    rapid_sns_products_list = [
        ("S2A_MSIL1C", "esa_s2a_msi_l1c"),
        ("S2B_MSIL1C", "esa_s2b_msi_l1c"),
    ]
    SNS_CURRENCY_JOB = [
        "echo DEA ODC Currency job started: $(date)",
        "sns-currency",
    ]
    rapid_aws_sns_tasks = [
        utilities.k8s_operator(
            dag=rapid_dag,
            image=ETL_IMAGE,
            task_id=f"aws-sns_{product_id}",
            cmds=SNS_CURRENCY_JOB,
            env_vars={
                "PRODUCT_ID": product_id,
                "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
                "PIPELINE": pipeline,
            },
            secrets=k8s_secrets.db_secrets(ENV),
        )
        for pipeline, product_id in rapid_sns_products_list
    ]

    rapid_tasks = rapid_aws_odc_tasks + rapid_aws_sns_tasks
    START_RAPID >> rapid_tasks
