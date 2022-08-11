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
from automated_reporting import k8s_secrets

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
rapid_dag = DAG(
    "rep_usgs_monitoring_rapid" + "_" + ENV,
    description="DAG for completeness and latency metric on USGS rapid mapping products",
    tags=["reporting"] if ENV == "prod" else ["reporting-dev"],
    default_args=default_args,
    schedule_interval="*/15 * * * *",
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


with rapid_dag:

    # Get last n days of acquisitions from USGS M2M API and cache in S3
    # LS8 RT and LS9 T1/T2
    usgs_acquisitions = k8s_operator(
        dag=rapid_dag,
        task_id="usgs-acquisitions",
        xcom=True,
        task_concurrency=1,
        cmds=[
            "echo DEA USGS Acquisitions job started: $(date)",
            "mkdir -p /airflow/xcom/",
            "usgs-acquisitions /airflow/xcom/return.json",
        ],
        env_vars={
            "DAYS": "{{ dag_run.conf['acquisition_days'] | default(3) }}",
            "CATEGORY": "nrt",
            "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
        },
    )

    # Insert cached acquisitions into dea.usgs_acquisitions table
    usgs_inserts = k8s_operator(
        dag=rapid_dag,
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

    # Insert cached acquisitions into high_granlarity.dataset table
    usgs_inserts_hg_l0 = k8s_operator(
        dag=rapid_dag,
        task_id="usgs-inserts-hg-l0",
        cmds=[
            "echo DEA USGS Insert Acquisitions job started: $(date)",
            "usgs-inserts-hg-l0",
        ],
        env_vars={
            "USGS_ACQ_XCOM": "{{ task_instance.xcom_pull(task_ids=\
                'usgs-acquisitions', key='return_value') }}",
        },
    )

    # Calculate USGS LS8 L1 NRT completeness, comparing LS8 RT acquisitions with S3 inventory
    usgs_l1_completness_ls8_product = dict(
        scene_prefix="LC8%", acq_categories=("RT",), rep_code="usgs_ls8c_level1_nrt_c2"
    )
    usgs_ls8_l1_completeness = k8s_operator(
        dag=rapid_dag,
        task_id="usgs-completeness-ls8-l1",
        xcom=True,
        cmds=[
            "echo DEA USGS Insert Acquisitions job started: $(date)",
            "mkdir -p /airflow/xcom/",
            "usgs-l1-completeness /airflow/xcom/return.json",
        ],
        env_vars={
            "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
            "DAYS": "30",
            "PRODUCT": json.dumps(usgs_l1_completness_ls8_product),
        },
    )

    # Calculate USGS LS9 L1 NRT completeness, comparing LS9 T1/T2 acquisitions with S3 inventory
    usgs_l1_completness_ls9_product = dict(
        scene_prefix="LC9%",
        acq_categories=("T1", "T2"),
        rep_code="usgs_ls9c_level1_nrt_c2",
    )
    usgs_ls9_l1_completeness = k8s_operator(
        dag=rapid_dag,
        task_id="usgs-completeness-ls9-l1",
        xcom=True,
        cmds=[
            "echo DEA USGS Insert Acquisitions job started: $(date)",
            "mkdir -p /airflow/xcom/",
            "usgs-l1-completeness /airflow/xcom/return.json",
        ],
        env_vars={
            "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
            "DAYS": "30",
            "PRODUCT": json.dumps(usgs_l1_completness_ls9_product),
        },
    )

    # Calculate USGS LS8 ARD NRT completeness, comparing acquisitions with ODC
    usgs_ard_completness_ls8_product = dict(
        odc_code="ga_ls8c_ard_provisional_3", acq_code="LC8%", acq_categories=("RT",)
    )
    usgs_ls8_ard_completeness = k8s_operator(
        dag=rapid_dag,
        task_id="usgs-completeness-ls8-ard",
        cmds=[
            "echo DEA USGS Insert Acquisitions job started: $(date)",
            "usgs-ard-completeness",
        ],
        env_vars={
            "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
            "DAYS": "30",
            "PRODUCT": json.dumps(usgs_ard_completness_ls8_product),
        },
    )

    # Generate USGS LS8 L1 NRT currency from the result of completness
    # Needed as this product is not indexed into the ODC
    usgs_ls8_l1_currency = k8s_operator(
        dag=rapid_dag,
        task_id="usgs-currency-ls8-l1",
        cmds=[
            "echo DEA USGS Insert Acquisitions job started: $(date)",
            "usgs-currency-from-completeness",
        ],
        env_vars={
            "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
            "USGS_COMPLETENESS_XCOM": "{{ task_instance.xcom_pull(task_ids=\
                'usgs-completeness-ls8-l1', key='return_value') }}",
        },
    )

    # Generate USGS LS9 L1 NRT currency from the result of completness
    # Needed as this product is not indexed into the ODC
    usgs_ls9_l1_currency = k8s_operator(
        dag=rapid_dag,
        task_id="usgs-currency-ls9-l1",
        cmds=[
            "echo DEA USGS Insert Acquisitions job started: $(date)",
            "usgs-currency-from-completeness",
        ],
        env_vars={
            "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
            "USGS_COMPLETENESS_XCOM": "{{ task_instance.xcom_pull(task_ids=\
                'usgs-completeness-ls9-l1', key='return_value') }}",
        },
    )

    usgs_acquisitions >> usgs_inserts
    usgs_inserts >> usgs_ls8_ard_completeness
    usgs_inserts >> usgs_ls8_l1_completeness >> usgs_ls8_l1_currency
    usgs_inserts >> usgs_ls9_l1_completeness >> usgs_ls9_l1_currency
    usgs_acquisitions >> usgs_inserts_hg_l0
