"""
# Record Sandbox User Logins

This DAG finds all user logins to the DEA Jupyter Sandbox from the logs
we capture within Loki. It runs a query, and dumps all the logins into
a table in the Reporting Database

"""
from datetime import datetime, timedelta
from typing import NamedTuple

import pendulum
import requests
from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.decorators import task
from airflow.providers.postgres.hooks.postgres import PostgresHook
import logging

# get the airflow.task logger
task_logger = logging.getLogger("airflow.task")

local_tz = pendulum.timezone("Australia/Canberra")
default_args = {
    "start_date": datetime(2020, 1, 1, tzinfo=local_tz),
    "email": ["damien@omad.net"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=15),
    "owner": "Damien Ayers",
}

NS = 1e9  # Loki records all it's timestamps in nanoseconds since the epoch!


class LoginRecord(NamedTuple):
    login_time: datetime
    email: str


@task()
def extract_logins_to_db(data_interval_start=None, data_interval_end=None):
    loki_query_params = {
        "query": '{namespace="sandbox", container="hub"} |~ "User logged in" '
        '| regexp ".*User logged in: (?P<email>.*)"',
        "start": int(data_interval_start.timestamp() * NS),
        "end": int(data_interval_end.timestamp() * NS),
    }
    response = requests.get(
        "http://loki-stack.monitoring.svc.cluster.local:3100/loki/api/v1/query_range",
        params=loki_query_params,
    )
    if response.status_code != 200:
        raise AirflowException(
            f"Invalid response from Loki ({response.status_code}): {response.text}"
        )

    logins = [
        LoginRecord(
            login_time=datetime.fromtimestamp(int(res["values"][0][0]) / NS),
            email=res["stream"]["email"],
        )
        for res in response.json()["data"]["result"]
    ]
    reporting_db = PostgresHook(postgres_conn_id="db_rep_writer_prod")

    upsert_rows(
        reporting_db,
        "dea.sandbox_logins",
        logins,
        target_fields=("login_time", "email"),
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
    extract_logins_to_db()


def upsert_rows(pghook, table, rows, target_fields, commit_every=1000):
    """
    Insert rows into a PostgreSQL table and ignore any conflicts.

    This is a replacement function for :method:`airflow.hooks.DbApiHook.insert_rows()`.
    It does support a `replace` argument, but with the PostgresHook it only works if
    only some of the rows can conflict, not all of them.

    See that method for documentation.
    """

    with pghook.get_conn() as conn:
        if pghook.supports_autocommit:
            pghook.set_autocommit(conn, False)

        conn.commit()

        with conn.cursor() as cur:
            for i, row in enumerate(rows, 1):

                sql = f"""
                INSERT INTO {table} ({', '.join(target_fields)})
                VALUES ({', '.join(['%s' * len(target_fields)])})
                ON CONFLICT DO NOTHING;
                """

                if i == 1 or i % 100 == 0:
                    task_logger.info("Generated sql: %s", sql)

                cur.execute(sql, row)
                if commit_every and i % commit_every == 0:
                    conn.commit()
                    task_logger.info("Loaded %s rows into %s so far", i, table)

        conn.commit()
    task_logger.info("Done loading. Loaded a total of %s rows", i)
