"""
# Landsat Collection 3 indexing for WO and FC

"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from airflow.kubernetes.secret import Secret
from airflow.operators.subdag_operator import SubDagOperator
from infra.images import INDEXER_IMAGE
from infra.podconfig import ONDEMAND_NODE_AFFINITY
from infra.variables import SECRET_ODC_WRITER_NAME, DB_HOSTNAME

DEFAULT_ARGS = {
    "owner": "Damien Ayers (from Alex)",
    "depends_on_past": False,
    "start_date": datetime(2020, 6, 14),
    "email": ["damien.ayers@ga.gov.au"],
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
            arguments = [
                "s3-to-dc",
                "--stac",
                "--no-sign-request",
                f"s3://dea-public-data/{bucket_path}/**/*.json",
                product,
            ]
            # for path in paths:
            INDEXING = KubernetesPodOperator(
                namespace="processing",
                image=INDEXER_IMAGE,
                image_pull_policy="Always",
                arguments=arguments,
                labels={"backlog": "s3-to-dc"},
                name=f"datacube-index-{product}-{path}",
                task_id=f"{product}--Backlog-indexing-row--{path}",
                get_logs=True,
                is_delete_operator_pod=True,
                affinity=ONDEMAND_NODE_AFFINITY,
                dag=subdag,
            )
    return subdag


DAG_NAME = "k8s_index_c3_wo_fc_backlog"

dag = DAG(
    dag_id=DAG_NAME,
    default_args=DEFAULT_ARGS,
    schedule_interval="@once",
    tags=["k8s", "landsat_c3", "backlog"],
    catchup=False,
)

with dag:
    product_details = [["ga_ls_fc_3", "2-5-0"], ["ga_ls_wo_3", "1-6-0"]]
    bucket_path = "derivative"
    # Rows should be from 88 to 116, and paths from 67 to 91
    paths = range(88, 117)
    # rows = range(67, 92)

    for product, number in product_details:
        TASK_NAME = f"{product}--backlog"
        index_backlog = SubDagOperator(
            task_id=TASK_NAME,
            subdag=load_subdag(
                DAG_NAME,
                TASK_NAME,
                product,
                f"{bucket_path}/{product}/{number}",
                paths,
                TASK_ARGS,
            ),
            default_args=TASK_ARGS,
            dag=dag,
        )
