"""
# Completeness metric on CaRSA nrt products: AWS ODC/Sentinel Catalog -> AIRFLOW -> Reporting DB

This DAG extracts latest timestamp values for a list of products in AWS ODC. It:
 * Checks relavent table and columns are present in reporting DB.
 * Downloads latest product list from Sentinel API (Copernicus).
 * Downloads a list of tiles in AOI from S3.
 * Connects to AWS ODC and downloads products list.
 * Iterates through tile list and computes completeness for each.
 * Inserts results into reporting DB [TODO].

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
from automated_reporting.sql import SELECT_BY_PRODUCT_LIST_AND_TIME_RANGE
from automated_reporting.helpers import python_dt


log = logging.getLogger("airflow.task")

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt(2021, 5, 1, tzinfo=timezone.utc),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": True,
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

        s2_inventory = []
        start_time = dt.now()

        # make a first api call with a zero offset
        resp = get(format_url(0))
        if resp.ok:

            # start a list of responses
            responses = [resp]

            # use count from first response to build a list of urls for multi-threaded download
            count = int(resp.json()["feed"]["opensearch:totalResults"])
            log.info("Downloading: {}".format(count))
            urls = [format_url(offset) for offset in range(100, count, 100)]

            # populate responses list with a multithreaded download
            with futures.ThreadPoolExecutor(max_workers=20) as executor:
                res = executor.map(get, urls)
                responses += list(res)

            # check responses and extract result in s2_inventory list
            for resp in responses:
                if resp.ok:
                    data = resp.json()["feed"]
                    for entry in data["entry"]:
                        row = {
                            "uuid": entry["id"],
                            "granule_id": get_entry_val(
                                entry, "str", "granuleidentifier"
                            ),
                            "tile_id": get_entry_val(entry, "str", "tileid"),
                        }
                        s2_inventory.append(row)
                else:
                    raise Exception("Sentinel API Failed: {}".format(resp.status_code))
            log.info("Downloaded: {}".format(len(s2_inventory)))

            # check that the inventory list is the same length as the expected count
            if count != len(s2_inventory):
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
        aoi_tiles = s3_hook.read_key(
            "aus_aoi_tile.txt", bucket_name="automated-reporting-airflow"
        ).splitlines()
        log.info("Downloaded AOI tile list: {} tiles found".format(len(aoi_tiles)))

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
        odc_products = []
        for row in odc_cursor:
            id, indexed_time, granule_id, tile_id, sat_acq_ts, processing_ts = row
            row = {
                "uuid": id,
                "granule_id": granule_id,
                "tile_id": tile_id,
                "center_dt": sat_acq_ts,
                "processing_dt": processing_ts,
            }
            odc_products.append(row)

        ###########
        ### Compute completeness and latency for every tile in AOI
        ###########
        log.info("Computing completeness")
        output = list()
        for tile_id in aoi_tiles:
            t_s2_inventory = list(
                filter(lambda x: x["tile_id"] == tile_id, s2_inventory)
            )
            t_odc_products = list(
                filter(lambda x: x["tile_id"] == tile_id, odc_products)
            )
            missing = [
                x["uuid"]
                for x in t_s2_inventory
                if x["uuid"] not in [y["uuid"] for y in t_odc_products]
            ]
            latest_sat_acq_time = None
            latest_processing_time = None
            if t_odc_products:
                latest_sat_acq_time = max(t_odc_products, key=lambda x: x["center_dt"])[
                    "center_dt"
                ]
                latest_processing_time = max(
                    t_odc_products, key=lambda x: x["processing_dt"]
                )["processing_dt"]
            t_output = {
                "tile_id": tile_id,
                "inventory": len(t_s2_inventory),
                "missing": len(missing),
                "total": len(t_odc_products),
                "latest_sat_acq_time": latest_sat_acq_time,
                "latest_processing_time": latest_processing_time,
                "missing_uuids": ", ".join(missing),
            }
            output.append(t_output)

        total_inventory = sum([x["inventory"] for x in output])
        total_missing = sum([x["missing"] for x in output])
        total_products = sum([x["total"] for x in output])

        log.info("Completeness complete")
        log.info("Total inventory: {}".format(total_inventory))
        log.info("Total missing: {}".format(total_missing))
        log.info("Total products: {}".format(total_products))

        ###########
        ### Insert completeness into reporting DB
        ###########
        log.info(
            "Inserting completeness output to reporting DB: {} records".format(
                len(output)
            )
        )
        # rep_pg_hook = PostgresHook(postgres_conn_id=DB_REP_WRITER_CONN)

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
        "aoi_polygon": "POLYGON((147.00 -44.93, 161.66 -32.15, 161.24 -16.65, 145.16 -8.17, \
            119.67 -11.63, 111.24 -22.15, 113.96 -36.60, 147.00 -44.93))",
        "producttype": "S2MSI1C",
        "days": 30,
    }

    compute_sentinel_completness = PythonOperator(
        task_id="compute_sentinel_completeness",
        python_callable=sentinel_completeness,
        op_kwargs=op_kwargs,
        provide_context=True,
    )

    # check_db >> compute_sentinel_completness
    compute_sentinel_completness
