"""
# Simple latency metric on nrt products: AWS ODC -> AIRFLOW -> Reporting DB

This DAG extracts latest timestamp values for a list of products in AWS ODC. It:
 * Connects to AWS ODC.
 * Runs multiple tasks (1 per product type) querying the latest timestamps for each from AWS ODC.
 * Inserts a summary of latest timestamps into the landsat.derivative_latency table in reporting DB.

"""
import os
import pathlib
import logging
from datetime import datetime as dt
from datetime import timedelta

from airflow import DAG
from airflow.configuration import conf
from airflow.operators.python import PythonOperator
from airflow.hooks.base_hook import BaseHook

from automated_reporting import connections
from automated_reporting.databases import schemas
from automated_reporting.utilities import helpers
from infra import connections as infra_connections

# Tasks
from automated_reporting.tasks.check_db import task as check_db_task
from automated_reporting.tasks.simple_latency import task as odc_latency_task
from automated_reporting.tasks.sns_latency import task as sns_latency_task

log = logging.getLogger("airflow.task")

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt.now() - timedelta(hours=1),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "rep_nrt_simple_latency_dev",
    description="DAG for simple latency metric on nrt products: AWS ODC -> AIRFLOW -> Reporting DB",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval=timedelta(minutes=15),
)

aux_data_path = os.path.join(
    pathlib.Path(conf.get("core", "dags_folder")).parent,
    "dags/automated_reporting/aux_data",
)
rep_conn = helpers.parse_connection(
    BaseHook.get_connection(connections.DB_REP_WRITER_CONN_DEV)
)
odc_conn = helpers.parse_connection(
    BaseHook.get_connection(infra_connections.DB_ODC_READER_CONN)
)

with dag:

    # Tasks
    check_db_kwargs = {
        "expected_schema": schemas.LATENCY_SCHEMA,
        "rep_conn": rep_conn,
    }
    check_db = PythonOperator(
        task_id="check_db_schema",
        python_callable=check_db_task,
        op_kwargs=check_db_kwargs,
    )

    # Product list to extract the metric for, could potentially be part of dag configuration and managed in airflow UI?
    products_list = [
        "s2a_nrt_granule",
        "s2b_nrt_granule",
        "ga_s2_wo_3",
        "ga_ls7e_ard_provisional_3",
        "ga_ls8c_ard_provisional_3",
        "ga_s2am_ard_provisional_3",
        "ga_s2bm_ard_provisional_3",
        "ga_s2_ba_provisional_3",
    ]

    def create_task(product_name):
        """
        Function to generate PythonOperator tasks with id based on `product_name`
        """
        latency_kwargs = {
            "rep_conn": rep_conn,
            "odc_conn": odc_conn,
            "product_name": product_name,
        }
        return PythonOperator(
            task_id="odc-latency_" + product_name,
            python_callable=odc_latency_task,
            op_kwargs=latency_kwargs,
            provide_context=True,
        )

    sns_list = [("S2A_MSIL1C", "esa_s2a_msi_l1c"), ("S2B_MSIL1C", "esa_s2b_msi_l1c")]

    def create_sns_task(pipeline, product_id):
        """
        Function to generate PythonOperator tasks with id based on `product_name`
        and pipeline from SNS table
        """
        latency_kwargs = {
            "rep_conn": rep_conn,
            "product_id": product_id,
            "pipeline": pipeline,
        }
        return PythonOperator(
            task_id="sns-latency_" + product_id,
            python_callable=sns_latency_task,
            op_kwargs=latency_kwargs,
            provide_context=True,
        )

    odc_tasks = [create_task(product_name) for product_name in products_list]
    sns_tasks = [create_sns_task(*args) for args in sns_list]
    check_db >> (odc_tasks + sns_tasks)
