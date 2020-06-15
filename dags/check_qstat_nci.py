"""
# Another test DAG
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.contrib.hooks.ssh_hook import SSHHook
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.hooks.postgres_hook import PostgresHook
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.postgres_operator import PostgresOperator

default_args = {
    'depends_on_past': False,
    'start_date': datetime(2020, 2, 1),
    'email': ['airflow@example.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


def ensure_table(postgres_conn_id, database):
    ssh_hook = SSHHook(ssh_conn_id='lpgs_gadi')
    ssh_hook.get_tunnel().start()
    hook = PostgresHook(postgres_conn_id=postgres_conn_id,
                        schema=database)
    hook.run(
        """CREATE TABLE ..."""
    )


dag = DAG('check_qstat_nci',
          default_args=default_args,
          catchup=False,
          schedule_interval=timedelta(days=1))

ensure_database_table = PythonOperator(
    task_id='ensure_database_table',
    python_callable=ensure_table)


get_qstat_output = SSHOperator(task_id='get_qstat_output',
                               ssh_conn_id='lpgs_gadi',
                               command='qstat -xf -F json',
                               do_xcom_push=True,
                               dag=dag)


# t1, t2 and t3 are examples of tasks created by instantiating operators
t1 = BashOperator(
    task_id='print_date',
    bash_command='date',
    dag=dag)

get_qstat_output >> t1
