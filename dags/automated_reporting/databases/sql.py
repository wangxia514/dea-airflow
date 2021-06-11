"""
SQL commands for automated reporting dags
"""

SELECT_BY_PRODUCT_AND_TIME_RANGE = """
    SELECT
        dataset.id,
        dataset.added AS indexed_time,
        dataset.metadata #>> '{tile_id}'::text[] as granule_id,
        RIGHT(SPLIT_PART(dataset.metadata #>> '{{tile_id}}'::text[], '_', 9), 5) as tile_id,
        agdc.common_timestamp(dataset.metadata #>> '{extent,center_dt}'::text[]) as satellite_acquisition_time,
        agdc.common_timestamp(dataset.metadata #>> '{system_information,time_processed}'::text[]) AS processing_time
    FROM agdc.dataset
        JOIN agdc.dataset_type ON dataset_type.id = dataset.dataset_type_ref
    WHERE
        dataset.archived IS NULL
    AND
        dataset_type.name = %s
    AND
        dataset.added > %s
    AND
        dataset.added <= %s;
"""

SELECT_SCHEMA = """SELECT * FROM information_schema.schemata WHERE catalog_name=%s and schema_name=%s;"""

SELECT_TABLE = """SELECT * FROM information_schema.tables WHERE table_catalog=%s AND table_schema=%s AND table_name=%s;"""

SELECT_COLUMN = """SELECT * FROM information_schema.columns WHERE table_catalog=%s AND table_schema=%s AND table_name=%s AND column_name=%s;"""

INSERT_LATENCY = """INSERT INTO landsat.derivative_latency VALUES (%s, %s, %s, %s);"""

INSERT_COMPLETENESS = """
    INSERT INTO reporting.completeness (geo_ref, completeness, expected_count, actual_count,
        product_id, sat_acq_time, processing_time, last_updated)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id;"""

INSERT_COMPLETENESS_MISSING = """
    INSERT INTO reporting.completeness_missing (completeness_id, dataset_id, last_updated)
    VALUES (%s, %s, %s);"""

EXPIRE_COMPLETENESS = """
    DELETE FROM reporting.completeness
    WHERE product_id = %(product_id)s
    AND geo_ref NOT LIKE 'all_%%'
    AND id NOT IN (
        SELECT rr.id from (
            SELECT geo_ref, max(last_updated) AS last_updated
            FROM reporting.completeness
            WHERE product_id = %(product_id)s
            GROUP BY geo_ref ) r
        INNER JOIN reporting.completeness rr
        ON rr.geo_ref = r.geo_ref AND rr.last_updated = r.last_updated
        AND rr.product_id = %(product_id)s);"""
