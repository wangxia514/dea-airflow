"""
# Debugging Tool (Admin use)
## Test branchoperator
During branchoperator behaviours with flag like input.

## Life span
May be altered to test advanced logics.

## Customisation
When dag is triggered without any configuration the expected task run is `task-c`

if `a` is set to `true`, `task-a` is expected to run

    {
        "a": "True"
    }

if `b` is set to `true`, `task-b` is expected to run

    {
        "b": "True"
    }

"""

from datetime import timedelta

from airflow import DAG
from airflow.operators.python_operator import BranchPythonOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.utils.dates import days_ago


DAG_NAME = "testing_branchoperator"

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


def parse_dagrun_conf(c, **kwargs):
    """
    parse input
    """
    return c


def check_dagrun_config(a="", b="", **kwargs):
    """
    determine task needed to perform
    """
    if a:
        return "task-a"
    elif b:
        return "task-b"
    else:
        return "task-c"


SET_REFRESH_PRODUCT_TASK_NAME = "parse_dagrun_conf"
CHECK_DAGRUN_CONFIG = "check_dagrun_config"

with dag:

    TASK_PLANNER = BranchPythonOperator(
        task_id=CHECK_DAGRUN_CONFIG,
        python_callable=check_dagrun_config,
        op_kwargs={
            "a": "{% if dag_run.conf.get('a') %} {{ dag_run.conf.a }} {% endif %}",
            "b": "{% if dag_run.conf.get('b') %} {{ dag_run.conf.b }} {% endif %}",
        },
        # provide_context=True,
    )

    op1 = DummyOperator(task_id="task-a")
    op2 = DummyOperator(task_id="task-b")
    op3 = DummyOperator(task_id="task-c")

    # SET_PRODUCTS = PythonOperator(
    #     task_id=SET_REFRESH_PRODUCT_TASK_NAME,
    #     python_callable=parse_dagrun_conf,
    #     op_kwargs={
    #         "c": "{% if dag_run.conf.get('c') %} {{ dag_run.conf.c }} {% endif %}"
    #     },
    #     # provide_context=True,
    # )

    TASK_PLANNER >> [op1, op2, op3]
    # SET_PRODUCTS >> op3
