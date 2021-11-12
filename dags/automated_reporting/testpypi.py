# -*- coding: utf-8 -*-

"""
testpypi
"""
import json

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)

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
    from datetime import datetime as dt

    return task(
        query_defs=kwargs["query_defs"],
        rep_conn=kwargs["rep_conn"],
        google_analytics_credentials=kwargs["google_analytics_credentials"],
        execution_date=dt.strptime(kwargs["ds_nodash"], "%Y%m%d"),
    )


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

    task_context = dict(
        query_defs=website_query_defs,
        google_analytics_credentials=google_analytics_credentials,
        rep_conn=None,
    )

    JOBS = [
        "echo Reporting task started: $(date)",
        "pip install ga-reporting-etls==1.1.7",
        "python3 -m nemo_reporting.google_analytics.etl",
        'mkdir -p /airflow/xcom/; echo \'{"status", "success"}\' > /airflow/xcom/return.json',
    ]

    k8s_task = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS)],
        name="write-xcom",
        do_xcom_push=True,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="k8s_task",
        get_logs=True,
        env_vars={
            "GOOGLE_ANALYTICS_CREDENTIALS": Variable.get("google_analytrics_apikey"),
            "QUERY_DEFS": json.dumps(website_query_defs),
            "REP_CONN": None,
            "EXECUTION_DATE": "{{ ds }}",
        },
    )

    k8s_task
