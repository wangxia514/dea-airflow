"""
# Debugging Tool (Admin use)
## Test python logging behaviour in kubernetesjoboperators and kubernetespodoperators
testing behaviour for python logging captured by airflow
## Life span
Forever
"""
from airflow import DAG
from airflow_kubernetes_job_operator.kubernetes_job_operator import (
    KubernetesJobOperator,
)
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from textwrap import dedent
from airflow.utils.dates import days_ago
from infra.images import WATERBODIES_UNSTABLE_IMAGE

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
    "test_k8slogging",
    default_args=default_args,
    description="Test k8s (job/pod) operator logging behavior",
    schedule_interval=None,
    tags=["k8s", "test"],
    doc_md=__doc__,
)

with dag:

    """K8s pod operator that says hello."""
    logging_cmd = [
        "bash",
        "-c",
        dedent(
            """
            echo "echo from bash"
            python - << EOF
            import logging
            logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
            logging.info('hello from Python')
            logging.debug('debug log from Python')
            logging.warning('warning from Python')
            print('Print from Python')
            EOF
            """
        ),
    ]

    pod_hello_w = KubernetesPodOperator(
        image=WATERBODIES_UNSTABLE_IMAGE,
        name="test-python-logging-pod-waterbodies-image",
        arguments=logging_cmd,
        image_pull_policy="IfNotPresent",
        labels={"app": "test-python-logging"},
        get_logs=True,
        is_delete_operator_pod=True,
        namespace="processing",
        task_id="test-python-logging-pod-waterbodies-image",
    )

    job_hello_w = KubernetesJobOperator(
        task_id="test-python-logging-job-waterbodies-image",
        image=WATERBODIES_UNSTABLE_IMAGE,
        command=logging_cmd,
        namespace="processing",
    )