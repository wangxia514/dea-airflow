"""
# Landsat Collection-3 indexing automation for odc db

DAG to periodically index/archive Landsat Collection-3 data.

This DAG uses k8s executors and in cluster with relevant tooling
and configuration installed.

"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.kubernetes.secret import Secret
from airflow.operators.subdag_operator import SubDagOperator
from infra.variables import (
    DB_DATABASE,
    DB_HOSTNAME,
    SECRET_ODC_WRITER_NAME,
)
from infra.images import INDEXER_IMAGE


DEFAULT_ARGS = {
    "owner": "KieranRIcardo",
    "depends_on_past": False,
    "start_date": datetime(2020, 6, 14),
    "email": ["kieran.ricardo@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "env_vars": {
        "DB_HOSTNAME": DB_HOSTNAME,
        "DB_DATABASE": DB_DATABASE,
    },
    "secrets": [
        Secret(
            "env",
            "DB_USERNAME",
            SECRET_ODC_WRITER_NAME,
            "postgres-username",
        ),
        Secret(
            "env",
            "DB_PASSWORD",
            SECRET_ODC_WRITER_NAME,
            "postgres-password",
        ),
    ],
}

TASK_ARGS = {
    "secrets": DEFAULT_ARGS["secrets"],
    "env_vars": DEFAULT_ARGS["env_vars"],
    "start_date": DEFAULT_ARGS["start_date"],
}


def load_subdag(parent_dag_name, child_dag_name, product, rows, args):
    """
    Make us a subdag to hide all the sub tasks
    """
    subdag = DAG(
        dag_id=f"{parent_dag_name}.{child_dag_name}", default_args=args, catchup=False
    )

    with subdag:
        for row in rows:
            INDEXING = KubernetesPodOperator(
                namespace="processing",
                image=INDEXER_IMAGE,
                image_pull_policy="Always",
                arguments=[
                    "s3-to-dc",
                    "--stac",
                    "--no-sign-request",
                    "--skip-lineage",
                    f"s3://dea-public-data/baseline/{product}/{row:03d}/**/*.json",
                    product,
                ],
                labels={"backlog": "s3-to-dc"},
                name="datacube-index",
                task_id=f"{product}--Backlog-indexing-row--{row}",
                get_logs=True,
                is_delete_operator_pod=True,
                dag=subdag,
            )
    return subdag


DAG_NAME = "k8s_index_ls_c3_backlog_odc"

dag = DAG(
    dag_id=DAG_NAME,
    default_args=DEFAULT_ARGS,
    schedule_interval="@once",
    tags=["k8s", "landsat_c3", "backlog"],
    catchup=False,
)

with dag:
    rows = range(88, 117)
    products = ["ga_ls5t_ard_3", "ga_ls7e_ard_3", "ga_ls8c_ard_3"]

    for product in products:
        TASK_NAME = f"{product}--backlog"
        index_backlog = SubDagOperator(
            task_id=TASK_NAME,
            subdag=load_subdag(DAG_NAME, TASK_NAME, product, rows, TASK_ARGS),
            default_args=TASK_ARGS,
            dag=dag,
        )
