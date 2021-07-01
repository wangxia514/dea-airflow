"""
# Simple latency metric on nrt products: AWS ODC -> AIRFLOW -> Reporting DB

This DAG extracts latest timestamp values for a list of products in AWS ODC. It:
 * Connects to AWS ODC.
 * Runs multiple tasks (1 per product type) querying the latest timestamps for each from AWS ODC.
 * Inserts a summary of latest timestamps into the landsat.derivative_latency table in reporting DB.

"""

import logging
from datetime import datetime as dt
from datetime import timedelta, timezone

from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

import infra.connections as connections

log = logging.getLogger("airflow.task")

from automated_reporting.databases import schemas
from automated_reporting.tasks import check_db_task, simple_latency_task


default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt(2021, 5, 1, tzinfo=timezone.utc),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "rep_nrt_simple_latency",
    description="DAG for simple latency metric on nrt products: AWS ODC -> AIRFLOW -> Reporting DB",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval=timedelta(minutes=15),
)

with dag:

    ## Tasks
    check_db_kwargs = {
        "expected_schema": schemas.LATENCY_SCHEMA,
        "connection_id": connections.DB_REP_WRITER_CONN,
    }
    check_db = PythonOperator(
        task_id="check_db_schema",
        python_callable=check_db_task,
        op_kwargs=check_db_kwargs,
    )

    # Product list to extract the metric for, could potentially be part of dag configuration and managed in airflow UI?
    products_list = ["s2a_nrt_granule", "s2b_nrt_granule", "ga_s2_wo_3"]

    def create_task(product_name):
        """
        Function to generate PythonOperator tasks with id based on `product_name`
        """
        latency_kwargs = {
            "connection_id": connections.DB_REP_WRITER_CONN,
            "product_name": product_name,
        }
        return PythonOperator(
            task_id="nrt-simple-latency_" + product_name,
            python_callable=simple_latency_task,
            op_kwargs=latency_kwargs,
            provide_context=True,
        )

    check_db >> [create_task(product_name) for product_name in products_list]
