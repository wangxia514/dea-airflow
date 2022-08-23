"""
# Run tasks to monitor NCI resource usage
"""
# pylint: skip-file
from datetime import datetime as dt, timedelta

from airflow import DAG
from automated_reporting import k8s_secrets, utilities

ENV = "prod"
ETL_IMAGE = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls:v2.7.0"

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt(2022, 8, 23),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": True if ENV == "prod" else False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

# A 2 hour minute cycle dag for nci resource
rapid_dag = DAG(
    "rep_nci_resource_monitoring" + "_" + ENV,
    description="DAG for monitoring resource usage on the NCI",
    tags=["reporting"] if ENV == "prod" else ["reporting_dev"],
    default_args=default_args,
    schedule_interval="5 */2 * * *",
)

with rapid_dag:

    nci_storage = utilities.k8s_operator(
        dag=rapid_dag,
        image=ETL_IMAGE,
        task_id="nci-storage-ingestion",
        task_concurrency=1,
        cmds=utilities.configure_ssh_cmds("LPGS_COMMAND_KEY")
        + [
            "echo Running command in NCI via SSH",
            'ssh -o StrictHostKeyChecking=no -o "IdentitiesOnly=yes" -i ~/.ssh/identity_file.pem \
                $NCI_TUNNEL_USER@$NCI_TUNNEL_HOST cat $NCI_DATA_CSV > $STORAGE_DATA_FILE',
            "echo NCI Storage Ingestion job started: $(date)",
            "nci-storage-ingestion",
        ],
        env_vars={
            "STORAGE_DATA_FILE": "/tmp/storage.csv",
            "NCI_DATA_CSV": "/scratch/v10/usage_reports/ga_storage_usage_latest.csv",
        },
        secrets=k8s_secrets.db_secrets(ENV) + k8s_secrets.nci_command_secrets,
    )

    nci_compute = utilities.k8s_operator(
        dag=rapid_dag,
        image=ETL_IMAGE,
        task_id="nci-compute-ingestion",
        task_concurrency=1,
        cmds=utilities.configure_ssh_cmds("LPGS_COMMAND_KEY")
        + [
            "echo Running command in NCI via SSH",
            'ssh -o StrictHostKeyChecking=no -o "IdentitiesOnly=yes" -i ~/.ssh/identity_file.pem \
                $NCI_TUNNEL_USER@$NCI_TUNNEL_HOST cat $NCI_DATA_CSV > $COMPUTE_DATA_FILE',
            "echo NCI Compute Ingestion job started: $(date)",
            "nci-compute-ingestion",
        ],
        env_vars={
            "COMPUTE_DATA_FILE": "/tmp/storage.csv",
            "NCI_DATA_CSV": "/home/547/lpgs/project_ksu.log",
        },
        secrets=k8s_secrets.db_secrets(ENV) + k8s_secrets.nci_command_secrets,
    )

    nci_storage
    nci_compute
