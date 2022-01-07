"""
# Simple latency metric on C3 products: AWS ODC -> AIRFLOW -> Reporting DB

This DAG extracts latest timestamp values for a list of products in AWS ODC. It:
 * Connects to AWS ODC.
 * Runs multiple tasks (1 per product type) querying the latest timestamps for each from AWS ODC.
 * Inserts a summary of latest timestamps into the landsat.derivative_latency table in reporting DB.

"""

import logging
from datetime import datetime as dt
from datetime import timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.hooks.base_hook import BaseHook
import pendulum

from automated_reporting import connections
from automated_reporting.databases import schemas
from automated_reporting.utilities import helpers
from infra import connections as infra_connections

# Tasks
from automated_reporting.tasks.check_db import task as check_db_task
from automated_reporting.tasks.simple_latency import task as odc_latency_task

log = logging.getLogger("airflow.task")

utc_tz = pendulum.timezone("UTC")

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt(2021, 12, 31, 22, 0, 0, tzinfo=utc_tz),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "rep_c3_simple_latency_prod",
    description="DAG for simple latency metric on nrt products: AWS ODC -> AIRFLOW -> Live Reporting DB",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval=timedelta(days=1),
)

rep_conn = helpers.parse_connection(
    BaseHook.get_connection(connections.DB_REP_WRITER_CONN_PROD)
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
        # Baseline
        "ga_ls5t_ard_3",  # static product, no longer generated
        "ga_ls7e_ard_3",
        "ga_ls8c_ard_3",
        # Derivavtives
        "ga_ls_wo_3",
        "ga_ls_fc_3",
    ]

    def create_task(product_name):
        """
        Function to generate PythonOperator tasks with id based on `product_name`
        """
        latency_kwargs = {
            "rep_conn": rep_conn,
            "odc_conn": odc_conn,
            "product_name": product_name,
            "product_suffix": "aws",
            "days": 90,
        }
        return PythonOperator(
            task_id="odc-latency_" + product_name,
            python_callable=odc_latency_task,
            op_kwargs=latency_kwargs,
        )

    odc_tasks = [create_task(product_name) for product_name in products_list]
    check_db >> odc_tasks
