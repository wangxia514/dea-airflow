"""### AWS NCI datacube db maintenance job

Daily DAG for AWS NCI datacube db maintenance operations
"""

from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from airflow.kubernetes.secret import Secret
from airflow.operators.dummy import DummyOperator
from datetime import datetime, timedelta
from textwrap import dedent
from infra.images import INDEXER_IMAGE
from infra.podconfig import ONDEMAND_NODE_AFFINITY
from infra.variables import DB_HOSTNAME, DB_PORT, SECRET_EXPLORER_NCI_ADMIN_NAME

# Templated DAG arguments
DEFAULT_ARGS = {
    "owner": "Damien Ayers",
    "depends_on_past": False,
    "start_date": datetime(2021, 4, 1),
    "email": ["damien.ayers@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "env_vars": {
        "DB_HOSTNAME": DB_HOSTNAME,
        "DB_PORT": DB_PORT,
    },
    # Use K8S secrets to send DB Creds
    # Lift secrets into environment variables for datacube database connectivity
    "secrets": [
        Secret("env", "DB_DATABASE", SECRET_EXPLORER_NCI_ADMIN_NAME, "database-name"),
        Secret(
            "env", "DB_ADMIN_USER", SECRET_EXPLORER_NCI_ADMIN_NAME, "postgres-username"
        ),
        Secret(
            "env", "PGPASSWORD", SECRET_EXPLORER_NCI_ADMIN_NAME, "postgres-password"
        ),
    ],
}

dag = DAG(
    "k8s_nci_db_maintenance",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    catchup=False,
    concurrency=1,
    max_active_runs=1,
    tags=["k8s", "nci-explorer"],
    schedule_interval="@weekly",
    dagrun_timeout=timedelta(minutes=60 * 6),
)

affinity = ONDEMAND_NODE_AFFINITY

MAINTENANCE_SCRIPT = [
    "bash",
    "-c",
    dedent(
        """
            # vaccum analyze agdc + cubedash tables
            psql -h $(DB_HOSTNAME) -U $(DB_ADMIN_USER) -d $(DB_DATABASE) -c \
            "vacuum verbose analyze agdc.dataset, agdc.dataset_type, agdc.dataset_source, agdc.metadata_type, agdc.dataset_location, cubedash.dataset_spatial, cubedash.product, cubedash.region, cubedash.time_overview;"
        """
    ),
]


with dag:
    START = DummyOperator(task_id="start")

    NCI_DB_MAINTENANCE = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        arguments=MAINTENANCE_SCRIPT,
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
