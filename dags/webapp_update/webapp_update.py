"""
# Update Explorer and OWS
This DAG runs every 6 hours to update for fresh index datasets
The current product list is available from https://github.com/GeoscienceAustralia/dea-airflow/blob/develop/dags/webapp_update/update_list.py

The list as at the time this docstring is created is:

```python
    OWS_UPDATE_LIST = (
        "s2_nrt_granule_nbar_t",
        "wofs_albers",
        "fc_albers_combined",
        "s2_ard_granule_nbar_t",
        "ga_ls_wo_3",
        "ga_s2_wo_3",
        "ga_ls_fc_3",
        "ga_ls_ard_3",
    )

    EXPLORER_UPDATE_LIST = (
        "s2a_nrt_granule",
        "s2b_nrt_granule",
        "s2a_ard_granule",
        "s2b_ard_granule",
        "wofs_albers",
        "ls5_fc_albers",
        "ls7_fc_albers",
        "ls8_fc_albers",
        "ga_ls_wo_3",
        "ga_s2_wo_3",
        "ga_ls_fc_3",
        "ga_ls5t_ard_3",
        "ga_ls7e_ard_3",
        "ga_ls8c_ard_3",
    )
```
"""

from datetime import datetime, timedelta

from airflow import DAG

from infra.variables import (
    DB_DATABASE,
    DB_HOSTNAME,
    AWS_DEFAULT_REGION,
)
from dea_utils.update_explorer_summaries import explorer_refresh_operator
from dea_utils.update_ows_products import ows_update_operator
from webapp_update.update_list import EXPLORER_UPDATE_LIST, OWS_UPDATE_LIST

DAG_NAME = "webapp_update"

# DAG CONFIGURATION
DEFAULT_ARGS = {
    "owner": "Pin Jin",
    "depends_on_past": False,
    "start_date": datetime(2020, 6, 14),
    "email": ["pin.jin@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "env_vars": {
        # TODO: Pass these via templated params in DAG Run
        "DB_HOSTNAME": DB_HOSTNAME,
        "DB_DATABASE": DB_DATABASE,
        "AWS_DEFAULT_REGION": AWS_DEFAULT_REGION,
    },
}

# THE DAG
with DAG(
    dag_id=DAG_NAME,
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval="0 */6 * * *",  # every 6 hours
    catchup=False,
    tags=["k8s", "ows-update", "explorer-update"],
) as dag:
    # Both OWS and Explorer can update at the same time

    ows_update_operator(products=OWS_UPDATE_LIST, dag=dag)

    explorer_refresh_operator(products=EXPLORER_UPDATE_LIST)
