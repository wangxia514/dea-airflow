"""
Task to calculate USGS NRT completeness using S3 listings and M2M API query
"""
import logging
from datetime import timedelta

from automated_reporting.utilities import helpers, completeness
from automated_reporting.databases import reporting_db_usgs, reporting_db

log = logging.getLogger("airflow.task")


def task(next_execution_date, product, rep_conn, days, aux_data_path, **kwargs):
    """
    Main function
    :return:
    """
    log.info("Starting completness calc for: {}".format(product["rep_code"]))

    # Correct issue with running at start of scheduled period
    execution_date = next_execution_date
    execution_date = helpers.python_dt(execution_date)

    # Get path row list
    regions_list = helpers.get_aoi_list(aux_data_path, "landsat_l1_path_row_list.txt")
    log.info("Loaded AOI regions list: {} found".format(len(regions_list)))

    # Get expected datasets from reporting table of USGS acquisitions
    start_time = execution_date - timedelta(days=days)
    end_time = execution_date
    expected_datasets = completeness.map_usgs_acqs_to_expected(
        reporting_db_usgs.get_m2m_metadata(
            rep_conn, product["acq_code"], start_time, end_time
        )
    )

    # Get actual datasets from S3 Listing
    actual_datasets = completeness.map_usgs_s3_to_actual(
        reporting_db_usgs.get_s3_listing(
            rep_conn, product["s3_code"], start_time, execution_date
        )
    )

    # compute completeness and latency for every tile in AOI
    # calculate summary stats for whole of AOI
    summary, output = completeness.compute_completeness(
        expected_datasets, actual_datasets, regions_list
    )

    # write results to Airflow logs
    completeness.log_results(product["rep_code"], summary, output)

    # generate the list of database writes for sensor/platform
    db_completeness_writes = completeness.generate_db_writes(
        product["rep_code"], summary, "all_ls", output, execution_date
    )

    # write records to reporting database
    reporting_db.insert_completeness(rep_conn, db_completeness_writes)
    log.info(
        "Inserting completeness output to reporting DB: {} records".format(
            len(db_completeness_writes)
        )
    )

    return completeness.get_xcom_summary(summary, product["rep_code"])
