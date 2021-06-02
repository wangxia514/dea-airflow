"""
Utilities for reporting db queries and inserts
"""

import logging
from airflow.hooks.postgres_hook import PostgresHook
from infra.connections import DB_REP_WRITER_CONN
from automated_reporting.databases import sql

log = logging.getLogger("airflow.task")


def insert_completeness(db_completeness_writes):
    """Insert completeness results into reporting DB"""

    rep_pg_hook = PostgresHook(postgres_conn_id=DB_REP_WRITER_CONN)
    rep_conn = None
    try:
        # open the connection to the Reporting DB and get a cursor
        with rep_pg_hook.get_conn() as rep_conn:
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
    except Exception as e:
        raise e
    finally:
        if rep_conn is not None:
            rep_conn.close()
