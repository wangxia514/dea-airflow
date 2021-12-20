"""
Task for s2 completeness calculations
"""
import logging

from automated_reporting.utilities import helpers
from automated_reporting.utilities import copernicus_api, completeness
from automated_reporting.databases import odc_db, reporting_db

log = logging.getLogger("airflow.task")


def filter_expected_to_sensor(expected_products, sensor):
    """filter expected products on 'sensor' key"""
    return [p for p in expected_products if p["sensor"] == sensor]


# Task callable for ard
def task(
    s2a,
    s2b,
    data_interval_end,
    days,
    rep_conn,
    odc_conn,
    aux_data_path,
    copernicus_api_credentials,
    **kwargs
):
    """
    Task to compute Sentinel2 ARD completeness
    """
    # Correct issue with running at start of scheduled period
    execution_date = data_interval_end

    # query Copernicus API for for all S2 L1 products for last X days
    expected_products = copernicus_api.query(
        execution_date, days, copernicus_api_credentials
    )

    # get a optimised tile list of AOI
    regions_list = helpers.get_aoi_list(aux_data_path, "sentinel2_aoi_list.txt")
    log.info("Loaded AOI regions list: {} found".format(len(regions_list)))

    # a list of tuples to store values before writing to database
    db_completeness_writes = []

    summary_out = dict()

    # calculate metrics for each s2 sensor/platform and add to output list
    for sensor in [s2a, s2b]:

        log.info("Computing completeness for: {}".format(sensor["odc_code"]))

        # query ODC for all S2 L1 products for last X days
        actual_datasets = completeness.map_s2_odc_to_actual(
            odc_db.query(odc_conn, sensor["odc_code"], execution_date, days)
        )

        # filter expected products on sensor (just for completeness between lo and l1)
        expected_datasets = completeness.map_s2_acq_to_expected(
            filter_expected_to_sensor(expected_products, sensor["id"])
        )

        # compute completeness and latency for every tile in AOI
        # calculate summary stats for whole of AOI
        summary, output = completeness.compute_completeness(
            expected_datasets, actual_datasets, regions_list
        )

        summary_out[sensor["id"]] = summary.copy()
        summary_out[sensor["id"]]["latest_sat_acq_ts"] = (
            summary_out[sensor["id"]]["latest_sat_acq_ts"].isoformat()
            if summary_out[sensor["id"]]["latest_sat_acq_ts"]
            else None
        )
        summary_out[sensor["id"]]["latest_processing_ts"] = (
            summary_out[sensor["id"]]["latest_processing_ts"].isoformat()
            if summary_out[sensor["id"]]["latest_processing_ts"]
            else None
        )

        # write results to Airflow logs
        completeness.log_results(sensor["odc_code"], summary, output)

        # generate the list of database writes for sensor/platform
        db_completeness_writes += completeness.generate_db_writes(
            sensor["rep_code"], summary, "all_s2", output, execution_date
        )

    # write records to reporting database
    reporting_db.insert_completeness(rep_conn, db_completeness_writes)
    log.info(
        "Inserting completeness output to reporting DB: {} records".format(
            len(db_completeness_writes)
        )
    )

    return summary_out
