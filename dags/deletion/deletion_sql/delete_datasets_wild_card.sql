--------------------------------------
-- SQL to Delete datasets from a product with a wild card clause
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
                                            WHERE  dt.NAME = '{product_name}'
                                        )
            AND ( -- by any clause
                    {clause}
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
                                            WHERE  dt.NAME = '{product_name}'
                                        )
            AND ( -- by any clause
                    {clause}
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
                                            WHERE  dt.NAME = '{product_name}'
                                        )
            AND ( -- by any clause
                    {clause}
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
         dt.NAME = '{product_name}'
   )
   AND ( -- by any clause
            {clause}
    );
