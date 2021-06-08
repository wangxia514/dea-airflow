"""
# Expires completeness metric on CaRSA nrt products

This DAG deletes values for completeness and completeness_missing in
Repoting DB for a list of product_ids. It keeps the latest set of
values and the aoi summary values.
"""

import logging
from datetime import datetime as dt
from datetime import timedelta, timezone

from airflow import DAG
from airflow.operators.python_operator import PythonOperator

from infra.connections import DB_REP_WRITER_CONN

from automated_reporting.databases import schemas, reporting_db

log = logging.getLogger("airflow.task")

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt(2021, 6, 7, tzinfo=timezone.utc),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "rep_expire_completeness",
    description="Expire redundent completeness metrics",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval="10 */2 * * *",  # try and avoid completeness generation
)

with dag:

    # Task callable
    def expire_completeness(product_id, **kwargs):
        """
        Task to redundent completeness metrics
        """
        log.info("Expiring completeness for product id: {}".format(product_id))

        removed_count = reporting_db.expire_completeness(product_id)

        log.info("Cleaned: {}".format(removed_count))

        return None

    ## Tasks
    check_db = PythonOperator(
        task_id="check_db_schema",
        python_callable=schemas.check_db_schema,
        op_kwargs={
            "expected_schema": schemas.COMPLETENESS_SCHEMA,
            "connection_id": DB_REP_WRITER_CONN,
        },
    )

    products_list = [
        "ga_s2a_msi_ard_c3",
        "ga_s2b_msi_ard_c3",
        "usgs_ls8c_level1_nrt_c2",
    ]

    def create_task(product_id):
        """
        Function to generate PythonOperator tasks with id based on `product_id`
        """
        return PythonOperator(
            task_id="expire_completeness_" + product_id,
            python_callable=expire_completeness,
            op_kwargs={"product_id": product_id},
            provide_context=True,
        )

    check_db >> [create_task(product_id) for product_id in products_list]
