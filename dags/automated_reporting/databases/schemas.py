"""
Schema utilities for automated reporting dags
"""

import logging

from airflow.hooks.postgres_hook import PostgresHook

from automated_reporting.utilities import helpers
from automated_reporting.databases import sql

log = logging.getLogger("airflow.task")

COMPLETENESS_SCHEMA = {
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
                    },
                    {
                        "name": "completeness_missing",
                        "columns": [
                            {"name": "id"},
                            {"name": "completeness_id"},
                            {"name": "dataset_id"},
                            {"name": "last_updated"},
                        ],
                    },
                ],
            }
        ],
    }
}

LATENCY_SCHEMA = {
    "database": {
        "name": "reporting",
        "schemas": [
            {
                "name": "landsat",
                "tables": [
                    {
                        "name": "derivative_latency",
                        "columns": [
                            {"name": "product"},
                            {"name": "sat_acq_date"},
                            {"name": "processing_date"},
                            {"name": "last_updated"},
                        ],
                    }
                ],
            }
        ],
    }
}


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
