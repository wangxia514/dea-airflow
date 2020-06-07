"""
# NCI to RDS Datacube DB migration

DAG to periodically sync NCI datacube to RDS mainly for the purpose of
running [Explorer](https://github.com/opendatacube/datacube-explorer)
and [Resto](https://github.com/jjrom/resto).

[Waits for S3Key](https://gist.github.com/nehiljain/6dace5faccb680653f7ea4d5d5273946)
for a day's backup to be available via 
[S3KeySensor](https://airflow.apache.org/docs/stable/_api/airflow/sensors/s3_key_sensor/index.html)
and excutes downstream task including verifying backup
integrity using md5sum
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.sensors.s3_key_sensor import S3KeySensor
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.contrib.kubernetes.secret import Secret
from airflow.operators.dummy_operator import DummyOperator

# Templated DAG arguments
DB_DATABASE = "nci_{{ ds_nodash }}"
DB_HOSTNAME = "database-write.local"
FILE_PREFIX = "105-{{ ds_nodash }}"
S3_KEY = f"s3://nci-db-dump/prod/{FILE_PREFIX}-datacube.pgdump"

DEFAULT_ARGS = {
    "owner": "Tisham Dhar",
    "depends_on_past": False,
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
EXPLORER_IMAGE = "opendatacube/dashboard:2.1.6"

dag = DAG(
    "k8s_db_sync",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    catchup=False,
    concurrency=1,
    max_active_runs=1,
    tags=["k8s"],
    schedule_interval=timedelta(hours=12),
)


with dag:
    START = DummyOperator(task_id="nci_rds_sync")
    # Wait for S3 Key
    S3_BACKUP_SENSE = S3KeySensor(
        task_id="s3_backup_sense",
        poke_interval=60 * 30,
        bucket_key=S3_KEY,
        aws_conn_id="aws_nci_db_backup",
    )

    # Download PostgreSQL backup from S3 to within K8S storage
    RESTORE_RDS_S3 = KubernetesPodOperator(
        namespace="processing",
        image=S3_TO_RDS_IMAGE,
        # TODO: Pass this via DAG parameters
        annotations={"iam.amazonaws.com/role": "svc-dea-dev-eks-processing-dbsync"},
        cmds=["/code/s3-to-rds.sh"],
        # Accept DB_NAME, S3_KEY only
        arguments=[DB_DATABASE, S3_KEY],
        # TODO: Need to version the helper image properly once stable
        image_pull_policy="Always",
        # TODO: Need PVC to use as scratch space since Nodes don't have enough storage
        labels={"step": "s3-to-rds"},
        name="s3-to-rds",
        task_id="s3-to-rds",
        get_logs=True,
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
    )

    # Enable PostGIS for explorer to use on the restored DB
    # This will fail without superuser. Keep retrying slowly
    # and wait for user to notice and manually do it then it should
    # pass
    # TODO: Use some other means e.g. new DB from templates with PostGIS
    # preinstalled
    ENABLE_POSTGRES = KubernetesPodOperator(
        namespace="processing",
        image=S3_TO_RDS_IMAGE,
        cmds=["psql"],
        arguments=[
            "-h",
            "$(DB_HOSTNAME)",
            "-U",
            "$(DB_USERNAME)",
            "-d",
            "$(DB_DATABASE)",
            "-c",
            "CREATE EXTENSION IF NOT EXISTS postgis;",
        ],
        retries = 12,
        retry_delay = timedelta(hours=1),
        labels={"step": "enable_postgres"},
        name="enable-postgres",
        task_id="enable-postgres",
        get_logs=True,
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
    )

    # Hand ownership back to explorer DB user
    CHANGE_DB_OWNER = KubernetesPodOperator(
        namespace="processing",
        image=S3_TO_RDS_IMAGE,
        cmds=["/code/change_db_owner.sh"],
        # TODO: Avoid hardcoding ?
        arguments=[
            "explorer"
        ],
        labels={"step": "change_db_owner"},
        name="change-db-owner",
        task_id="change-db-owner",
        get_logs=True,
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
    RESTORE_RDS_S3 >> ENABLE_POSTGRES
    ENABLE_POSTGRES >> SUMMARIZE_DATACUBE
    DYNAMIC_INDICES >> SUMMARIZE_DATACUBE
    SUMMARIZE_DATACUBE >> CHANGE_DB_OWNER

    CHANGE_DB_OWNER >> SPIN_PODS
    SPIN_PODS >> AUDIT_EXPLORER
    AUDIT_EXPLORER >> COMPLETE
