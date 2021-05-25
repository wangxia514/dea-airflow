"""
## Testing branching operator behavior

condition: pass three dag_run.conf parameters

```
    "a": "",
    "b": "",
    "c": ""
```
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python_operator import PythonOperator, BranchPythonOperator
from airflow.operators.dummy_operator import DummyOperator

DAG_NAME = "testing_branchoperator"

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


def check_dagrun_config(a, b, **kwargs):
    """
    determine task needed to perform
    """
    if a and b:
        return ["task-a", "task-b"]
    elif a:
        return "task-a"
    elif b:
        return "task-b"
    else:
        return "task-a"


SET_REFRESH_PRODUCT_TASK_NAME = "parse_dagrun_conf"
CHECK_DAGRUN_CONFIG = "check_dagrun_config"

with dag:

    TASK_PLANNER = BranchPythonOperator(
        task_id=CHECK_DAGRUN_CONFIG,
        python_callable=check_dagrun_config,
        op_args=[
            "{{ dag_run.conf.a }}",
            "{{ dag_run.conf.b }}",
        ],
        # provide_context=True,
    )

    op1 = DummyOperator(task_id="task-a")
    op2 = DummyOperator(task_id="task-b")
    op3 = DummyOperator(task_id="task-c")

    SET_PRODUCTS = PythonOperator(
        task_id=SET_REFRESH_PRODUCT_TASK_NAME,
        python_callable=parse_dagrun_conf,
        op_args=["{{ dag_run.conf.c }}"],
        # provide_context=True,
    )

    TASK_PLANNER >> [op1, op2] >> SET_PRODUCTS >> op3
