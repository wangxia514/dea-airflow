"""
# Another test DAG
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.operators.bash_operator import BashOperator

default_args = {
    # 'owner': 'Airflow',
    'depends_on_past': False,
    'start_date': datetime(2020, 2, 1),
    'email': ['airflow@example.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    # 'queue': 'bash_queue',
    # 'pool': 'backfill',
    # 'priority_weight': 10,
    # 'end_date': datetime(2016, 1, 1),
}

dag = DAG('check_qstat_nci',
          default_args=default_args,
          catchup=False,
          schedule_interval=timedelta(days=1))

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
