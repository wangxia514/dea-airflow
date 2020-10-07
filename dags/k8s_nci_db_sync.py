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
DATESTRING = "{{ ds_nodash }}"
DB_HOSTNAME = "db-writer"
DB_DATABASE = f"nci_{DATESTRING}"
FILE_PREFIX = f"dea-db.nci.org.au-{DATESTRING}"
S3_KEY = f"s3://nci-db-dump/prod/{FILE_PREFIX}-datacube.pgdump"
S3_KEY = f"s3://nci-db-dump/prod/{FILE_PREFIX}-datacube.pgdump"
BACKUP_PATH = "/scripts/backup"

DEFAULT_ARGS = {
    "owner": "Nikita Gandhi",
    "email": ["nikita.gandhi@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "depends_on_past": False,
    "start_date": datetime(2020, 10, 7),
    "retries": 1,
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
S3_TO_RDS_IMAGE = "geoscienceaustralia/s3-to-rds:0.1.1-unstable.37.gecc8ab3"
EXPLORER_IMAGE = "opendatacube/explorer:2.2.1"

dag = DAG(
    "k8s_nci_db_sync",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    catchup=False,
    concurrency=1,
    max_active_runs=1,
    tags=["k8s"],
    schedule_interval=timedelta(days=7),
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
    START = DummyOperator(task_id="nci-db-sync")

    # Wait for S3 Key
    S3_BACKUP_SENSE = S3KeySensor(
        labels={"step": "s3-backup-sense"},
        name="s3-backup-sense",
        task_id="s3-backup-sense",
        poke_interval=60 * 30,
        bucket_key=S3_KEY,
        aws_conn_id="aws_nci_db_backup",
    )

    # Download PostgreSQL full backup from S3 and restore to RDS Aurora
    RESTORE_RDS_S3 = KubernetesPodOperator(
        namespace="processing",
        image=S3_TO_RDS_IMAGE,
        annotations={"iam.amazonaws.com/role": "svc-dea-sandbox-eks-processing-dbsync"},
        cmds=["./s3_to_rds.sh"],
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

    # Restore dynamic indices
    DYNAMIC_INDICES = KubernetesPodOperator(
        namespace="processing",
        image=EXPLORER_IMAGE,
        cmds=["datacube"],
        arguments=["-v", "system", "init", "--lock-table"],
        labels={"step": "odc-indices"},
        name="odc-indices",
        task_id="odc-indices",
        get_logs=True,
        is_delete_operator_pod=True,
        affinity=affinity,
    )

    # Run summary
    SUMMARIZE_DATACUBE = KubernetesPodOperator(
        namespace="processing",
        image=EXPLORER_IMAGE,
        cmds=["cubedash-gen"],
        arguments=["--init", "--all"],
        labels={"step": "summarize-datacube"},
        name="summarize-datacube",
        task_id="summarize-datacube",
        get_logs=True,
        is_delete_operator_pod=True,
        affinity=affinity,
    )

    # Setup DB user permissions
    SETUP_DB_PERMISSIONS = KubernetesPodOperator(
        namespace="processing",
        image=S3_TO_RDS_IMAGE,
        cmds=["./setup_db_permissions.sh"],
        labels={"step": "setup-db-permissions"},
        name="setup-db-permissions",
        task_id="setup-db-permissions",
        get_logs=True,
        is_delete_operator_pod=True,
        affinity=affinity,
    )

    COMPLETE = DummyOperator(task_id="done")

    START >> S3_BACKUP_SENSE
    S3_BACKUP_SENSE >> RESTORE_RDS_S3
    RESTORE_RDS_S3 >> DYNAMIC_INDICES
    DYNAMIC_INDICES >> SUMMARIZE_DATACUBE
    SUMMARIZE_DATACUBE >> SETUP_DB_PERMISSIONS
    SETUP_DB_PERMISSIONS >> COMPLETE