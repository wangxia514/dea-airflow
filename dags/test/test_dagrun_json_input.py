"""
# Debugging Tool (Admin use)
## Test dag_run input as array/list
Test behavior when dag run input is json list

## Life span
May be altered to test advanced logics.

## Customisation
When dag is triggered without any configuration the expected task run is `task-c`

if `a` is set to `true`, `task-a` is expected to run

    {
        "array_input": ["a", "b", "c"]
    }

"""

from datetime import timedelta
from airflow.operators.bash import BashOperator
from textwrap import dedent

from airflow import DAG
from airflow.operators.python_operator import BranchPythonOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.utils.dates import days_ago


DAG_NAME = "testing_dagrun_as_array_input"

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

PRODUCT_UPDATE_CMD = [
    "bash",
    "-c",
    dedent(
        """
            datacube -v product update --allow-unsafe\
            {% for p in dag_run.conf.array_input %}
            {{ p }}{% endfor %}
        """
    ),
]


# THE DAG
dag = DAG(
    dag_id=DAG_NAME,
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,
    catchup=False,
    tags=["k8s", "test"],
)


with dag:

    test_json_array_input = BashOperator(
            task_id='test_json_array_input',
            bash_command="echo {{ dag_run.conf.array_input }}",
        )

    test_json_input_w_jinja = BashOperator(
            task_id='test_json_input_w_jinja',
            bash_command="{% for p in dag_run.conf.array_input %} echo {{ p }} \n {% endfor %}",
        )

    test_json_input_w_dedent = BashOperator(
        task_id='test_json_input_w_dedent',
        bash_command=PRODUCT_UPDATE_CMD,
    )