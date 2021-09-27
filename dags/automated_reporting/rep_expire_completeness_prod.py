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
from airflow.operators.python import PythonOperator
from airflow.hooks.base_hook import BaseHook

from automated_reporting import connections
from automated_reporting.utilities import helpers
from automated_reporting.databases import schemas

# Tasks
from automated_reporting.tasks.check_db import task as check_db_task
from automated_reporting.tasks.expire_completeness import (
    task as expire_completeness_task,
)

log = logging.getLogger("airflow.task")

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt(2021, 7, 12, tzinfo=timezone.utc),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "rep_expire_completeness_prod",
    description="Expire redundent completeness metrics in live reporting DB",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval="10 */2 * * *",  # try and avoid completeness generation
)

rep_conn = helpers.parse_connection(
    BaseHook.get_connection(connections.DB_REP_WRITER_CONN_PROD)
)

with dag:

    check_db_kwargs = {
        "expected_schema": schemas.COMPLETENESS_SCHEMA,
        "rep_conn": rep_conn,
    }
    check_db = PythonOperator(
        task_id="check_db_schema",
        python_callable=check_db_task,
        op_kwargs=check_db_kwargs,
    )

    products_list = [
        "ga_s2a_msi_ard_c3",
        "ga_s2b_msi_ard_c3",
        "usgs_ls8c_level1_nrt_c2",
        "usgs_ls7e_level1_nrt_c2",
        "ga_s2am_ard_provisional_3",
        "ga_s2bm_ard_provisional_3",
        "ga_ls7e_ard_provisional_3",
        "ga_ls8c_ard_provisional_3",
        "ga_s2_ba_provisional_3",
        "ga_s2_wo_3",
    ]

    def create_task(product_id):
        """
        Function to generate PythonOperator tasks with id based on `product_id`
        """
        expire_completeness_kwargs = {
            "rep_conn": rep_conn,
            "product_id": product_id,
        }
        return PythonOperator(
            task_id="expire_completeness_" + product_id,
            python_callable=expire_completeness_task,
            op_kwargs=expire_completeness_kwargs,
            provide_context=True,
        )

    check_db >> [create_task(product_id) for product_id in products_list]
