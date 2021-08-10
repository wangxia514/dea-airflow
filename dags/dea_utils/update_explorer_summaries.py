"""
A reusable Task for refreshing datacube explorer instances
"""
from collections.abc import Sequence

from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.kubernetes.secret import Secret

from infra.images import EXPLORER_IMAGE
from infra.podconfig import ONDEMAND_NODE_AFFINITY
from infra.variables import SECRET_EXPLORER_WRITER_NAME

EXPLORER_SECRETS = [
    Secret("env", "DB_USERNAME", SECRET_EXPLORER_WRITER_NAME, "postgres-username"),
    Secret("env", "DB_PASSWORD", SECRET_EXPLORER_WRITER_NAME, "postgres-password"),
]


def explorer_refresh_operator(products):
    """
    Sets up a Task to Refresh Datacube Explorer

    Expects to be run within the context of a DAG

    The `products` argument can either be:
    - a list of products to refresh
    - a string, which may include Airflow template syntax which is filled in when the DAG is executed.
      For example: `{{ dag_run.conf.products }}` would allows manual execution, passing in a space separated string
      of products
    """
    if isinstance(products, Sequence) and not isinstance(products, str):
        products = " ".join(products)

    EXPLORER_BASH_COMMAND = [
        "bash",
        "-c",
        f"cubedash-gen -v --no-init-database --refresh-stats {products}",
    ]
    return KubernetesPodOperator(
        namespace="processing",
        image=EXPLORER_IMAGE,
        arguments=EXPLORER_BASH_COMMAND,
        secrets=EXPLORER_SECRETS,
        labels={"app": "explorer-refresh-stats"},
        name="explorer-summary",
        task_id="explorer-summary-task",
        get_logs=True,
        is_delete_operator_pod=True,
        affinity=ONDEMAND_NODE_AFFINITY,
        log_events_on_failure=True,
    )
