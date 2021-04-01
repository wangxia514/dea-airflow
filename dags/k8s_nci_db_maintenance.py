"""### AWS NCI datacube db maintenance job

Daily DAG for AWS NCI datacube db maintenance operations
"""

from airflow import DAG
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.kubernetes.secret import Secret
from airflow.operators.dummy_operator import DummyOperator
from datetime import datetime, timedelta
from textwrap import dedent
from infra.images import S3_TO_RDS_IMAGE
from infra.podconfig import NODE_AFFINITY

# Templated DAG arguments
DB_HOSTNAME = "db-writer"
DEFAULT_ARGS = {
    "owner": "Nikita Gandhi",
    "depends_on_past": False,
    "start_date": datetime(2021, 4, 1),
    "email": ["nikita.gandhi@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "env_vars": {
        "DB_HOSTNAME": DB_HOSTNAME,
        "DB_PORT": "5432",
    },
    # Use K8S secrets to send DB Creds
    # Lift secrets into environment variables for datacube database connectivity
    "secrets": [
        Secret("env", "DB_DATABASE", "explorer-nci-admin", "database-name"),
        Secret("env", "DB_ADMIN_USER", "explorer-nci-admin", "postgres-username"),
        Secret("env", "PGPASSWORD", "explorer-nci-admin", "postgres-password"),
    ],
}

dag = DAG(
    "k8s_nci_db_maintenance",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    catchup=False,
    concurrency=1,
    max_active_runs=1,
    tags=["k8s"],
    schedule_interval="10 2 * * 2,4,6",  # every second day 2:10AM
    dagrun_timeout=timedelta(minutes=60 * 4),
)

affinity = NODE_AFFINITY

MAINTENANCE_SCRIPT = [
    "bash",
    "-c",
    dedent(
        """
            # agdc tables
            psql -h $(DB_HOSTNAME) -U $(DB_ADMIN_USER) -d $(DB_DATABASE) -c \
            "vacuum verbose analyze agdc.dataset, agdc.dataset_type, agdc.dataset_source, agdc.metadata_type, agdc.dataset_location;"
            
            # cubedash tables
            psql -h $(DB_HOSTNAME) -U $(DB_ADMIN_USER) -d $(DB_DATABASE) -c \ 
            "vacuum verbose analyze cubedash.dataset_spatial, cubedash.product, cubedash.region, cubedash.time_overview;"
        """
    ),
]


with dag:
    START = DummyOperator(task_id="nci-db-maintenance")

    # Download NCI db incremental backup from S3 and restore to RDS Aurora
    NCI_DB_MAINTENANCE = KubernetesPodOperator(
        namespace="processing",
        image=S3_TO_RDS_IMAGE,
        cmds=[MAINTENANCE_SCRIPT],
        image_pull_policy="Always",
        labels={"step": "nci-db-maintenance"},
        name="nci-db-maintenance",
        task_id="nci-db-maintenance",
        get_logs=True,
        is_delete_operator_pod=True,
        affinity=affinity,
    )

    # Task complete
    COMPLETE = DummyOperator(task_id="done")

    START >> NCI_DB_MAINTENANCE
    NCI_DB_MAINTENANCE >> COMPLETE
