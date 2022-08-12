"""
# Run tasks to monitor USGS NRT Products

This DAG
 * Connects to USGS M2M API to determine USGS Inventory
 * Inserts data into reporting DB, in both hg and landsat schemas
 * Runs completeness and latency checks
 * Inserts summary completeness and latency reporting data
 * Inserts completeness data for each wrs path row
"""
import json
from datetime import datetime as dt, timedelta

from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from automated_reporting import k8s_secrets, utilities

ENV = "dev"
ETL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls-dev:latest"
)

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt.now() - timedelta(hours=1),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": True if ENV == "prod" else False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "secrets": k8s_secrets.s3_secrets
    + k8s_secrets.db_secrets(ENV)
    + k8s_secrets.aws_odc_secrets
    + k8s_secrets.m2m_api_secrets,
}

# A 15 minute cycle dag for USGS monitoring
daily_dag = DAG(
    "rep_usgs_monitoring_daily" + "_" + ENV,
    description="DAG for completeness metric on USGS definitive mapping products",
    tags=["reporting"] if ENV == "prod" else ["reporting-dev"],
    default_args=default_args,
    schedule_interval="@daily",
)


def k8s_operator(dag, task_id, cmds, env_vars, task_concurrency=None, xcom=False):
    """
    A helper function to save a few lines of code on the common kwargs for KubernetesPodOperator
    """
    return KubernetesPodOperator(
        namespace="processing",
        image=ETL_IMAGE,
        arguments=["bash", "-c", " &&\n".join(cmds)],
        name=task_id,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id=task_id,
        get_logs=True,
        do_xcom_push=xcom,
        task_concurrency=task_concurrency,
        env_vars=env_vars,
    )


with daily_dag:

    # Get last n (default 7) days of acquisitions from USGS M2M API and cache in S3
    # LS8 T1/T2 and LS9 T1/T2
    usgs_acquisitions = k8s_operator(
        dag=daily_dag,
        task_id="usgs-acquisitions",
        xcom=True,
        task_concurrency=1,
        cmds=[
            "echo DEA USGS Acquisitions job started: $(date)",
            "mkdir -p /airflow/xcom/",
            "usgs-acquisitions /airflow/xcom/return.json",
        ],
        env_vars={
            "DAYS": "{{ dag_run.conf['acquisition_days'] | default(7) }}",
            "CATEGORY": "def",  # query for definitive acquisitions
            "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
        },
    )

    # Insert cached acquisitions into dea.usgs_acquisitions table
    usgs_inserts = k8s_operator(
        dag=daily_dag,
        task_id="usgs-inserts",
        cmds=[
            "echo DEA USGS Insert Acquisitions job started: $(date)",
            "usgs-inserts",
        ],
        env_vars={
            "USGS_ACQ_XCOM": "{{ task_instance.xcom_pull(task_ids=\
                'usgs-acquisitions', key='return_value') }}",
        },
    )

    # NB. Not inserting cached acquisitions into high_granlarity.dataset table for
    #     definitive products at this time.

    # usgs_ls8_l1_nci_completeness
    # Calculate USGS LS8 ARD NRT completeness, comparing acquisitions with ODC
    usgs_ls8_l1_nci_product = dict(
        acq_code="LC8%", acq_categories=("T1", "T2"), odc_code="usgs_ls8c_level1_2"
    )
    usgs_ls8_l1_nci_completeness = k8s_operator(
        dag=daily_dag,
        task_id="usgs-completeness-ls8-ard",
        cmds=utilities.NCI_TUNNEL_CMDS
        + [
            "echo DEA USGS Completeness Job: $(date)",
            "export ODC_DB_HOST=localhost",
            "export ODC_DB_PORT=54320",
            "usgs-odc-completeness",
        ],
        env_vars={
            "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
            "DAYS": "90",
            "PRODUCT": json.dumps(usgs_ls8_l1_nci_product),
        },
    )

    # usgs_ls9_l1_nci_completeness (not indexed yet)

    # usgs_ls8_ard_aws_completeness
    # usgs_ls8_ard_nci_completeness

    usgs_acquisitions >> usgs_inserts
    usgs_inserts >> usgs_ls8_l1_nci_completeness
    # usgs_inserts >> usgs_ls8_ard_aws_completeness
    # usgs_inserts >> usgs_ls8_ard_nci_completeness
