"""
# Expires completeness metric on rapid mapping products

This DAG deletes values for completeness and completeness_missing in
Repoting DB for a list of product_ids. It keeps the latest set of
values and the aoi summary values.
"""
import json
from datetime import datetime as dt, timedelta
from airflow import DAG
from automated_reporting import k8s_secrets, utilities

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt.now() - timedelta(hours=4),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

ENV = "prod"
ETL_IMAGE = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls:v2.13.0"

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
        "ga_ls9c_ard_provisional_3",
        "ga_s2_ba_provisional_3",
        "ga_s2_wo_3",
        "esa_s2a_msi_l1c",
        "esa_s2b_msi_l1c",
    ]

    usgs_inserts_job = [
        "echo DEA Expire Completeness job started: $(date)",
        "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
        "expire-completeness",
    ]
    usgs_inserts = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo DEA Expire Completeness job started: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "expire-completeness",
        ],
        task_id="expire-completeness",
        env_vars={"PRODUCT_IDS": json.dumps(products_list)},
        secrets=k8s_secrets.db_secrets(ENV),
    )
