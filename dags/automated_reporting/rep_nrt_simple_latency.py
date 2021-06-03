"""
# Simple latency metric on nrt products: AWS ODC -> AIRFLOW -> Reporting DB

This DAG extracts latest timestamp values for a list of products in AWS ODC. It:
 * Connects to AWS ODC.
 * Runs multiple tasks (1 per product type) querying the latest timestamps for each from AWS ODC.
 * Inserts a summary of latest timestamps into the landsat.derivative_latency table in reporting DB.

"""

import logging
from datetime import datetime as dt
from datetime import timedelta, timezone, date

from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.hooks.postgres_hook import PostgresHook

from infra.connections import DB_REP_WRITER_CONN

log = logging.getLogger("airflow.task")

from automated_reporting.databases import schemas, odc_db, reporting_db
from automated_reporting.utilities import helpers

rep_pg_hook = PostgresHook(postgres_conn_id=DB_REP_WRITER_CONN)

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt(2021, 5, 1, tzinfo=timezone.utc),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "rep_nrt_simple_latency",
    description="DAG for simple latency metric on nrt products: AWS ODC -> AIRFLOW -> Reporting DB",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval=timedelta(minutes=15),
)

with dag:

    # Task callable
    def nrt_simple_latency(execution_date, product_name, **kwargs):
        """
        Task to query AWS ODC with supplied `product_name` and insert a summary of latest timestamps into reporting DB
        """

        # Convert pendulum to python datetime to make stripping timezone possible
        execution_date = helpers.python_dt(execution_date)

        log.info(
            "Starting Task for: {}@{}".format(product_name, execution_date.isoformat())
        )

        # List of days in the past to check latency on
        timedelta_list = [5, 15, 30, 90]

        results = odc_db.query_stepped(product_name, execution_date, timedelta_list)

        # Find the latest values for sat_acq and processing in the returned rows by updating latest_sat_acq_ts and latest_processing_ts
        latest_sat_acq_ts = helpers.ZERO_TS
        latest_processing_ts = helpers.ZERO_TS
        for row in results:
            sat_acq_ts = row["center_dt"]
            processing_ts = row["processing_dt"]
            if sat_acq_ts > latest_sat_acq_ts:
                latest_sat_acq_ts = sat_acq_ts
            if processing_ts > latest_processing_ts:
                latest_processing_ts = processing_ts

        # This is the case that no data was found for any of the time periods specified
        if (
            latest_processing_ts == helpers.ZERO_TS
            or latest_processing_ts == helpers.ZERO_TS
        ):
            raise Exception(
                "Unable to find data in ODC for last {} days".format(
                    max(timedelta_list)
                )
            )

        # Log success
        log.info("Latest Satellite Acquisition Time: {}".format(latest_sat_acq_ts))
        log.info("Latest Processing Time Stamp: {}".format(latest_processing_ts))

        # Insert latest processing and satellite acquisition time for current execution time into reporting database
        # for landsat.dervivative data the table is not TZ aware acq_date and processing_date are in UTC, last_updated is in AEST.
        reporting_db.insert_latency(
            product_name, latest_sat_acq_ts, latest_processing_ts, execution_date
        )

        return "Completed latency for {}".format(product_name)

    # Product list to extract the metric for, could potentially be part of dag configuration and managed in airflow UI?
    products_list = ["s2a_nrt_granule", "s2b_nrt_granule"]

    ## Tasks
    check_db = PythonOperator(
        task_id="check_db_schema",
        python_callable=schemas.check_db_schema,
        op_kwargs={
            "expected_schema": schemas.COMPLETENESS_SCHEMA,
            "connection_id": DB_REP_WRITER_CONN,
        },
    )

    def create_task(product_name):
        """
        Function to generate PythonOperator tasks with id based on `product_name`
        """
        return PythonOperator(
            task_id="nrt-simple-latency_" + product_name,
            python_callable=nrt_simple_latency,
            op_kwargs={"product_name": product_name},
            provide_context=True,
        )

    check_db >> [create_task(product_name) for product_name in products_list]
