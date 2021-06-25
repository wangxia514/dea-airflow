"""
# Landsat C3 backlog indexing

"""
from datetime import datetime, timedelta

import kubernetes.client.models as k8s
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from airflow.kubernetes.secret import Secret
from airflow.operators.subdag_operator import SubDagOperator
from infra.variables import SECRET_ODC_WRITER_NAME, DB_HOSTNAME
from infra.images import INDEXER_IMAGE
from infra.podconfig import ONDEMAND_NODE_AFFINITY

DEFAULT_ARGS = {
    "owner": "Alex Leith",
    "depends_on_past": False,
    "start_date": datetime(2020, 6, 14),
    "email": ["alex.leith@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
    "retry_delay": timedelta(minutes=5),
    "env_vars": {
        "DB_HOSTNAME": DB_HOSTNAME,
    },
    "secrets": [
        Secret(
            "env",
            "DB_DATABASE",
            SECRET_ODC_WRITER_NAME,
            "database-name",
        ),
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
    "env_vars": DEFAULT_ARGS["env_vars"],
    "secrets": DEFAULT_ARGS["secrets"],
    "start_date": DEFAULT_ARGS["start_date"],
}


def load_subdag(parent_dag_name, child_dag_name, product, bucket_path, paths, args):
    """
    Make us a subdag to hide all the sub tasks
    """
    subdag = DAG(
        dag_id=f"{parent_dag_name}.{child_dag_name}", default_args=args, catchup=False
    )

    with subdag:
        for path in paths:
            # for path in paths:
            INDEXING = KubernetesPodOperator(
                namespace="processing",
                image=INDEXER_IMAGE,
                image_pull_policy="Always",
                arguments=[
                    "s3-to-dc",
                    "--stac",
                    "--no-sign-request",
                    f"s3://dea-public-data/{bucket_path}/{product}/{path:03d}/**/*.json",
                    "--skip-lineage",
                    product,
                ],
                labels={"backlog": "s3-to-dc"},
                name=f"datacube-index-{product}-{path}",
                task_id=f"{product}--Backlog-indexing-row--{path}",
                get_logs=True,
                is_delete_operator_pod=True,
                affinity=ONDEMAND_NODE_AFFINITY,
                dag=subdag,
            )
    return subdag


DAG_NAME = "k8s_index_c3_backlog"

dag = DAG(
    dag_id=DAG_NAME,
    default_args=DEFAULT_ARGS,
    schedule_interval="@once",
    tags=["k8s", "landsat_c3", "backlog"],
    catchup=False,
)

with dag:
    products = ["ga_ls8c_ard_3", "ga_ls7e_ard_3", "ga_ls5t_ard_3"]
    bucket_path = "baseline"
    # Rows should be from 88 to 116, and paths from 67 to 91
    paths = range(88, 117)
    # rows = range(67, 92)

    for product in products:
        TASK_NAME = f"{product}--backlog"
        index_backlog = SubDagOperator(
            task_id=TASK_NAME,
            subdag=load_subdag(
                DAG_NAME, TASK_NAME, product, bucket_path, paths, TASK_ARGS
            ),
            default_args=TASK_ARGS,
            dag=dag,
        )
