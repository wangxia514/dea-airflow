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

dag = DAG("testpy_test", description="DAG for testing pypi flow", tags=["testpypi"], default_args=default_args, schedule_interval=timedelta(minutes=15),)


def callable_virtualenv():
    """
    Example function that will be performed in a virtual environment.

    Importing at the module level ensures that it will not attempt to import the
    library before it is installed.
    """
    from time import sleep

    from colorama import Back, Fore, Style

    print(Fore.RED + 'some red text')
    print(Back.GREEN + 'and with a green background')
    print(Style.DIM + 'and in dim text')
    print(Style.RESET_ALL)
    for _ in range(10):
        print(Style.DIM + 'Please wait...', flush=True)
        sleep(10)
    print('Finished')


with dag:

    virtualenv_task = PythonVirtualenvOperator(task_id="virtualenv_python", python_callable=callable_virtualenv, requirements=["colorama==0.4.0"], system_site_packages=False,)
