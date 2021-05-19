"""
# Completeness metric on CaRSA nrt products: AWS ODC/Sentinel Catalog -> AIRFLOW -> Reporting DB

This DAG extracts latest timestamp values for a list of products in AWS ODC. It:
 * Checks relavent table and columns are present in reporting DB.
 * Downloads latest product list from Sentinel API (Copernicus).
 * Downloads a list of tiles in AOI from S3.
 * Connects to AWS ODC and downloads products list.
 * Iterates through tile list and computes completeness for each.
 * Inserts results into reporting DB.

"""
import logging
import requests
from concurrent import futures
from datetime import datetime as dt
from datetime import timedelta, timezone

from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.hooks.postgres_hook import PostgresHook
from airflow.hooks.S3_hook import S3Hook
from airflow.models import Variable

from infra.connections import DB_ODC_READER_CONN, DB_REP_WRITER_CONN, S3_REP_CONN
from infra.variables import COP_API_REP_CREDS

from automated_reporting.tasks import check_db_schema
from automated_reporting.schemas import COMPLETENESS_SCHEMA
from automated_reporting.sql import (
    SELECT_BY_PRODUCT_LIST_AND_TIME_RANGE,
    INSERT_COMPLETENESS,
    INSERT_COMPLETENESS_MISSING,
)
from automated_reporting.helpers import python_dt
from automated_reporting.aoi import AOI_POLYGON


log = logging.getLogger("airflow.task")

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt(2021, 5, 15, tzinfo=timezone.utc),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "rep_nrt_completeness",
    description="Completeness metric on Sentinel nrt products: AWS ODC/Sentinel Catalog \
        -> AIRFLOW -> Reporting DB",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval=timedelta(minutes=15),
)

with dag:

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
            latest_processing_time = max(
                actual_products, key=lambda x: x["processing_dt"]
            )["processing_dt"]

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

    def calculate_metrics_for_all_regions(aoi_list, expected_products, actual_products):
        """calculate completeness and latency for every region in AOI"""

        output = list()

        # loop through each tile and compute completeness and latency
        for region in aoi_list:

            # create lists of products for expected and actual, filtered to this tile
            r_expected_products = filter_products_to_region(expected_products, region)
            r_actual_products = filter_products_to_region(actual_products, region)

            # calculate completness and latency for this region
            t_output = calculate_metric_for_region(
                r_expected_products, r_actual_products
            )

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
        sat_acq_time_list = list(
            filter(lambda x: x["latest_sat_acq_ts"] != None, output)
        )
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

    # Task callable
    def sentinel_completeness(execution_date, days, producttype, aoi_polygon, **kwargs):
        """
        Task to compute Sentinel L1 completeness
        """

        execution_date = python_dt(execution_date)

        ###########
        ### Query Copernicus API for for all S2 L1 products for last X days
        ###########
        copernicus_api_creds = Variable.get(COP_API_REP_CREDS, deserialize_json=True)

        # base Copernicus API url and query, needs query arguments inserted
        cop_url = 'https://scihub.copernicus.eu/dhus/search?q=ingestiondate:[{} TO {}] AND \
            producttype:{} AND footprint:"Intersects({})"&start={}&rows=100&format=json'

        # gets dates in a format suitable for Copernicus API
        cop_start_time = (execution_date - timedelta(days=days)).astimezone(
            tz=timezone.utc
        ).replace(tzinfo=None).isoformat() + "Z"
        cop_end_time = (
            execution_date.astimezone(tz=timezone.utc).replace(tzinfo=None).isoformat()
            + "Z"
        )

        log.info(
            "Querying Copernicus API between {} - {} for {}".format(
                cop_start_time, cop_end_time, producttype
            )
        )

        ### Helper functions
        def get(url):
            """
            Perform a GET to copernicus api for paged inventory data
            """
            return requests.get(
                url,
                auth=(copernicus_api_creds["user"], copernicus_api_creds["password"]),
            )

        def format_url(offset=0):
            """
            Format url with query arguments
            """
            return cop_url.format(
                cop_start_time, cop_end_time, producttype, aoi_polygon, offset
            )

        def get_entry_val(entry, data_type, name):
            """
            Extract a value from entry section of response
            """
            for val in entry[data_type]:
                if val["name"] == name:
                    return val["content"]
            return None

        expected_products = []
        start_time = dt.now()

        # make a first api call with a zero offset
        resp = get(format_url(0))
        if resp.ok:

            # start a list of responses
            responses = [resp]

            # use count from first response to build a list of urls for
            # multi-threaded download
            count = int(resp.json()["feed"]["opensearch:totalResults"])
            log.info("Downloading: {}".format(count))
            urls = [format_url(offset) for offset in range(100, count, 100)]

            # populate responses list with a multithreaded download
            with futures.ThreadPoolExecutor(max_workers=20) as executor:
                res = executor.map(get, urls)
                responses += list(res)

            # check responses and extract result in expected_products list
            for resp in responses:
                if resp.ok:
                    data = resp.json()["feed"]
                    if type(data["entry"]) == dict:
                        data["entry"] = [data["entry"]]
                    for entry in data["entry"]:
                        row = {
                            "uuid": entry["id"],
                            "granule_id": get_entry_val(
                                entry, "str", "granuleidentifier"
                            ),
                            "region_id": get_entry_val(entry, "str", "tileid"),
                        }
                        expected_products.append(row)
                else:
                    raise Exception("Sentinel API Failed: {}".format(resp.status_code))
            log.info("Downloaded: {}".format(len(expected_products)))

            # check that the inventory list is the same length as the expected count
            if count != len(expected_products):
                raise Exception("Sentinel API Failed: products missing from download")
        else:
            raise Exception("Sentinel API Failed: {}".format(resp.status_code))

        log.info(
            "Copernicus API download completed in {} seconds".format(
                (dt.now() - start_time).total_seconds()
            )
        )

        ###########
        ### Get a optimised tile list of AOI from S3
        ###########
        s3_hook = S3Hook(aws_conn_id=S3_REP_CONN)
        aoi_list = s3_hook.read_key(
            "aus_aoi_tile.txt", bucket_name="automated-reporting-airflow"
        ).splitlines()
        log.info("Downloaded AOI tile list: {} tiles found".format(len(aoi_list)))

        ###########
        ### Query ODC for all S2 L1 products for last 30 days
        ###########

        odc_pg_hook = PostgresHook(postgres_conn_id=DB_ODC_READER_CONN)

        # caluclate a start and end time for the AWS ODC query
        odc_start_time = execution_date - timedelta(days=days)
        odc_end_time = execution_date
        log.info(
            "Querying Sentinel/Copernicus Inventory between {} - {}".format(
                start_time.isoformat(), odc_end_time.isoformat()
            )
        )
        # extact a processing and acquisition timestamps from AWS for product and timerange,
        # print logs of query and row count

        # open the connection to the AWS ODC and get a cursor
        odc_cursor = odc_pg_hook.get_conn().cursor()
        odc_cursor.execute(
            SELECT_BY_PRODUCT_LIST_AND_TIME_RANGE,
            ("s2a_nrt_granule", "s2b_nrt_granule", odc_start_time, odc_end_time),
        )
        log.debug("ODC Executed SQL: {}".format(odc_cursor.query.decode()))
        log.info("ODC query returned: {} rows".format(odc_cursor.rowcount))

        # if nothing is returned in the given timeframe, loop again and go back further in time
        if odc_cursor.rowcount == 0:
            raise Exception("ODC query error, no data returned")

        # Find the latest values for sat_acq and processing in the returned rows by updating
        # latest_sat_acq_ts and latest_processing_ts
        actual_products = []
        for row in odc_cursor:
            id, indexed_time, granule_id, region_id, sat_acq_ts, processing_ts = row
            row = {
                "uuid": id,
                "granule_id": granule_id,
                "region_id": region_id,
                "center_dt": sat_acq_ts,
                "processing_dt": processing_ts,
            }
            actual_products.append(row)

        ###########
        ### Compute completeness and latency for every tile in AOI
        ###########

        log.info("Computing completeness")

        output = calculate_metrics_for_all_regions(
            aoi_list, expected_products, actual_products
        )

        # log tile level completeness and latency
        for record in output:
            log.info(
                "{} - {}:{}:{}".format(
                    record["region_id"],
                    record["expected"],
                    record["actual"],
                    record["missing"],
                )
            )
            # log missing granule ids for each tile
            for product_id in record["missing_ids"]:
                log.info("    Missing:{}".format(product_id))

        # calculate summary stats for whole of AOI
        summary = calculate_summary_stats_for_aoi(output)

        # log summary completenss and latency
        log.info("Completeness complete")
        log.info("Total expected: {}".format(summary["expected"]))
        log.info("Total missing: {}".format(summary["missing"]))
        log.info("Total actual: {}".format(summary["actual"]))
        log.info("Total completeness: {}".format(summary["completeness"]))
        log.info("Latest Sat Acq Time: {}".format(summary["latest_sat_acq_ts"]))
        log.info("Latest Processing Time: {}".format(summary["latest_processing_ts"]))

        ###########
        ### Insert completeness into reporting DB
        ###########
        log.info(
            "Inserting completeness output to reporting DB: {} records".format(
                len(output)
            )
        )
        # get a reporting database connection and cursor
        rep_pg_hook = PostgresHook(postgres_conn_id=DB_REP_WRITER_CONN)
        rep_conn = rep_pg_hook.get_conn()
        rep_cursor = rep_conn.cursor()
        # insert summary metrics
        rep_cursor.execute(
            INSERT_COMPLETENESS,
            (
                "all_s2",
                summary["completeness"],
                summary["expected"],
                summary["actual"],
                "esa_s2_msi_level1c",
                summary["latest_sat_acq_ts"],
                summary["latest_processing_ts"],
                execution_date,
            ),
        )
        for record in output:
            rep_cursor.execute(
                INSERT_COMPLETENESS,
                (
                    record["region_id"],
                    record["completeness"],
                    record["expected"],
                    record["actual"],
                    "esa_s2_msi_level1c",
                    record["latest_sat_acq_ts"],
                    record["latest_processing_ts"],
                    execution_date,
                ),
            )
            log.debug("Reporting Executed SQL: {}".format(rep_cursor.query.decode()))
            last_id = rep_cursor.fetchone()[0]
            for missing_id in record["missing_ids"]:
                rep_cursor.execute(
                    INSERT_COMPLETENESS_MISSING, (last_id, missing_id, execution_date)
                )
                log.debug(
                    "Reporting Executed SQL: {}".format(rep_cursor.query.decode())
                )
        rep_conn.commit()
        return None

    ## Tasks
    check_db = PythonOperator(
        task_id="check_db_schema",
        python_callable=check_db_schema,
        op_kwargs={
            "expected_schema": COMPLETENESS_SCHEMA,
            "connection_id": DB_REP_WRITER_CONN,
        },
    )

    op_kwargs = {
        "aoi_polygon": AOI_POLYGON,
        "producttype": "S2MSI1C",
        "days": 30,
    }

    compute_sentinel_completeness = PythonOperator(
        task_id="compute_sentinel_completeness",
        python_callable=sentinel_completeness,
        op_kwargs=op_kwargs,
        provide_context=True,
    )

    check_db >> compute_sentinel_completeness
