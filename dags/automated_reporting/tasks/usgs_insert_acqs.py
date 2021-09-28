"""
Insert USGS acquisitions into reporting DB
"""
import logging
from automated_reporting.databases import reporting_db_usgs

logger = logging.getLogger("airflow.task")


def gen_m2m_api_inserts(rep_conn, m2mApiMatrix):
    """
    Insert M2M API metadata into DB
    :param m2mApiMatrix:
    :return:
    """
    conn, cursor = reporting_db_usgs.open_cursor(rep_conn)
    for row in m2mApiMatrix:
        executionStr = """INSERT INTO landsat.usgs_l1_nrt_c2_stac_listing (scene_id, wrs_path, wrs_row,
        collection_category, collection_number, sat_acq) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING;"""

        params = (row[0], row[1], row[2], row[3], int(row[4]), row[5])
        reporting_db_usgs.execute_query(executionStr, params, cursor)

    return reporting_db_usgs.conn_commit(conn, cursor)


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


def task(rep_conn, acquisitions, **kwargs):
    """
    Main function
    :return:
    """

    # convert m2m2 api to a matrix format
    m2mApiMatrix = convert_m2m_to_matrix(acquisitions)
    logger.debug(m2mApiMatrix)

    logger.info(
        "Inserting USGS inventory into DB: {} acquisitions".format(len(m2mApiMatrix))
    )
    gen_m2m_api_inserts(rep_conn, m2mApiMatrix)

    return None
