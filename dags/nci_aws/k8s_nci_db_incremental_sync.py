# -*- coding: utf-8 -*-

"""
### NCI to DEA RDS Datacube DB incremental sync

Daily DAG to sync NCI Datacube DB CSVs from S3 to RDS for the purpose of
running [NCI Explorer](https://explorer.dea.ga.gov.au/)
and [Resto](https://github.com/jjrom/resto).

**Upstream dependency**
[NCI DB Incremental CSVs](/tree?dag_id=nci_db_incremental_csvs)

**Downstream dependency for Explorer Updates**
[K8s NCI DB Update Summary](/tree?dag_id=k8s_nci_db_incremental_update_summary)

#### Docker image notes
s3-to-rds: https://bitbucket.org/geoscienceaustralia/s3-to-rds/src/master/

### Airflow dependencies
[Waits for S3Key](https://gist.github.com/nehiljain/6dace5faccb680653f7ea4d5d5273946)
for a day's backup to be available via
[S3KeySensor](https://airflow.apache.org/docs/stable/_api/airflow/sensors/s3_key_sensor/index.html)
and executes downstream task
"""

from datetime import datetime, timedelta

from kubernetes.client.models import V1Volume, V1VolumeMount
from kubernetes.client import models as k8s
import pendulum
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.operators.dummy_operator import DummyOperator
from airflow.providers.amazon.aws.sensors.s3_key import S3KeySensor
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)

from infra.connections import AWS_NCI_DB_BACKUP_CONN
from infra.iam_roles import NCI_DBSYNC_ROLE
from infra.images import S3_TO_RDS_IMAGE, INDEXER_IMAGE
from infra.podconfig import ONDEMAND_NODE_AFFINITY
from infra.variables import AWS_DEFAULT_REGION
from infra.variables import DB_HOSTNAME, DB_PORT, SECRET_EXPLORER_NCI_ADMIN_NAME

local_tz = pendulum.timezone("Australia/Canberra")

# Templated DAG arguments
DATESTRING = (
    "{% if dag_run.conf %}{{ dag_run.conf.DATESTRING }}{% else %}{{ ds }}{% endif %}"
)
S3_BUCKET = "nci-db-dump"
S3_PREFIX = f"csv-changes/{DATESTRING}"
S3_KEY = f"s3://{S3_BUCKET}/{S3_PREFIX}/md5sums"
BACKUP_PATH = "/scripts/backup"

DEFAULT_ARGS = {
    "owner": "Nikita Gandhi",
    "depends_on_past": False,
    "start_date": datetime(2020, 9, 24, tzinfo=local_tz),
    "email": ["nikita.gandhi@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "env_vars": {
        "AWS_DEFAULT_REGION": AWS_DEFAULT_REGION,
        "DB_HOSTNAME": DB_HOSTNAME,
        "DB_PORT": DB_PORT,
        "BACKUP_PATH": BACKUP_PATH,
        "DATESTRING": DATESTRING,
        "S3_BUCKET": S3_BUCKET,
        "S3_PREFIX": S3_PREFIX,
        "S3_KEY": S3_KEY,
    },
}

# Lift secrets into environment variables for datacube database connectivity
SECRET_RESTORE_INCREMENTAL_SYNC = [
    Secret("env", "DB_DATABASE", SECRET_EXPLORER_NCI_ADMIN_NAME, "database-name"),
    Secret("env", "DB_ADMIN_USER", SECRET_EXPLORER_NCI_ADMIN_NAME, "postgres-username"),
    Secret(
        "env", "DB_ADMIN_PASSWORD", SECRET_EXPLORER_NCI_ADMIN_NAME, "postgres-password"
    ),
]

SECRET_INDEXER = [
    Secret("env", "DB_DATABASE", SECRET_EXPLORER_NCI_ADMIN_NAME, "database-name"),
    Secret("env", "DB_USERNAME", SECRET_EXPLORER_NCI_ADMIN_NAME, "postgres-username"),
    Secret("env", "DB_PASSWORD", SECRET_EXPLORER_NCI_ADMIN_NAME, "postgres-password"),
]

dag = DAG(
    "k8s_nci_db_incremental_sync",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    catchup=False,
    concurrency=1,
    max_active_runs=1,
    tags=["k8s", "nci-explorer"],
    schedule_interval="45 0 * * *",  # every day 0:45AM
    dagrun_timeout=timedelta(minutes=60 * 3),
)

affinity = ONDEMAND_NODE_AFFINITY

s3_backup_volume_mount = V1VolumeMount(
    name="s3-backup-volume", mount_path=BACKUP_PATH, sub_path=None, read_only=False
)

s3_backup_volume = V1Volume(
    name="s3-backup-volume",
    persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(
        claim_name="s3-backup-volume"
    ),
)

with dag:
    START = DummyOperator(task_id="start")

    # Wait for S3 Key
    S3_BACKUP_SENSE = S3KeySensor(
        task_id="s3-backup-sense",
        poke_interval=60 * 30,
        bucket_key=S3_KEY,
        aws_conn_id=AWS_NCI_DB_BACKUP_CONN,
    )

    # Download NCI db incremental backup from S3 and restore to RDS Aurora
    RESTORE_NCI_INCREMENTAL_SYNC = KubernetesPodOperator(
        namespace="processing",
        image=S3_TO_RDS_IMAGE,
        image_pull_policy="Always",
        annotations={"iam.amazonaws.com/role": NCI_DBSYNC_ROLE},
        cmds=["./import_from_s3.sh"],
        secrets=SECRET_RESTORE_INCREMENTAL_SYNC,
        labels={"step": "nci-db-restore-incremental-sync"},
        name="nci-db-restore-incremental-sync",
        task_id="nci-db-restore-incremental-sync",
        get_logs=True,
        is_delete_operator_pod=True,
        affinity=affinity,
        volumes=[s3_backup_volume],
        volume_mounts=[s3_backup_volume_mount],
    )

    NCI_DB_INDEXER = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        image_pull_policy="Always",
        cmds=["datacube", "-v", "system", "init"],
        secrets=SECRET_INDEXER,
        labels={"step": "nci-db-indexer"},
        name="nci-db-indexer",
        task_id="nci-db-indexer",
        get_logs=True,
        is_delete_operator_pod=True,
        affinity=affinity,
    )

    # Task complete
    COMPLETE = DummyOperator(task_id="done")

    START >> S3_BACKUP_SENSE
    S3_BACKUP_SENSE >> RESTORE_NCI_INCREMENTAL_SYNC
    RESTORE_NCI_INCREMENTAL_SYNC >> NCI_DB_INDEXER
    NCI_DB_INDEXER >> COMPLETE
