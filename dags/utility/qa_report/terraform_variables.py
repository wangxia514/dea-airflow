"""
Check all terraform variables are provided by checking if VARIABLE has been injected to env.
"""
from datetime import date, datetime, timedelta
from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from textwrap import dedent

from airflow.utils.dates import days_ago

DAG_NAME = "utility_qa_terraform_variables_listing"

DEFAULT_ARGS = {
    "owner": "Pin Jin",
    "depends_on_past": False,
    "start_date": datetime(2021, 4, 20),
    "email": ["pin.jin@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

VARIABLE_QA_COMMAND = [
    "bash",
    "-c",
    dedent(
        """
            echo 'total number of variables:'
            env | grep -o 'AIRFLOW_VAR_[^.]*=' | wc -l
            env | grep -o 'AIRFLOW_VAR_[^.]*=' | awk -F= '{print $1}' | cut -d'_' -f3- | tr '[:upper:]' '[:lower:]'

        """
    ),
]

dag = DAG(
    dag_id=DAG_NAME,
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval="@weekly",  # weekly
    catchup=False,
    tags=["k8s", "developer_support", "rds", "s3", "db"],
)

with dag:

    # [START howto_operator_bash]
    run_this = BashOperator(
        task_id="variable-env",
        bash_command=VARIABLE_QA_COMMAND,
    )
    # [END howto_operator_bash]

    run_this
