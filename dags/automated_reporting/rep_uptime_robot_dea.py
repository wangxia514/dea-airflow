# -*- coding: utf-8 -*-

"""
uptime robot dea dag
"""

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
from airflow.kubernetes.secret import Secret
from datetime import datetime as dt, timedelta
from automated_reporting import k8s_secrets, utilities
from infra.variables import REPORTING_UPTIME_API_SECRET

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": False,
    "start_date": dt(2022, 2, 22),
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(days=1),
    "secrets": [
        Secret("env", "API_KEY", REPORTING_UPTIME_API_SECRET, "UPTIME_KEY"),
    ],
}

dag = DAG(
    "rep_uptime_robot_dea_prod",
    description="DAG for uptime robot dea",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval="0 14 * * *",  # daily at 1am AEDT
)

ENV = "prod"
ETL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls:v2.10.0"
)

with dag:
    uptime_robot_processing_dea = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo uptime robot processing dea started: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "jsonresult=`python3 -c 'from nemo_reporting.uptime_robot import dea_uptime_robot_processing; dea_uptime_robot_processing.task()'`",
        ],
        task_id="uptime_robot_processing_dea",
        env_vars={
            "MONITORING_IDS": "784117804, 784122998, 784122995",
            "EXECUTION_DATE": "{{ ds }}",
        },
        secrets=k8s_secrets.db_secrets(ENV)
    )
    uptime_robot_processing_dea
