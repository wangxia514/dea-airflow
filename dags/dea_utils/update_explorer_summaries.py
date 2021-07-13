"""
A reusable Task for refreshing datacube explorer instances
"""

from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.kubernetes.secret import Secret

from infra.images import EXPLORER_IMAGE
from infra.podconfig import ONDEMAND_NODE_AFFINITY
from infra.variables import SECRET_EXPLORER_WRITER_NAME
from webapp_update.update_list import EXPLORER_UPDATE_LIST

EXPLORER_SECRETS = [
    Secret("env", "DB_USERNAME", SECRET_EXPLORER_WRITER_NAME, "postgres-username"),
    Secret("env", "DB_PASSWORD", SECRET_EXPLORER_WRITER_NAME, "postgres-password"),
]


def explorer_refresh_operator():
    """
    Expects to be run within the context of a DAG
    """
    EXPLORER_BASH_COMMAND = [
        "bash",
        "-c",
        "cubedash-gen -v --no-init-database --refresh-stats "
        "{% if dag_run.conf.products %}"
        "{{ dag_run.conf.products }}"
        "{% else %}"
        "{{ param.default_products|join(' ') }}"
        "{% endif %}",
    ]
    return KubernetesPodOperator(
        namespace="processing",
        image=EXPLORER_IMAGE,
        arguments=EXPLORER_BASH_COMMAND,
        secrets=EXPLORER_SECRETS,
        labels={"step": "explorer-refresh-stats"},
        name="explorer-summary",
        task_id="explorer-summary-task",
        get_logs=True,
        is_delete_operator_pod=True,
        affinity=ONDEMAND_NODE_AFFINITY,
        params=dict(default_products=EXPLORER_UPDATE_LIST),
    )
