"""
Common tasks for automated reporting dags
"""

import logging

from airflow.hooks.postgres_hook import PostgresHook

from automated_reporting.helpers import db_has_object
from automated_reporting.sql import SELECT_SCHEMA, SELECT_TABLE, SELECT_COLUMN

log = logging.getLogger("airflow.task")


def check_db_schema(expected_schema, connection_id):
    """
    Task to check that the schema in reporting db has the correct tables, columns, fields before progressing
    """
    rep_pg_hook = PostgresHook(postgres_conn_id=connection_id)
    rep_conn = rep_pg_hook.get_conn()
    rep_cursor = rep_conn.cursor()
    database = expected_schema["database"]
    structure_good = True
    for schema in database["schemas"]:
        result = db_has_object(
            rep_cursor, SELECT_SCHEMA, (database["name"], schema["name"])
        )
        if not result:
            structure_good = False
        log.info(
            "Test database '{}' has schema '{}: {}".format(
                database["name"], schema["name"], result
            )
        )
        for table in schema["tables"]:
            result = db_has_object(
                rep_cursor,
                SELECT_TABLE,
                (database["name"], schema["name"], table["name"]),
            )
            if not result:
                structure_good = False
            log.info(
                "Test schema '{}' has table '{}: {}".format(
                    schema["name"], table["name"], result
                )
            )
            for column in table["columns"]:
                result = db_has_object(
                    rep_cursor,
                    SELECT_COLUMN,
                    (
                        database["name"],
                        schema["name"],
                        table["name"],
                        column["name"],
                    ),
                )
                if not result:
                    structure_good = False
                log.info(
                    "Test table '{}' has column '{}: {}".format(
                        table["name"], column["name"], result
                    )
                )
    if not structure_good:
        raise Exception("Database structure does not match structure definition")
    return "Database structure check passed"
