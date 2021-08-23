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
from datetime import datetime, timedelta
from airflow.operators.sql import SQLCheckOperator
from infra.connections import DB_ODC_READER_CONN

# from dea_utils.update_explorer_summaries import (
#     explorer_forcerefresh_operator,
# )
from infra.variables import (
    DB_DATABASE,
    DB_HOSTNAME,
    AWS_DEFAULT_REGION,
)

DAG_NAME = "qa-explorer-ds-count"

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
    schedule_interval=None,
    catchup=False,
    tags=["k8s", "explorer", "qa"],
)

CHECK_DAGRUN_CONFIG = "check_dagrun_config"


with dag:

    SQLCheckOperator(
        task_id="explorer_dataset_count_qa_assessor",
        conn_id=DB_ODC_READER_CONN,
        sql="explorer_ds_count_qa.sql",
    )

    # EXPLORER_SUMMARY_FORCE_REFRESH = explorer_forcerefresh_operator(
    #     "{{ dag_run.conf.products }}",
    # )
