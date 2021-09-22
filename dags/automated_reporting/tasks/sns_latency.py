"""
Task to query AWS SQS with supplied `product_name` and insert a summary of latest timestamps into reporting DB
"""
import logging

from automated_reporting.utilities import helpers
from automated_reporting.databases import reporting_db

log = logging.getLogger("airflow.task")


def task(rep_conn, next_execution_date, pipeline, product_id, **kwargs):
    """
    Task to query reporting DB SNS table with supplied `product_name`
    and insert a summary of latest timestamps into reporting DB
    """
    # Correct issue with running at start of scheduled period
    execution_date = next_execution_date

    # Convert pendulum to python datetime to make stripping timezone possible
    execution_date = helpers.python_dt(execution_date)

    log.info("Starting Task for: {}@{}".format(product_id, execution_date.isoformat()))

    # New query for latest processing time
    # New query for latest sat acq time
    results = reporting_db.read_sns_currency(rep_conn, pipeline)

    # This is the case that no data was found for any of the time periods specified
    if results["latest_processing"] == None or results["latest_sat_acq"] == None:
        log.error("Unable to find data in SNS reporting table")
        return None

    # Log success
    log.info("Latest Satellite Acquisition Time: {}".format(results["latest_sat_acq"]))
    log.info("Latest Processing Time Stamp: {}".format(results["latest_processing"]))

    # Insert latest processing and satellite acquisition time for current execution time into reporting database
    # for landsat.dervivative data the table is not TZ aware acq_date and processing_date are in UTC, last_updated is in AEST.
    reporting_db.insert_latency(
        rep_conn,
        product_id,
        results["latest_sat_acq"],
        results["latest_processing"],
        execution_date,
    )

    log.info("Completed latency for {}".format(product_id))
    return None
