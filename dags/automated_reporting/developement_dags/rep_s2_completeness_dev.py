"""
# Completeness metric on CaRSA nrt products: AWS ODC/Sentinel Catalog -> AIRFLOW -> Reporting DB

This DAG extracts latest timestamp values for a list of products in AWS ODC. It:
 * Checks relavent table and columns are present in reporting DB.
 * Downloads latest product list from Sentinel API (Copernicus).
 * Downloads a list of tiles in AOI from S3.
 * Connects to AWS ODC and downloads products list.
 * Iterates through tile list and computes completeness for each.
 * Inserts results into reporting DB.

"""
import logging
from datetime import datetime as dt
from datetime import timedelta, timezone

from airflow import DAG
from airflow.operators.python_operator import PythonOperator

from automated_reporting import connections
from automated_reporting.databases import schemas
from automated_reporting.tasks import (
    s2_completeness_ard_task,
    s2_completeness_wo_task,
    check_db_task,
)

log = logging.getLogger("airflow.task")

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt(2021, 7, 5, tzinfo=timezone.utc),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "rep_s2_completeness_dev",
    description="Completeness metric on Sentinel nrt products: AWS ODC/Sentinel Catalog \
        -> AIRFLOW -> Reporting DB",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval=timedelta(minutes=15),
)

with dag:

    check_db_kwargs = {
        "expected_schema": schemas.COMPLETENESS_SCHEMA,
        "connection_id": connections.DB_REP_WRITER_CONN_DEV,
    }
    check_db = PythonOperator(
        task_id="check_db_schema",
        python_callable=check_db_task,
        op_kwargs=check_db_kwargs,
    )

    completeness_kwargs = {
        "days": 30,
        "connection_id": connections.DB_REP_WRITER_CONN_DEV,
    }
    compute_sentinel_ard_completeness = PythonOperator(
        task_id="compute_sentinel_ard_completeness",
        python_callable=s2_completeness_ard_task,
        op_kwargs=completeness_kwargs,
        provide_context=True,
    )

    compute_sentinel_wo_completeness = PythonOperator(
        task_id="compute_sentinel_wo_completeness",
        python_callable=s2_completeness_wo_task,
        op_kwargs=completeness_kwargs,
        provide_context=True,
    )

    check_db >> [compute_sentinel_ard_completeness, compute_sentinel_wo_completeness]
