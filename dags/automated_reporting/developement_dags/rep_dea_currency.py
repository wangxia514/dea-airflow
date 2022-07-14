# -*- coding: utf-8 -*-

"""
sara_history dag
"""

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from airflow.operators.dummy import DummyOperator
from datetime import datetime as dt, timedelta
from infra.variables import REPORTING_ODC_DB_SECRET
from infra.variables import REPORTING_DB_DEV_SECRET

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt.now() - timedelta(hours=1),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "secrets": [
        Secret("env", "DB_HOST", REPORTING_DB_DEV_SECRET, "DB_HOST"),
        Secret("env", "DB_NAME", REPORTING_DB_DEV_SECRET, "DB_NAME"),
        Secret("env", "DB_PORT", REPORTING_DB_DEV_SECRET, "DB_PORT"),
        Secret("env", "DB_USER", REPORTING_DB_DEV_SECRET, "DB_USER"),
        Secret("env", "DB_PASSWORD", REPORTING_DB_DEV_SECRET, "DB_PASSWORD"),
        Secret("env", "ODC_DB_HOST", REPORTING_ODC_DB_SECRET, "DB_HOST"),
        Secret("env", "ODC_DB_NAME", REPORTING_ODC_DB_SECRET, "DB_DB_NAME"),
        Secret("env", "ODC_DB_PORT", REPORTING_ODC_DB_SECRET, "DB_DB_PORT"),
        Secret("env", "ODC_DB_USER", REPORTING_ODC_DB_SECRET, "DB_USER"),
        Secret("env", "ODC_DB_PASSWORD", REPORTING_ODC_DB_SECRET, "DB_PASSWORD"),
    ],
}

daily_args = default_args.copy()
daily_args["retry_delay"] = timedelta(minutes=5)
daily_args["retries"] = 3

daily_dag = DAG(
    "rep_dea_currency_daily",
    default_args=daily_args,
    description="DAG for currency of dea products (run daily)",
    tags=["reporting_dev"],
    schedule_interval=timedelta(days=1)
)

ODC_CURRENCY_JOB = [
    "echo DEA ODC Currency job started: $(date)",
    "pip install ga-reporting-etls==2.2.2",
    "odc-currency",
]

def create_odc_task(dag, product_id, days, product_suffix=None):
    """
    Function to generate KubernetesPodOperator tasks with id based on `product_id`
    """
    env_vars={
        "DAYS": str(days),
        "PRODUCT_ID": product_id,
        "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}"
    }
    if product_suffix:
        env_vars["PRODUCT_SUFFIX"] = product_suffix

    return  KubernetesPodOperator(
                dag=dag,
                namespace="processing",
                image="python:3.8-slim-buster",
                arguments=["bash", "-c", " &&\n".join(ODC_CURRENCY_JOB)],
                name=f"odc_currency-{product_id}",
                is_delete_operator_pod=True,
                in_cluster=True,
                task_id=f"odc_currency-{product_id}",
                get_logs=True,
                env_vars=env_vars
    )

with daily_dag:

    START = DummyOperator(task_id="dea-currency-daily")

    # Product list to extract the metric for, could potentially be part of dag configuration and managed in airflow UI?
    products_list = [
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
    daily_odc_tasks = [create_odc_task(daily_dag, product_id, 90, "aws") for product_id in products_list]
    START >> daily_odc_tasks