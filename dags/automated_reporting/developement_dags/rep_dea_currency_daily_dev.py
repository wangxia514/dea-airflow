# -*- coding: utf-8 -*-
"""
DEA Currency Dags
"""

# The DAG object; we'll need this to instantiate a DAG
# pylint: skip-file
import json
from datetime import datetime as dt, timedelta

from airflow import DAG
from airflow.operators.dummy import DummyOperator
from airflow.models import Variable

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

daily_dag = DAG(
    f"rep_dea_currency_daily_v2_{ENV}",
    description="DAG for currency of dea products (run daily)",
    tags=["reporting"] if ENV == "prod" else ["reporting_dev"],
    default_args=default_args,
    schedule_interval="@daily",
)

with daily_dag:

    START_DAILY = DummyOperator(task_id="dea-currency-daily")

    # AWS TASKS
    aws_products_list = [
        # Baseline
        "ga_ls7e_ard_3",
        "ga_ls8c_ard_3",
        "s2a_ard_granule",
        "s2b_ard_granule",
        # Derivavtives
        "ga_ls_wo_3",
        "ga_ls_fc_3",
        "ga_ls8c_nbart_gm_cyear_3",
        "ga_ls7e_nbart_gm_cyear_3",
        "ga_ls_wo_fq_cyear_3",
        "ga_ls_wo_fq_apr_oct_3",
        "ga_ls_wo_fq_nov_mar_3",
    ]
    AWS_ODC_CURRENCY_JOB = [
        "echo DEA AWS ODC Currency job started: $(date)",
        "odc-currency",
    ]
    daily_aws_odc_tasks = [
        utilities.k8s_operator(
            dag=daily_dag,
            image=ETL_IMAGE,
            task_id=f"aws-odc_{product_id}",
            cmds=AWS_ODC_CURRENCY_JOB,
            env_vars={
                "PRODUCT_ID": product_id,
                "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
                "DAYS": "90",
                "PRODUCT_SUFFIX": "aws",
            },
            secrets=k8s_secrets.db_secrets(ENV) + k8s_secrets.aws_odc_secrets,
        )
        for product_id in aws_products_list
    ]

    # NCI TASKS
    products_list = json.loads(Variable.get("rep_currency_product_list_nci_odc"))
    nci_products_list = [
        product for product in products_list if product["rate"] == "daily"
    ]
    NCI_ODC_CURRENCY_JOB = [
        "echo DEA NCI ODC Currency job started: $(date)",
        "export ODC_DB_HOST=localhost",
        "export ODC_DB_PORT=54320",
        "odc-currency-views",
    ]
    daily_nci_odc_tasks = [
        utilities.k8s_operator(
            dag=daily_dag,
            image=ETL_IMAGE,
            task_id=f"nci-odc_{product.get('product_id')}",
            cmds=utilities.NCI_TUNNEL_CMDS + NCI_ODC_CURRENCY_JOB,
            env_vars={
                "PRODUCT_ID": product.get("product_id"),
                "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
                "DAYS": product.get("days", "0")
            },
            secrets=k8s_secrets.db_secrets(ENV) + k8s_secrets.nci_odc_secrets
        )
        for product in nci_products_list
    ]

    daily_odc_tasks = daily_aws_odc_tasks + daily_nci_odc_tasks
    START_DAILY >> daily_odc_tasks
