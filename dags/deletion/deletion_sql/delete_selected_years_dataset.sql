--------------------------------------
-- SQL to Delete datasets from product in year (Y1, Y2)
--------------------------------------
SET search_path = 'agdc';
-------------------------------------
-- Matching dataset location and delete
-------------------------------------
DELETE
FROM   dataset_location dl
WHERE  dl.dataset_ref in
       ( -- SELECT all the dataset id that matches the WHERE Clause
            SELECT ds.id
            FROM   dataset ds
            WHERE  ds.dataset_type_ref = ( -- Limit the selection to a single product name
                                            SELECT id
                                            FROM   dataset_type dt
                                            WHERE  dt.NAME = '{{ params.product_name }}'
                                        )
            AND (
                    ( -- select the years
                        ds.metadata -> 'extent' ->> 'center_dt' LIKE '{{ params.selected_year }}%'
                    )
                    OR ( -- select the years
                        ds.metadata -> 'properties' ->> 'datetime' LIKE '{{ params.selected_year }}%'
                    )
            )
        );

-- -- -------------------------------------
-- -- -- Check and delete lineage
-- -- -------------------------------------
DELETE
FROM   dataset_source ds_source
WHERE  ds_source.source_dataset_ref in
       ( -- SELECT all the dataset id that matches the WHERE Clause
            SELECT ds.id
            FROM   dataset ds
            WHERE  ds.dataset_type_ref = ( -- Limit the selection to a single product name
                                            SELECT id
                                            FROM   dataset_type dt
                                            WHERE  dt.NAME = '{{ params.product_name }}'
                                        )
            AND (
                    ( -- select the years
                        ds.metadata -> 'extent' ->> 'center_dt' LIKE '{{ params.selected_year }}%'
                    )
                    OR ( -- select the years
                        ds.metadata -> 'properties' ->> 'datetime' LIKE '{{ params.selected_year }}%'
                    )
            )
        )
        OR
        ds_source.dataset_ref in
        ( -- SELECT all the dataset id that matches the WHERE Clause
            SELECT ds.id
            FROM   dataset ds
            WHERE  ds.dataset_type_ref = ( -- Limit the selection to a single product name
                                            SELECT id
                                            FROM   dataset_type dt
                                            WHERE  dt.NAME = '{{ params.product_name }}'
                                        )
            AND (
                    ( -- select the years
                        ds.metadata -> 'extent' ->> 'center_dt' LIKE '{{ params.selected_year }}%'
                    )
                    OR ( -- select the years
                        ds.metadata -> 'properties' ->> 'datetime' LIKE '{{ params.selected_year }}%'
                    )
            )
        );

-- -------------------------------------
-- -- finally delete datasets
-- -------------------------------------
DELETE
FROM
   dataset ds
WHERE
   ds.dataset_type_ref =
   ( -- limit to the product name
      SELECT
         id
      FROM
         dataset_type dt
      WHERE
         dt.NAME = '{{ params.product_name }}'
   )
    AND (
            ( -- select the years
                ds.metadata -> 'extent' ->> 'center_dt' LIKE '{{ params.selected_year }}%'
            )
            OR ( -- select the years
                ds.metadata -> 'properties' ->> 'datetime' LIKE '{{ params.selected_year }}%'
            )
    );
