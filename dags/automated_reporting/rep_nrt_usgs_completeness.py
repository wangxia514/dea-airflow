"""
# Calculate completeness metric on nrt products: AWS ODC -> AIRFLOW -> Reporting DB

This DAG
 * Connects to USGS Stac API to determine USGS Inventory
 * Inserts data into reporting DB
 * Gets 30 day archive from DB for GA and USGS archives
 * Runs completeness and latency checks
 * Inserts summary completeness and latency reporting data
 * Inserts completeness data for each wrs path row
"""

import logging
from datetime import datetime, timedelta, timezone
import requests
import json
from pathlib import Path
import os

from airflow import DAG
from airflow.configuration import conf
from airflow.utils.dates import days_ago
from airflow.operators.python_operator import PythonOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.hooks.postgres_hook import PostgresHook

from infra.connections import DB_ODC_READER_CONN, DB_REP_WRITER_CONN

# Initialisations

logger = logging.getLogger("airflow.task")

rep_pg_hook = PostgresHook(postgres_conn_id=DB_REP_WRITER_CONN)

default_args = {
    "owner": "James Miller",
    "depends_on_past": False,
    "start_date": datetime(2021, 5, 27, tzinfo=timezone.utc),
    "email": ["james.miller@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": True,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# Initiations for global variables
serviceUrl = "https://landsatlook.usgs.gov/sat-api/collections/landsat-c2l1/items"
collectionCategory = "RT"
bbox = [106, -47, 160, -5]
missions = [
    "LANDSAT_8",
    #    'LANDSAT_7'
]
databaseCompTable = "reporting.completeness"
databaseMissingTable = "reporting.completeness_missing"
databaseStacTable = "landsat.usgs_l1_nrt_c2_stac_listing"
databaseGAS3Table = "landsat.ga_s3_level1_nrt_s3_listing"
utcTimeNow = datetime.now(timezone.utc)

# Set amount of days to look back to
dayRange = 30

# Get UTC datetime now and add one day to ensure nothing is missed
utcTimeTomorrow = datetime.now(timezone.utc) + timedelta(days=1)

# Minus X days
utcDaysAgo = utcTimeNow - timedelta(days=int(dayRange))

# Format dates to example '2020-11-01'
startDate = utcDaysAgo.strftime("%Y-%m-%d")
endDate = utcTimeTomorrow.strftime("%Y-%m-%d")

selectSchema = """SELECT * FROM information_schema.schemata WHERE catalog_name=%s and schema_name=%s;"""
selectTable = """SELECT * FROM information_schema.tables WHERE table_catalog=%s AND table_schema=%s AND table_name=%s;"""
selectColumn = """SELECT * FROM information_schema.columns WHERE table_catalog=%s AND table_schema=%s AND table_name=%s AND column_name=%s;"""
structure = {
    "database": {
        "name": "reporting",
        "schemas": [
            {
                "name": "reporting",
                "tables": [
                    {
                        "name": "completeness",
                        "columns": [
                            {"name": "id"},
                            {"name": "geo_ref"},
                            {"name": "completeness"},
                            {"name": "expected_count"},
                            {"name": "actual_count"},
                            {"name": "product_id"},
                            {"name": "sat_acq_time"},
                            {"name": "processing_time"},
                            {"name": "last_updated"},
                        ],
                    }
                ],
            }
        ],
    }
}

dag = DAG(
    "rep_usgs_completeness_nrt_l1",
    description="DAG for completeness and latency metric on USGS L1 C2 nrt product",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval=timedelta(minutes=120),
)


def db_has_object(rep_cursor, sql, query_args):
    """
    Tests if an SQL query returns any rows, returns boolean
    """
    rep_cursor.execute(sql, query_args)
    if rep_cursor.rowcount == 0:
        return False
    return True


with dag:
    # Task callable
    def check_db_structure():
        """
        Task to check that the schema in reporting db has the correct tables, columns, fields before progressing
        """
        rep_conn = rep_pg_hook.get_conn()
        rep_cursor = rep_conn.cursor()
        database = structure["database"]
        structure_good = True
        for schema in database["schemas"]:
            result = db_has_object(
                rep_cursor, selectSchema, (database["name"], schema["name"])
            )
            if not result:
                structure_good = False
            logger.info(
                "Test database '{}' has schema '{}: {}".format(
                    database["name"], schema["name"], result
                )
            )
            for table in schema["tables"]:
                result = db_has_object(
                    rep_cursor,
                    selectTable,
                    (database["name"], schema["name"], table["name"]),
                )
                if not result:
                    structure_good = False
                logger.info(
                    "Test schema '{}' has table '{}: {}".format(
                        schema["name"], table["name"], result
                    )
                )
                for column in table["columns"]:
                    result = db_has_object(
                        rep_cursor,
                        selectColumn,
                        (
                            database["name"],
                            schema["name"],
                            table["name"],
                            column["name"],
                        ),
                    )
                    if not result:
                        structure_good = False
                    logger.info(
                        "Test table '{}' has column '{}: {}".format(
                            table["name"], column["name"], result
                        )
                    )
        if not structure_good:
            raise Exception("Database structure does not match structure definition")
        return "Database structure check passed"

    def main():
        """
        Main function
        :return:
        """
        logger.info("Starting reporting workflow for Landsat L1 NRT")
        logger.info("Using service URL: {}".format(serviceUrl))

        # Get path row list
        file_path = "dags/automated_reporting/aux_data/landsat_l1_path_row_list.txt"
        wrsPathRowList = landsat_path_row(file_path)
        logger.info("Loaded Path Row Listing")

        for mission in missions:
            logger.info("Checking Stac API {}".format(mission))
            output = landsat_search_stac(serviceUrl, logger, mission)
            stacApiMatrix = collect_stac_api_results(output)
            logger.debug(stacApiMatrix)

            logger.info("Inserting Stac metadata into DB {}".format(mission))
            gen_stac_api_inserts(stacApiMatrix)

            logger.info("Get last 30 days Stac metadata from DB {}".format(mission))
            stacApiData = get_stac_metadata()

            if mission == "LANDSAT_8":
                logger.info("Checking GA S3 Listing {}".format(mission))
                s3List = get_s3_listing("L8C2")
                logger.debug("GA-S3 Listing: - {} - {}".format(mission, s3List))
                productId = "usgs_ls8c_level1_nrt_c2"
            elif mission == "LANDSAT_7":
                logger.info("Checking GA S3 Listing {}".format(mission))
                s3List = get_s3_listing("L7C2")
                logger.debug("GA-S3 Listing: - {} - {}".format(mission, s3List))
                productId = "usgs_ls7e_level1_nrt_c2"

            logger.info("Filtering out data from outside AOI {}".format(mission))
            filteredStacApiData, filteredS3List = filter_aoi(
                wrsPathRowList, stacApiData, s3List
            )

            logger.info("Running completeness metrics for {}".format(mission))
            (
                successCounter,
                missingCounter,
                missingMatrix,
                usgsCount,
                gaCount,
                latestSatAcq,
                pathRowCounterMatrix,
            ) = completeness_comparison_all(
                filteredStacApiData, filteredS3List, wrsPathRowList, logger
            )
            expectedCount = gaCount + missingCounter
            completeness = (gaCount / (gaCount + missingCounter)) * 100
            completenessId = gen_sql_completeness(
                "all_ls",
                completeness,
                expectedCount,
                gaCount,
                productId,
                latestSatAcq,
                "Null",
                utcTimeNow,
            )

            if len(missingMatrix) > 0:
                gen_sql_completeness_missing(completenessId, missingMatrix, utcTimeNow)

            logger.info("***{} MISSION***".format(mission))
            logger.info(
                "Completeness - {}%. Expected Count - {}. Actual Count - {}.".format(
                    completeness, expectedCount, gaCount
                )
            )
            logger.info("Missing Matrix - {}".format(missingMatrix))
            gen_sql_completeness_path_row(
                pathRowCounterMatrix, productId, "Null", "Null", utcTimeNow
            )

            return

    def sendRequest(url, data, logger):
        """
        Send HTTPS Request
        :param url: URL of stac API
        :param data: Search Criteria
        :param logger: Logging
        :return: JSON output
        """
        jsonData = json.dumps(data)
        response = requests.post(url, jsonData)
        logger.debug("Response - {}".format(response))
        output = json.loads(response.text)
        logger.debug("Output - {}".format(output))

        try:
            httpStatusCode = response.status_code
            if httpStatusCode == 404:
                logger.error("404 Not Found")
                exit()
            elif httpStatusCode == 401:
                logger.error("401 Unauthorized")
                exit()
            elif httpStatusCode == 400:
                logger.error("Error Code", httpStatusCode)
                exit()
            elif httpStatusCode == 502:
                logger.error("Internal Server Error", httpStatusCode)
                exit()
        except Exception as e:
            response.close()
            logger.error(e)
            exit()
        response.close()

        return output

    def landsat_search_stac(serviceUrl, logger, mission):
        """
        Conduct the search on the stac api
        :param serviceUrl: Stac API URL
        :param logger:
        :param mission: the mission to search for in the collection
        :return: response from stac API
        """
        searchParameters = {
            "page": 1,
            "limit": 10000,
            "bbox": bbox,
            "query": {
                "landsat:collection_category": {"eq": "{}".format(collectionCategory)},
                "platform": {"eq": "{}".format(mission)},
            },
            "time": "{0}T/{1}T".format(startDate, endDate),
        }
        response = sendRequest(serviceUrl, searchParameters, logger)
        return response

    def collect_stac_api_results(output):
        """
        Collectio STAC API Results
        :param output: The Stac API output
        :return: matrix of relevant results
        """
        returned = int(output["meta"]["returned"])

        stacApiMatrix = [[]]

        for i in range(0, returned):
            stacApiMatrix.append(
                [
                    output["features"][i]["properties"]["landsat:scene_id"],
                    output["features"][i]["properties"]["landsat:wrs_path"],
                    output["features"][i]["properties"]["landsat:wrs_row"],
                    output["features"][i]["properties"]["landsat:collection_category"],
                    output["features"][i]["properties"]["landsat:collection_number"],
                    output["features"][i]["properties"]["datetime"],
                ]
            )

        stacApiMatrix.pop(0)
        return stacApiMatrix

    def completeness_comparison_all(stacApi, s3Listing, wrsPathRowList, logger):
        """
        Compare USGS Stac API against GA S3 Listing. Note logic is based on
        First - what is in USGS index as source of truth - then checking to see if all have been downloaded.
        If there is data showing up missing on Stac - this wont get captured in these statistics
        :param stacApi: Results from Stac API
        :param s3Listing: Results from S3 Listing
        :param wrsPathRowList: List of landsat wrs path rows
        :param logger: logging
        :return: successCounter, missingCounter, missingMatrix, usgsCount, gaCount, latestSatAcq, pathRowCounterMatrix
        """
        successCounter = 0
        missingCounter = 0
        missingMatrix = [[]]
        satAcqList = []

        # Populating matrix with path rows and starting counters at 0
        matrixWidth, matrixHeight = 3, len(wrsPathRowList)
        pathRowCounterMatrix = [
            ["" for x in range(matrixWidth)] for y in range(matrixHeight)
        ]

        for i in range(0, matrixHeight):
            pathRowCounterMatrix[i][0] = wrsPathRowList[i]
            for j in range(1, matrixWidth):
                pathRowCounterMatrix[i][j] = 0

        for scene in stacApi:
            satAcqList.append(scene[5])
            wrsPathRow = "{}_{}".format(scene[1], scene[2])

            # Loop through and add counters to each path-row for usgs index
            for i in range(0, matrixHeight):

                if pathRowCounterMatrix[i][0] == wrsPathRow:
                    pathRowCounterMatrix[i][1] += 1

            # If product has been downloaded by GA
            if scene[0] in s3Listing:

                # Loop through and add counters to each path-row for ga index
                for i in range(0, matrixHeight):

                    if pathRowCounterMatrix[i][0] == wrsPathRow:
                        pathRowCounterMatrix[i][2] += 1

            # Counter for the sum of all wrs-path rows
            if scene[0] in s3Listing:
                successCounter += 1
            else:
                missingCounter += 1
                missingMatrix.append([scene[0], wrsPathRow, scene[5]])

        missingMatrix.pop(0)
        usgsCount = len(stacApi)
        gaCount = len(s3Listing)
        latestSatAcq = max(satAcqList)

        gaCountValidation = 0
        usgsCountValidation = 0
        for row in pathRowCounterMatrix:
            gaCountValidation += row[2]
            usgsCountValidation += row[1]
        logger.info(
            "Count of GA scenes from wrs-path-row:{0}. This should equal total USGS count minus anything missing:"
            "{1}".format(gaCountValidation, (usgsCount - missingCounter))
        )
        logger.info(
            "Count of USGS scenes from wrs-path-row:{0}. This should equal total USGS count:{1}".format(
                usgsCountValidation, usgsCount
            )
        )

        return (
            successCounter,
            missingCounter,
            missingMatrix,
            usgsCount,
            gaCount,
            latestSatAcq,
            pathRowCounterMatrix,
        )

    def landsat_path_row(filePath):
        """
        Get list of path rows from file
        :param filePath: file path of path row list
        :return: wrsPathRowList
        """

        root = Path(conf.get("core", "dags_folder")).parent
        wrsPathRowList = []

        with open(os.path.join(root, filePath)) as f:
            reader = f.readlines()

            for row in reader:
                wrsPathRowList.append(row[0:7])

        return wrsPathRowList

    def filter_aoi(wrsPathRowList, stacApiData, s3List):
        """
        Filter out those outside of AOI
        :param wrsPathRowList:
        :param stacApiData:
        :param s3List:
        :return: filteredStacApiData, filteredS3List
        """

        filteredStacApiData = [[]]
        filteredS3List = []

        for scene in stacApiData:
            wrsPathRow = "{}_{}".format(scene[1], scene[2])
            if wrsPathRow in wrsPathRowList:
                filteredStacApiData.append(scene)

        for sceneId in s3List:
            wrsPathRow = "{}_{}".format(sceneId[0][3:6], sceneId[0][6:9])
            if wrsPathRow in wrsPathRowList:
                filteredS3List.append(sceneId[0])

        filteredStacApiData.pop(0)

        return filteredStacApiData, filteredS3List

    def gen_sql_completeness_path_row(
        pathRowCounterMatrix, productId, satAcqTime, processingTime, lastUpdated
    ):
        """
        Generate and insert execution scripts for wrs path row completeness
        :param pathRowCounterMatrix: Matrix of data
        :param productId: Product Id
        :param satAcqTime: Satelitte Acquisition Time
        :param processingTime: Processing time
        :param lastUpdated: Last updated time of query
        :return:
        """
        conn, cursor = open_cursor()

        for row in pathRowCounterMatrix:
            geoRef = row[0]
            expectedCount = int(row[1])
            actualCount = int(row[2])

            try:
                completeness = (actualCount / expectedCount) * 100

            except:
                # division by zero results in python error
                completeness = 0

            executionStr = """INSERT INTO reporting.completeness (geo_ref, completeness, expected_count,
            actual_count, product_id, sat_acq_time, processing_time, last_updated) VALUES (%s,%s,%s,%s,%s,Null,Null,%s);"""

            params = (
                geoRef,
                float(completeness),
                int(expectedCount),
                int(actualCount),
                productId,
                lastUpdated,
            )

            execute_query(executionStr, params, cursor)

        return conn_commit(conn, cursor)

    def gen_sql_completeness(
        geoRef,
        completeness,
        expectedCount,
        actualCount,
        productId,
        satAcqTime,
        processingTime,
        lastUpdated,
    ):
        """
        Generate the SQL Inserts
        :param geoRef: the wrs path row or region code
        :param completeness: percentage of completeness
        :param expectedCount: the expected count
        :param actualCount: the actual count
        :param productId: the product id
        :param satAcqTime: the satellite acquisition time
        :param processingTime: the processing or download time
        :param lastUpdated: the timestamp of this run
        :return: string to run query
        """
        conn, cursor = open_cursor()

        executionStr = """INSERT INTO reporting.completeness (geo_ref, completeness, expected_count, actual_count, product_id, sat_acq_time,
        processing_time, last_updated) VALUES (%s,%s,%s,%s,%s,%s,Null,%s) RETURNING id;"""

        params = (
            geoRef,
            float(completeness),
            int(expectedCount),
            actualCount,
            productId,
            satAcqTime,
            lastUpdated,
        )

        execute_query(executionStr, params, cursor)

        return conn_commit_return_id(conn, cursor)

    def gen_sql_completeness_missing(completeness_id, missingMatrix, lastUpdated):
        """
        Generate SQL Inserts for missing data
        :param databaseMissingTable:
        :param completeness_id:
        :param missingMatrix:
        :param lastUpdated:
        :return:
        """
        conn, cursor = open_cursor()
        for missing in missingMatrix:
            executionStr = """INSERT INTO reporting.completeness_missing (completeness_id, dataset_id, last_updated)
            VALUES (%s, %s, %s);
            """
            params = int(completeness_id), missing[0], lastUpdated
            execute_query(executionStr, params, cursor)

        return conn_commit(conn, cursor)

    def gen_stac_api_inserts(stacApiMatrix):
        """
        Insert STAC API metadata into DB
        :param stacApiMatrix:
        :return:
        """
        conn, cursor = open_cursor()
        for row in stacApiMatrix:
            executionStr = """INSERT INTO landsat.usgs_l1_nrt_c2_stac_listing (scene_id, wrs_path, wrs_row,
            collection_category, collection_number, sat_acq) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING;"""

            params = (row[0], row[1], row[2], row[3], int(row[4]), row[5])
            execute_query(executionStr, params, cursor)

        return conn_commit(conn, cursor)

    def get_stac_metadata():
        """
        Get last 30 days of stac metadata from DB
        :return: stacAPI data
        """
        executionStr = (
            """SELECT * FROM landsat.usgs_l1_nrt_c2_stac_listing WHERE sat_acq >= %s;"""
        )
        params = (startDate,)
        return data_select(executionStr, params)

    def get_s3_listing(pipeline):
        """
        Get last 30 days of stac metadata from DB
        :param pipeline: Name of pipeline to get data from e.g. L7C2
        :return:
        """
        executionStr = """SELECT scene_id FROM landsat.ga_s3_level1_nrt_s3_listing
        WHERE last_updated >= %s AND pipeline = %s;"""
        params = (startDate, pipeline)
        return data_select(executionStr, params)

    # Open database connection
    def open_cursor():
        """
        Open database connection
        :return: conn, cursor
        """
        conn = rep_pg_hook.get_conn()
        cursor = conn.cursor()
        return conn, cursor

    def execute_query(query, params, cursor):
        """
        Execute Queries
        :param query:
        :param params:
        :param cursor:
        :return:
        """
        cursor.execute(query, params)
        return

    def conn_commit(conn, cursor):
        """
        Commit the queries to DB
        :param conn:
        :param cursor:
        :return:
        """
        try:
            conn.commit()
        except:
            if conn:
                # logger.error("Failed to insert records into DB", error)
                logger.error("Failed to insert records into DB")

        finally:
            if conn:
                cursor.close()
                conn.close()
            return

    def conn_commit_return_id(conn, cursor):
        """
        Commit the queries to DB and return id
        :param conn:
        :param cursor:
        :return:
        """
        try:
            conn.commit()

            try:
                lastId = cursor.fetchone()[0]
            except:
                lastId = []
                pass

        # except (Exception, psycopg2.Error) as error:
        except:
            lastId = []
            if conn:
                # logger.error("Failed to insert records into DB", error)
                logger.error("Failed to insert records into DB")

        finally:
            if conn:
                cursor.close()
                conn.close()
            return lastId

    def data_select(query, params):
        """
        Get selected data
        :param query:
        :return:
        """
        conn, cursor = open_cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    ## Tasks
    check_db = PythonOperator(
        task_id="check_db_structure", python_callable=check_db_structure
    )

    run_code = PythonOperator(
        task_id="run_main",
        python_callable=main,
    )

    check_db >> run_code
