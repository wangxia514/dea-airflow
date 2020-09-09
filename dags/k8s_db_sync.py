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
DB_DATABASE = "nci_{{ ds_nodash }}"
FILE_PREFIX = "dea-db.nci.org.au-{{ ds_nodash }}"
S3_KEY = f"s3://nci-db-dump/prod/{FILE_PREFIX}-datacube.pgdump"
WORK_DIR = "/tmp"

DEFAULT_ARGS = {
    "owner": "Tisham Dhar",
    "depends_on_past": False,
    "is_delete_operator_pod": True,
    "start_date": datetime(2020, 2, 1),
    "email": ["tisham.dhar@ga.gov.au"],
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
        "DB_HOSTNAME": DB_HOSTNAME,
        # The run day's DB
        "DB_DATABASE": DB_DATABASE,
    },
    # Use K8S secrets to send DB Creds
    # Lift secrets into environment variables for datacube
    "secrets": [
        Secret("env", "DB_USERNAME", "replicator-db", "postgres-username"),
        # For Datacube to use
        Secret("env", "DB_PASSWORD", "replicator-db", "postgres-password"),
        # For psql to use
        Secret("env", "PGPASSWORD", "replicator-db", "postgres-password"),
    ],
}

# Point to Geoscience Australia / OpenDataCube Dockerhub
S3_TO_RDS_IMAGE = "geoscienceaustralia/s3-to-rds:latest"
EXPLORER_IMAGE = "opendatacube/explorer:2.1.11-151-g93e46e7"

dag = DAG(
    "k8s_db_sync",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    catchup=False,
    concurrency=1,
    max_active_runs=1,
    tags=["k8s"],
    schedule_interval=timedelta(days=7),
)

s3_backup_mount = VolumeMount(
    "s3-backup-volume", mount_path=WORK_DIR, sub_path=None, read_only=False
)

affinity = {
    'nodeAffinity': {
        'requiredDuringSchedulingIgnoredDuringExecution': [
            {
                "labelSelector": {
                    "matchExpressions": [
                        {
                            "key": "nodetype",
                            "operator": "In",
                            "values": ["spot"]
                        }
                    ]
                },
            }
        ]
    }
}

s3_backup_volume_config = {
    'persistentVolumeClaim':
        {
            'claimName': "s3-backup-volume"
        }
}

s3_backup_volume = Volume(name="s3-backup-volume", configs=s3_backup_volume_config)

with dag:
    START = DummyOperator(task_id="nci_rds_sync")
    # Wait for S3 Key
    S3_BACKUP_SENSE = S3KeySensor(
        task_id="s3_backup_sense",
        poke_interval=60 * 30,
        bucket_key=S3_KEY,
        aws_conn_id="aws_nci_db_backup",
    )

    # Download PostgreSQL backup from S3 and restore to RDS Aurora
    RESTORE_RDS_S3 = KubernetesPodOperator(
        namespace="processing",
        image=S3_TO_RDS_IMAGE,
        annotations={"iam.amazonaws.com/role": "svc-dea-dev-eks-processing-dbsync"}, # TODO: Pass this via DAG parameters
        cmds=["/code/s3-to-rds.sh"],
        arguments=[DB_DATABASE, S3_KEY, WORK_DIR],
        image_pull_policy="Always", # TODO: Need to version the helper image properly once stable
        volumes=[s3_backup_volume],
        volume_mounts=[s3_backup_mount],
        labels={"step": "s3-to-rds"},
        name="s3-to-rds",
        task_id="s3-to-rds",
        get_logs=True,
        is_delete_operator_pod=True,
        affinity=affinity,
    )

    # Restore dynamic indices skipped in the previous step
    DYNAMIC_INDICES = KubernetesPodOperator(
        namespace="processing",
        image=EXPLORER_IMAGE,
        cmds=["datacube"],
        arguments=["-v", "system", "init", "--lock-table"],
        labels={"step": "restore_indices"},
        name="odc-indices",
        task_id="odc-indices",
        get_logs=True,
        is_delete_operator_pod=True,
        affinity=affinity,
    )

    # Restore to a local db and link it to explorer codebase and run summary
    SUMMARIZE_DATACUBE = KubernetesPodOperator(
        namespace="processing",
        image=EXPLORER_IMAGE,
        cmds=["cubedash-gen"],
        arguments=["--init", "--all"],
        labels={"step": "summarize_datacube"},
        name="summarize-datacube",
        task_id="summarize-datacube",
        get_logs=True,
        is_delete_operator_pod=True,
        affinity=affinity,
    )

    # Hand ownership back to explorer DB user
    CHANGE_DB_OWNER = KubernetesPodOperator(
        namespace="processing",
        image=S3_TO_RDS_IMAGE,
        cmds=["/code/change_db_owner.sh"],
        # TODO: Avoid hardcoding ?
        arguments=["explorer"],
        labels={"step": "change_db_owner"},
        name="change-db-owner",
        task_id="change-db-owner",
        get_logs=True,
        is_delete_operator_pod=True,
        affinity=affinity,
    )

    # Change DB connection config of application pods and spin up fresh ones
    # TODO: Currently manual find a smooth way to automate
    SPIN_PODS = DummyOperator(task_id="spin_pods")

    # Get API responses from Explorer and ensure product count summaries match
    AUDIT_EXPLORER = DummyOperator(task_id="audit_explorer")
    COMPLETE = DummyOperator(task_id="all_done")

    START >> S3_BACKUP_SENSE
    S3_BACKUP_SENSE >> RESTORE_RDS_S3
    RESTORE_RDS_S3 >> DYNAMIC_INDICES
    DYNAMIC_INDICES >> SUMMARIZE_DATACUBE
    SUMMARIZE_DATACUBE >> CHANGE_DB_OWNER

    CHANGE_DB_OWNER >> SPIN_PODS
    SPIN_PODS >> AUDIT_EXPLORER
    AUDIT_EXPLORER >> COMPLETE
