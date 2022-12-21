"""
# Task Pools
"""
from airflow.models import Variable

# Task Pools
WAGL_TASK_POOL = Variable.get("wagl_task_pool", default_var="wagl_processing_pool")
DEA_NEWDATA_PROCESSING_POOL = Variable.get(
    "newdata_indexing_pool", default_var="NewDeaData_indexing_pool"
)
C3_INDEXING_POOL = Variable.get("c3_indexing_pool", default_var="c3_indexing_pool")
