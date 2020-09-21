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
DB_HOSTNAME = "db-writer"
DB_DATABASE = "nci_20200917"
local_tz = pendulum.timezone("Australia/Canberra")
DATESTRING  = "{{ ds }}"
S3_KEY = f"s3://nci-db-dump/csv-changes/{DATESTRING}/agdc.dataset_changes.csv.gz"

DEFAULT_ARGS = {
    "owner": "Nikita Gandhi",
    "depends_on_past": False,
    "start_date": datetime(2020, 9, 25, tzinfo=local_tz),
    "email": ["nikita.gandhi@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
    "retry_delay": timedelta(minutes=5),
    "env_vars": {
        "AWS_DEFAULT_REGION": "ap-southeast-2",
        "S3_KEY": S3_KEY,
        "DB_HOSTNAME": DB_HOSTNAME,
        "DB_DATABASE": DB_DATABASE,
        "DB_PORT": "5432",
    },
    # Use K8S secrets to send DB Creds
    # Lift secrets into environment variables for datacube
    "secrets": [
        Secret("env", "DB_USERNAME", "explorer-admin", "postgres-username"),
        Secret("env", "DB_PASSWORD", "explorer-admin", "postgres-password"),
    ],
}

# Point to Geoscience Australia / OpenDataCube Dockerhub
S3_TO_RDS_IMAGE = "geoscienceaustralia/s3-to-rds:0.1.1-unstable.9.g05c505e"
EXPLORER_IMAGE = "opendatacube/explorer:2.1.11-157-g6b143e0"

dag = DAG(
    "k8s_nci_db_incremental_sync",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    catchup=False,
    concurrency=1,
    max_active_runs=1,
    tags=["k8s"],
    schedule_interval=timedelta(days=1),
)


with dag:
    START = DummyOperator(task_id="nci_db_incremental_sync")

    # Wait for S3 Key
    S3_BACKUP_SENSE = S3KeySensor(
        task_id="s3_backup_sense",
        poke_interval=60 * 30,
        bucket_key=S3_KEY,
        aws_conn_id="aws_nci_db_backup",
    )

    # Download PostgreSQL incremental backup from S3 and restore to RDS Aurora
    RESTORE_NCI_INCREMENTAL_SYNC = DummyOperator(task_id="restore_nci_incremental_sync")

    # Run update summary
    UPDATE_SUMMARY = DummyOperator(task_id="update_summary")

    # Task complete
    COMPLETE = DummyOperator(task_id="all_done")


    START >> S3_BACKUP_SENSE
    S3_BACKUP_SENSE >> RESTORE_NCI_INCREMENTAL_SYNC
    RESTORE_NCI_INCREMENTAL_SYNC >> UPDATE_SUMMARY
    UPDATE_SUMMARY >> COMPLETE
