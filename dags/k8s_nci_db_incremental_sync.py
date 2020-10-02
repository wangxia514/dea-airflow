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

from airflow import DAG
from airflow.sensors.s3_key_sensor import S3KeySensor
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.kubernetes.secret import Secret
from airflow.kubernetes.volume import Volume
from airflow.kubernetes.volume_mount import VolumeMount
from airflow.operators.dummy_operator import DummyOperator
from datetime import datetime, timedelta
from dateutil.parser import parse

def is_date(string, fuzzy=False):
    """
    Return whether the string can be interpreted as a date.

    :param string: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
    """
    try:
        parse(string, fuzzy=fuzzy)
        return True

    except ValueError:
        return False

# Templated DAG arguments
DB_HOSTNAME = "db-writer"
DB_DATABASE = "nci_20200925"
DATESTRING = "{{ ds }}"
# S3_IMPORT_DATE = "{{ dag_run.conf and dag_run.conf.get('s3importdate', '') }}"
S3_IMPORT_DATE = "{{ dag_run.conf.s3importdate if dag_run else '' }}"
S3_BUCKET = "nci-db-dump"
if is_date(S3_IMPORT_DATE):
    S3_PREFIX=f"csv-changes/{S3_IMPORT_DATE}"
else:
    S3_PREFIX=f"csv-changes/{DATESTRING}"
S3_KEY = f"s3://{S3_BUCKET}/{S3_PREFIX}/agdc.dataset_changes.csv.gz"
BACKUP_PATH = "/scripts/backup"

DEFAULT_ARGS = {
    "owner": "Nikita Gandhi",
    "depends_on_past": False,
    "start_date": datetime(2020, 9, 24),
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
        "BACKUP_PATH": BACKUP_PATH,
        "S3_BUCKET": S3_BUCKET,
        "S3_PREFIX": S3_PREFIX,
        "S3_KEY": S3_KEY
    },
    # Use K8S secrets to send DB Creds
    # Lift secrets into environment variables for datacube
    "secrets": [
        Secret("env", "DB_ADMIN_USER", "explorer-admin", "postgres-username"),  # To run import from s3
        Secret("env", "DB_ADMIN_PASSWORD", "explorer-admin", "postgres-password"),
    ],
}

# Point to Geoscience Australia / OpenDataCube Dockerhub
S3_TO_RDS_IMAGE = "geoscienceaustralia/s3-to-rds:0.1.1-unstable.33.g50e2acc"

dag = DAG(
    "k8s_nci_db_incremental_sync",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    catchup=False,
    concurrency=1,
    max_active_runs=1,
    tags=["k8s"],
    schedule_interval='45 0 * * *',     # every day 0:45AM
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
    START = DummyOperator(task_id="nci-db-incremental-sync")

    # Wait for S3 Key
    S3_BACKUP_SENSE = S3KeySensor(
        labels={"step": "s3-backup-sense"},
        name="s3-backup-sense",
        task_id="s3-backup-sense",
        poke_interval=60 * 30,
        bucket_key=S3_KEY,
        aws_conn_id="aws_nci_db_backup",
    )

    # Download NCI db incremental backup from S3 and restore to RDS Aurora
    RESTORE_NCI_INCREMENTAL_SYNC = KubernetesPodOperator(
        namespace="processing",
        image=S3_TO_RDS_IMAGE,
        annotations={"iam.amazonaws.com/role": "svc-dea-dev-eks-processing-dbsync"},
        cmds=["./import_from_s3.sh"],
        image_pull_policy="Always",
        labels={"step": "s3-to-rds"},
        name="s3-to-rds",
        task_id="s3-to-rds",
        get_logs=True,
        is_delete_operator_pod=True,
        affinity=affinity,
        volumes=[s3_backup_volume],
        volume_mounts=[s3_backup_volume_mount],
    )

    # Task complete
    COMPLETE = DummyOperator(task_id="done")


    START >> S3_BACKUP_SENSE
    S3_BACKUP_SENSE >> RESTORE_NCI_INCREMENTAL_SYNC
    RESTORE_NCI_INCREMENTAL_SYNC >> COMPLETE
