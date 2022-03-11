"""
Task for pulling acquisitions USGS L0/L1 from USGS from APIs and making them availbale to
subsequent tasks.
"""
import logging

from automated_reporting.utilities import m2m_api, helpers

log = logging.getLogger("airflow.task")


def task(
    product_ids, data_interval_end, m2m_credentials, aux_data_path, days, **kwargs
):
    """
    Task to fetch recent USGS aquisitions and write to reporting database
    """
    # Correct issue with running at start of scheduled period
    execution_date = data_interval_end

    task_output = list()

    for product_id in product_ids:
        log.info("Querying USGS M2M API for new aquisitions: {}".format(product_id))

        results = m2m_api.get(
            dataset=product_id,
            start_time=execution_date,
            days=days,
            credentials=m2m_credentials,
        )

        # Filter to AOI
        # We searched by bounding box, so lets filter further to the optimised AOI lists
        aoi_list = helpers.get_aoi_list(aux_data_path, "landsat_l1_path_row_list.txt")
        results = [r for r in results if r["wrs2"] in aoi_list]

        # Log results of M2M query
        for result in results:
            log.debug("{} - {}".format(result["display_id"], result["acq_time"]))

        task_output += results
        log.info("M2M query returned: {}".format(len(results)))

    return task_output
