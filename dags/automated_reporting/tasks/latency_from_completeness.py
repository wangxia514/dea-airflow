"""
Task for inserting latency from the latest completeness record
"""
import logging

from automated_reporting.utilities import helpers
from automated_reporting.databases import reporting_db

log = logging.getLogger("airflow.task")


def task(connection_id, execution_date, **kwargs):
    """
    Task for inserting latency from the latest completeness record
    """

    # Convert pendulum to python datetime to make stripping timezone possible
    execution_date = helpers.python_dt(execution_date)

    latency_results = kwargs["task_instance"].xcom_pull(task_ids="usgs_completeness")
    if latency_results:
        print(latency_results)
        reporting_db.insert_latency_list(connection_id, latency_results, execution_date)
