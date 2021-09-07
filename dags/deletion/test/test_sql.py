"""
# USED FOR TESTING #
"""
GET_PRODUCT_NAME_WHOSE_DATASET_CONTAIN_MORE_THAN_ONE_LOCATION = """
select DISTINCT(dt.name)
from agdc.dataset ds, agdc.dataset_type dt
where ds.id IN (
    SELECT dl.dataset_ref
    from agdc.dataset_location dl
    GROUP BY dl.dataset_ref
    HAVING count(dl.uri_body) >1
)
and dt.id=ds.dataset_type_ref;
"""

GET_DATASET_CONTAIN_MORE_THAN_ONE_LOCATION = """
SELECT dl.dataset_ref, count(dl.uri_body)
from agdc.dataset_location dl
GROUP BY dl.dataset_ref
HAVING count(dl.uri_body) >1;
"""
