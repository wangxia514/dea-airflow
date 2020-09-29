"""
# NCI to RDS Datacube DB migration

DAG to periodically sync NCI datacube to RDS mainly for the purpose of
running [Explorer](https://github.com/opendatacube/datacube-explorer)
and [Resto](https://github.com/jjrom/resto).

[Waits for S3Key](https://gist.github.com/nehiljain/6dace5faccb680653f7ea4d5d5273946)
for a day's backup to be available via
[S3KeySensor](https://airflow.apache.org/docs/stable/_api/airflow/sensors/s3_key_sensor/index.html)
and executes downstream task including verifying backup
integrity using md5sum
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.sensors.s3_key_sensor import S3KeySensor
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.kubernetes.secret import Secret
from airflow.kubernetes.volume import Volume
from airflow.kubernetes.volume_mount import VolumeMount
from airflow.operators.dummy_operator import DummyOperator
from datetime import datetime, timedelta

import pendulum

# Templated DAG arguments
local_tz = pendulum.timezone("Australia/Canberra")
DB_HOSTNAME = "db-writer"
DB_DATABASE = "nci_20200925"

DEFAULT_ARGS = {
    "owner": "Nikita Gandhi",
    "depends_on_past": False,
    "start_date": datetime(2020, 10, 3, tzinfo=local_tz),
    "email": ["nikita.gandhi@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
    "retry_delay": timedelta(minutes=5),
    "env_vars": {
        "AWS_DEFAULT_REGION": "ap-southeast-2",
        "DB_HOSTNAME": DB_HOSTNAME,
        "DB_DATABASE": DB_DATABASE,
        "DB_PORT": "5432",

    },
    # Use K8S secrets to send DB Creds
    # Lift secrets into environment variables for datacube
    "secrets": [
        Secret("env", "DB_USERNAME", "explorer-writer", "postgres-username"),   # To run cubedash-gen
        Secret("env", "DB_PASSWORD", "explorer-writer", "postgres-password"),
    ],
}

EXPLORER_IMAGE = "opendatacube/explorer:2.1.11-166-ga34234b"

dag = DAG(
    "k8s_nci_db_update_summary",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    catchup=False,
    concurrency=1,
    max_active_runs=1,
    tags=["k8s"],
    schedule_interval=timedelta(days=7),
    execution_timeout=timedelta(hours=15),
)

affinity = {
    "nodeAffinity": {
        "requiredDuringSchedulingIgnoredDuringExecution": {
            "nodeSelectorTerms": [{
                "matchExpressions": [{
                    "key": "nodetype",
                    "operator": "In",
                    "values": [
                        "ondemand",
                    ]
                }]
            }]
        }
    }
}

with dag:
    START = DummyOperator(task_id="nci-db-update-summary")

    # Run update summary
    UPDATE_SUMMARY = KubernetesPodOperator(
        namespace="processing",
        image=EXPLORER_IMAGE,
        cmds=["cubedash-gen"],
        arguments=["--no-init-database", "--refresh-stats", "--force-refresh", "--all"],
        labels={"step": "summarize-datacube"},
        name="summarize-datacube",
        task_id="summarize-datacube",
        get_logs=True,
        is_delete_operator_pod=True,
        affinity=affinity,
    )

    # Task complete
    COMPLETE = DummyOperator(task_id="done")


    START >> UPDATE_SUMMARY
    UPDATE_SUMMARY >> COMPLETE
