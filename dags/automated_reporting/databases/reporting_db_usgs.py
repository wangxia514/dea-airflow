"""
Common Database functions frrom USGS completeness work by JM
"""
import logging
import psycopg2
import psycopg2.extras
from psycopg2.errors import UniqueViolation  # pylint: disable-msg=E0611

logger = logging.getLogger("airflow.task")


# Open database connection
def open_cursor(connection_parameters):
    """
    Open database connection
    :return: conn, cursor
    """
    conn = psycopg2.connect(**connection_parameters)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
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


def data_select(rep_conn, query, params):
    """
    Get selected data
    :param query:
    :return:
    """
    conn, cursor = open_cursor(rep_conn)
    cursor.execute(query, params)
    return cursor.fetchall()


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


def get_m2m_metadata(rep_conn, mission, start_time, end_time):
    """
    Get last 30 days of m2m metadata from DB
    :return: m2mAPI data
    """
    executionStr = """SELECT * FROM landsat.usgs_l1_nrt_c2_stac_listing WHERE scene_id like %s AND sat_acq > %s AND sat_acq <= %s;"""
    params = (mission, start_time, end_time)

    results = data_select(rep_conn, executionStr, params)
    return results


def get_s3_listing(rep_conn, pipeline, start_time, end_time):
    """
    Get last 30 days of m2m metadata from DB
    :param pipeline: Name of pipeline to get data from e.g. L7C2
    :return:
    """
    executionStr = """SELECT * FROM landsat.ga_s3_level1_nrt_s3_listing
    WHERE last_updated > %s AND last_updated <= %s AND pipeline = %s;"""
    params = (start_time, end_time, pipeline)
    return data_select(rep_conn, executionStr, params)
