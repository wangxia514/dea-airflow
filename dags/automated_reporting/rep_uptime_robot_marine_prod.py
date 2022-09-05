# -*- coding: utf-8 -*-

"""
Automated Reporting - Uptime Robot Monitoring - Marine
"""
from datetime import datetime as dt, timedelta

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG

from automated_reporting import k8s_secrets, utilities
from airflow.models import Variable

ENV = "prod"
ETL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls:v2.12.0"
)

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt(2022, 8, 28),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": True if ENV == "prod" else False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=60),
}

dag = DAG(
    f"rep_uptime_robot_marine_{ENV}",
    description="DAG pulling stats from Uptime robot",
    tags=["reporting"] if ENV == "prod" else ["reporting_dev"],
    default_args=default_args,
    schedule_interval="0 1 * * *",
)

UPTIME_ROBOT_JOB = [
    "echo Reporting task started: $(date)",
    "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
    "marine-uptime-monitoring",
]

with dag:

    monitoring_ids = Variable.get("marine_uptime_monitoring", deserialize_json=True)

    def create_task(monitor_id):
        """Generate tasks based on list of query parameters"""
        env_vars = {
            "MONITOR_ID": str(monitor_id),
            "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts }}",
        }
        return utilities.k8s_operator(
            dag=dag,
            image=ETL_IMAGE,
            task_id=f"monitor_{monitor_id}",
            cmds=UPTIME_ROBOT_JOB,
            env_vars=env_vars,
            secrets=k8s_secrets.db_secrets(ENV) + k8s_secrets.uptime_robot_secret,
        )

    [create_task(monitor_id) for monitor_id in monitoring_ids]
