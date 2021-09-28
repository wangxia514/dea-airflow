"""
Task for s2 completeness calculations
"""
import logging

from automated_reporting.databases import reporting_db

log = logging.getLogger("airflow.task")


# Task callable
def task(rep_conn, product_id, **kwargs):
    """
    Task to redundent completeness metrics
    """
    log.info("Expiring completeness for product id: {}".format(product_id))

    removed_count = reporting_db.expire_completeness(rep_conn, product_id)

    log.info("Cleaned: {}".format(removed_count))

    return None
