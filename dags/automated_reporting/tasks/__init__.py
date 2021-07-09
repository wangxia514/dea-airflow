"""
Pull all tasks under namespace tasks.####
"""
from .check_db import task as check_db_task
from .s2_completeness import (
    task_ard as s2_completeness_ard_task,
)  # pylint: disable-msg=E0401
from .s2_completeness import (
    task_wo as s2_completeness_wo_task,
)  # pylint: disable-msg=E0401
from .simple_latency import task as simple_latency_task
from .expire_completeness import task as expire_completeness_task
from .usgs_completeness import (
    task as usgs_completeness_task,
)  # pylint: disable-msg=E0401
from .latency_from_completeness import task as latency_from_completeness_task
