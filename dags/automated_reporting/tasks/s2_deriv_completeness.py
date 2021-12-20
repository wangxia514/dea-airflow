"""
Task for s2 completeness calculations
"""
import logging

from automated_reporting.utilities import helpers
from automated_reporting.utilities import completeness
from automated_reporting.databases import odc_db, reporting_db

log = logging.getLogger("airflow.task")


def map_odc_to_actual(datasets):
    """convert list of odc records into Actual objects"""
    actual_datasets = list()
    for dataset in datasets:
        actual_datasets.append(
            completeness.Actual(
                dataset_id=dataset.get("granule_id"),
                parent_id=dataset.get("parent_id"),
                region_id=dataset.get("tile_id"),
                center_dt=dataset.get("satellite_acquisition_time"),
                processing_dt=dataset.get("processing_time"),
            )
        )
    return actual_datasets


def map_odc_to_expected(datasets):
    """convert list of odc records into Expected objects"""
    expected_datasets = list()
    for dataset in datasets:
        expected_datasets.append(
            completeness.Expected(
                dataset_id=dataset.get("granule_id"),
                region_id=dataset.get("tile_id"),
                center_dt=dataset.get("satellite_acquisition_time"),
            )
        )
    return expected_datasets


# Task callable for derivatives
def task(
    upstream,
    target,
    data_interval_end,
    days,
    rep_conn,
    odc_conn,
    aux_data_path,
    **kwargs
):
    """
    Task to compute Sentinel2 derivative completeness
    """
    # Correct issue with running at start of scheduled period
    execution_date = data_interval_end

    # query ODC for for all upstream products for last X days
    expected_datasets_odc = list()
    for product_code in upstream:
        expected_datasets_odc += odc_db.query(
            odc_conn, product_code, execution_date, days
        )
    expected_datasets = map_odc_to_expected(expected_datasets_odc)

    # get a optimised tile list of AOI
    regions_list = helpers.get_aoi_list(aux_data_path, "sentinel2_aoi_list.txt")
    log.info("Loaded AOI tile list: {} tiles found".format(len(regions_list)))

    # a list of tuples to store values before writing to database
    db_completeness_writes = []

    log.info("Computing completeness for: {}".format(target))

    # query ODC for all S2 L1 products for last X days
    actual_datasets = map_odc_to_actual(
        odc_db.query(odc_conn, target, execution_date, days)
    )

    # compute completeness and latency for every tile in AOI
    summary, output = completeness.compute_completeness(
        expected_datasets, actual_datasets, regions_list
    )

    # calculate summary stats for whole of AOI
    summary_out = {target: summary.copy()}
    summary_out[target]["latest_sat_acq_ts"] = summary_out[target][
        "latest_sat_acq_ts"
    ].isoformat()
    summary_out[target]["latest_processing_ts"] = summary_out[target][
        "latest_processing_ts"
    ].isoformat()

    # write results to Airflow logs
    completeness.log_results(target, summary, output)

    # generate the list of database writes for sensor/platform
    db_completeness_writes = completeness.generate_db_writes(
        target, summary, "all_s2", output, execution_date
    )

    # write records to reporting database
    reporting_db.insert_completeness(rep_conn, db_completeness_writes)
    log.info(
        "Inserting completeness output to reporting DB: {} records".format(
            len(db_completeness_writes)
        )
    )

    return summary_out
