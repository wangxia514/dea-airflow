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
from datetime import datetime as dt
from datetime import timedelta, timezone

from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.hooks.S3_hook import S3Hook

from infra.connections import DB_REP_WRITER_CONN, S3_REP_CONN

from automated_reporting.aux_data import aoi
from automated_reporting.utilities import copernicus_api, s2_completeness
from automated_reporting.databases import schemas, odc_db, reporting_db

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
    "rep_s2_completeness",
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

        # query Copernicus API for for all S2 L1 products for last X days
        expected_products = copernicus_api.query(
            producttype, execution_date, days, aoi_polygon
        )

        # get a optimised tile list of AOI from S3
        s3_hook = S3Hook(aws_conn_id=S3_REP_CONN)
        aoi_list = s3_hook.read_key(
            "aus_aoi_tile.txt", bucket_name="automated-reporting-airflow"
        ).splitlines()
        log.info("Downloaded AOI tile list: {} tiles found".format(len(aoi_list)))

        # a list of tuples to store values before writing to database
        db_completeness_writes = []

        # calculate metrics for each s2 sensor/platform and add to output list
        for sensor in ["s2a", "s2b"]:

            log.info("Computing completeness for: {}".format(sensor))

            # query ODC for all S2 L1 products for last X days
            actual_products = odc_db.query(
                "{}_nrt_granule".format(sensor), execution_date, days
            )

            # compute completeness and latency for every tile in AOI
            output = s2_completeness.calculate_metrics_for_all_regions(
                sensor, aoi_list, expected_products, actual_products
            )

            # calculate summary stats for whole of AOI
            summary = s2_completeness.calculate_summary_stats_for_aoi(output)

            # write results to Airflow logs
            s2_completeness.log_results(sensor, summary, output)

            # generate the list of database writes for sensor/platform
            db_completeness_writes += s2_completeness.generate_db_writes(
                sensor, summary, output, execution_date
            )

        # write records to reporting database
        reporting_db.insert_completeness(db_completeness_writes)
        log.info(
            "Inserting completeness output to reporting DB: {} records".format(
                len(db_completeness_writes)
            )
        )

        return None

    ## Tasks
    check_db = PythonOperator(
        task_id="check_db_schema",
        python_callable=schemas.check_db_schema,
        op_kwargs={
            "expected_schema": schemas.COMPLETENESS_SCHEMA,
            "connection_id": DB_REP_WRITER_CONN,
        },
    )

    op_kwargs = {
        "aoi_polygon": aoi.AOI_POLYGON,
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
