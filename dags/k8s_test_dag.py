from datetime import datetime, timedelta
from airflow import DAG
from airflow.contrib.operators.kubernetes_pod_operator import (
    KubernetesPodOperator,
    Resources,
)

from unittest.mock import patch

default_args = {
    "owner": "Imam Alam",
    "depends_on_past": False,
    "start_date": datetime(2020, 9, 11),
    "email": ["imam.alam@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

pipeline = DAG(
    "k8s_test_dag",
    doc_md=__doc__,
    default_args=default_args,
    description="test dag please ignore",
    catchup=False,
    params={},
    schedule_interval=None,  # timedelta(minutes=30),
    tags=["k8s", "dea", "psc", "wagl", "nrt"],
)

resources = {
    "request_memory": "2G",
    "request_cpu": "1000m",
}


class PatchResources(Resources):
    def to_k8s_client_obj(self):
        return {"requests": {"memory": "1Gi"}}


def _set_resources(resources):
    if not resources:
        return []
    return [PatchResources(**resources)]


with pipeline:
    _set_resources_backup = KubernetesPodOperator._set_resources
    KubernetesPodOperator._set_resources = _set_resources

    COPY = KubernetesPodOperator(
        namespace="processing",
        name="test_dag",
        task_id="test_dag",
        image_pull_policy="IfNotPresent",
        image="ubuntu:18.04",
        cmds=["echo", "test dag please ignore"],
        resources=resources,
        labels={
            "runner": "airflow",
            "product": "Sentinel-2",
            "app": "nrt",
            "stage": "test",
        },
        get_logs=True,
        is_delete_operator_pod=True,
    )

    KubernetesPodOperator._set_resources = _set_resources_backup
