"""
# Debugging Tool (Admin use)
## Test dag_run conf
During dag_run conf behaviours.

## Life span
May be altered to test advanced logics.

## Customisation
    {
        "a": "",
        "b": "",
        "c": ""
    }
"""

from datetime import timedelta

from airflow import DAG
from airflow.operators.python_operator import PythonOperator, BranchPythonOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.utils.dates import days_ago


DAG_NAME = "testing_dagrun_conf"

# DAG CONFIGURATION
DEFAULT_ARGS = {
    "owner": "Pin Jin",
    "depends_on_past": False,
    "start_date": days_ago(2),
    "email": ["pin.jin@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
    "retry_delay": timedelta(minutes=5),
}


# THE DAG
dag = DAG(
    dag_id=DAG_NAME,
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,
    catchup=False,
    tags=["k8s", "test"],
)


def parse_dagrun_conf(a=False, b=False, c=False, **kwargs):
    """
    parse input
    """
    print("a", a)
    print("b", b)
    print("c", c)
    if a:
        print("a is true")
    return a, b, c


SET_REFRESH_PRODUCT_TASK_NAME = "parse_dagrun_conf"
CHECK_DAGRUN_CONFIG = "check_dagrun_config"

with dag:

    SET_PRODUCTS = PythonOperator(
        task_id=SET_REFRESH_PRODUCT_TASK_NAME,
        python_callable=parse_dagrun_conf,
        op_args=[
            "{{ dag_run.conf.a }}",
            "{{ dag_run.conf.b }}",
            "{{ dag_run.conf.c }}",
        ],
        # provide_context=True,
    )
