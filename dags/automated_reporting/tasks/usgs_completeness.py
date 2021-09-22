"""
Task to calculate USGS NRT completeness using S3 listings and Stac API query
"""
import logging
from datetime import timedelta, timezone
import psycopg2
from psycopg2.errors import UniqueViolation  # pylint: disable-msg=E0611

from automated_reporting.utilities import helpers

logger = logging.getLogger("airflow.task")

# Initiations for global variables
missions = [("LANDSAT_8", "landsat_ot_c2_l1"), ("LANDSAT_7", "landsat_etm_c2_l1")]
databaseCompTable = "reporting.completeness"
databaseMissingTable = "reporting.completeness_missing"
databaseStacTable = "landsat.usgs_l1_nrt_c2_stac_listing"
databaseGAS3Table = "landsat.ga_s3_level1_nrt_s3_listing"


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
    matrixWidth, matrixHeight = 5, len(wrsPathRowList)
    pathRowCounterMatrix = [
        ["" for x in range(matrixWidth)] for y in range(matrixHeight)
    ]

    for i in range(0, matrixHeight):
        pathRowCounterMatrix[i][0] = wrsPathRowList[i]
        for j in range(1, matrixWidth):
            pathRowCounterMatrix[i][j] = 0

    # Lists to store missing ids and acq times for each pathrow
    for i in range(0, matrixHeight):
        pathRowCounterMatrix[i][3] = list()
        pathRowCounterMatrix[i][4] = list()

    for scene in stacApi:
        wrsPathRow = "{}_{}".format(scene[1], scene[2])

        # Loop through and add counters to each path-row for usgs index
        for i in range(0, matrixHeight):

            if pathRowCounterMatrix[i][0] == wrsPathRow:
                pathRowCounterMatrix[i][1] += 1

        # If product has been downloaded by GA
        if scene[0] in s3Listing:
            satAcqList.append(scene[5])
            # Loop through and add counters to each path-row for ga index
            for i in range(0, matrixHeight):
                if pathRowCounterMatrix[i][0] == wrsPathRow:
                    pathRowCounterMatrix[i][2] += 1
                    pathRowCounterMatrix[i][4].append(
                        scene[5]
                    )  # store a list of sat_acq_times
        # If product is missing store missing ids in matrix
        else:
            for i in range(0, matrixHeight):
                if pathRowCounterMatrix[i][0] == wrsPathRow:
                    pathRowCounterMatrix[i][3].append(scene[0])

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
    rep_conn,
    pathRowCounterMatrix,
    productId,
    satAcqTime,
    processingTime,
    lastUpdated,
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
    conn, cursor = open_cursor(rep_conn)

    for row in pathRowCounterMatrix:
        geoRef = row[0]
        expectedCount = int(row[1])
        actualCount = int(row[2])
        satAcqTime = None
        if row[4]:
            satAcqTime = max(row[4])

        try:
            completeness = (float(actualCount) / float(expectedCount)) * 100.0

        except:
            # division by zero results in python error
            # set this to none to match s2 logic
            completeness = None

        executionStr = """INSERT INTO reporting.completeness (geo_ref, completeness, expected_count,
            actual_count, product_id, sat_acq_time, processing_time, last_updated) VALUES (%s,%s,%s,%s,%s,%s,Null,%s)
            RETURNING id;"""

        params = (
            geoRef,
            completeness,
            int(expectedCount),
            int(actualCount),
            productId,
            satAcqTime,
            lastUpdated,
        )
        print(params)
        last_id = execute_query_id(executionStr, params, cursor)
        print("Last ID:", last_id)
        if last_id is not None:
            # Insert missing scenes for each row_path
            executionStr = """INSERT INTO reporting.completeness_missing (completeness_id, dataset_id, last_updated)
                VALUES (%s, %s, %s);
            """
            for missing_scene in row[3]:
                params = (last_id, missing_scene, lastUpdated)
                execute_query(executionStr, params, cursor)

    return conn_commit(conn, cursor)


def gen_sql_completeness(
    rep_conn,
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
    conn, cursor = open_cursor(rep_conn)

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
    return conn_commit(conn, cursor)


def gen_m2m_api_inserts(rep_conn, stacApiMatrix):
    """
    Insert STAC API metadata into DB
    :param stacApiMatrix:
    :return:
    """
    conn, cursor = open_cursor(rep_conn)
    for row in stacApiMatrix:
        executionStr = """INSERT INTO landsat.usgs_l1_nrt_c2_stac_listing (scene_id, wrs_path, wrs_row,
        collection_category, collection_number, sat_acq) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING;"""

        params = (row[0], row[1], row[2], row[3], int(row[4]), row[5])
        execute_query(executionStr, params, cursor)

    return conn_commit(conn, cursor)


def get_stac_metadata(rep_conn, mission, start_time, end_time):
    """
    Get last 30 days of stac metadata from DB
    :return: stacAPI data
    """
    executionStr = """SELECT * FROM landsat.usgs_l1_nrt_c2_stac_listing WHERE scene_id like %s AND sat_acq > %s AND sat_acq <= %s;"""
    params = (mission, start_time, end_time)

    results = data_select(rep_conn, executionStr, params)
    return results


def get_s3_listing(rep_conn, pipeline, start_time, end_time):
    """
    Get last 30 days of stac metadata from DB
    :param pipeline: Name of pipeline to get data from e.g. L7C2
    :return:
    """
    executionStr = """SELECT scene_id FROM landsat.ga_s3_level1_nrt_s3_listing
    WHERE last_updated > %s AND last_updated <= %s AND pipeline = %s;"""
    params = (start_time, end_time, pipeline)
    return data_select(rep_conn, executionStr, params)


# Open database connection
def open_cursor(connection_parameters):
    """
    Open database connection
    :return: conn, cursor
    """
    conn = psycopg2.connect(**connection_parameters)
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
    try:
        cursor.execute(query, params)
        return True
    except UniqueViolation as e:
        logger.error("Duplicate item in database")
        return False


def execute_query_id(query, params, cursor):
    """
    Execute Queries and return the inserted id
    :param query:
    :param params:
    :param cursor:
    :return: id of last inserted record
    """
    try:
        cursor.execute(query, params)
        last_id = cursor.fetchone()[0]
        return last_id
    except UniqueViolation as e:
        logger.error("Duplicate item in database")
        return None


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


def data_select(rep_conn, query, params):
    """
    Get selected data
    :param query:
    :return:
    """
    conn, cursor = open_cursor(rep_conn)
    cursor.execute(query, params)
    return cursor.fetchall()


def convert_m2m_to_matrix(acquisitions):
    """
    Modifies the results to of M2M API call
    to a list of lists(matrix) for use in this task.
    """

    # Reformat the results to a matrix
    matrix_output = list()
    for item in acquisitions:
        matrix_output.append(
            [
                item["id"],
                item["wrs2"].split("_")[0],
                item["wrs2"].split("_")[1],
                item["collect_cat"],
                item["collect_num"],
                item["acq_time"],
            ]
        )
    return matrix_output


def task(next_execution_date, rep_conn, task_instance, aux_data_path, **kwargs):
    """
    Main function
    :return:
    """
    # Correct issue with running at start of scheduled period
    execution_date = next_execution_date

    # get the results for upstream call to USGS M2M Api
    acquisitions = task_instance.xcom_pull(task_ids="usgs_acquisitions")

    # Set amount of days to look back to
    dayRange = 30

    execution_date = helpers.python_dt(execution_date)

    # Format dates to example '2020-11-01'
    start_time = execution_date - timedelta(days=dayRange)
    end_time = execution_date

    logger.info("Starting reporting workflow for Landsat L1 NRT")

    # Get path row list
    wrsPathRowList = helpers.get_aoi_list(aux_data_path, "landsat_l1_path_row_list.txt")
    logger.info("Loaded Path Row Listing")
    latency_results = []

    # convert m2m2 api to a matrix format
    m2mApiMatrix = convert_m2m_to_matrix(acquisitions)
    logger.debug(m2mApiMatrix)

    logger.info(
        "Inserting USGS inventory into DB: {} acquisitions".format(len(m2mApiMatrix))
    )
    gen_m2m_api_inserts(rep_conn, m2mApiMatrix)

    for mission in missions:

        logger.info("Get last 30 days USGS inventory from DB: {}".format(mission[0]))
        logger.info("Checking GA S3 Listing: {}".format(mission[0]))

        if mission[0] == "LANDSAT_8":
            stacApiData = get_stac_metadata(rep_conn, "LC8%", start_time, end_time)
            s3List = get_s3_listing(rep_conn, "L8C2", start_time, execution_date)
            logger.debug("GA-S3 Listing: {} - {}".format(mission[0], s3List))
            productId = "usgs_ls8c_level1_nrt_c2"
        elif mission[0] == "LANDSAT_7":
            stacApiData = get_stac_metadata(rep_conn, "LE7%", start_time, end_time)
            s3List = get_s3_listing(rep_conn, "L7C2", start_time, execution_date)
            logger.debug("GA-S3 Listing: {} - {}".format(mission[0], s3List))
            productId = "usgs_ls7e_level1_nrt_c2"

        logger.info("Filtering out data from outside AOI: {}".format(mission[0]))
        filteredStacApiData, filteredS3List = filter_aoi(
            wrsPathRowList, stacApiData, s3List
        )

        logger.info("Running completeness metrics for: {}".format(mission[0]))
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
        try:
            completeness = (float(gaCount) / float(expectedCount)) * 100.0
        except:
            # division by zero results in python error
            # set this to none to match s2 dag logic
            completeness = None

        gen_sql_completeness(
            rep_conn,
            "all_ls",
            completeness,
            expectedCount,
            gaCount,
            productId,
            latestSatAcq,
            "Null",
            execution_date,
        )
        latency_results.append(
            {
                "product_name": productId,
                "latest_sat_acq_ts": latestSatAcq.astimezone(
                    tz=timezone.utc
                ).timestamp(),
                "latest_processing_ts": None,
            }
        )
        logger.info("***{} MISSION***".format(mission[0]))
        logger.info(
            "Completeness - {}%. Expected Count - {}. Actual Count - {}.".format(
                completeness, expectedCount, gaCount
            )
        )
        logger.info("Missing Matrix - {}".format(missingMatrix))
        gen_sql_completeness_path_row(
            rep_conn,
            pathRowCounterMatrix,
            productId,
            "Null",
            "Null",
            execution_date,
        )

    return latency_results
