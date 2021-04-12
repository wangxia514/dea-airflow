"""
#
# Pools setup either by UI or backend
#
"""

from airflow.models import Variable

# Task Pools
WAGL_TASK_POOL = Variable.get("wagl_task_pool", "wagl_processing_pool")
