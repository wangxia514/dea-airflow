"""
test manual trigger
"""

# The DAG object; we'll need this to instantiate a DAG
import os 
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": False,
    "start_date": datetime(2022, 4, 6),
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
}


dag = DAG(
    "test_manual",
    description="test manual trigger",
    tags=["reporting_dev"],
    default_args=default_args,
    schedule_interval=timedelta(minutes=3),
)


def some_task_py(**context):
    """ some task """
    run_id = context['templates_dict']['run_id']
    is_manual = run_id.startswith('manual__')
    is_scheduled = run_id.startswith('scheduled__')
    print(f" is manual {is_manual} is scheduled {is_scheduled}")
    execution_date = os.environ.get("EXECUTION_DATE")
    if is_manual:
        print(f" manual run date {execution_date}")
        raise Exception('Cannot trigger manually')
    else:
        print(f" scheduled run date {execution_date}")


with dag:
    some_task = PythonOperator(
        task_id='some_task',
        dag=dag,
        templates_dict={'run_id': '{{ run_id }}'},
        python_callable=some_task_py,
        provide_context=True,
        env_vars={
            "EXECUTION_DATE": "{{ (dag_run.data_interval_start | ds) }}",
        },
    )
    some_task
