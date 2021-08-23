--------------------------------------
-- SQL to Delete ls5_fc_albers in year (1986, 1995, 1997, 1999)
--------------------------------------
-- SET search_path = 'cubedash';
-- select pg_is_in_recovery();
-- SHOW default_transaction_read_only;
-------------------------------------
-- Matching dataset location and delete
-------------------------------------
SELECT id, dataset_count FROM cubedash.product WHERE name = 'ls5_fc_albers';
SELECT count(*) FROM agdc.dataset ds WHERE ds.dataset_type_ref = (SELECT id from agdc.dataset_type dt WHERE dt.name = 'ls5_fc_albers');

SELECT count(id) FROM cubedash.dataset_spatial dspatial WHERE dataset_type_ref = (
    SELECT id FROM agdc.dataset_type dt WHERE dt.name = 'ls5_fc_albers'
);

SELECT count(id) FROM cubedash.dataset_spatial dspatial WHERE id not in (
    SELECT id FROM agdc.dataset
);
-- SELECT Count(*)
-- FROM   dataset_location dl
-- WHERE  dl.dataset_ref in
--        (
--             SELECT ds.id
--             FROM   dataset ds
--             WHERE  ds.dataset_type_ref = (SELECT id
--                                         FROM   dataset_type dt
--                                         WHERE  dt.NAME = 'ls5_fc_albers')
--             AND ( ds.metadata -> 'extent' ->> 'center_dt' LIKE '1986%'
--                     OR ds.metadata -> 'extent' ->> 'center_dt' LIKE '1995%'
--                     OR ds.metadata -> 'extent' ->> 'center_dt' LIKE '1997%'
--                     OR ds.metadata -> 'extent' ->> 'center_dt' LIKE '1999%' )
--         );
