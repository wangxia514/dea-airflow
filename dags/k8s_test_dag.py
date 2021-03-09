from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow_kubernetes_job_operator.kubernetes_job_operator import (
    KubernetesJobOperator,
)


MOD6_IMAGE = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/dev/mod6:test-20210309"


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
    schedule_interval=None,
    tags=["k8s", "dea", "psc", "dev"],
)


with pipeline:
    JOB = KubernetesPodOperator(
        task_id="run-one",
        namespace="processing",
        name="mod6-test",
        image_pull_policy="Always",
        image=MOD6_IMAGE,
        startup_timeout_seconds=120,
        labels={
            "runner": "airflow",
            "app": "CaRSA",
        },
        is_delete_operator_pod=True,
    )
