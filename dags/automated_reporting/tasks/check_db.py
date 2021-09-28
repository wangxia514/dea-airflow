"""
Task to check that the schema in reporting db has the correct tables, columns, fields before progressing
"""
import logging
import psycopg2
from automated_reporting.utilities import helpers
from automated_reporting.databases import sql

log = logging.getLogger("airflow.task")


def task(expected_schema, rep_conn):
    """
    Task to check that the schema in reporting db has the correct tables, columns, fields before progressing
    """
    rep_conn = psycopg2.connect(**rep_conn)
    rep_cursor = rep_conn.cursor()
    database = expected_schema["database"]
    structure_good = True
    for schema in database["schemas"]:
        result = helpers.db_has_object(
            rep_cursor, sql.SELECT_SCHEMA, (database["name"], schema["name"])
        )
        if not result:
            structure_good = False
        log.info(
            "Test database '{}' has schema '{}: {}".format(
                database["name"], schema["name"], result
            )
        )
        for table in schema["tables"]:
            result = helpers.db_has_object(
                rep_cursor,
                sql.SELECT_TABLE,
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
                result = helpers.db_has_object(
                    rep_cursor,
                    sql.SELECT_COLUMN,
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
