"""
# Sentinel-2 backlog indexing automation

DAG to index Sentinel-2 backlog data.

"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator

from textwrap import dedent

import kubernetes.client.models as k8s

DEFAULT_ARGS = {
    "owner": "Alex Leith",
    "depends_on_past": False,
    "start_date": datetime(2020, 6, 14),
    "email": ["alex.leith@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "schedule_interval": "@once",
    "retry_delay": timedelta(minutes=5),
    "env_vars": {
        "DB_HOSTNAME": "db-writer",
        "WMS_CONFIG_PATH": "/env/config/ows_cfg.py",
        "DATACUBE_OWS_CFG": "config.ows_cfg.ows_cfg",
    },
    "secrets": [
        Secret(
            "env",
            "DB_USERNAME",
            "ows-db",
            "postgres-username",
        ),
        Secret(
            "env",
            "DB_PASSWORD",
            "ows-db",
            "postgres-password",
        ),
    ],
}

INDEXER_IMAGE = "opendatacube/datacube-index:0.0.12"

dag = DAG(
    "Sentinel-2_indexing",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    catchup=False,
    tags=["k8s", "landsat_c3"],
)

dag = DAG(
    "Sentinel-2-backlog-indexing",
    default_args=DEFAULT_ARGS,
    schedule_interval=DEFAULT_ARGS["schedule_interval"],
    tags=["Sentinel-2", "indexing"],
    catchup=False,
)

with dag:
    # This needs to be updated in the future in case more zones have been added
    # Rows should be from 88 to 116, and paths from 67 to 91
    paths = range(88, 117)
    rows = range(67, 92)
    products = ["ga_ls_fc_3", "ga_ls_wo_3"]
    utm_zones = range(26, 42)
    for path in paths:
        for row in rows:
            for product in products:
                INDEXING = KubernetesPodOperator(
                    namespace="processing",
                    image=INDEXER_IMAGE,
                    image_pull_policy="Always",
                    arguments=[
                        "s3-to-dc",
                        "--stac",
                        "--no-sign-request",
                        f"s3://dea-public-data/derivative/{product}/{row}/{path}/**/*.json",
                        " ".join(products),
                    ],
                    labels={"backlog": "s3-to-dc"},
                    name="datacube-index",
                    task_id=f"Sentinel-2-backlog-indexing-task-{product}-{path}-{row}",
                    get_logs=True,
                    is_delete_operator_pod=True,
                )
