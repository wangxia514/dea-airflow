"""
Utilities for reporting db queries and inserts
"""

import logging
import psycopg2
from psycopg2.errors import UniqueViolation  # pylint: disable-msg=E0611
import psycopg2.extras
from automated_reporting.databases import sql
from datetime import timezone, timedelta
import dateutil.parser as parser


log = logging.getLogger("airflow.task")


def read_sns_currency(connection_parameters, pipeline):
    """ """
    rep_conn = None
    output = {"latest_sat_aq": None, "latest_processing": None}
    try:
        # open the connection to the Reporting DB and get a cursor
        with psycopg2.connect(**connection_parameters) as rep_conn:
            with rep_conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            ) as rep_cursor:
                rep_cursor.execute(sql.SELECT_SNS_CURRENCY, (pipeline,))
                output = rep_cursor.fetchone()
                log.debug(
                    "Reporting Executed SQL: {}".format(
                        rep_cursor.query.decode().strip()
                    )
                )
    except Exception as e:
        raise e
    finally:
        if rep_conn is not None:
            rep_conn.close()
    return output


def query_sns(connection_parameters, pipeline, execution_date, days):
    """ """

    start_time = execution_date - timedelta(days=days)
    end_time = execution_date
    rep_conn = None
    datasets = []
    try:
        # open the connection to the Reporting DB and get a cursor
        with psycopg2.connect(**connection_parameters) as rep_conn:
            with rep_conn.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            ) as rep_cursor:
                rep_cursor.execute(
                    sql.SELECT_SNS_COMPLETENESS, (pipeline, start_time, end_time)
                )
                log.debug(
                    "Reporting Executed SQL: {}".format(
                        rep_cursor.query.decode().strip()
                    )
                )
                for row in rep_cursor:
                    datasets.append(row)
    except Exception as e:
        raise e
    finally:
        if rep_conn is not None:
            rep_conn.close()
    return datasets


def insert_completeness(connection_parameters, db_completeness_writes):
    """Insert completeness results into reporting DB"""

    rep_conn = None
    try:
        # open the connection to the Reporting DB and get a cursor
        with psycopg2.connect(**connection_parameters) as rep_conn:
            with rep_conn.cursor() as rep_cursor:
                for record in db_completeness_writes:
                    missing_scenes = record.pop()
                    rep_cursor.execute(sql.INSERT_COMPLETENESS, tuple(record))
                    log.debug(
                        "Reporting Executed SQL: {}".format(rep_cursor.query.decode())
                    )
                    last_id = rep_cursor.fetchone()[0]
                    for missing_scene in missing_scenes:
                        missing_scene.insert(0, last_id)
                        rep_cursor.execute(
                            sql.INSERT_COMPLETENESS_MISSING, tuple(missing_scene)
                        )
                        log.debug(
                            "Reporting Executed SQL: {}".format(
                                rep_cursor.query.decode()
                            )
                        )
    except UniqueViolation as e:
        log.error("Duplicate item in database")
    except Exception as e:
        raise e
    finally:
        if rep_conn is not None:
            rep_conn.close()


def insert_latency(
    connection_parameters,
    product_name,
    latest_sat_acq_ts,
    latest_processing_ts,
    execution_date,
):
    """Insert latency result into reporting DB"""

    rep_conn = None
    try:
        # open the connection to the Reporting DB and get a cursor
        with psycopg2.connect(**connection_parameters) as rep_conn:
            with rep_conn.cursor() as rep_cursor:
                rep_cursor.execute(
                    sql.INSERT_LATENCY,
                    (
                        product_name,
                        latest_sat_acq_ts.astimezone(tz=timezone.utc).replace(
                            tzinfo=None
                        ),
                        latest_processing_ts.astimezone(tz=timezone.utc).replace(
                            tzinfo=None
                        ),
                        execution_date.astimezone(
                            tz=timezone(timedelta(hours=10), name="AEST")
                        ).replace(tzinfo=None),
                    ),
                )
                log.info("REP Executed SQL: {}".format(rep_cursor.query.decode()))
                log.info("REP returned: {}".format(rep_cursor.statusmessage))
    except UniqueViolation as e:
        log.error("Duplicate item in database")
    except Exception as e:
        raise e
    finally:
        if rep_conn is not None:
            rep_conn.close()


def expire_completeness(connection_parameters, product_id):
    """Expire completeness results in reporting DB"""

    rep_conn = None
    count = None
    try:
        # open the connection to the Reporting DB and get a cursor
        with psycopg2.connect(**connection_parameters) as rep_conn:
            with rep_conn.cursor() as rep_cursor:
                rep_cursor.execute(sql.EXPIRE_COMPLETENESS, {"product_id": product_id})
                count = rep_cursor.rowcount
    except Exception as e:
        raise e
    finally:
        if rep_conn is not None:
            rep_conn.close()
    return count


def insert_latency_from_completeness(
    connection_parameters, completeness_summary, execution_date
):
    """Insert latency result into reporting DB"""

    rep_conn = None
    try:
        # open the connection to the Reporting DB and get a cursor
        with psycopg2.connect(**connection_parameters) as rep_conn:
            with rep_conn.cursor() as rep_cursor:
                sat_acq_ts = parser.isoparse(completeness_summary["latest_sat_acq_ts"])
                proc_ts = None
                if completeness_summary["latest_processing_ts"]:
                    proc_ts = parser.isoparse(
                        completeness_summary["latest_processing_ts"]
                    )
                rep_cursor.execute(
                    sql.INSERT_LATENCY,
                    (
                        completeness_summary["product_code"],
                        sat_acq_ts,
                        proc_ts,
                        execution_date.astimezone(
                            tz=timezone(timedelta(hours=10), name="AEST")
                        ).replace(tzinfo=None),
                    ),
                )
                log.info("REP Executed SQL: {}".format(rep_cursor.query.decode()))
                log.info("REP returned: {}".format(rep_cursor.statusmessage))
    except UniqueViolation as e:
        log.error("Duplicate item in database")
    except Exception as e:
        raise e
    finally:
        if rep_conn is not None:
            rep_conn.close()
