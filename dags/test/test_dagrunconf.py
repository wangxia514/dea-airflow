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
from airflow.operators.python_operator import PythonOperator
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


def r_pythonoperator(a, b, **kwargs):
    """testing behaviour"""
    if a and b:
        bash_command = "echo a and b"
    elif a:
        bash_command = "echo a"
    else:
        bash_command = "echo else"

    return bash_command


SET_REFRESH_PRODUCT_TASK_NAME = "parse_dagrun_conf"
CHECK_DAGRUN_CONFIG = "check_dagrun_config"

with dag:

    all_conf_wo_condition = PythonOperator(
        task_id="all_conf_wo_condition",
        python_callable=r_pythonoperator,
        op_kwargs={"a": "{{ dag_run.conf.a }}", "b": "{{ dag_run.conf.b }}"},
    )

    all_conf_w_condition = PythonOperator(
        task_id="all_conf_w_condition",
        python_callable=r_pythonoperator,
        op_kwargs={
            "a": "{% if dag_run.conf.get('a') %} {{ dag_run.conf.a }} {% endif %}",
            "b": "{% if dag_run.conf.get('b') %} {{ dag_run.conf.b }} {% endif %}",
        },
    )
