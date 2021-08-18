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
from airflow.operators.bash_operator import BashOperator

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


def r_pythonoperator(a=None, b=None, c=None, task_name=""):
    """testing behaviour"""
    if a.lower() == "true":
        bash_command = "echo a"
    elif b:
        bash_command = "echo b"
    elif c:
        bash_command = "echo c"
    elif not (a and b and c):
        bash_command = "echo not a b c"
    else:
        bash_command = "echo a " + a + " b " + b + " c " + c

    return BashOperator(
        task_id=task_name,
        bash_command=bash_command,
        # provide_context=True,
    )


SET_REFRESH_PRODUCT_TASK_NAME = "parse_dagrun_conf"
CHECK_DAGRUN_CONFIG = "check_dagrun_config"

with dag:

    all_conf = r_pythonoperator(
        "{{ dag_run.conf['a'] }}",
        "{{ dag_run.conf.b }}",
        "{{ dag_run.conf.c }}",
        task_name="all_conf",
    )

    only_a_via_dict = r_pythonoperator(
        a="{{ dag_run.conf['a'] }}",
        task_name="only_a_via_dict",
    )

    only_a_via_get = r_pythonoperator(
        a="{{ dag_run.conf.a }}",
        task_name="only_a_via_get",
    )

    no_conf = r_pythonoperator(
        task_name="no_conf",
    )
