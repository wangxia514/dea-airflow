"""
Utilities for odc db queries
"""

import logging
from datetime import timedelta

from airflow.hooks.postgres_hook import PostgresHook

from infra.connections import DB_ODC_READER_CONN
from automated_reporting.utilities import helpers
from automated_reporting.databases import sql

log = logging.getLogger("airflow.task")


def query(product_id, execution_date, days):
    """Query odc for a product id, date and number of days"""
    odc_pg_hook = PostgresHook(postgres_conn_id=DB_ODC_READER_CONN)

    execution_date = helpers.python_dt(execution_date)

    # caluclate a start and end time for the AWS ODC query
    odc_start_time = execution_date - timedelta(days=days)
    odc_end_time = execution_date
    log.info(
        "Querying Sentinel/Copernicus Inventory between {} - {}".format(
            odc_start_time.isoformat(), odc_end_time.isoformat()
        )
    )
    # extact a processing and acquisition timestamps from AWS for product and timerange,
    # print logs of query and row count

    odc_conn = None
    actual_products = []
    try:
        # open the connection to the AWS ODC and get a cursor
        with odc_pg_hook.get_conn() as odc_conn:
            with odc_conn.cursor() as odc_cursor:
                odc_cursor.execute(
                    sql.SELECT_BY_PRODUCT_AND_TIME_RANGE,
                    (product_id, odc_start_time, odc_end_time),
                )
                log.debug("ODC Executed SQL: {}".format(odc_cursor.query.decode()))
                log.info("ODC query returned: {} rows".format(odc_cursor.rowcount))

                # if nothing is returned in the given timeframe, loop again and go back further in time
                if odc_cursor.rowcount == 0:
                    raise Exception("ODC query error, no data returned")

                # Find the latest values for sat_acq and processing in the returned rows by updating
                # latest_sat_acq_ts and latest_processing_ts

                for row in odc_cursor:
                    (
                        id,
                        indexed_time,
                        granule_id,
                        region_id,
                        sat_acq_ts,
                        processing_ts,
                    ) = row
                    row = {
                        "uuid": id,
                        "granule_id": granule_id,
                        "region_id": region_id,
                        "center_dt": sat_acq_ts,
                        "processing_dt": processing_ts,
                    }
                    actual_products.append(row)
    except Exception as e:
        raise e
    finally:
        if odc_conn is not None:
            odc_conn.close()
    return actual_products


def query_stepped(product_id, execution_date, steps):
    """Query odc progressively until a result is returned"""

    odc_pg_hook = PostgresHook(postgres_conn_id=DB_ODC_READER_CONN)
    odc_conn = None
    results = []
    try:
        # open the connection to the AWS ODC and get a cursor
        with odc_pg_hook.get_conn() as odc_conn:
            with odc_conn.cursor() as odc_cursor:

                # Loop through the time_delta list until we get some data back. Prevents returning a huge amount of data unecessarily from ODC.
                for days_previous in steps:

                    # caluclate a start and end time for the AWS ODC query
                    end_time = execution_date
                    start_time = end_time - timedelta(days=days_previous)

                    # extact a processing and acquisition timestamps from AWS for product and timerange, print logs of query and row count
                    odc_cursor.execute(
                        sql.SELECT_BY_PRODUCT_AND_TIME_RANGE,
                        (product_id, start_time, end_time),
                    )
                    log.info("ODC Query for: {} days".format(days_previous))
                    log.info("ODC Executed SQL: {}".format(odc_cursor.query.decode()))
                    log.info("ODC query returned: {} rows".format(odc_cursor.rowcount))

                    # if nothing is returned in the given timeframe, loop again and go back further in time
                    if odc_cursor.rowcount > 0:
                        break
                    else:
                        continue

                for row in odc_cursor:
                    (
                        id,
                        indexed_time,
                        granule_id,
                        region_id,
                        sat_acq_ts,
                        processing_ts,
                    ) = row
                    row = {
                        "uuid": id,
                        "granule_id": granule_id,
                        "region_id": region_id,
                        "center_dt": sat_acq_ts,
                        "processing_dt": processing_ts,
                    }
                    results.append(row)
    except Exception as e:
        raise e
    finally:
        if odc_conn is not None:
            odc_conn.close()
    return results

    # Loop through the time_delta list until we get some data back. Prevents returning a huge amount of data unecessarily from ODC.
    for days_previous in steps:

        # caluclate a start and end time for the AWS ODC query
        end_time = execution_date
        start_time = end_time - timedelta(days=days_previous)

        # extact a processing and acquisition timestamps from AWS for product and timerange, print logs of query and row count
        odc_cursor.execute(
            sql.SELECT_BY_PRODUCT_AND_TIME_RANGE, (product_id, start_time, end_time)
        )
        log.info("ODC Query for: {} days".format(days_previous))
        log.info("ODC Executed SQL: {}".format(odc_cursor.query.decode()))
        log.info("ODC query returned: {} rows".format(odc_cursor.rowcount))

        # if nothing is returned in the given timeframe, loop again and go back further in time
        if odc_cursor.rowcount == 0:
            continue
