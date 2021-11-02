# -*- coding: utf-8 -*-

"""
testpypi
"""
# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
from airflow.operators.python import PythonVirtualenvOperator

# [START instantiate_dag]
pipeline = DAG(
    "testpypi",
    doc_md=__doc__,
    description="testpypi",
    concurrency=1,
    max_active_runs=1,
    catchup=False,
    tags=["testpypi"],
)
# [END instantiate_dag]


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


with pipeline:

    virtualenv_task = PythonVirtualenvOperator(
        task_id="virtualenv_python",
        python_callable=callable_virtualenv,
        requirements=["ga-reporting-etls==0.0.15"],
        system_site_packages=False,
        )
