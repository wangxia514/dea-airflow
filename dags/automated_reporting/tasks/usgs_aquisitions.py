"""
Task for pulling acquisitions USGS L0/L1 from USGS from APIs and making them availbale to
subsequent tasks.
"""
import os
import logging

from automated_reporting.utilities import m2m_api

log = logging.getLogger("airflow.task")


def get_aoi_list(aux_data_path, file_name):
    """
    Open an AOI file and read names into Python list
    """
    with open(os.path.join(aux_data_path, file_name)) as f:
        return f.read().splitlines()


def task(product_ids, execution_date, m2m_credentials, aux_data_path, **kwargs):
    """
    Task to fetch recent USGS aquisitions and write to reporting database
    """
    task_output = list()

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

        task_output += results
        log.info("M2M query returned: {}".format(len(results)))

    return task_output
