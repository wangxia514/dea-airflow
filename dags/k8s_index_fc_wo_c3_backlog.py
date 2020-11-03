"""
# Sentinel-2 backlog indexing automation

DAG to index Sentinel-2 backlog data.

"""
from datetime import datetime, timedelta
from textwrap import dedent

import kubernetes.client.models as k8s
from airflow import DAG
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.kubernetes.secret import Secret
from airflow.operators.subdag_operator import SubDagOperator

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
TASK_ARGS = {
    "secrets": DEFAULT_ARGS["secrets"],
    "start_date": DEFAULT_ARGS["start_date"],
}

INDEXER_IMAGE = "opendatacube/datacube-index:0.0.12"


def load_subdag(parent_dag_name, child_dag_name, product, rows, args):
    """
    Make us a subdag to hide all the sub tasks
    """
    subdag = DAG(
        dag_id=f"{parent_dag_name}.{child_dag_name}", default_args=args, catchup=False
    )

    with subdag:
        for row in rows:
            # for path in paths:
            INDEXING = KubernetesPodOperator(
                namespace="processing",
                image=INDEXER_IMAGE,
                image_pull_policy="Always",
                arguments=[
                    "s3-to-dc",
                    "--stac",
                    "--no-sign-request",
                    f"s3://dea-public-data/derivative/{product}/{row}/**/*.json",
                    " ".join(products),
                ],
                labels={"backlog": "s3-to-dc"},
                name="datacube-index",
                task_id=f"{product}--Backlog-indexing-row--{row}",
                get_logs=True,
                is_delete_operator_pod=True,
                dag=subdag,
            )
    return subdag


DAG_NAME = "k8s_index_wo_fc_c3_backlog"

dag = DAG(
    dag_id=DAG_NAME,
    default_args=DEFAULT_ARGS,
    schedule_interval=DEFAULT_ARGS["schedule_interval"],
    tags=["k8s", "landsat_c3", "backlog"],
    catchup=False,
)

with dag:
    # Rows should be from 88 to 116, and paths from 67 to 91
    # paths = range(88, 117)
    rows = range(67, 92)
    products = ["ga_ls_fc_3", "ga_ls_wo_3"]

    for product in products:
        TASK_NAME = f"{product}--backlog"
        index_backlog = SubDagOperator(
            task_id=TASK_NAME,
            subdag=load_subdag(DAG_NAME, TASK_NAME, product, rows, TASK_ARGS),
            default_args=TASK_ARGS,
            dag=dag,
        )
