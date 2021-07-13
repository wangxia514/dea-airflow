"""
## Utility Tool
### ows update ranges
This is utility is to provide administrators the easy accessiblity to run ad-hoc --views and update-ranges

#### default run
    `datacube-ows-update --views`
    `datacube-ows-update s2_nrt_granule_nbar_t`

#### Utility customisation
The DAG can be parameterized with run time configuration `products`

To run with all, set `dag_run.conf.products` to `--all`
otherwise provide products to be refreshed seperated by space, i.e. `s2a_nrt_granule s2b_nrt_granule`
dag_run.conf format:

#### example conf in json format
    "products": "--all"
    "products": "s2a_nrt_granule s2b_nrt_granule"
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python_operator import PythonOperator

from infra.variables import (
    DB_DATABASE,
    DB_HOSTNAME,
    AWS_DEFAULT_REGION,
)
from dea_utils.update_ows_products import ows_update_operator
from webapp_update.update_list import (
    OWS_UPDATE_LIST,
)

DAG_NAME = "utility_ows-update-extent"

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


def parse_dagrun_conf(products, **kwargs):
    """Extract the list of products from the DAGRun Configuration"""
    if products:
        return products
    else:
        return " ".join(OWS_UPDATE_LIST)


SET_REFRESH_PRODUCT_TASK_NAME = "parse_dagrun_conf"

with DAG(
    dag_id=DAG_NAME,
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,
    catchup=False,
    tags=["k8s", "ows"],
) as dag:
    SET_PRODUCTS = PythonOperator(
        task_id=SET_REFRESH_PRODUCT_TASK_NAME,
        python_callable=parse_dagrun_conf,
        op_args=["{{ dag_run.conf.products }}"],
        # provide_context=True,
    )

    OWS_UPDATE_EXTENTS = ows_update_operator(
        xcom_task_id=SET_REFRESH_PRODUCT_TASK_NAME,
        dag=dag,
    )

    SET_PRODUCTS >> OWS_UPDATE_EXTENTS
