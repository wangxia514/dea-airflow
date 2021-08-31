"""
# refresh Explorer Utility Tool (QA)

This is utility is to provide administrators the easy accessiblity to run ad-hoc --refresh-stats

## Note
All list of utility dags here: https://github.com/GeoscienceAustralia/dea-airflow/tree/develop/dags/utility, see Readme

## Customisation
The DAG can be parameterized with run time configuration `products`

To run with all, set `dag_run.conf.products` to `--all`
otherwise provide products to be refreshed seperated by space, i.e. `s2a_nrt_granule s2b_nrt_granule`
dag_run.conf format:

"""

from airflow import DAG
import csv
import pandas as pd
import glob, os

from datetime import datetime, timedelta
from airflow.operators.python_operator import PythonOperator

from infra.variables import (
    DB_DATABASE,
    DB_HOSTNAME,
    AWS_DEFAULT_REGION,
)

DAG_NAME = "qa_explorer_product_ds_count"

# DAG CONFIGURATION
DEFAULT_ARGS = {
    "owner": "Pin Jin",
    "depends_on_past": False,
    "start_date": datetime(2020, 6, 14),
    "email": ["pin.jin@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "env_vars": {
        # TODO: Pass these via templated params in DAG Run
        "DB_HOSTNAME": DB_HOSTNAME,
        "DB_DATABASE": DB_DATABASE,
        "AWS_DEFAULT_REGION": AWS_DEFAULT_REGION,
    },
}

# THE DAG
dag = DAG(
    dag_id=DAG_NAME,
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,  # Manual
    catchup=False,
    tags=["qa", "index-check"],
)

def compare_dsreport_csv():
    """
    fetch dsreport csv from explorer endpoints
    """
    path = os.path.dirname(os.path.abspath(__file__))

    base_csv = pd.read_csv(os.path.join(path, 'sample_dsreport.csv'))
    comparewith_csv = pd.read_csv(os.path.join(path, 'sample_dsreport1.csv'))
    c = pd.merge(base_csv, comparewith_csv, on=['product_name', 'period_type', 'date'])
    for row in range(len(c['product_name'])):
        if c['dataset_count_x'][row] != c['dataset_count_y'][row]:
            print(c.loc[row, :])

with dag:

    PythonOperator(
        task_id="parse_explorer_csv",
        python_callable=compare_dsreport_csv
    )