# -*- coding: utf-8 -*-

"""
uptime robot marine dag
"""
from airflow import DAG
from airflow.kubernetes.secret import Secret
from datetime import datetime as dt, timedelta
from automated_reporting import k8s_secrets, utilities

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": False,
    "start_date": dt(2022, 2, 22),
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(days=1),
}

dag = DAG(
    "rep_uptime_robot_marine_prod",
    description="DAG for uptime robot marine",
    tags=["reporting"],
    default_args=default_args,
    schedule_interval="0 14 * * *",  # daily at 1am AEDT
)

ENV = "prod"
ETL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls:v2.10.0"
)

with dag:
    uptime_robot_processing_marine = utilities.k8s_operator(
        dag=dag,
        image=ETL_IMAGE,
        cmds=[
            "echo uptime robot processing marine started: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "jsonresult=`python3 -c 'from nemo_reporting.uptime_robot import marine_uptime_robot_processing; marine_uptime_robot_processing.task()'`",
        ],
        task_id="uptime_robot_processing_marine",
        env_vars={
            "MONITORING_IDS": "785233301, 785236465, 785236456, 785233316, 785233317, 785233343, 785233341, 785251927, 785251954, 785252068, 785252069, 790085518",
            "EXECUTION_DATE": "{{ ds }}",
        },
        secrets=k8s_secrets.db_secrets(ENV) + k8s_secrets.uptime_api,
    )
    uptime_robot_processing_marine
