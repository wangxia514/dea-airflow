"""
Task for inserting latency from the latest completeness record
"""
import logging

from automated_reporting.utilities import helpers
from automated_reporting.databases import reporting_db

log = logging.getLogger("airflow.task")


def task(rep_conn, next_execution_date, completeness_summary, **kwargs):
    """
    Task for inserting latency from the latest completeness record
    """
    # Correct issue with running at start of scheduled period
    execution_date = next_execution_date

    # Convert pendulum to python datetime to make stripping timezone possible
    execution_date = helpers.python_dt(execution_date)

    reporting_db.insert_latency_from_completeness(
        rep_conn, completeness_summary, execution_date
    )
