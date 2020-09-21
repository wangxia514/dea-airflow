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
# from env_var.infra import DB_HOSTNAME

# Templated DAG arguments
DB_HOSTNAME = "db-writer"
DB_DATABASE = "nci_20200917"
DATESTRING  = "2020-09-18"      # TODO: fetch datestring
S3_PATH = f"s3://nci-db-dump/csv-changes/{DATESTRING}"

DEFAULT_ARGS = {
    "owner": "Nikita Gandhi",
    "depends_on_past": False,
    "is_delete_operator_pod": True,
    "start_date": datetime(2020, 2, 1),
    "email": ["nikita.gandhi@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    # 'queue': 'bash_queue',
    # 'pool': 'backfill',
    # 'priority_weight': 10,
    # 'end_date': datetime(2016, 1, 1),
    "env_vars": {
        "AWS_DEFAULT_REGION": "ap-southeast-2",
        "S3_PATH": S3_PATH,
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
    S3_BACKUP_SENSE = DummyOperator(task_id="s3_backup_sense")

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
