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
from infra import connections as infra_connections

# Tasks
from automated_reporting.tasks.check_db import task as check_db_task
from automated_reporting.tasks.usgs_l1_completeness import (
    task as usgs_l1_completeness_task,
)
from automated_reporting.tasks.usgs_ard_completeness import (
    task as usgs_ard_completeness_task,
)
from automated_reporting.tasks.latency_from_completeness import (
    task as latency_from_completeness_task,
)
from automated_reporting.tasks.usgs_aquisitions import task as usgs_acquisitions_task
from automated_reporting.tasks.usgs_insert_hg_l0 import task as usgs_insert_hg_l0_task
from automated_reporting.tasks.usgs_insert_acqs import task as usgs_insert_acqs_task

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt(2021, 8, 16, tzinfo=timezone.utc),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "rep_usgs_monitoring_prod",
    description="DAG for completeness and latency metric on USGS L1 C2 nrt product",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval=timedelta(minutes=15),
)

aux_data_path = os.path.join(
    pathlib.Path(conf.get("core", "dags_folder")).parent,
    "dags/automated_reporting/aux_data",
)
product_ids = ["landsat_etm_c2_l1", "landsat_ot_c2_l1"]
m2m_credentials = Variable.get(M2M_API_REP_CREDS, deserialize_json=True)
rep_conn = helpers.parse_connection(
    BaseHook.get_connection(connections.DB_REP_WRITER_CONN_PROD)
)
odc_conn = helpers.parse_connection(
    BaseHook.get_connection(infra_connections.DB_ODC_READER_CONN)
)


def usgs_insert_hg_l0_xcom(task_instance, **kwargs):
    """
    A wrapper to use Xcom in a task without adding an Airflow dependcy in the task itself
    """
    kwargs["acquisitions"] = task_instance.xcom_pull(task_ids="usgs_acquisitions")
    return usgs_insert_hg_l0_task(**kwargs)


def usgs_insert_acqs_xcom(task_instance, **kwargs):
    """
    A wrapper to use Xcom in a task without adding an Airflow dependcy in the task itself
    """
    kwargs["acquisitions"] = task_instance.xcom_pull(task_ids="usgs_acquisitions")
    return usgs_insert_acqs_task(**kwargs)


def insert_ls8_l1_latency_xcom(task_instance, **kwargs):
    """
    A wrapper to use Xcom in a task without adding an Airflow dependcy in the task itself
    """
    kwargs["completeness_summary"] = task_instance.xcom_pull(
        task_ids="usgs_l1_completeness_ls8"
    )
    return latency_from_completeness_task(**kwargs)


def insert_ls7_l1_latency_xcom(task_instance, **kwargs):
    """
    A wrapper to use Xcom in a task without adding an Airflow dependcy in the task itself
    """
    kwargs["completeness_summary"] = task_instance.xcom_pull(
        task_ids="usgs_l1_completeness_ls7"
    )
    return latency_from_completeness_task(**kwargs)


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
        op_kwargs=acquisitions_kwargs,
        task_concurrency=1,
    )

    # Insert Aquisitions to Reporting DB
    check_db_kwargs_acquisitions = {
        "expected_schema": schemas.USGS_ACQUISITIONS_SCHEMA,
        "rep_conn": rep_conn,
    }
    check_db_schema_acquisitions = PythonOperator(
        task_id="check_db_schema_acquisitions",
        python_callable=check_db_task,
        op_kwargs=check_db_kwargs_acquisitions,
    )

    insert_acqs_kwargs = {"rep_conn": rep_conn}
    usgs_insert_acqs = PythonOperator(
        task_id="usgs_insert_acqs",
        python_callable=usgs_insert_acqs_xcom,
        op_kwargs=insert_acqs_kwargs,
    )

    # Calculate USGS Completeness Metrics
    check_db_kwargs_completeness = {
        "expected_schema": schemas.USGS_COMPLETENESS_SCHEMA,
        "rep_conn": rep_conn,
    }
    check_db_completeness = PythonOperator(
        task_id="check_db_schema_completeness",
        python_callable=check_db_task,
        op_kwargs=check_db_kwargs_completeness,
    )

    # L1 Completeness

    completeness_kwargs = {
        "rep_conn": rep_conn,
        "aux_data_path": aux_data_path,
        "days": 30,
        "odc_conn": odc_conn,
    }

    # LS8
    usgs_l1_completness_ls8_kwargs = {
        "product": {
            "s3_code": "L8C2",
            "acq_code": "LC8%",
            "rep_code": "usgs_ls8c_level1_nrt_c2",
        }
    }
    usgs_l1_completness_ls8_kwargs.update(completeness_kwargs)
    usgs_l1_completeness_ls8 = PythonOperator(
        task_id="usgs_l1_completeness_ls8",
        python_callable=usgs_l1_completeness_task,
        op_kwargs=usgs_l1_completness_ls8_kwargs,
    )

    # LS7
    usgs_l1_completness_ls7_kwargs = {
        "product": {
            "s3_code": "L7C2",
            "acq_code": "LE7%",
            "rep_code": "usgs_ls7e_level1_nrt_c2",
        }
    }
    usgs_l1_completness_ls7_kwargs.update(completeness_kwargs)
    usgs_l1_completeness_ls7 = PythonOperator(
        task_id="usgs_l1_completeness_ls7",
        python_callable=usgs_l1_completeness_task,
        op_kwargs=usgs_l1_completness_ls7_kwargs,
    )

    # ARD Completeness

    # LS8
    usgs_ard_completness_ls8_kwargs = {
        "product": {"odc_code": "ga_ls8c_ard_provisional_3", "acq_code": "LC8%"}
    }
    usgs_ard_completness_ls8_kwargs.update(completeness_kwargs)
    usgs_ard_completeness_ls8 = PythonOperator(
        task_id="usgs_ard_completeness_ls8",
        python_callable=usgs_ard_completeness_task,
        op_kwargs=usgs_ard_completness_ls8_kwargs,
    )

    # LS7
    usgs_ard_completness_ls7_kwargs = {
        "product": {"odc_code": "ga_ls7e_ard_provisional_3", "acq_code": "LE7%"}
    }
    usgs_ard_completness_ls7_kwargs.update(completeness_kwargs)
    usgs_ard_completeness_ls7 = PythonOperator(
        task_id="usgs_ard_completeness_ls7",
        python_callable=usgs_ard_completeness_task,
        op_kwargs=usgs_ard_completness_ls7_kwargs,
    )

    # Latency from Completeness

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
    usgs_ls8_l1_latency = PythonOperator(
        task_id="usgs_ls8_l1_latency",
        python_callable=insert_ls8_l1_latency_xcom,
        op_kwargs=latency_kwargs,
    )

    latency_kwargs = {"rep_conn": rep_conn}
    usgs_ls7_l1_latency = PythonOperator(
        task_id="usgs_ls7_l1_latency",
        python_callable=insert_ls7_l1_latency_xcom,
        op_kwargs=latency_kwargs,
    )

    # High Granularity Flow
    check_db_kwargs_hg = {
        "expected_schema": schemas.HIGH_GRANULARITY_SCHEMA,
        "rep_conn": rep_conn,
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
        op_kwargs=completeness_kwargs,
    )

    (
        usgs_acquisitions
        >> check_db_schema_acquisitions
        >> usgs_insert_acqs
        >> check_db_completeness
    )
    check_db_completeness >> check_db_latency
    check_db_latency >> usgs_l1_completeness_ls8 >> usgs_ls8_l1_latency
    check_db_latency >> usgs_l1_completeness_ls7 >> usgs_ls7_l1_latency
    check_db_completeness >> usgs_ard_completeness_ls8
    check_db_completeness >> usgs_ard_completeness_ls7
    usgs_acquisitions >> check_db_hg >> usgs_insert_hg_l0
