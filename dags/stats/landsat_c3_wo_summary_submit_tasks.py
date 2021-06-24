"""
# Landsat Collection-3 WOfS summary tasks to SQS

DAG to manually submit WOfS summary task on Landsat Collection-3.

This DAG uses k8s executors and in submit tasks to SQS with relevant tooling
and configuration installed.

The DAG can be parameterized with run time configuration `FREQUENCY` and `YEAR`.

Based on odc-stats: https://github.com/opendatacube/odc-tools/tree/develop/libs/stats
* The `FREQUENCY` can be: annual|annual-fy|semiannual|seasonal|all
* The `YEAR` can be: integer of a given year, e.g. 2009

The product name is always ga_ls_wo_3 as this DAG aims to process Landset C3 WOfs Summary relative tasks.

When manually trigger this DAG, we can put dag_run.conf there. The dag_run.conf format:

#### example conf in json format

    If we try to only select special year, passing example JSON
    {
        "FREQUENCY": "annual",
        "YEAR": "2009"
    },

    If we plan to include all years, do not put YEAR value, passing example JSON
    {
        "FREQUENCY": "annual-fy"
    }

    NOTE: it does NOT support multi-year like
        {
        "FREQUENCY": "annual",
        "YEAR": "2009-2010"
    }

if the DAG run config is empty, the default year is 2009, and default frequency is annual.

"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.dummy_operator import DummyOperator

from infra.images import STAT_IMAGE
from infra.variables import (
    DB_DATABASE,
    DB_HOSTNAME,
    SECRET_ODC_READER_NAME,
    PROCESSING_STATS_USER_SECRET
)
from infra.sqs_queues import LS_C3_WO_SUMMARY_QUEUE
from infra.pools import DEA_NEWDATA_PROCESSING_POOL

from infra.podconfig import ONDEMAND_NODE_AFFINITY

# DAG CONFIGURATION
DEFAULT_ARGS = {
    "owner": "Sai Ma",
    "depends_on_past": False,
    "start_date": datetime(2021, 6, 14),
    "email": ["sai.ma@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "env_vars": {
        # We need the DB access to get the Tasks from ODC
        "DB_HOSTNAME": DB_HOSTNAME,
        "DB_DATABASE": DB_DATABASE,
        "DB_PORT": "5432",
    },
    # Lift secrets into environment variables
    "secrets": [
        Secret("env", "DB_USERNAME", SECRET_ODC_READER_NAME, "postgres-username"),
        Secret("env", "DB_PASSWORD", SECRET_ODC_READER_NAME, "postgres-password"),
        Secret(
            "env",
            "AWS_DEFAULT_REGION",
            PROCESSING_STATS_USER_SECRET,
            "AWS_DEFAULT_REGION",
        ),
        Secret(
            "env",
            "AWS_ACCESS_KEY_ID",
            PROCESSING_STATS_USER_SECRET,
            "AWS_ACCESS_KEY_ID",
        ),
        Secret(
            "env",
            "AWS_SECRET_ACCESS_KEY",
            PROCESSING_STATS_USER_SECRET,
            "AWS_SECRET_ACCESS_KEY",
        )
    ],
}

# annual summary input is the daily WOfS
PRODUCT_NAME = "ga_ls_wo_3"

frequence_input = "{{ dag_run.conf.FREQUENCY }}"
year_input = "{{ dag_run.conf.YEAR }}"

FREQUENCY = frequence_input if frequence_input else "annual" # if not define frequence from out side, use annual as default

YEAR = year_input if year_input else "2009" # if not define year from outside, use 2009 as default

# the expected name pattern is: ga_ls_wo_3_annual_2009 or ga_ls_wo_3_annual_all
OUTPUT_DB = f"ga_ls_wo_3_{FREQUENCY}_{YEAR}.db"

LS_C3_WO_SUMMARY_QUEUE_NAME = LS_C3_WO_SUMMARY_QUEUE.split("/")[-1]

# Please use the airflow {{ dag_run.conf }} to pass search expression, and add relative 'workable' examples in this DAG's doc.
CACHE_AND_UPLOADING_BASH_COMMAND = [
    #f"odc-stats save-tasks {PRODUCT_NAME} --year=2009 --grid au-30 --frequency {FREQUENCY} ga_ls_wo_3_{FREQUENCY}.db && ls -lh && " \
    #f"odc-stats save-tasks {PRODUCT_NAME} --grid au-30 --frequency {FREQUENCY} {YEAR} {OUTPUT_DB} && ls -lh && " \
    f"odc-stats save-tasks {PRODUCT_NAME} --grid au-30 --frequency {FREQUENCY} {YEAR} {OUTPUT_DB} && ls -lh"
    # f"aws s3 cp ga_ls_wo_3_{FREQUENCY}.db s3://dea-dev-stats-processing/dbs/{OUTPUT_DB}_from_airflow",
]

# Test CMD in JupyterHub: odc-stats publish-tasks s3://dea-dev-stats-processing/dbs/ga_ls_wo_3_annual_test_from_airflow.db dea-dev-eks-stats-kk ":1"
# Only submit single message to do the test
SUBIT_TASKS_BASH_COMMAND = [
    f"odc-stats publish-tasks s3://dea-dev-stats-processing/dbs/{OUTPUT_DB} {LS_C3_WO_SUMMARY_QUEUE_NAME} ':1'",
]

# THE DAG
dag = DAG(
    "landset_c3_wo_summary_submit_tasks",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,  # manually trigger it every year
    catchup=False,
    tags=["k8s", "ls-c3-wofs-summary", "submit-stat-task"],
    params={"labels": {"env": "dev"}},
)

def print_context(ds):
    """Print the Airflow context and dynamic values."""
    print(ds, type(ds))
    if ds:
        print("empty string is also a true?")
    else:
        print("else statement")
    print(CACHE_AND_UPLOADING_BASH_COMMAND)
    return "Whatever you return gets printed in the logs"

with dag:

    START = DummyOperator(task_id="start-stats-submit-tasks")

    PRINTOUT = PythonOperator(
            task_id='print_the_debug_context',
            python_callable=print_context,
            op_args=["{{ dag_run.conf.test_value }}"]
        )

    CACHEING = KubernetesPodOperator(
        namespace="processing",
        image=STAT_IMAGE,
        image_pull_policy="IfNotPresent",
        cmds=["bash", "-c"],
        arguments=CACHE_AND_UPLOADING_BASH_COMMAND,
        labels={"step": "task-to-s3"},
        name="datacube-stats",
        task_id="cache-stat-tasks",
        get_logs=True,
        affinity=ONDEMAND_NODE_AFFINITY,
        is_delete_operator_pod=True,
    )

    """
    SUBMITTING = KubernetesPodOperator(
        namespace="processing",
        image=STAT_IMAGE,
        image_pull_policy="IfNotPresent",
        cmds=["bash", "-c"],
        arguments=SUBIT_TASKS_BASH_COMMAND,
        labels={"step": "task-to-sqs"},
        name="datacube-stats",
        task_id="submit-stat-tasks",
        get_logs=True,
        affinity=ONDEMAND_NODE_AFFINITY,
        is_delete_operator_pod=True,
    )
    """
    
    COMPLETE = DummyOperator(task_id="complete-stats-submit-tasks")

    # START >> PRINTOUT >> CACHEING >> SUBMITTING >> COMPLETE
    START >> PRINTOUT >> CACHEING >> COMPLETE