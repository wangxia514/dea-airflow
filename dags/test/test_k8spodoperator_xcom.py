"""
# Debugging Tool (Admin use)
## Test kubernetes Pod Operators xcom side car image

## Life span
Forever
"""
from airflow.utils.dates import days_ago
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)

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
    "test_k8sjoboperator",
    default_args=default_args,
    description="Test base job operator",
    schedule_interval=None,
    tags=["k8s", "test"],
    doc_md=__doc__,
)

with dag:

    k = KubernetesPodOperator(
        namespace="default",
        image="ubuntu:16.04",
        cmds=["bash", "-cx"],
        arguments=["echo 10"],
        labels={"foo": "bar"},
        name="test-xcom-image",
        task_id="task-test",
        in_cluster=False,
        do_xcom_push=True,
    )
