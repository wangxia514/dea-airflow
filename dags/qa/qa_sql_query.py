"""
SQL Query strings
"""

explorer_ds_count_compare = """
SELECT *, (OUTPUT_QUERY.agdc_ds_count - OUTPUT_QUERY.explorer_ds_count) as diff
FROM (select count(ds.id) as agdc_ds_count, p.dataset_count as explorer_ds_count, dt.id, p.name from cubedash.product p, agdc.dataset_type dt, agdc.dataset ds where dt.name = p.name and dt.id = ds.dataset_type_ref and ds.archived is NULL GROUP BY p.name, dt.id, p.dataset_count) AS OUTPUT_QUERY
WHERE NOT OUTPUT_QUERY.agdc_ds_count = OUTPUT_QUERY.explorer_ds_count;
"""
