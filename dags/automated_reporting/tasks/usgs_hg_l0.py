"""
Task for pulling acquisitions USGS L0/L1 from USGS from APIs and loading into
'High Granlarity' schema of reporting database.
"""
import os
import logging

from automated_reporting.utilities import m2m_api
from automated_reporting.databases import reporting_db_hg

log = logging.getLogger("airflow.task")


def get_aoi_list(aux_data_path, file_name):
    """
    Open an AOI file and read names into Python list
    """
    with open(os.path.join(aux_data_path, file_name)) as f:
        return f.read().splitlines()


def task(
    execution_date, connection_id, rep_conn, m2m_credentials, aux_data_path, **kwargs
):
    """
    Task to fetch recent USGS aquisitions and write to reporting database
    """
    product_ids = ["landsat_etm_c2_l1", "landsat_ot_c2_l1"]

    for product_id in product_ids:
        log.info("Querying USGS M2M API for new aquisitions: {}".format(product_id))

        results = m2m_api.get(
            dataset=product_id,
            start_time=execution_date,
            days=3,
            credentials=m2m_credentials,
        )

        # Filter to AOI
        # We searched by bounding box, so lets filter further to the optimised AOI lists
        aoi_list = get_aoi_list(aux_data_path, "landsat_l1_path_row_list.txt")
        results = [r for r in results if r["wrs2"] in aoi_list]

        # Log results of M2M query
        for result in results:
            log.debug("{} - {}".format(result["display_id"], result["acq_time"]))
        log.info("M2M query returned: {}".format(len(results)))

        # Attempt to insert all values into database, get a count of successes (new aquisitions)
        count = reporting_db_hg.insert_usgs_l0(rep_conn, results)

        log.info("New aquisitions inserted: {}".format(count))

    return None
