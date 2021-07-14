"""
Task for s2 completeness calculations
"""
import logging

from automated_reporting.utilities import helpers
from automated_reporting.utilities import copernicus_api
from automated_reporting.databases import odc_db, reporting_db

log = logging.getLogger("airflow.task")


def filter_products_to_region(products, region_id):
    """Filter odc products to the relavent region"""
    return list(filter(lambda x: x["region_id"] == region_id, products))


def get_expected_ids_missing_in_actual(r_expected_products, r_actual_products):
    """return list of granule_ids in expected, that are missing in actual, for region"""
    return list(
        set([x["granule_id"] for x in r_expected_products])
        - set([y["granule_id"] for y in r_actual_products])
    )


def get_products_in_expected_and_actual(r_expected_products, r_actual_products):
    """return a list of products that are in both expected and actual lists, for region"""
    actual_ids = list(
        set([x["granule_id"] for x in r_expected_products])
        & set([y["granule_id"] for y in r_actual_products])
    )
    return list(filter(lambda x: x["granule_id"] in actual_ids, r_actual_products))


def calculate_metric_for_region(r_expected_products, r_actual_products):
    """calculate completeness and latency for a single region"""

    # make a list of granule_ids in the expected list, not in not in actual list, for this region
    missing_ids = get_expected_ids_missing_in_actual(
        r_expected_products, r_actual_products
    )

    # filter the actual products list for region to those in expected products for region
    actual_products = get_products_in_expected_and_actual(
        r_expected_products, r_actual_products
    )

    # get latest sat_acq_time and latest_processing_time from odc list for this tile
    latest_sat_acq_time = None
    latest_processing_time = None

    if actual_products:
        latest_sat_acq_time = max(actual_products, key=lambda x: x["center_dt"])[
            "center_dt"
        ]
        latest_processing_time = max(actual_products, key=lambda x: x["processing_dt"])[
            "processing_dt"
        ]

    # calculate expected, actual, missing and completeness
    expected = len(r_expected_products)
    missing = len(missing_ids)
    actual = expected - missing
    # if there are no tiles expected show completeness as None/null
    if expected > 0:
        completeness = (float(actual) / float(expected)) * 100
    else:
        completeness = None

    # add a dictionary representing this tile to the main output list
    r_output = {
        "completeness": completeness,
        "expected": expected,
        "missing": missing,
        "actual": actual,
        "latest_sat_acq_ts": latest_sat_acq_time,
        "latest_processing_ts": latest_processing_time,
        "missing_ids": missing_ids,
    }
    return r_output


def filter_expected_to_sensor(expected_products, sensor):
    """filter expected products on 'sensor' key"""
    return [p for p in expected_products if p["sensor"] == sensor]


def calculate_metrics_for_all_regions(aoi_list, expected_products, actual_products):
    """calculate completeness and latency for every region in AOI"""

    output = list()

    # loop through each tile and compute completeness and latency
    for region in aoi_list:

        # create lists of products for expected and actual, filtered to this tile
        r_expected_products = filter_products_to_region(expected_products, region)
        r_actual_products = filter_products_to_region(actual_products, region)

        # calculate completness and latency for this region
        t_output = calculate_metric_for_region(r_expected_products, r_actual_products)

        # add the metrics result to output_list
        t_output["region_id"] = region
        output.append(t_output)

    return output


def calculate_summary_stats_for_aoi(output):
    """calculate summary stats for whole of AOI based on output from each region"""

    summary = dict()
    # get completeness for whole of aoi
    summary["expected"] = sum([x["expected"] for x in output])
    summary["missing"] = sum([x["missing"] for x in output])
    summary["actual"] = sum([x["actual"] for x in output])
    if summary["expected"] > 0:
        summary["completeness"] = completeness = (
            float(summary["actual"]) / float(summary["expected"])
        ) * 100
    else:
        summary["completeness"] = None

    # get latency for whole of AOI
    summary["latest_sat_acq_ts"] = None
    sat_acq_time_list = list(filter(lambda x: x["latest_sat_acq_ts"] != None, output))
    if sat_acq_time_list:
        summary["latest_sat_acq_ts"] = max(
            sat_acq_time_list,
            key=lambda x: x["latest_sat_acq_ts"],
        )["latest_sat_acq_ts"]

    # get latency for whole of AOI
    summary["latest_processing_ts"] = None
    processing_time_list = list(
        filter(lambda x: x["latest_processing_ts"] != None, output)
    )
    if processing_time_list:
        summary["latest_processing_ts"] = max(
            processing_time_list,
            key=lambda x: x["latest_processing_ts"],
        )["latest_processing_ts"]

    return summary


def log_results(sensor, summary, output):
    """log a resulkts list to Airflow logs"""

    # log summary completeness and latency
    log.info("{} Completeness complete".format(sensor.upper()))
    log.info("{} Total expected: {}".format(sensor.upper(), summary["expected"]))
    log.info("{} Total missing: {}".format(sensor.upper(), summary["missing"]))
    log.info("{} Total actual: {}".format(sensor.upper(), summary["actual"]))
    log.info(
        "{} Total completeness: {}".format(sensor.upper(), summary["completeness"])
    )
    log.info(
        "{} Latest Sat Acq Time: {}".format(
            sensor.upper(), summary["latest_sat_acq_ts"]
        )
    )
    log.info(
        "{} Latest Processing Time: {}".format(
            sensor.upper(), summary["latest_processing_ts"]
        )
    )
    # log region level completeness and latency
    # for record in output:
    #     log.info(
    #         "{} - {} - {}:{}:{}".format(
    #             sensor,
    #             record["region_id"],
    #             record["expected"],
    #             record["actual"],
    #             record["missing"],
    #         )
    #     )
    #     # log missing granule ids for each tile
    #     for scene_id in record["missing_ids"]:
    #         log.info("    Missing:{}".format(scene_id))


def generate_db_writes(sensor, summary, output, execution_date):
    """Generate a list of db writes from a results list"""

    # format a GA standard product_id
    product_id = "ga_{}_msi_ard_c3".format(sensor)

    execution_date = helpers.python_dt(execution_date)

    db_completeness_writes = []
    # append summary stats to output list
    db_completeness_writes.append(
        [
            "all_s2",
            summary["completeness"],
            summary["expected"],
            summary["actual"],
            product_id,
            summary["latest_sat_acq_ts"],
            summary["latest_processing_ts"],
            execution_date,
            [],
        ]
    )
    # append detailed stats for eacgh region to list
    for record in output:
        completeness_record = [
            record["region_id"],
            record["completeness"],
            record["expected"],
            record["actual"],
            product_id,
            record["latest_sat_acq_ts"],
            record["latest_processing_ts"],
            execution_date,
            [],
        ]
        # add a list of missing scene ids to each region_code
        for scene_id in record["missing_ids"]:
            completeness_record[-1].append([scene_id, execution_date])
        db_completeness_writes.append(completeness_record)
    return db_completeness_writes


def streamline_with_copericus_format(product_list):
    """
    Modify the data returned from odc to match that returned from Copernicus to make
    calculations reuseable for different levels.
    """
    copernicus_format = list()
    for product in product_list:
        row = {
            "uuid": product["uuid"],
            "granule_id": product["granule_id"],
            "region_id": product["region_id"],
            "sensor": product["granule_id"][:3].lower(),
        }
        copernicus_format.append(row)
    return copernicus_format


def swap_in_parent(product_list):
    """
    Swap parent_id into granule_id to allow reusing completeness calculation.
    """
    for product in product_list:
        product["granule_id"] = product["parent_id"]
    return product_list


def get_aoi_list():
    file_path = "dags/automated_reporting/aux_data/sentinel2_aoi_list.txt"
    with open(file_path) as f:
        return f.read().splitlines()


# Task callable
def task_wo(execution_date, days, connection_id, **kwargs):
    """
    Task to compute Sentinel2 WO completeness
    """

    # query ODC for for all S2 ARD products for last X days
    expected_products_odc = odc_db.query("s2a_nrt_granule", execution_date, days)
    expected_products_odc += odc_db.query("s2b_nrt_granule", execution_date, days)

    # streamline the ODC results back to match the Copernicus query
    expected_products = streamline_with_copericus_format(expected_products_odc)

    # get a optimised tile list of AOI
    aoi_list = get_aoi_list()
    log.info("Loaded AOI tile list: {} tiles found".format(len(aoi_list)))

    # a list of tuples to store values before writing to database
    db_completeness_writes = []

    # calculate metrics for each s2 sensor/platform and add to output list
    sensor = "ga_s2_wo_3"

    log.info("Computing completeness for: {}".format(sensor))

    # query ODC for all S2 L1 products for last X days
    actual_products = odc_db.query(sensor, execution_date, days)

    # swap granule_id and parent_id
    actual_products = swap_in_parent(actual_products)

    # compute completeness and latency for every tile in AOI
    output = calculate_metrics_for_all_regions(
        aoi_list, expected_products, actual_products
    )

    # calculate summary stats for whole of AOI
    summary = calculate_summary_stats_for_aoi(output)

    # write results to Airflow logs
    log_results(sensor, summary, output)

    # generate the list of database writes for sensor/platform
    db_completeness_writes += generate_db_writes(
        sensor, summary, output, execution_date
    )

    # write records to reporting database
    reporting_db.insert_completeness(connection_id, db_completeness_writes)
    log.info(
        "Inserting completeness output to reporting DB: {} records".format(
            len(db_completeness_writes)
        )
    )

    return None


# Task callable
def task_ard(execution_date, days, connection_id, **kwargs):
    """
    Task to compute Sentinel2 ARD completeness
    """

    # query Copernicus API for for all S2 L1 products for last X days
    expected_products = copernicus_api.query(execution_date, days)

    # get a optimised tile list of AOI
    aoi_list = get_aoi_list()
    log.info("Loaded AOI tile list: {} tiles found".format(len(aoi_list)))

    # a list of tuples to store values before writing to database
    db_completeness_writes = []

    # calculate metrics for each s2 sensor/platform and add to output list
    for sensor in ["s2a", "s2b"]:

        log.info("Computing completeness for: {}".format(sensor))

        # query ODC for all S2 L1 products for last X days
        actual_products = odc_db.query(
            "{}_nrt_granule".format(sensor), execution_date, days
        )

        # filter expected products on sensor (just for completeness between lo and l1)
        filtered_expected_products = filter_expected_to_sensor(
            expected_products, sensor
        )

        # compute completeness and latency for every tile in AOI
        output = calculate_metrics_for_all_regions(
            aoi_list, filtered_expected_products, actual_products
        )

        # calculate summary stats for whole of AOI
        summary = calculate_summary_stats_for_aoi(output)

        # write results to Airflow logs
        log_results(sensor, summary, output)

        # generate the list of database writes for sensor/platform
        db_completeness_writes += generate_db_writes(
            sensor, summary, output, execution_date
        )

    # write records to reporting database
    reporting_db.insert_completeness(connection_id, db_completeness_writes)
    log.info(
        "Inserting completeness output to reporting DB: {} records".format(
            len(db_completeness_writes)
        )
    )

    return None
