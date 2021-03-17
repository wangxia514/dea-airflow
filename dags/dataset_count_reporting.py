"""
# Count Collection 3 Datasets in Different Environments

Products
- ga_ls5t_ard_3
- ga_ls7e_ard_3
- ga_ls8c_ard_3
- ga_ls_wo_3
- ga_ls_fc_3

Environments
- NCI Filesystem (THREDDS/gdata)
- S3
- NCI Explorer
- Sandbox Explorer
- OWS-Dev Explorer
- OWS-Prod Explorer
"""
from datetime import timedelta

from airflow import DAG
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago

default_args = {
    'owner': 'Damien Ayers',
    'start_date': days_ago(2),
    'retry_delay': timedelta(minutes=5)
}

dag = DAG(
    'collection_3_dataset_count_reporting',
    default_args=default_args,
    schedule_interval=timedelta(days=1)
)


with dag:
    t1 = SSHOperator(
        task_id="task1",
        command='qstat -x -f -F json',
        ssh_conn_id='lpgs_gadi')

    example_bash_task = BashOperator(
        task_id='example_bash_task',
        bash_command='echo {{ task_instance.xcom_pull(task_ids="get_files") }}',
    )

    put_into_postgres = PythonOperator(
        task_id="save_qstat_to_postgres",
        python_callable=my_python_callable
    )

