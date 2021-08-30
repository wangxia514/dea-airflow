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
