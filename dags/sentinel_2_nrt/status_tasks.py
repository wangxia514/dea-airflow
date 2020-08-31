"""
# Sentinel-2_nrt status marker,
 - start
 - complete
"""
from airflow.operators.dummy_operator import DummyOperator

START = DummyOperator(task_id="start_sentinel_2_nrt")

COMPLETE = DummyOperator(task_id="all_done")