"""
# refresh Explorer Utility Tool (Self Serve)

This is utility is to provide administrators the easy accessiblity to run ad-hoc --refresh-stats

## Note
All list of utility dags here: https://github.com/GeoscienceAustralia/dea-airflow/tree/develop/dags/utility, see Readme

## Customisation
The DAG can be parameterized with run time configuration `products`

To run with all, set `dag_run.conf.products` to `--all`
otherwise provide products to be refreshed seperated by space, i.e. `s2a_nrt_granule s2b_nrt_granule`
dag_run.conf format:

### Sample configuration in json format

    {
        "products": "--all"
    }

    or

    {
        "products": "s2a_nrt_granule s2b_nrt_granule"
    }

## Advanced usage
If there are datasets manually deleted, dag run can take a flag

    {
        "products": "product_a product_b",
        "forcerefresh": "True"
    }

"""

from airflow import DAG
from datetime import datetime, timedelta
from airflow.operators.python_operator import BranchPythonOperator
from dea_utils.update_explorer_summaries import (
    explorer_refresh_operator,
    explorer_forcerefresh_operator,
)
from infra.variables import (
    DB_DATABASE,
    DB_HOSTNAME,
    AWS_DEFAULT_REGION,
)

DAG_NAME = "utility_explorer-refresh-stats"

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


def check_dagrun_config(forcerefresh, **kwargs):
    """
    determine task needed to perform
    """
    if forcerefresh:
        return EXPLORER_SUMMARY_FORCE_REFRESH_TASK_ID
    else:
        return EXPLORER_SUMMARY_REFRESH_STATS_TASK_ID


# THE DAG
dag = DAG(
    dag_id=DAG_NAME,
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,
    catchup=False,
    tags=["k8s", "explorer", "self-service"],
)

CHECK_DAGRUN_CONFIG = "check_dagrun_config"

EXPLORER_SUMMARY_FORCE_REFRESH_TASK_ID = "explorer-force-refresh-summary-task"
EXPLORER_SUMMARY_REFRESH_STATS_TASK_ID = "explorer-summary-task"

with dag:

    EXPLORER_CMD_DECIDER = BranchPythonOperator(
        task_id=CHECK_DAGRUN_CONFIG,
        python_callable=check_dagrun_config,
        op_args=[
            "{{ dag_run.conf.forcerefresh }}",
        ],
    )

    EXPLORER_SUMMARY_REFRESH_STATS = explorer_refresh_operator(
        "{{ dag_run.conf.products }}"
    )
    EXPLORER_SUMMARY_FORCE_REFRESH = explorer_forcerefresh_operator(
        "{{ dag_run.conf.products }}",
    )
