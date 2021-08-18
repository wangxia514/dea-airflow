"""
# Run tasks to monitor USGS NRT Products

This DAG
 * Connects to USGS M2M API to determine USGS Inventory
 * Inserts data into reporting DB, in both hg and landsat schemas
 * Runs completeness and latency checks
 * Inserts summary completeness and latency reporting data
 * Inserts completeness data for each wrs path row
"""
import os
import pathlib
from datetime import datetime as dt, timedelta, timezone

from airflow import DAG
from airflow.configuration import conf
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from airflow.hooks.base_hook import BaseHook

from automated_reporting.variables import M2M_API_REP_CREDS
from automated_reporting import connections
from automated_reporting.databases import schemas
from automated_reporting.utilities import helpers

# Tasks
from automated_reporting.tasks.check_db import task as check_db_task
from automated_reporting.tasks.usgs_completeness import task as usgs_completeness_task
from automated_reporting.tasks.latency_from_completeness import (
    task as latency_from_completeness_task,
)
from automated_reporting.tasks.usgs_aquisitions import task as usgs_acquisitions_task
from automated_reporting.tasks.usgs_insert_hg_l0 import task as usgs_insert_hg_l0_task

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt(2021, 8, 17, 0, 0, 5, tzinfo=timezone.utc),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "rep_usgs_monitoring_dev",
    description="DAG for completeness and latency metric on USGS L1 C2 nrt product",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval=timedelta(minutes=15),
    concurrency=1,
)

aux_data_path = os.path.join(
    pathlib.Path(conf.get("core", "dags_folder")).parent,
    "dags/automated_reporting/aux_data",
)
product_ids = ["landsat_etm_c2_l1", "landsat_ot_c2_l1"]
m2m_credentials = Variable.get(M2M_API_REP_CREDS, deserialize_json=True)
rep_conn = helpers.parse_connection(
    BaseHook.get_connection(connections.DB_REP_WRITER_CONN_DEV)
)


def usgs_insert_hg_l0_xcom(task_instance, **kwargs):
    """
    A wrapper to use Xcom in a task without adding an Airflow dependcy in the task itself
    """
    kwargs["acquisitions"] = task_instance.xcom_pull(task_ids="usgs_acquisitions")
    return usgs_insert_hg_l0_task(**kwargs)


with dag:

    # Acquisitions from M2M Api
    acquisitions_kwargs = {
        "product_ids": product_ids,
        "m2m_credentials": m2m_credentials,
        "aux_data_path": aux_data_path,
    }
    usgs_acquisitions = PythonOperator(
        task_id="usgs_acquisitions",
        python_callable=usgs_acquisitions_task,
        provide_context=True,
        op_kwargs=acquisitions_kwargs,
    )

    # Completeness and Latency Metrics
    check_db_kwargs_completeness = {
        "expected_schema": schemas.USGS_COMPLETENESS_SCHEMA,
        "rep_conn": rep_conn,
    }
    check_db_completeness = PythonOperator(
        task_id="check_db_schema_completeness",
        python_callable=check_db_task,
        op_kwargs=check_db_kwargs_completeness,
    )

    completeness_kwargs = {"rep_conn": rep_conn, "aux_data_path": aux_data_path}
    usgs_completeness = PythonOperator(
        task_id="usgs_completeness",
        python_callable=usgs_completeness_task,
        provide_context=True,
        op_kwargs=completeness_kwargs,
    )

    check_db_kwargs_latency = {
        "expected_schema": schemas.LATENCY_SCHEMA,
        "rep_conn": rep_conn,
    }
    check_db_latency = PythonOperator(
        task_id="check_db_schema_latency",
        python_callable=check_db_task,
        op_kwargs=check_db_kwargs_latency,
    )

    latency_kwargs = {"rep_conn": rep_conn}
    usgs_latency = PythonOperator(
        task_id="latency",
        python_callable=latency_from_completeness_task,
        provide_context=True,
        op_kwargs=completeness_kwargs,
    )

    # High Granularity Flow
    check_db_kwargs_hg = {
        "expected_schema": schemas.HIGH_GRANULARITY_SCHEMA,
        "connection_id": connections.DB_REP_WRITER_CONN_DEV,
    }
    check_db_hg = PythonOperator(
        task_id="check_db_schema_hg",
        python_callable=check_db_task,
        op_kwargs=check_db_kwargs_completeness,
    )

    completeness_kwargs = {"rep_conn": rep_conn}
    usgs_insert_hg_l0 = PythonOperator(
        task_id="usgs_insert_hg_l0",
        python_callable=usgs_insert_hg_l0_xcom,
        provide_context=True,
        op_kwargs=completeness_kwargs,
    )

    (
        usgs_acquisitions
        >> check_db_completeness
        >> usgs_completeness
        >> check_db_latency
        >> usgs_latency
    )
    usgs_acquisitions >> check_db_hg >> usgs_insert_hg_l0
