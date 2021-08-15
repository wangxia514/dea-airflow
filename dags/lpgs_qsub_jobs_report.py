"""
Another test DAG
"""
from datetime import timedelta

from airflow import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

default_args = {
    "owner": "damien",
    "start_date": days_ago(2),
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "lpgs_qsub_jobs_report",
    default_args=default_args,
    schedule_interval=timedelta(days=1),
)


def my_python_callable(*args, **kwargs):
    """
    Mock
    """
    print("foo")


with dag:
    # TODO: This could filter out jobs completed outside this period
    t1 = SSHOperator(
        task_id="task1", command="qstat -x -f -F json", ssh_conn_id="lpgs_gadi"
    )

    example_bash_task = BashOperator(
        task_id="example_bash_task",
        bash_command='echo {{ task_instance.xcom_pull(task_ids="get_files") }}',
    )

    put_into_postgres = PythonOperator(
        task_id="save_qstat_to_postgres", python_callable=my_python_callable
    )
