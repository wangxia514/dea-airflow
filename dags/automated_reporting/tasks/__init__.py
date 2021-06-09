"""
Pull all tasks under namespace tasks.####
"""
from .check_db import task as check_db_task
from .s2_completeness import task as s2_completeness_task
from .simple_latency import task as simple_latency_task
from .expire_completeness import task as expire_completeness_task
from .usgs_completeness import task as usgs_completeness_task
