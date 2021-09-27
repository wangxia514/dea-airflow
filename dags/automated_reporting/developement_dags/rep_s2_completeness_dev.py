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
import os
import pathlib
import logging
from datetime import datetime as dt
from datetime import timedelta, timezone

from airflow import DAG
from airflow.configuration import conf
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from airflow.hooks.base_hook import BaseHook

from automated_reporting import variables
from automated_reporting import connections
from automated_reporting.databases import schemas
from automated_reporting.utilities import helpers
from infra import connections as infra_connections

# Tasks
from automated_reporting.tasks.check_db import task as check_db_task
from automated_reporting.tasks.s2_ard_completeness import (
    task as s2_completeness_ard_task,
)
from automated_reporting.tasks.s2_deriv_completeness import (
    task as s2_completeness_derivative_task,
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

copernicus_api_creds = Variable.get(variables.COP_API_REP_CREDS, deserialize_json=True)


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

    completeness_kwargs = {
        "days": 30,
        "rep_conn": rep_conn,
        "odc_conn": odc_conn,
        "copernicus_api_credentials": copernicus_api_creds,
        "aux_data_path": aux_data_path,
    }

    completeness_kwargs_ard = {
        "s2a": {
            "id": "s2a",
            "odc_code": "s2a_nrt_granule",
            "rep_code": "ga_s2a_msi_ard_c3",
        },
        "s2b": {
            "id": "s2b",
            "odc_code": "s2b_nrt_granule",
            "rep_code": "ga_s2b_msi_ard_c3",
        },
    }
    completeness_kwargs_ard.update(completeness_kwargs)
    compute_sentinel_ard_completeness = PythonOperator(
        task_id="compute_s2_ard_completeness",
        python_callable=s2_completeness_ard_task,
        op_kwargs=completeness_kwargs_ard,
        provide_context=True,
    )

    completeness_kwargs_ard_prov = {
        "s2a": {
            "id": "s2a",
            "odc_code": "ga_s2am_ard_provisional_3",
            "rep_code": "ga_s2am_ard_provisional_3",
        },
        "s2b": {
            "id": "s2b",
            "odc_code": "ga_s2bm_ard_provisional_3",
            "rep_code": "ga_s2bm_ard_provisional_3",
        },
    }
    completeness_kwargs_ard_prov.update(completeness_kwargs)
    compute_sentinel_ard_prov_completeness = PythonOperator(
        task_id="compute_s2_ard_completeness_prov",
        python_callable=s2_completeness_ard_task,
        op_kwargs=completeness_kwargs_ard_prov,
        provide_context=True,
    )

    completeness_kwargs_wo = {
        "upstream": ["s2a_nrt_granule", "s2b_nrt_granule"],
        "target": "ga_s2_wo_3",
    }
    completeness_kwargs_wo.update(completeness_kwargs)
    compute_sentinel_wo_completeness = PythonOperator(
        task_id="compute_sentinel_wo_completeness",
        python_callable=s2_completeness_derivative_task,
        op_kwargs=completeness_kwargs_wo,
        provide_context=True,
    )

    completeness_kwargs_ba = {
        "upstream": ["ga_s2am_ard_provisional_3", "ga_s2bm_ard_provisional_3"],
        "target": "ga_s2_ba_provisional_3",
    }
    completeness_kwargs_ba.update(completeness_kwargs)
    compute_sentinel_ba_completeness = PythonOperator(
        task_id="compute_sentinel_ba_completeness",
        python_callable=s2_completeness_derivative_task,
        op_kwargs=completeness_kwargs_ba,
        provide_context=True,
    )

    check_db >> [
        compute_sentinel_ard_completeness,
        compute_sentinel_ard_prov_completeness,
        compute_sentinel_wo_completeness,
        compute_sentinel_ba_completeness,
    ]
