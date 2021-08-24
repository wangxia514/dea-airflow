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
from airflow.hooks.postgres_hook import PostgresHook
from airflow.operators.python_operator import PythonBranchOperator
from airflow.operators.dummy_operator import DummyOperator

from infra.connections import DB_EXPLORER_READ_CONN
from qa.qa_sql_query import explorer_ds_count_compare
from webapp_update.update_list import EXPLORER_UPDATE_LIST

from dea_utils.update_explorer_summaries import (
    explorer_refresh_operator,
)
from infra.variables import (
    DB_DATABASE,
    DB_HOSTNAME,
    AWS_DEFAULT_REGION,
)

DAG_NAME = "qa_explorer_ds_count"

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
    schedule_interval="0 */1 * * *",  # hourly
    catchup=False,
    tags=["k8s", "explorer", "qa"],
)

CHECK_DAGRUN_CONFIG = "check_dagrun_config"


def qa_ds_count():
    """
    return sql query result
    """
    pg_hook = PostgresHook(postgres_conn_id=DB_EXPLORER_READ_CONN)
    connection = pg_hook.get_conn()
    cursor = connection.cursor()
    cursor.execute(explorer_ds_count_compare)
    rows = cursor.fetchall()
    for row in rows:
        print(
            f"Product: {row[2]} - Diff {row[3]} - agdc dataset count {row[0]} - explorer dataset count {row[1]}"
        )
    if len(rows) > 0:
        return "explorer-summary-task"
    else:
        return "dummy_option"


with dag:

    qa_assessor = PythonBranchOperator(
        task_id="return_ds_count",
        python_callable=qa_ds_count,
    )

    explorer_update = explorer_refresh_operator(products=EXPLORER_UPDATE_LIST)

    dummy3 = DummyOperator(
        task_id="dummy_option",
    )

    qa_assessor >> [explorer_update, dummy3]
