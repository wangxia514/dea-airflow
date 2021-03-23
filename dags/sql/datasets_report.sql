-- Count Collection 3 ODC Datasets
SELECT product.name, count(*), max(d.added)
FROM agdc.dataset d
LEFT JOIN agdc.dataset_type product on d.dataset_type_ref = product.id
WHERE d.archived is null
and product.name in ('ga_ls5t_ard_3', 'ga_ls7e_ard_3', 'ga_ls8c_ard_3', 'ga_ls_fc_3', 'ga_ls_wo_3')
group by product.name;