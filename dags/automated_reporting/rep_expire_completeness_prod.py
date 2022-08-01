"""
# Expires completeness metric on rapid mapping products

This DAG deletes values for completeness and completeness_missing in
Repoting DB for a list of product_ids. It keeps the latest set of
values and the aoi summary values.
"""
import json
from datetime import datetime as dt, timedelta

from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from infra.variables import REPORTING_DB_SECRET

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt.now() - timedelta(hours=4),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "secrets": [
        Secret("env", "DB_HOST", REPORTING_DB_SECRET, "DB_HOST"),
        Secret("env", "DB_NAME", REPORTING_DB_SECRET, "DB_NAME"),
        Secret("env", "DB_PORT", REPORTING_DB_SECRET, "DB_PORT"),
        Secret("env", "DB_USER", REPORTING_DB_SECRET, "DB_USER"),
        Secret("env", "DB_PASSWORD", REPORTING_DB_SECRET, "DB_PASSWORD"),
    ],
}

ETL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls:v2.4.4"
)

dag = DAG(
    "rep_expire_completeness_prod",
    description="Expire redundent completeness metrics",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval="10 */2 * * *",  # try and avoid completeness generation
)

with dag:

    products_list = [
        "s2a_nrt_granule",
        "s2b_nrt_granule",
        "usgs_ls8c_level1_nrt_c2",
        "usgs_ls7e_level1_nrt_c2",
        "ga_s2am_ard_provisional_3",
        "ga_s2bm_ard_provisional_3",
        "ga_ls7e_ard_provisional_3",
        "ga_ls8c_ard_provisional_3",
        "ga_s2_ba_provisional_3",
        "ga_s2_wo_3",
        "esa_s2a_msi_l1c",
        "esa_s2b_msi_l1c",
    ]

    usgs_inserts_job = [
        "echo DEA Expire Completeness job started: $(date)",
        "expire-completeness",
    ]
    usgs_inserts = KubernetesPodOperator(
        namespace="processing",
        image=ETL_IMAGE,
        arguments=["bash", "-c", " &&\n".join(usgs_inserts_job)],
        name="expire-completeness",
        image_pull_policy="IfNotPresent",
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="expire-completeness",
        get_logs=True,
        env_vars={"PRODUCT_IDS": json.dumps(products_list)},
    )
