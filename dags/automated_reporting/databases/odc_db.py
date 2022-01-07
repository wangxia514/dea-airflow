"""
Utilities for odc db queries
"""

import logging
import psycopg2
from datetime import timedelta

from automated_reporting.utilities import helpers
from automated_reporting.databases import sql

log = logging.getLogger("airflow.task")


SQL_QUERY = {
    "s2a_nrt_granule": sql.SELECT_BY_PRODUCT_AND_TIME_RANGE_TYPE1,
    "s2b_nrt_granule": sql.SELECT_BY_PRODUCT_AND_TIME_RANGE_TYPE1,
    "ga_s2_wo_3": sql.SELECT_BY_PRODUCT_AND_TIME_RANGE_TYPE2,
    "ga_ls7e_ard_provisional_3": sql.SELECT_BY_PRODUCT_AND_TIME_RANGE_TYPE3,
    "ga_ls8c_ard_provisional_3": sql.SELECT_BY_PRODUCT_AND_TIME_RANGE_TYPE3,
    "ga_ls5t_ard_3": sql.SELECT_BY_PRODUCT_AND_TIME_RANGE_TYPE3,
    "ga_ls7e_ard_3": sql.SELECT_BY_PRODUCT_AND_TIME_RANGE_TYPE3,
    "ga_ls8c_ard_3": sql.SELECT_BY_PRODUCT_AND_TIME_RANGE_TYPE3,
    "ga_ls_wo_3": sql.SELECT_BY_PRODUCT_AND_TIME_RANGE_TYPE3,
    "ga_ls_fc_3": sql.SELECT_BY_PRODUCT_AND_TIME_RANGE_TYPE3,
    "ga_s2am_ard_provisional_3": sql.SELECT_BY_PRODUCT_AND_TIME_RANGE_TYPE4,
    "ga_s2bm_ard_provisional_3": sql.SELECT_BY_PRODUCT_AND_TIME_RANGE_TYPE4,
    "ga_s2_ba_provisional_3": sql.SELECT_BY_PRODUCT_AND_TIME_RANGE_TYPE4,
}


def query(connection_parameters, product_id, execution_date, days):
    """Query odc for a product id, date and number of days"""

    execution_date = helpers.python_dt(execution_date)

    # caluclate a start and end time for the AWS ODC query
    odc_start_time = execution_date - timedelta(days=days)
    odc_end_time = execution_date
    log.info(
        "Querying ODC Inventory between {} - {}".format(
            odc_start_time.isoformat(), odc_end_time.isoformat()
        )
    )
    # extact a processing and acquisition timestamps from AWS for product and timerange,
    # print logs of query and row count

    odc_conn = None
    datasets = []
    try:
        # open the connection to the AWS ODC and get a cursor
        with psycopg2.connect(**connection_parameters) as odc_conn:
            with odc_conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            ) as odc_cursor:
                odc_cursor.execute(
                    SQL_QUERY[product_id],
                    (product_id, odc_start_time, odc_end_time),
                )
                log.debug("ODC Executed SQL: {}".format(odc_cursor.query.decode()))
                log.info("ODC query returned: {} rows".format(odc_cursor.rowcount))
                for row in odc_cursor:
                    datasets.append(row)
    except Exception as e:
        raise e
    finally:
        if odc_conn is not None:
            odc_conn.close()
    return datasets


def query_stepped(connection_parameters, product_id, execution_date, steps):
    """Query odc progressively until a result is returned"""

    odc_conn = None
    results = []
    try:
        # open the connection to the AWS ODC and get a cursor
        with psycopg2.connect(**connection_parameters) as odc_conn:
            with odc_conn.cursor() as odc_cursor:

                # Loop through the time_delta list until we get some data back. Prevents returning a huge amount of data unecessarily from ODC.
                for days_previous in steps:

                    # caluclate a start and end time for the AWS ODC query
                    end_time = execution_date
                    start_time = end_time - timedelta(days=days_previous)

                    # extact a processing and acquisition timestamps from AWS for product and timerange, print logs of query and row count
                    odc_cursor.execute(
                        SQL_QUERY[product_id],
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
                        parent_id,
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
