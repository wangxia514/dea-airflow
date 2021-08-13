"""
Utilities for reporting db queries and inserts
"""

import logging
import uuid
import psycopg2
from psycopg2.errors import UniqueViolation  # pylint: disable-msg=E0611

from automated_reporting.databases import sql

log = logging.getLogger("airflow.task")
psycopg2.extras.register_uuid()


def insert_usgs_l0(connection_parameters, usgs_l0_list):
    """Insert USGS L0 high granularity data into reporting DB"""
    count = 0
    rep_conn = None
    try:
        # open the connection to the Reporting DB and get a cursor
        with psycopg2.connect(**connection_parameters) as rep_conn:
            with rep_conn.cursor() as rep_cursor:
                for record in usgs_l0_list:
                    product_code_l0 = "usgs_{}_acq".format(record["platform"])
                    uuid_l0 = uuid.uuid4()
                    # write l0
                    l0 = dict(
                        id=uuid_l0,
                        label=record["display_id"],
                        product_code=product_code_l0,
                        timestamp=record["acq_time"],
                        source_id=record["id"],
                        region_code=record["wrs2"],
                        extra=psycopg2.extras.Json(
                            dict(cloud_cover=round(float(record["cloud_cover"])))
                        ),
                        status="Complete",
                    )
                    rep_cursor.execute(sql.INSERT_DATASET, l0)
                    l0_row_count = rep_cursor.rowcount
                    # write pl1
                    product_code_pl1 = "usgs_{}_l1".format(record["platform"])
                    uuid_pl1 = uuid.uuid4()
                    l1 = dict(
                        id=uuid_pl1,
                        label=record["display_id"],
                        product_code=product_code_pl1,
                        timestamp=record["l1_time"],
                        source_id=record["id"],
                        region_code=record["wrs2"],
                        extra=None,
                        status="Complete",
                    )
                    rep_cursor.execute(sql.INSERT_DATASET, l1)
                    l1_row_count = rep_cursor.rowcount

                    # write association
                    if l0_row_count and l1_row_count:
                        rep_cursor.execute(
                            sql.INSERT_ASSOCIATION,
                            dict(upstream_id=uuid_l0, downstream_id=uuid_pl1),
                        )
                        count += 1
    except UniqueViolation as e:
        log.error("Duplicate item in database")
    except Exception as e:
        raise e
    finally:
        if rep_conn is not None:
            rep_conn.close()
    return count
