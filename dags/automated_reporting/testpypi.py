# -*- coding: utf-8 -*-

"""
testpypi
"""
# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
from airflow.operators.python import PythonVirtualenvOperator
from datetime import datetime as dt, timedelta

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": False,
    "start_date": dt.now() - timedelta(hours=1),
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "testpy_test",
    description="DAG for testing pypi flow",
    tags=["testpypi"],
    default_args=default_args,
    schedule_interval=timedelta(minutes=15),

def callable_virtualenv():
    """
    Example function that will be performed in a virtual environment.

    Importing at the module level ensures that it will not attempt to import the
    library before it is installed.
    """
    from testpypi.testpypi import say_hello

    name1 = say_hello()
    name2 = say_hello("Everybody")
    print(name1)
    print(name2)
    print("finished")


with dag:

    virtualenv_task = PythonVirtualenvOperator(task_id="virtualenv_python", python_callable=callable_virtualenv, requirements=["ga-reporting-etls==0.0.15"], system_site_packages=False,)
