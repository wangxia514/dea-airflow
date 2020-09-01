"""
# Explorer cubedash-gen refresh-stats
"""

from airflow import DAG
from textwrap import dedent
from datetime import datetime, timedelta
from airflow.operators.dummy_operator import DummyOperator

from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.kubernetes.secret import Secret
from sentinel_2_nrt.env_cfg import INDEXING_PRODUCTS
from sentinel_2_nrt.images import EXPLORER_IMAGE
from sentinel_2_nrt.env_cfg import DB_DATABASE, SECRET_EXPLORER_NAME, SECRET_AWS_NAME

from sentinel_2_nrt.env_cfg import DB_DATABASE, SECRET_EXPLORER_NAME, SECRET_AWS_NAME


EXPLORER_SECRETS = [
    Secret("env", "DB_USERNAME", SECRET_EXPLORER_NAME, "postgres-username"),
    Secret("env", "DB_PASSWORD", SECRET_EXPLORER_NAME, "postgres-password"),
]


def explorer_refresh_stats_subdag(parent_dag_name, child_dag_name, args, xcom_task_id):

    EXPLORER_BASH_COMMAND = [
        "bash",
        "-c",
        dedent(
            """
            for product in %s; do
                cubedash-gen --no-init-database --refresh-stats --force-refresh $product;
            done;
        """
        )
        % ("{{{{ task_instance.xcom_pull(dag_id='{}', task_ids='{}') }}}}".format(parent_dag_name, xcom_task_id)),
    ]

    dag_subdag = DAG(
        dag_id="%s.%s" % (parent_dag_name, child_dag_name),
        default_args=args,
        catchup=False,
    )

    KubernetesPodOperator(
        namespace="processing",
        image=EXPLORER_IMAGE,
        arguments=EXPLORER_BASH_COMMAND,
        secrets=EXPLORER_SECRETS,
        labels={"step": "explorer-refresh-stats"},
        name="explorer-summary",
        task_id="explorer-summary-task",
        get_logs=True,
        is_delete_operator_pod=True,
        dag=dag_subdag,
    )

    return dag_subdag
