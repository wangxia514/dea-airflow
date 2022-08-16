# -*- coding: utf-8 -*-
"""
DEA Currency Dags
"""

# The DAG object; we'll need this to instantiate a DAG
import json
from datetime import datetime as dt, timedelta
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from airflow.operators.dummy import DummyOperator
from airflow.models import Variable

default_args = {
    "owner": "Tom McAdam",
    "depends_on_past": False,
    "start_date": dt(2022, 8, 1),
    "email": ["tom.mcadam@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retry_delay": timedelta(minutes=5),
    "retries": 2,
}

ETL_IMAGE = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/ga-reporting-etls:v2.5.1"

REPORTING_DB_SECRET = "reporting-db"

nci_odc_secrets = [
    Secret("volume", "/var/secrets/lpgs", "lpgs-port-forwarder", "PORT_FORWARDER_KEY"),
    Secret("env", "NCI_TUNNEL_HOST", "reporting-nci-tunnel", "NCI_HOST"),
    Secret("env", "NCI_TUNNEL_USER", "reporting-nci-tunnel", "NCI_USER"),
    Secret("env", "ODC_DB_HOST", "reporting-nci-odc-db", "DB_HOST"),
    Secret("env", "ODC_DB_NAME", "reporting-nci-odc-db", "DB_NAME"),
    Secret("env", "ODC_DB_PORT", "reporting-nci-odc-db", "DB_PORT"),
    Secret("env", "ODC_DB_USER", "reporting-nci-odc-db", "DB_USER"),
    Secret("env", "ODC_DB_PASSWORD", "reporting-nci-odc-db", "DB_PASSWORD"),
]
aws_odc_secrets = [
    Secret("env", "ODC_DB_HOST", "reporting-odc-db", "DB_HOST"),
    Secret("env", "ODC_DB_NAME", "reporting-odc-db", "DB_NAME"),
    Secret("env", "ODC_DB_PORT", "reporting-odc-db", "DB_PORT"),
    Secret("env", "ODC_DB_USER", "reporting-odc-db", "DB_USER"),
    Secret("env", "ODC_DB_PASSWORD", "reporting-odc-db", "DB_PASSWORD"),
]
rep_db_secrets = [
    Secret("env", "DB_HOST", REPORTING_DB_SECRET, "DB_HOST"),
    Secret("env", "DB_NAME", REPORTING_DB_SECRET, "DB_NAME"),
    Secret("env", "DB_PORT", REPORTING_DB_SECRET, "DB_PORT"),
    Secret("env", "DB_USER", REPORTING_DB_SECRET, "DB_USER"),
    Secret("env", "DB_PASSWORD", REPORTING_DB_SECRET, "DB_PASSWORD"),
]

monthly_dag = DAG(
    "rep_dea_currency_monthly_prod",
    default_args=default_args,
    description="DAG for currency of dea products (run monthly)",
    tags=["reporting"],
    schedule_interval="@monthly",
)

daily_dag = DAG(
    "rep_dea_currency_daily_prod",
    default_args=default_args,
    description="DAG for currency of dea products (run daily)",
    tags=["reporting"],
    schedule_interval="@daily",
)

rapid_dag = DAG(
    "rep_dea_currency_rapid_prod",
    default_args=default_args,
    description="DAG for currency of dea products (run 15mins)",
    tags=["reporting"],
    schedule_interval="*/15 * * * *",
)

NCI_ODC_CURRENCY_JOB = [
    "echo Configuring SSH",
    "mkdir -p ~/.ssh",
    "cat /var/secrets/lpgs/PORT_FORWARDER_KEY > ~/.ssh/identity_file.pem",
    "chmod 0400 ~/.ssh/identity_file.pem",
    "echo Establishing NCI tunnel",
    "ssh -o StrictHostKeyChecking=no -f -N -i ~/.ssh/identity_file.pem -L 54320:$ODC_DB_HOST:$ODC_DB_PORT $NCI_TUNNEL_USER@$NCI_TUNNEL_HOST",
    "echo NCI tunnel established",
    "echo DEA NCI ODC Currency job started: $(date)",
    "export ODC_DB_HOST=localhost",
    "export ODC_DB_PORT=54320",
    "odc-currency-views",
]
AWS_ODC_CURRENCY_JOB = [
    "echo DEA ODC Currency job started: $(date)",
    "odc-currency",
]
SNS_CURRENCY_JOB = [
    "echo DEA ODC Currency job started: $(date)",
    "sns-currency",
]


def create_operator(method, dag, job, env_vars, secrets):
    """
    Create a K8S Operator
    """
    task_id = f"{method}-{env_vars['PRODUCT_ID']}"
    if "PRODUCT_SUFFIX" in env_vars:
        task_id = f"{task_id}-{env_vars['PRODUCT_SUFFIX']}"
    return KubernetesPodOperator(
        dag=dag,
        namespace="processing",
        image=ETL_IMAGE,
        arguments=["bash", "-c", " &&\n".join(job)],
        name=task_id,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id=task_id,
        get_logs=True,
        env_vars=env_vars,
        secrets=secrets,
    )


def create_odc_task(dag, job, product_id, days, odc_secrets, product_suffix=None):
    """
    Function to generate KubernetesPodOperator tasks with id based on `product_id`
    """
    env_vars = {
        "PRODUCT_ID": product_id,
        "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
    }
    if days:
        env_vars["DAYS"] = str(days)
    if product_suffix:
        env_vars["PRODUCT_SUFFIX"] = product_suffix
    secrets = rep_db_secrets + odc_secrets
    return create_operator("odc", dag, job, env_vars, secrets)


def create_sns_task(dag, product_id, pipeline):
    """
    Function to generate KubernetesPodOperator tasks with id based on `product_id`
    """
    env_vars = {
        "PRODUCT_ID": product_id,
        "PIPELINE": pipeline,
        "DATA_INTERVAL_END": "{{  dag_run.data_interval_end | ts  }}",
    }
    secrets = rep_db_secrets
    return create_operator("sns", dag, SNS_CURRENCY_JOB, env_vars, secrets)


with monthly_dag:

    START_MONTHLY = DummyOperator(task_id="dea-currency-monthly")

    nci_monthly_products_list = [
        x
        for x in json.loads(Variable.get("rep_currency_product_list_nci_odc"))
        if x["rate"] == "monthly"
    ]
    monthly_nci_odc_tasks = [
        create_odc_task(
            monthly_dag,
            NCI_ODC_CURRENCY_JOB,
            product["product_id"],
            product.get("days"),
            nci_odc_secrets,
        )
        for product in nci_monthly_products_list
    ]
    START_MONTHLY >> monthly_nci_odc_tasks


with daily_dag:

    START_DAILY = DummyOperator(task_id="dea-currency-daily")

    # Product list to extract the metric for, could potentially be part of dag configuration and managed in airflow UI?
    aws_products_list = [
        # Baseline
        "ga_ls7e_ard_3",
        "ga_ls8c_ard_3",
        "s2a_ard_granule",
        "s2b_ard_granule",
        # Derivavtives
        "ga_ls_wo_3",
        "ga_ls_fc_3",
        "ga_ls8c_nbart_gm_cyear_3",
        "ga_ls7e_nbart_gm_cyear_3",
        "ga_ls_wo_fq_cyear_3",
        "ga_ls_wo_fq_apr_oct_3",
        "ga_ls_wo_fq_nov_mar_3",
    ]

    nci_daily_products_list = [
        x
        for x in json.loads(Variable.get("rep_currency_product_list_nci_odc"))
        if x["rate"] == "daily"
    ]

    # Generate a task for each product
    daily_aws_odc_tasks = [
        create_odc_task(
            daily_dag, AWS_ODC_CURRENCY_JOB, product_id, 90, aws_odc_secrets, "aws"
        )
        for product_id in aws_products_list
    ]
    daily_nci_odc_tasks = [
        create_odc_task(
            daily_dag,
            NCI_ODC_CURRENCY_JOB,
            product["product_id"],
            product.get("days"),
            nci_odc_secrets,
        )
        for product in nci_daily_products_list
    ]

    daily_odc_tasks = daily_aws_odc_tasks + daily_nci_odc_tasks
    START_DAILY >> daily_odc_tasks


with rapid_dag:

    START_RAPID = DummyOperator(task_id="dea-currency-rapid")

    # Product list to extract the metric for, could potentially be part of dag configuration and managed in airflow UI?
    odc_products_list = [
        "s2a_nrt_granule",
        "s2b_nrt_granule",
        "ga_s2_wo_3",
        "ga_ls7e_ard_provisional_3",
        "ga_ls8c_ard_provisional_3",
        "ga_s2am_ard_provisional_3",
        "ga_s2bm_ard_provisional_3",
        "ga_s2_ba_provisional_3",
    ]
    sns_products_list = [
        ("S2A_MSIL1C", "esa_s2a_msi_l1c"),
        ("S2B_MSIL1C", "esa_s2b_msi_l1c"),
    ]

    rapid_odc_tasks = [
        create_odc_task(
            rapid_dag, AWS_ODC_CURRENCY_JOB, product_id, 30, aws_odc_secrets
        )
        for product_id in odc_products_list
    ]
    rapid_sns_tasks = [
        create_sns_task(rapid_dag, product_id, pipeline)
        for pipeline, product_id in sns_products_list
    ]
    START_RAPID >> rapid_odc_tasks
    START_RAPID >> rapid_sns_tasks
