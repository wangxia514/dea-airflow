# -*- coding: utf-8 -*-

"""
Restore DB DAG based on a date
"""

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime as dt, timedelta

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": False,
    "start_date": dt(2022, 6, 6),
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(days=1),
}

dag = DAG(
    dag_id='restore_db',
    default_args=default_args,
    schedule_interval=None
)

bash = BashOperator(
    task_id='bash',
    bash_command='echo {{ params.EXECUTION_DATE }}', # Output: value1
    dag=dag
)
