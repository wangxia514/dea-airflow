"""
# Thredds to Datacube Indexing

DAG to periodically/one-shot update explorer and ows schemas in RDS
after a given Dataset has been indexed from Thredds

- Run Explorer summaries
- Run ows update ranges for ARD products
- Run ows update ranges for ARD multi-products

This DAG uses k8s executors and fresh pods in cluster with relevant tooling
and configuration installed.

The DAG has to be parameterized with Thredds catalog root and Target products as below.
The lineage indexing strategy also has to be passed in.

    "params" : "--auto-add-lineage",
    "thredds_catalog": "http://dapds00.nci.org.au/thredds/catalog/if87/2018-11-29/",
    "products": "s2a_ard_granule s2a_level1c_granule s2b_ard_granule s2b_level1c_granule"

"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from airflow.kubernetes.secret import Secret
from airflow.operators.dummy_operator import DummyOperator


DEFAULT_ARGS = {
    "owner": "Tisham Dhar",
    "depends_on_past": False,
    "start_date": datetime(2020, 3, 4),
    "email": ["tisham.dhar@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "env_vars": {
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
OWS_IMAGE = "opendatacube/ows:1.8.0"
EXPLORER_IMAGE = "opendatacube/explorer:2.1.9"

dag = DAG(
    "k8s_thredds_orchestrate",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,
    catchup=False,
    tags=["k8s"],
)


with dag:
    START = DummyOperator(task_id="thredds_index_publish")

    # TODO: Bootstrap if targeting a Blank DB
    # TODO: Initialize Datacube
    # TODO: Add metadata types
    # TODO: Add products
    BOOTSTRAP = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        cmds=["datacube", "system", "check"],
        labels={"step": "bootstrap"},
        name="odc-bootstrap",
        task_id="bootstrap-task",
        get_logs=True,
    )

    """
    {
        "params" : "--auto-add-lineage",
        "thredds_catalog": "http://dapds00.nci.org.au/thredds/catalog/if87/2018-11-29/",
        "products": "s2a_ard_granule s2a_level1c_granule s2b_ard_granule s2b_level1c_granule"
    }
    """
    INDEXING = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        cmds=["thredds-to-dc"],
        # TODO: Collect form JSON used to trigger DAG
        arguments=[
            "{{ dag_run.conf.params}}",
            "{{ dag_run.conf.thredds_catalog }}",
            "{{ dag_run.conf.products }}",
        ],
        labels={"step": "thredds-to-rds"},
        name="datacube-index",
        task_id="indexing-task",
        get_logs=True,
    )

    UPDATE_RANGES = KubernetesPodOperator(
        namespace="processing",
        image=OWS_IMAGE,
        cmds=["datacube-ows-update"],
        arguments=["--help"],
        labels={"step": "ows"},
        name="ows-update-ranges",
        task_id="update-ranges-task",
        get_logs=True,
    )

    SUMMARY = KubernetesPodOperator(
        namespace="processing",
        image=EXPLORER_IMAGE,
        cmds=["cubedash-gen"],
        arguments=["--help"],
        labels={"step": "explorer"},
        name="explorer-summary",
        task_id="explorer-summary-task",
        get_logs=True,
    )

    COMPLETE = DummyOperator(task_id="all_done")

    START >> BOOTSTRAP
    BOOTSTRAP >> INDEXING
    INDEXING >> UPDATE_RANGES
    INDEXING >> SUMMARY
    UPDATE_RANGES >> COMPLETE
    SUMMARY >> COMPLETE
