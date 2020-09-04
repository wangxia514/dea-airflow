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

from airflow import DAG
from datetime import datetime, timedelta
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator


from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.kubernetes.secret import Secret
from airflow.operators.subdag_operator import SubDagOperator
from sentinel_2_nrt.subdag_ows_views import ows_update_extent_subdag

from env_var.infra import DB_DATABASE, DB_HOSTNAME, SECRET_OWS_NAME, SECRET_AWS_NAME
from sentinel_2_nrt.env_cfg import (
    UPDATE_EXTENT_PRODUCTS,
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
    },
    # Lift secrets into environment variables
    "secrets": [
        Secret("env", "DB_USERNAME", SECRET_OWS_NAME, "postgres-username"),
        Secret("env", "DB_PASSWORD", SECRET_OWS_NAME, "postgres-password"),
        Secret("env", "AWS_DEFAULT_REGION", SECRET_AWS_NAME, "AWS_DEFAULT_REGION"),
    ],
}


# THE DAG
dag = DAG(
    dag_id=DAG_NAME,
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,
    catchup=False,
    tags=["k8s", "ows"],
)


def parse_dagrun_conf(products, **kwargs):
    if products:
        return products
    else:
        return UPDATE_EXTENT_PRODUCTS


SET_REFRESH_PRODUCT_TASK_NAME = "parse_dagrun_conf"

with dag:

    SET_PRODUCTS = PythonOperator(
        task_id=SET_REFRESH_PRODUCT_TASK_NAME,
        python_callable=parse_dagrun_conf,
        op_args=["{{ dag_run.conf.products }}"],
        # provide_context=True,
    )
    OWS_UPDATE_EXTENTS = SubDagOperator(
        task_id="run-ows-update-ranges",
        subdag=ows_update_extent_subdag(
            DAG_NAME, "run-ows-update-ranges", DEFAULT_ARGS
        ),
    )

    START = DummyOperator(task_id="start_ows_update_ranges")

    COMPLETE = DummyOperator(task_id="all_done")

    START >> SET_PRODUCTS
    SET_PRODUCTS >> OWS_UPDATE_EXTENTS
    OWS_UPDATE_EXTENTS >> COMPLETE
