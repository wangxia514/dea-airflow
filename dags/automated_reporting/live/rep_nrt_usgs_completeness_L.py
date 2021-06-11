"""
# Calculate completeness metric on nrt products: AWS ODC -> AIRFLOW -> Reporting DB

This DAG
 * Connects to USGS Stac API to determine USGS Inventory
 * Inserts data into reporting DB
 * Gets 30 day archive from DB for GA and USGS archives
 * Runs completeness and latency checks
 * Inserts summary completeness and latency reporting data
 * Inserts completeness data for each wrs path row
"""

from datetime import datetime, timedelta, timezone

from airflow import DAG
from airflow.operators.python_operator import PythonOperator

import infra.connections as connections
from automated_reporting.databases import schemas
from automated_reporting.tasks import usgs_completeness_task, check_db_task

default_args = {
    "owner": "James Miller",
    "depends_on_past": False,
    "start_date": datetime(2021, 5, 27, tzinfo=timezone.utc),
    "email": ["james.miller@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": True,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "rep_usgs_completeness_nrt_l1_L",
    description="DAG for completeness and latency metric on USGS L1 C2 nrt product  in live reporting DB",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval=timedelta(minutes=15),
)

with dag:
    # Task callable
    schema = schemas.USGS_COMPLETENESS_SCHEMA

    check_db_kwargs = {
        "expected_schema": schema,
        "connection_id": connections.DB_REP_WRITER_CONN_L,
    }
    check_db = PythonOperator(
        task_id="check_db_schema",
        python_callable=check_db_task,
        op_kwargs=check_db_kwargs,
    )

    completeness_kwargs = {"connection_id": connections.DB_REP_WRITER_CONN_L}
    usgs_completeness = PythonOperator(
        task_id="usgs_completeness",
        python_callable=usgs_completeness_task,
        provide_context=True,
        op_kwargs=completeness_kwargs,
    )

    check_db >> usgs_completeness
