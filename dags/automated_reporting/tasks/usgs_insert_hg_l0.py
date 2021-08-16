"""
Task for pulling acquisitions USGS L0/L1 from USGS from APIs and loading into
'High Granlarity' schema of reporting database.
"""
import os
import logging

from automated_reporting.databases import reporting_db_hg

log = logging.getLogger("airflow.task")


def task(acquisitions, rep_conn, **kwargs):
    """
    Task to fetch recent USGS aquisitions and write to reporting database
    """

    # Insert all acquisitions into HG schema of database, get a count of successes (new aquisitions),
    # fail silently on duplicate
    count = reporting_db_hg.insert_usgs_l0(rep_conn, acquisitions)

    log.info("New aquisitions inserted: {}".format(count))

    return None
