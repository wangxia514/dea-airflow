"""
A reusable Task for checking s3_glob
"""

from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator

from infra.images import INDEXER_IMAGE
from infra.podconfig import ONDEMAND_NODE_AFFINITY

from airflow.utils.trigger_rule import TriggerRule


def s3_find_operator(s3_glob):
    """
    Sets up a Task to valid s3_glob

    Expects to be run within the context of a DAG
    """
    S3_FIND_BASH_COMMAND = [
        "bash",
        "-c",
        f"s3-find --no-sign-request {s3_glob}",
    ]

    return KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        arguments=S3_FIND_BASH_COMMAND,
        labels={"app": "s3-glob-validator"},
        name="s3-glob-validator",
        task_id="s3-glob-validator-task",
        get_logs=True,
        is_delete_operator_pod=True,
        affinity=ONDEMAND_NODE_AFFINITY,
        log_events_on_failure=True,
        trigger_rule=TriggerRule.NONE_FAILED_OR_SKIPPED,  # Needed in case add product was skipped
    )
