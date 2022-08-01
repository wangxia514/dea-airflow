"""
# Debugging Tool (Admin use)
## Test kubernetes Pod Operators xcom side car image
Test if sidecar pulls alpine image from ecr

## Life span
Forever
"""
from airflow.utils.dates import days_ago
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from infra.images import INDEXER_IMAGE

default_args = {
    "owner": "Pin Jin",
    "start_date": days_ago(2),
    "retries": 0,
    "email": ["pin.jin@ga.gov.au"],
    "email_on_failure": False,
    "depends_on_past": False,
    "email_on_retry": False,
}

dag = DAG(
    "test_k8spodoperator_xcom",
    default_args=default_args,
    description="Test k8spodoperator xcom image",
    schedule_interval=None,
    tags=["k8s", "test"],
    doc_md=__doc__,
)

r_value = '{"foo": "bar"\n, "buzz": 2}'

with dag:

    KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        cmds=["bash", "-cx"],
        arguments=["echo '{}' > /airflow/xcom/return.json".format(r_value)],
        name="test-k8s-xcom-sidecar",
        task_id="task-test",
        labels={"dag": "test-xcom-sidecar"},
        get_logs=True,
        do_xcom_push=True,
        is_delete_operator_pod=False,
        log_events_on_failure=True,
    )
