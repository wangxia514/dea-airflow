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

ENV = "prod"
ETL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls-dev:9fad0a823a"
)

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt(2022, 8, 1),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": True if ENV == "prod" else False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

monthly_dag = DAG(
    f"rep_dea_currency_monthly_{ENV}",
    description="DAG for currency of dea products (run monthly)",
    tags=["reporting"] if ENV == "prod" else ["reporting_dev"],
    default_args=default_args,
    schedule_interval="@monthly",
)

with monthly_dag:

    START_MONTHLY = DummyOperator(task_id="dea-currency-monthly")

    # NCI TASKS
    products_list = json.loads(Variable.get("rep_currency_product_list_nci_odc"))
    nci_products_list = [
        product for product in products_list if product["rate"] == "monthly"
    ]
    NCI_ODC_CURRENCY_JOB = [
        "echo DEA NCI ODC Currency job started: $(date)",
        "export ODC_DB_HOST=localhost",
        "export ODC_DB_PORT=54320",
        "odc-currency-views",
    ]
    monthly_nci_odc_tasks = [
        utilities.k8s_operator(
            dag=monthly_dag,
            image=ETL_IMAGE,
            task_id=f"nci-odc_{product.get('product_id')}",
            cmds=utilities.NCI_TUNNEL_CMDS + NCI_ODC_CURRENCY_JOB,
            env_vars={
                "PRODUCT_ID": product.get("product_id"),
                "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
                "DAYS": str(product.get("days", 0)),
            },
            secrets=k8s_secrets.db_secrets(ENV) + k8s_secrets.nci_odc_secrets,
        )
        for product in nci_products_list
    ]

    START_MONTHLY >> monthly_nci_odc_tasks
