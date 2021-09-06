"""
select sql query for deletion dag
"""

DATASET_COUNT_CONFIRMATION = """
    SELECT
        count(*)
    FROM
        agdc.dataset ds
    WHERE
        ds.dataset_type_ref =
        ( -- limit to the product name
            SELECT
                id
            FROM
                agdc.dataset_type dt
            WHERE
                dt.NAME = '{product_name}'
        )
        AND (
                ( -- select the years
                    ds.metadata -> 'extent' ->> 'center_dt' LIKE '{selected_year}%'
                )
                OR ( -- select the years
                    ds.metadata -> 'properties' ->> 'dtr:start_datetime' LIKE '{selected_year}%'
                )
        );
"""


CONFIRM_DATASET_HAS_MORE_THAN_ONE_LOCATION = """
    select
        count(*)
    from (
        SELECT dl.dataset_ref, count(dl.uri_body) as num_locations
        from agdc.dataset_location dl
        where dl.dataset_ref IN (
            select id
            from agdc.dataset ds
            where ds.dataset_type_ref = (
                select id
                from agdc.dataset_type dt
                where dt.name ='{product_name}'
            )
        )
        GROUP BY dl.dataset_ref
        HAVING count(dl.uri_body) >1
    ) as ds_location_check;
"""

CONFIRM_TOTAL_DATASET_IN_PRODUCT = """
    select
        count(*)
    from
        agdc.dataset
    where
        dataset_type_ref = (
            select id
            from agdc.dataset_type
            where name ='{product_name}'
        );
"""

SELECT_ALL_PRODUCTS_MATCHING_URI_PATTERNS = """
    SELECT
        count(*)
    FROM
        agdc.dataset_type
    WHERE
        id IN (
            SELECT
                DISTINCT(ds.dataset_type_ref)
            FROM
                agdc.dataset ds
            WHERE
                ds.id IN (
                    SELECT dataset_ref FROM agdc.dataset_location WHERE uri_body LIKE '%{uri_pattern}%'
                )
        );
"""
