"""
Task to query AWS ODC with supplied `product_name` and insert a summary of latest timestamps into reporting DB
"""
import logging

from automated_reporting.utilities import helpers
from automated_reporting.databases import odc_db, reporting_db

log = logging.getLogger("airflow.task")


# Task callable
def task(rep_conn, odc_conn, execution_date, product_name, **kwargs):
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

    results = odc_db.query_stepped(
        odc_conn, product_name, execution_date, timedelta_list
    )

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
        log.error(
            "Unable to find data in ODC for last {} days".format(max(timedelta_list))
        )
        return None

    # Log success
    log.info("Latest Satellite Acquisition Time: {}".format(latest_sat_acq_ts))
    log.info("Latest Processing Time Stamp: {}".format(latest_processing_ts))

    # Insert latest processing and satellite acquisition time for current execution time into reporting database
    # for landsat.dervivative data the table is not TZ aware acq_date and processing_date are in UTC, last_updated is in AEST.
    reporting_db.insert_latency(
        rep_conn,
        product_name,
        latest_sat_acq_ts,
        latest_processing_ts,
        execution_date,
    )

    log.info("Completed latency for {}".format(product_name))
    return None
