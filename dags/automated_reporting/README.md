# Automated Reporting Dags

There are two ways to run and test automated_reporting dags locally

## Docker (Old Way)
It is possible to bring up a set of Airflow containers using `docker-compose up` at the repository root and test that dags are loading correctly. With the upgrade to Airflow 2.x this uses a lot of system resources and has become difficult to run locally on a PC/laptop. Therefore another method of developing dags locally has been developed.

## Python Venv (New Way)
Using a virtual environment and by structuring tasks and dags slightly differently it is possible to run and test the ETL code locally without Airflow. The key is to removing all Airflow dependencies from the tasks and their sub-dependencies(utilities etc.). Only use Airflow objects in the Dag file itself and pass them down into to the task in kwargs. In this way the task can run with a local set of kwargs (from .env, file etc.) in a very similar environment to Airflow without a lot of it's complexity.

Basic steps:

  - Install Python 3.6 (or whatever Airflow currently uses) on your devlopment machine
  - Create a virtual environment inside the `dags/automated_reporting` folder
  - Modify the `[VENV FOLDER HERE]/bin/activate` file with a modified Python path to bring the dags folder into scope
    - `export PYTHONPATH=[ABSOLUTE PATH HERE]/dea-airflow/dags`
  - Install the `automated_reporting/requirements.txt` in the new venv
  - Add a `.env` in the `automated_reporting/tests` folder for secrets

This should allow the running of tasks (not Dags) using python 3.6, in a very similar environment to how Airflow runs them.

## Tests
Using the new way of structuring dags and their sub-dependencies it should be simple to test everything apart from the dag.

From with automated_reporting venv:

  - `python3.6 dags/automated_reporting/tests/test_completeness.py`
  - `python3.6 dags/automated_reporting/tests/test_usgs_completeness.py`

## ToDo

  - Move to the VirtualenvPythonOpertor and install automated_reporting requirements.txt
    - We don't have any third-party dependencies that are not already included in Airflow (requests, pytz etc.), but an Airflow update or requirement version change could change that and break the automated reporting dags
  - Move all code (except the actual dags) to the automated reporting ETL repo and install into VirtualenvPythonOperator (which uses pip) using a private python package
    - `https://bitbucket.org/geoscienceaustralia/automated-reporting-etl/`
    - This can installed in the requirements list using something like:
      - `https://[user]:[token]@bitbucket.org/geoscienceaustralia/automated-reporting-etl/get/import-test.tar.gz#egg=ga_nemo_monitoring&subdirectory=ga_nemo_monitoring`
      - Token is not the account password, it's a token associated to the account with limited privilege
      - The code is structured as a Python package (has a setup.py, etc.) in a subfolder within the repo
    - One issue with this is that the token is not obscured in the Airflow logs, but this should be solvable by modifying (sub-classing) the VirtualenvPythonOperator
