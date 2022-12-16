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

from automated_reporting import k8s_secrets, utilities

ENV = "prod"
ETL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls:v2.19.0"
)

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt(2022, 8, 19),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": True if ENV == "prod" else False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

# A 15 minute cycle dag for USGS monitoring
rapid_dag = DAG(
    "rep_usgs_monitoring_rapid" + "_" + ENV,
    description="DAG for completeness and latency metric on USGS rapid mapping products",
    tags=["reporting"] if ENV == "prod" else ["reporting_dev"],
    default_args=default_args,
    schedule_interval="*/15 * * * *",
)

with rapid_dag:

    # Get last n days of acquisitions from USGS M2M API and cache in S3
    # LS8 RT and LS9 T1/T2
    usgs_acquisitions = utilities.k8s_operator(
        dag=rapid_dag,
        image=ETL_IMAGE,
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
        secrets=k8s_secrets.m2m_api_secrets
        + k8s_secrets.s3_automated_operation_bucket
        + k8s_secrets.iam_rep_secrets,
        labels={
            "sub-system": "reporting",
            "products": "usgs_ls8c_level1_nrt_c2...usgs_ls9c_level1_nrt_c2",
        },
    )

    # Insert cached acquisitions into dea.usgs_acquisitions table
    usgs_inserts = utilities.k8s_operator(
        dag=rapid_dag,
        image=ETL_IMAGE,
        task_id="usgs-inserts",
        cmds=[
            "echo DEA USGS Insert Acquisitions job started: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "usgs-inserts",
        ],
        env_vars={
            "USGS_ACQ_XCOM": "{{ task_instance.xcom_pull(task_ids=\
                'usgs-acquisitions', key='return_value') }}",
        },
        secrets=k8s_secrets.s3_automated_operation_bucket
        + k8s_secrets.iam_rep_secrets
        + k8s_secrets.db_secrets(ENV),
        labels={
            "sub-system": "reporting",
            "products": "usgs_ls8c_level1_nrt_c2...usgs_ls9c_level1_nrt_c2",
        },
    )

    # Insert cached acquisitions into high_granlarity.dataset table
    usgs_inserts_hg_l0 = utilities.k8s_operator(
        dag=rapid_dag,
        image=ETL_IMAGE,
        task_id="usgs-inserts-hg-l0",
        cmds=[
            "echo DEA USGS Insert Acquisitions job started: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "usgs-inserts-hg-l0",
        ],
        env_vars={
            "USGS_ACQ_XCOM": "{{ task_instance.xcom_pull(task_ids=\
                'usgs-acquisitions', key='return_value') }}",
        },
        secrets=k8s_secrets.s3_automated_operation_bucket
        + k8s_secrets.iam_rep_secrets
        + k8s_secrets.db_secrets(ENV),
        labels={
            "sub-system": "reporting",
            "products": "usgs_ls8c_level1_nrt_c2...usgs_ls9c_level1_nrt_c2",
        },
    )

    # Calculate USGS LS8 L1 NRT completeness, comparing LS8 RT acquisitions with S3 inventory
    usgs_l1_completness_ls8_product = dict(
        scene_prefix="LC8%", acq_categories=("RT",), rep_code="usgs_ls8c_level1_nrt_c2"
    )
    usgs_ls8_l1_completeness = utilities.k8s_operator(
        dag=rapid_dag,
        image=ETL_IMAGE,
        task_id="usgs-completeness-ls8-l1",
        xcom=True,
        cmds=[
            "echo DEA USGS Insert Acquisitions job started: $(date)",
            "parse-uri $REP_DB_URI /tmp/env; source /tmp/env",
            "mkdir -p /airflow/xcom/",
            "usgs-s3-completeness /airflow/xcom/return.json",
        ],
        env_vars={
            "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
            "DAYS": "30",
            "PRODUCT": json.dumps(usgs_l1_completness_ls8_product),
        },
        secrets=k8s_secrets.db_secrets(ENV),
        labels={"sub-system": "reporting", "products": "usgs_ls8c_level1_nrt_c2"},
    )

    # Calculate USGS LS9 L1 NRT completeness, comparing LS9 T1/T2 acquisitions with S3 inventory
    usgs_l1_completness_ls9_product = dict(
        scene_prefix="LC9%",
        acq_categories=("T1", "T2"),
        rep_code="usgs_ls9c_level1_nrt_c2",
    )
    usgs_ls9_l1_completeness = utilities.k8s_operator(
        dag=rapid_dag,
        image=ETL_IMAGE,
        task_id="usgs-completeness-ls9-l1",
        xcom=True,
        cmds=[
            "echo DEA USGS Insert Acquisitions job started: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "mkdir -p /airflow/xcom/",
            "usgs-s3-completeness /airflow/xcom/return.json",
        ],
        env_vars={
            "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
            "DAYS": "30",
            "PRODUCT": json.dumps(usgs_l1_completness_ls9_product),
        },
        secrets=k8s_secrets.db_secrets(ENV),
        labels={"sub-system": "reporting", "products": "usgs_ls9c_level1_nrt_c2"},
    )

    # Calculate USGS LS8 ARD NRT completeness, comparing acquisitions with ODC
    usgs_ard_completness_ls8_product = dict(
        odc_code="ga_ls8c_ard_provisional_3", acq_code="LC8%", acq_categories=("RT",)
    )
    usgs_ls8_ard_completeness = utilities.k8s_operator(
        dag=rapid_dag,
        image=ETL_IMAGE,
        task_id="usgs-completeness-ls8-ard",
        cmds=[
            "echo DEA USGS Insert Acquisitions job started: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "usgs-odc-completeness",
        ],
        env_vars={
            "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
            "DAYS": "30",
            "PRODUCT": json.dumps(usgs_ard_completness_ls8_product),
        },
        secrets=k8s_secrets.db_secrets(ENV) + k8s_secrets.aws_odc_secrets,
        labels={"sub-system": "reporting", "products": "ga_ls8c_ard_provisional_3"},
    )

    # Generate USGS LS8 L1 NRT currency from the result of completness
    # Needed as this product is not indexed into the ODC
    usgs_ls8_l1_currency = utilities.k8s_operator(
        dag=rapid_dag,
        image=ETL_IMAGE,
        task_id="usgs-currency-ls8-l1",
        cmds=[
            "echo DEA USGS Insert Acquisitions job started: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "usgs-currency-from-completeness",
        ],
        env_vars={
            "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
            "USGS_COMPLETENESS_XCOM": "{{ task_instance.xcom_pull(task_ids=\
                'usgs-completeness-ls8-l1', key='return_value') }}",
        },
        secrets=k8s_secrets.db_secrets(ENV),
        labels={"sub-system": "reporting", "products": "usgs_ls8c_level1_nrt_c2"},
    )

    # Generate USGS LS9 L1 NRT currency from the result of completness
    # Needed as this product is not indexed into the ODC
    usgs_ls9_l1_currency = utilities.k8s_operator(
        dag=rapid_dag,
        image=ETL_IMAGE,
        task_id="usgs-currency-ls9-l1",
        cmds=[
            "echo DEA USGS Insert Acquisitions job started: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "usgs-currency-from-completeness",
        ],
        env_vars={
            "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
            "USGS_COMPLETENESS_XCOM": "{{ task_instance.xcom_pull(task_ids=\
                'usgs-completeness-ls9-l1', key='return_value') }}",
        },
        secrets=k8s_secrets.db_secrets(ENV),
        labels={"sub-system": "reporting", "products": "usgs_ls9c_level1_nrt_c2"},
    )

    usgs_l1_nrt_downloads = utilities.k8s_operator(
        dag=rapid_dag,
        image=ETL_IMAGE,
        cmds=[
            "echo DEA USGS downloader job started: $(date)",
            "mkdir -p /airflow/xcom/",
            "usgs-l1-nrt-downloads /airflow/xcom/return.json",
        ],
        task_id="usgs_l1_nrt_downloads",
        xcom=True,
        env_vars={
            "QUEUE_NAME": "automated-reporting-ls-l1-nrt",
        },
        secrets=k8s_secrets.sqs_secrets,
        labels={
            "sub-system": "reporting",
            "products": "usgs_ls8c_level1_nrt_c2...usgs_ls9c_level1_nrt_c2",
        },
    )

    usgs_l1_nrt_inserts = utilities.k8s_operator(
        dag=rapid_dag,
        image=ETL_IMAGE,
        cmds=[
            "echo DEA USGS Ingestion job started: $(date)",
            "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
            "usgs-l1-nrt-ingestion",
        ],
        task_id="usgs_l1_nrt_inserts",
        env_vars={
            "METRICS": "{{ task_instance.xcom_pull(task_ids='usgs_l1_nrt_downloads') }}",
        },
        secrets=k8s_secrets.db_secrets(ENV),
        labels={
            "sub-system": "reporting",
            "products": "usgs_ls8c_level1_nrt_c2...usgs_ls9c_level1_nrt_c2",
        },
    )

    usgs_l1_nrt_downloads >> usgs_l1_nrt_inserts
    usgs_acquisitions >> usgs_inserts
    usgs_inserts >> usgs_ls8_ard_completeness
    (
        [usgs_inserts, usgs_l1_nrt_inserts]
        >> usgs_ls8_l1_completeness
        >> usgs_ls8_l1_currency
    )
    usgs_inserts >> usgs_ls9_l1_completeness >> usgs_ls9_l1_currency
    usgs_acquisitions >> usgs_inserts_hg_l0
