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
DB_DATABASE = "nci_20200918"
DATESTRING = "{{ macros.ds_add(ds, -1) }}"
S3_KEY = f"s3://nci-db-dump/csv-changes/{DATESTRING}/agdc.dataset_changes.csv.gz"
BACKUP_PATH = "/scripts/backup"

DEFAULT_ARGS = {
    "owner": "Nikita Gandhi",
    "depends_on_past": False,
    "start_date": datetime(2020, 9, 24, tzinfo=local_tz),
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
        "BACKUP_PATH": BACKUP_PATH,
        "DATESTRING": DATESTRING
    },
    # Use K8S secrets to send DB Creds
    # Lift secrets into environment variables for datacube
    "secrets": [
        Secret("env", "DB_USERNAME", "explorer-admin", "postgres-username"),
        Secret("env", "DB_PASSWORD", "explorer-admin", "postgres-password"),
    ],
}

# Point to Geoscience Australia / OpenDataCube Dockerhub
S3_TO_RDS_IMAGE = "geoscienceaustralia/s3-to-rds:0.1.1-unstable.15.g74dee44"
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

s3_backup_volume_mount = VolumeMount(name="s3-backup-volume",
                                     mount_path=BACKUP_PATH,
                                     sub_path=None,
                                     read_only=False)

s3_backup_volume_config = {
    "persistentVolumeClaim":
        {
            "claimName": "s3-backup-volume"
        }
}

s3_backup_volume = Volume(name="s3-backup-volume", configs=s3_backup_volume_config)

with dag:
    START = DummyOperator(task_id="nci_db_incremental_sync")

    # Wait for S3 Key
    S3_BACKUP_SENSE = S3KeySensor(
        labels={"step": "s3-backup-sense"},
        name="s3-backup-sense",
        task_id="s3_backup_sense",
        poke_interval=60 * 30,
        bucket_key=S3_KEY,
        aws_conn_id="aws_nci_db_backup",
    )

    # Download NCI db incremental backup from S3 and restore to RDS Aurora
    RESTORE_NCI_INCREMENTAL_SYNC = KubernetesPodOperator(
        namespace="processing",
        image=S3_TO_RDS_IMAGE,
        annotations={"iam.amazonaws.com/role": "svc-dea-dev-eks-processing-dbsync"},  # TODO: Pass this via DAG parameters
        cmds=["./import_from_s3.sh"],
        image_pull_policy="Always",
        labels={"step": "s3-to-rds"},
        name="s3-to-rds",
        task_id="s3_to_rds",
        get_logs=True,
        is_delete_operator_pod=True,
        affinity=affinity,
        volumes=[s3_backup_volume],
        volume_mounts=[s3_backup_volume_mount],
    )

    # Run update summary
    UPDATE_SUMMARY = KubernetesPodOperator(
        namespace="processing",
        image=EXPLORER_IMAGE,
        cmds=["cubedash-gen"],
        arguments=["--no-init-database", "--refresh-stats", "--force-refresh", "--all"],
        labels={"step": "summarize-datacube"},
        name="summarize-datacube",
        task_id="summarize_datacube",
        get_logs=True,
        is_delete_operator_pod=True,
        affinity=affinity,
    )

    # Task complete
    COMPLETE = DummyOperator(task_id="all_done")


    START >> S3_BACKUP_SENSE
    S3_BACKUP_SENSE >> RESTORE_NCI_INCREMENTAL_SYNC
    RESTORE_NCI_INCREMENTAL_SYNC >> UPDATE_SUMMARY
    UPDATE_SUMMARY >> COMPLETE
