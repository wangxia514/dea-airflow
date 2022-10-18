"""
# Record Sandbox User Logins

This DAG finds all user logins to the DEA Jupyter Sandbox from the logs
we capture within Loki. It runs a query, and dumps all the logins into
a table in the Reporting Database

"""
from datetime import datetime, timedelta
from typing import NamedTuple

import requests
from airflow import DAG
from airflow.decorators import task
from airflow.providers.postgres.hooks.postgres import PostgresHook

default_args = {
    "start_date": datetime(2020, 1, 1),
    "email": ["damien@omad.net"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=15),
    "owner": "Damien Ayers",
}

NS = 1e9  # Loki records all it's timestamps in nanoseconds since the epoch!


class LoginRecord(NamedTuple):
    time: datetime
    user: str


@task()
def extract_user_logins_to_db(data_interval_start=None, data_interval_end=None):
    loki_query_params = {
        "query": '{namespace="sandbox", container="hub"} |~ "User logged in" '
        '| regexp ".*User logged in: (?P<user>.*)"',
        "start": data_interval_start.timestamp() * NS,
        "end": data_interval_end.timestamp() * NS,
    }
    response = requests.get(
        "http://loki-stack.monitoring.svc.cluster.local:3100/loki/api/v1/query_range",
        params=loki_query_params,
    )

    logins = [
        LoginRecord(
            time=datetime.fromtimestamp(int(res["values"][0][0]) / NS),
            user=res["stream"]["user"],
        )
        for res in response.json()["data"]["result"]
    ]
    reporting_db = PostgresHook(postgres_conn_id="db_rep_writer_prod")
    reporting_db.insert_rows(
        "dea.sandbox_logins", logins, target_fields=("time", "user")
    )


with DAG(
    dag_id="rep_dea_sandbox_user_logins",
    description="Record Production Sandbox User Logins",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval=timedelta(days=1),
    catchup=False,
    doc_md=__doc__,
) as dag:
    extract_user_logins_to_db()
