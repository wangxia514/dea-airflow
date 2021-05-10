"""
# Simple latency metric on nrt products: AWS ODC -> AIRFLOW -> Reporting DB

This DAG extracts latest timestamp values for a list of products in AWS ODC. It:
 * Connects to AWS ODC.
 * Runs multiple tasks (1 per product type) querying the latest timestamps for each from AWS ODC.
 * Inserts a summary of latest timestamps into the landsat.derivative_latency table in reporting DB.

"""

import logging
from datetime import datetime as dt
from datetime import timedelta, timezone

from airflow import DAG
from airflow.utils.dates import days_ago
from airflow.operators.python_operator import PythonOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.hooks.postgres_hook import PostgresHook

from infra.connections import DB_ODC_READER_CONN, DB_REP_WRITER_CONN

log = logging.getLogger("airflow.task")

odc_pg_hook = PostgresHook(postgres_conn_id=DB_ODC_READER_CONN)
rep_pg_hook = PostgresHook(postgres_conn_id=DB_REP_WRITER_CONN)

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": days_ago(0),
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

SELECT_BY_PRODUCT_AND_TIME_RANGE = """
    SELECT
        dataset.id,
        dataset.added AS indexed_time,
        agdc.common_timestamp(dataset.metadata #>> '{extent,center_dt}'::text[]) as satellite_acquisition_time,
        agdc.common_timestamp(dataset.metadata #>> '{system_information,time_processed}'::text[]) AS processing_time
    FROM agdc.dataset
        JOIN agdc.dataset_type ON dataset_type.id = dataset.dataset_type_ref
    WHERE
        dataset.archived IS NULL
    AND
        dataset_type.name = %s
    AND
        dataset.added >= %s
    AND
        dataset.added <= %s;
"""
SELECT_SCHEMA = """SELECT * FROM information_schema.schemata WHERE catalog_name=%s and schema_name=%s;"""
SELECT_TABLE = """SELECT * FROM information_schema.tables WHERE table_catalog=%s AND table_schema=%s AND table_name=%s;"""
SELECT_COLUMN = """SELECT * FROM information_schema.columns WHERE table_catalog=%s AND table_schema=%s AND table_name=%s AND column_name=%s;"""
INSERT_LATENCY = """INSERT INTO landsat.derivative_latency VALUES (%s, %s, %s, %s);"""
STRUCTURE = {
    "database": {
        "name": "reporting",
        "schemas": [
            {
                "name": "landsat",
                "tables": [
                    {
                        "name": "derivative_latency",
                        "columns": [
                            {"name": "product"},
                            {"name": "sat_acq_date"},
                            {"name": "processing_date"},
                            {"name": "last_updated"},
                        ],
                    }
                ],
            }
        ],
    }
}


def db_has_object(rep_cursor, sql, query_args):
    """
    Tests if an SQL query returns any rows, returns boolean
    """
    rep_cursor.execute(sql, query_args)
    if rep_cursor.rowcount == 0:
        return False
    return True


with dag:

    # Task callable
    def check_db_structure():
        """
        Task to check that the schema in reporting db has the correct tables, columns, fields before progressing
        """
        rep_conn = rep_pg_hook.get_conn()
        rep_cursor = rep_conn.cursor()
        database = STRUCTURE["database"]
        structure_good = True
        for schema in database["schemas"]:
            result = db_has_object(
                rep_cursor, SELECT_SCHEMA, (database["name"], schema["name"])
            )
            if not result:
                structure_good = False
            log.info(
                "Test database '{}' has schema '{}: {}".format(
                    database["name"], schema["name"], result
                )
            )
            for table in schema["tables"]:
                result = db_has_object(
                    rep_cursor,
                    SELECT_TABLE,
                    (database["name"], schema["name"], table["name"]),
                )
                if not result:
                    structure_good = False
                log.info(
                    "Test schema '{}' has table '{}: {}".format(
                        schema["name"], table["name"], result
                    )
                )
                for column in table["columns"]:
                    result = db_has_object(
                        rep_cursor,
                        SELECT_COLUMN,
                        (
                            database["name"],
                            schema["name"],
                            table["name"],
                            column["name"],
                        ),
                    )
                    if not result:
                        structure_good = False
                    log.info(
                        "Test table '{}' has column '{}: {}".format(
                            table["name"], column["name"], result
                        )
                    )
        if not structure_good:
            raise Exception("Database structure does not match structure definition")
        return "Database structure check passed"

    # Task callable
    def nrt_simple_latency(execution_date, product_name, **kwargs):
        """
        Task to query AWS ODC with supplied `product_name` and insert a summary of latest timestamps into reporting DB
        """

        # Convert pendulum to python datetime to make stripping timezone possible
        execution_date = dt(
            execution_date.year,
            execution_date.month,
            execution_date.day,
            execution_date.hour,
            execution_date.minute,
            execution_date.second,
            execution_date.microsecond,
            tzinfo=execution_date.tz,
        )

        log.info(
            "Starting Task for: {}@{}".format(product_name, execution_date.isoformat())
        )

        # open the connection to the AWS ODC and get a cursor
        odc_cursor = odc_pg_hook.get_conn().cursor()
        # open the connection to the Reporting DB and get a cursor
        rep_conn = rep_pg_hook.get_conn()
        rep_cursor = rep_conn.cursor()

        # List of days in the past to check latency on
        timedelta_list = [5, 15, 30, 90]

        ZERO_TS = dt(1970, 1, 1, tzinfo=timezone.utc)

        latest_sat_acq_ts = ZERO_TS
        latest_processing_ts = ZERO_TS

        # Loop through the time_delta list until we get some data back. Prevents returning a huge amount of data unecessarily from ODC.
        for days_previous in timedelta_list:

            # caluclate a start and end time for the AWS ODC query
            end_time = execution_date
            start_time = end_time - timedelta(days=days_previous)

            # extact a processing and acquisition timestamps from AWS for product and timerange, print logs of query and row count
            odc_cursor.execute(
                SELECT_BY_PRODUCT_AND_TIME_RANGE, (product_name, start_time, end_time)
            )
            log.info("ODC Query for: {} days".format(days_previous))
            log.info("ODC Executed SQL: {}".format(odc_cursor.query.decode()))
            log.info("ODC query returned: {} rows".format(odc_cursor.rowcount))

            # if nothing is returned in the given timeframe, loop again and go back further in time
            if odc_cursor.rowcount == 0:
                continue

            # Find the latest values for sat_acq and processing in the returned rows by updating latest_sat_acq_ts and latest_processing_ts
            for row in odc_cursor:
                id, indexed_time, sat_acq_ts, processing_ts = row
                if sat_acq_ts > latest_sat_acq_ts:
                    latest_sat_acq_ts = sat_acq_ts
                if processing_ts > latest_processing_ts:
                    latest_processing_ts = processing_ts

            # Stop looping once latest has been found
            break

        # This is the case that no data was found for any of the time periods specified
        if latest_processing_ts == ZERO_TS or latest_processing_ts == ZERO_TS:
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
        rep_cursor.execute(
            INSERT_LATENCY,
            (
                product_name,
                latest_sat_acq_ts.astimezone(tz=timezone.utc).replace(tzinfo=None),
                latest_processing_ts.astimezone(tz=timezone.utc).replace(tzinfo=None),
                execution_date.astimezone(
                    tz=timezone(timedelta(hours=10), name="AEST")
                ).replace(tzinfo=None),
            ),
        )
        rep_conn.commit()
        log.info("REP Executed SQL: {}".format(rep_cursor.query.decode()))
        log.info("REP returned: {}".format(rep_cursor.statusmessage))

        return "Completed latency for {}".format(product_name)

    # Product list to extract the metric for, could potentially be part of dag configuration and managed in airflow UI?
    products_list = ["s2a_nrt_granule", "s2b_nrt_granule"]

    ## Tasks
    check_db = PythonOperator(
        task_id="check_db_structure", python_callable=check_db_structure
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
