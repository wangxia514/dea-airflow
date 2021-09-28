"""
Common completeness functions
"""
import logging

from automated_reporting.utilities import helpers

log = logging.getLogger("airflow.task")


class Expected:
    """
    Storage class for an Expected dataset
    """

    def __init__(self, dataset_id, region_id, center_dt=None):
        self.dataset_id = dataset_id
        self.region_id = region_id
        self.center_dt = center_dt


class Actual:
    """
    Storage class for an Actual dataset
    """

    def __init__(
        self, dataset_id, parent_id, region_id, center_dt=None, processing_dt=None
    ):
        self.dataset_id = dataset_id
        self.region_id = region_id
        self.parent_id = parent_id
        self.center_dt = center_dt
        self.processing_dt = processing_dt


def compute_completeness(expected_datasets, actual_datasets, regions_list):
    """Main entry point for this module"""
    region_results = calculate_metrics_for_all_regions(
        expected_datasets, actual_datasets, regions_list
    )
    summary_results = calculate_summary_stats(region_results)
    return summary_results, region_results


def log_results(sensor, summary, output):
    """log a results list to Airflow logs"""

    # log summary completeness and latency
    log.info("{} Completeness complete".format(sensor))
    log.info("{} Total expected: {}".format(sensor, summary["expected"]))
    log.info("{} Total missing: {}".format(sensor, summary["missing"]))
    log.info("{} Total actual: {}".format(sensor, summary["actual"]))
    log.info("{} Total completeness: {}".format(sensor, summary["completeness"]))
    log.info("{} Latest Sat Acq Time: {}".format(sensor, summary["latest_sat_acq_ts"]))
    log.info(
        "{} Latest Processing Time: {}".format(sensor, summary["latest_processing_ts"])
    )
    # log region level completeness and latency
    for record in output:
        log.debug(
            "{} - {} - {}:{}:{}".format(
                sensor,
                record["region_id"],
                record["expected"],
                record["actual"],
                record["missing"],
            )
        )
        # log missing granule ids for each tile
        for scene_id in record["missing_ids"]:
            log.debug("    Missing:{}".format(scene_id))


def filter_datasets_to_region(datasets, region_id):
    """Filter odc products to the relavent region"""
    return list(filter(lambda x: x.region_id == region_id, datasets))


def get_expected_ids_missing_in_actual(r_expected_datasets, r_actual_datasets):
    """return list of granule_ids in expected, that are missing in actual, for region"""
    return list(
        set([x.dataset_id for x in r_expected_datasets])
        - set([y.parent_id for y in r_actual_datasets])
    )


def get_datasets_in_expected_and_actual(r_expected_datasets, r_actual_datasets):
    """return a list of products that are in both expected and actual lists, for region"""
    actual_ids = list(
        set([x.dataset_id for x in r_expected_datasets])
        & set([y.parent_id for y in r_actual_datasets])
    )
    return list(filter(lambda x: x.parent_id in actual_ids, r_actual_datasets))


def calculate_metric_for_region(r_expected_datasets, r_actual_datasets):
    """calculate completeness and currency for a single region"""

    # make a list of granule_ids in the expected list, not in not in actual list, for this region
    missing_ids = get_expected_ids_missing_in_actual(
        r_expected_datasets, r_actual_datasets
    )

    # filter the actual products list for region to those in expected products for region
    actual_datasets = get_datasets_in_expected_and_actual(
        r_expected_datasets, r_actual_datasets
    )

    # get latest sat_acq_time and latest_processing_time from odc list for this tile
    latest_sat_acq_time = None
    latest_processing_time = None

    if actual_datasets:
        # take latest sat_acq_time from expected record, if not in actual record e.g. s3 listing
        for actual_dataset in actual_datasets:
            if not actual_dataset.center_dt:
                expected_dataset = [
                    d
                    for d in r_expected_datasets
                    if d.dataset_id == actual_dataset.parent_id
                ][0]
                actual_dataset.center_dt = expected_dataset.center_dt

        latest_sat_acq_time = max(actual_datasets, key=lambda x: x.center_dt).center_dt

        latest_processing_time = max(
            actual_datasets, key=lambda x: x.processing_dt
        ).processing_dt

    # calculate expected, actual, missing and completeness
    expected = len(r_expected_datasets)
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


def calculate_metrics_for_all_regions(expected_datasets, actual_datasets, regions_list):
    """calculate completeness and latency for every region in AOI"""

    output = list()

    # loop through each tile and compute completeness and latency
    for region in regions_list:

        # create lists of products for expected and actual, filtered to this tile
        r_expected_datasets = filter_datasets_to_region(expected_datasets, region)
        r_actual_datasets = filter_datasets_to_region(actual_datasets, region)

        # calculate completness and latency for this region
        t_output = calculate_metric_for_region(r_expected_datasets, r_actual_datasets)

        # add the metrics result to output_list
        t_output["region_id"] = region
        output.append(t_output)

    return output


def calculate_summary_stats(output):
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


def generate_db_writes(product_id, summary, summary_region, output, execution_date):
    """Generate a list of db writes from a results list"""

    execution_date = helpers.python_dt(execution_date)

    db_completeness_writes = []
    # append summary stats to output list
    db_completeness_writes.append(
        [
            summary_region,
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


def s2_region_from_id(id):
    """S2 region code from identifier"""
    parts = id.split("_")
    return parts[5][1:]


def map_s2_sns_to_actual(datasets):
    """convert list of sns records into Actual objects"""
    actual_datasets = list()
    for dataset in datasets:
        actual_datasets.append(
            Actual(
                dataset_id=dataset.get("id"),
                parent_id=dataset.get("id"),
                region_id=s2_region_from_id(dataset.get("id")),
                center_dt=dataset.get("sat_acq_time"),
                processing_dt=dataset.get("processing_time"),
            )
        )
    return actual_datasets


def map_s2_odc_to_actual(datasets):
    """convert list of odc records into Actual objects"""
    actual_datasets = list()
    for dataset in datasets:
        actual_datasets.append(
            Actual(
                dataset_id=dataset.get("granule_id"),
                parent_id=dataset.get("parent_id"),
                region_id=dataset.get("tile_id"),
                center_dt=dataset.get("satellite_acquisition_time"),
                processing_dt=dataset.get("processing_time"),
            )
        )
    return actual_datasets


def map_usgs_odc_to_actual(datasets):
    """convert list of odc records into Actual objects"""
    actual_datasets = list()
    for dataset in datasets:
        actual_datasets.append(
            Actual(
                dataset_id=dataset.get("granule_id"),
                parent_id=dataset.get("parent_id"),
                region_id="{}_{}".format(
                    dataset.get("tile_id")[0:3], dataset.get("tile_id")[3:6]
                ),
                center_dt=dataset.get("satellite_acquisition_time"),
                processing_dt=dataset.get("processing_time"),
            )
        )
    return actual_datasets


def map_usgs_acqs_to_expected(datasets):
    """convert list of M2M acquisition records into Expected objects"""
    expected_datasets = list()
    for dataset in datasets:
        expected_datasets.append(
            Expected(
                dataset_id=dataset.get("scene_id"),
                region_id="{}_{}".format(
                    dataset.get("wrs_path"), dataset.get("wrs_row")
                ),
                center_dt=dataset.get("sat_acq"),
            )
        )
    return expected_datasets


def map_s2_acq_to_expected(datasets, use_identifier=False):
    """convert list of Copernicus API records into Expected objects"""
    expected_datasets = list()
    for dataset in datasets:
        expected_datasets.append(
            Expected(
                dataset_id=dataset.get("identifier")
                if use_identifier
                else dataset.get("granule_id"),
                region_id=dataset.get("region_id"),
            )
        )
    return expected_datasets


def map_usgs_s3_to_actual(datasets):
    """convert list of M2M acquisition records into Expected objects"""
    expected_datasets = list()
    for dataset in datasets:
        expected_datasets.append(
            Actual(
                dataset_id=dataset.get("scene_id"),
                parent_id=dataset.get("scene_id"),
                region_id="{}_{}".format(
                    dataset.get("scene_id")[3:6], dataset.get("scene_id")[6:9]
                ),
                processing_dt=dataset.get("last_updated"),
            )
        )
    return expected_datasets


def get_xcom_summary(summary, product_code):
    """
    Reformats the output of completness task to make it compatiable with xcom
    """
    summary_out = summary.copy()
    summary_out["latest_sat_acq_ts"] = (
        summary_out["latest_sat_acq_ts"].isoformat()
        if summary_out["latest_sat_acq_ts"]
        else None
    )
    summary_out["latest_processing_ts"] = (
        summary_out["latest_processing_ts"].isoformat()
        if summary_out["latest_processing_ts"]
        else None
    )
    summary_out["product_code"] = product_code
    return summary_out
