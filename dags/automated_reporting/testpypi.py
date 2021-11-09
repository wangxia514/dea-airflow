# -*- coding: utf-8 -*-

"""
testpypi
"""
# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
from airflow.operators.python import PythonVirtualenvOperator
from datetime import datetime as dt, timedelta
from airflow.models import Variable


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
    tags=["reporting_tests"],
    default_args=default_args,
    schedule_interval=timedelta(minutes=15),
)


def callable_virtualenv(**kwargs):
    """
    Example function that will be performed in a virtual environment.

    Importing at the module level ensures that it will not attempt to import the
    library before it is installed.
    """

    from nemo_reporting.google_analytics.etl import task

    return task(**kwargs)


google_analytics_credentials = Variable.get(
    "google_analytrics_apikey", deserialize_json=True
)


with dag:

    # ***AusSeabed Website All Data - Google Analytics***
    website_query_defs = dict(
        view_id="177791816",  # AusSeabed Website All Data
        name="AusSeabed Website",
        # List of dimensions and table to import data into
        dimensions=[
            dict(
                name=None,
                table_name="marine.ausseabed_website_user_stat",
                column_name=None,
            ),
            dict(
                name="ga:country",
                table_name="marine.ausseabed_website_country_user_stat",
                column_name="country",
            ),
            dict(
                name="ga:browser",
                table_name="marine.ausseabed_website_browser_stat",
                column_name="browser",
            ),
            dict(
                name="ga:fullReferrer",
                table_name="marine.ausseabed_website_full_referrer",
                column_name="referrer",
            ),
        ],
    )

    op_kwargs = dict(
        query_defs=website_query_defs,
        google_analytics_credentials=google_analytics_credentials,
        rep_conn=None,
    )

    virtualenv_task = PythonVirtualenvOperator(
        task_id="virtualenv_python",
        python_callable=callable_virtualenv,
        requirements=["ga-reporting-etls==1.1.2"],
        system_site_packages=True,
        op_kwargs=op_kwargs,
    )
