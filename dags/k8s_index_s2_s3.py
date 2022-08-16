"""
# S3 to Datacube Indexing

DAG to run indexing for Sentinel-2 data on S3 into AWS DB.

This DAG uses k8s executors and pre-existing pods in cluster with relevant tooling
and configuration installed.

The DAG has to be parameterized with index date as below.

    "index_date": "2020-05-01"
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from airflow.kubernetes.secret import Secret


DEFAULT_ARGS = {
    "owner": "Damien Ayers",
    "depends_on_past": False,
    "start_date": datetime(2020, 2, 21),
    "email": ["damien.ayers@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 0,
    "retry_delay": timedelta(minutes=5),
    "env_vars": {
        "AWS_DEFAULT_REGION": "ap-southeast-2",
        # TODO: Pass these via templated params in DAG Run
        "DB_HOSTNAME": "db-writer",
        "DB_DATABASE": "ows-index",
    },
    # Use K8S secrets to send DB Creds
    # Lift secrets into environment variables for datacube
    "secrets": [
        Secret("env", "DB_USERNAME", "ows-db", "postgres-username"),
        Secret("env", "DB_PASSWORD", "ows-db", "postgres-password"),
    ],
}


INDEXER_IMAGE = "opendatacube/datacube-index:0.0.5"
EXPLORER_IMAGE = "opendatacube/explorer:2.1.9"

dag = DAG(
    "k8s_index_s2_s3",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,
    catchup=False,
    tags=["k8s", "sentinel_2"],
)


with dag:

    # TODO: Bootstrap if targeting a Blank DB
    # TODO: Initialize Datacube
    # TODO: Add metadata types
    # TODO: Add products
    BOOTSTRAP = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        cmds=["datacube", "product", "list"],
        labels={"step": "bootstrap"},
        name="odc-bootstrap",
        task_id="bootstrap-task",
        get_logs=True,
    )

    ADD_PRODUCT = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        cmds=["datacube", "product", "add"],
        arguments=[
            "https://raw.githubusercontent.com/GeoscienceAustralia/dea-config/"
            "9c12bb30bff1f81ccd2a94e2c5052288688c55d1/products/ga_s2_ard_nbar/ga_s2_ard_nbar_granule.yaml"
        ],
        labels={"step": "add-product"},
        name="odc-add-product",
        task_id="add-product-task",
        get_logs=True,
    )

    INDEXING = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        cmds=["s3-to-dc"],
        # Assume kube2iam role via annotations
        # TODO: Pass this via DAG parameters
        annotations={"iam.amazonaws.com/role": "svc-dea-dev-eks-processing-index"},
        # TODO: Collect form JSON used to trigger DAG
        arguments=[
            "s3://dea-public-data-dev/L2/sentinel-2-nbar/S2MSIARD_NBAR/{{ dag_run.conf.index_date }}/*/*.yaml",
            "ga_s2a_ard_nbar_granule",
            "ga_s2b_ard_nbar_granule",
        ],
        labels={"step": "s3-to-rds"},
        name="datacube-index-s2-nbar",
        task_id="indexing-task",
        get_logs=True,
    )

    BOOTSTRAP >> ADD_PRODUCT
    ADD_PRODUCT >> INDEXING
