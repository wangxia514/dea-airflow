# -*- coding: utf-8 -*-

"""
Automated Reporting - ASB - Google Analytics
"""

import json
from datetime import datetime as dt, timedelta

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG

from automated_reporting import k8s_secrets, utilities

ENV = "prod"
ETL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls:v2.13.0"
)

default_args = {
    "owner": utilities.REPORTING_OWNERS,
    "depends_on_past": False,
    "start_date": dt(2020, 6, 15),
    "email": utilities.REPORTING_ADMIN_EMAILS,
    "email_on_failure": True if ENV == "prod" else False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=60),
}

dag = DAG(
    f"rep_asb_google_analytics_{ENV}",
    description="DAG pulling Google Analytics stats",
    tags=["reporting"] if ENV == "prod" else ["reporting_dev"],
    default_args=default_args,
    schedule_interval="0 1 * * *",
)

# fmt: off
GOOGLE_ANALYTICS_JOB = [
    "echo Reporting task started: $(date)",
    "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
    "marine-google-analytics"
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
                landing_page="/persona/marine",
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
        env_vars = {
            "QUERY_DEFS": json.dumps(task_def["query_defs"]),
            "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ds }}",
        }
        return utilities.k8s_operator(
            dag=dag,
            image=ETL_IMAGE,
            task_id=task_def["id"],
            cmds=GOOGLE_ANALYTICS_JOB,
            env_vars=env_vars,
            secrets=k8s_secrets.db_secrets(ENV) + k8s_secrets.google_analytics_secret
        )

    [create_task(task_def) for task_def in tasks_list]
