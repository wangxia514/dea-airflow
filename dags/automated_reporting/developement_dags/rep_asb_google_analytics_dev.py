# -*- coding: utf-8 -*-

"""
Automated Reporting - ASB - Google Analytics
"""

import json
from datetime import datetime as dt, timedelta

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from airflow.models import Variable

REP_CONN_STR = Variable.get("db_rep_dev_secret")
REPORTING_PACKAGE_VERSION = "1.1.7"
GOOGLE_ANALYTICS_CREDENTIALS_STR = Variable.get("google_analytics_apikey")

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt(2021, 11, 1),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=60),
}

dag = DAG(
    "rep_asb_google_analytics_dev",
    description="DAG pulling Google Analytics stats",
    tags=["reporting_tests"],
    default_args=default_args,
    schedule_interval="0 1 * * *",
)

# fmt: off
JOBS = [
    "echo Reporting task started: $(date)",
    f"pip install ga-reporting-etls=={REPORTING_PACKAGE_VERSION}",
    "python3 -m nemo_reporting.google_analytics.etl",
    "mkdir -p /airflow/xcom/; echo '{\"exit_status\": '\"$?}\" > /airflow/xcom/return.json",
]

with dag:
    # noqa: E128
    tasks_list = [
        # ***AusSeabed Website All Data - Google Analytics***
        dict(
            id="website_stats",
            query_defs=dict(
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
        ),
        # ***AusSeabed Marine Portal - Google Analytics***
        dict(
            id="marine_portal_stats",
            query_defs=dict(
                view_id='184682265',  # AusSeabed Website All Data
                name="AusSeabed Marine Portal",
                # List of dimensions and table to import data into
                dimensions=[
                        dict(name=None,
                            table_name='marine.ausseabed_marine_portal_user_stat',
                            column_name=None),
                        dict(name='ga:country',
                            table_name='marine.ausseabed_marine_portal_country_user_stat',
                            column_name="country"),
                        dict(name='ga:browser',
                            table_name='marine.ausseabed_marine_portal_browser_stat',
                            column_name="browser"),
                        dict(name='ga:fullReferrer',
                            table_name='marine.ausseabed_marine_portal_full_referrer',
                            column_name="referrer")
                ]
            )
        ),

        # ***AusSeabed Planning Portal - Google Analytics***
        dict(
            id="planning_portal_stats",
            query_defs=dict(
                view_id='220576104',  # AusSeabed Website All Data
                name="AusSeabed Planning Portal",
                # List of dimensions and table to import data into
                dimensions=[
                    dict(name=None,
                        table_name='marine.ausseabed_planning_portal_user_stat',
                        column_name=None),
                    dict(name='ga:country',
                        table_name='marine.ausseabed_planning_portal_country_user_stat',
                        column_name="country"),
                    dict(name='ga:browser',
                        table_name='marine.ausseabed_planning_portal_browser_stat',
                        column_name="browser"),
                    dict(name='ga:fullReferrer',
                        table_name='marine.ausseabed_planning_portal_full_referrer',
                        column_name="referrer")
                ]
            )
        )
    ]

    def create_task(task_def):
        """Genrate tasks based on list of query parameters"""
        return KubernetesPodOperator(
            namespace="processing",
            image="python:3.8-slim-buster",
            arguments=["bash", "-c", " &&\n".join(JOBS)],
            name="write-xcom",
            do_xcom_push=True,
            is_delete_operator_pod=True,
            in_cluster=True,
            task_id=task_def["id"],
            get_logs=True,
            env_vars={
                "GOOGLE_ANALYTICS_CREDENTIALS": GOOGLE_ANALYTICS_CREDENTIALS_STR,
                "QUERY_DEFS": json.dumps(task_def["query_defs"]),
                "REP_CONN": REP_CONN_STR,
                "EXECUTION_DATE": "{{ ds }}",
            }
        )

    [create_task(task_def) for task_def in tasks_list]
