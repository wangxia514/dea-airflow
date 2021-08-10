"""
# Debugging Tool (Admin use)
## Test kubernetes job operators
```
airflow_kubernetes_job_operator.kube_api.exceptions.KubeApiClientException: airflow_kubernetes_job_operator.kube_api.operations.CreateNamespaceResource,
Forbidden: jobs.batch is forbidden:
User "system:serviceaccount:processing:airflow" cannot create resource "jobs" in API group "batch" in the namespace "processing"
```
## Life span
Forever
"""
from airflow import DAG
from airflow_kubernetes_job_operator.kubernetes_job_operator import (
    KubernetesJobOperator,
)
from airflow_kubernetes_job_operator.kubernetes_legacy_job_operator import (
    KubernetesLegacyJobOperator,
)
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from textwrap import dedent
from airflow.utils.dates import days_ago
from infra.images import INDEXER_IMAGE, WATERBODIES_UNSTABLE_IMAGE

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

body = {
    "kind": "Pod",
    "metadata": {"name": "k8sjoboperator-pod", "namespace": "processing"},
    "spec": {
        "containers": [
            {
                "name": "odc-admin",
                "image": "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/opendatacube/datacube-index:latest",
                "command": ["/bin/sh", "-ec", "datacube product list"],
                "env": [
                    {"name": "DB_HOSTNAME", "value": "db-writer"},
                    {
                        "name": "DB_DATABASE",
                        "valueFrom": {
                            "secretKeyRef": {
                                "name": "odc-admin",
                                "key": "database-name",
                            }
                        },
                    },
                    {
                        "name": "DB_USERNAME",
                        "valueFrom": {
                            "secretKeyRef": {
                                "name": "odc-admin",
                                "key": "postgres-username",
                            }
                        },
                    },
                    {
                        "name": "DB_PASSWORD",
                        "valueFrom": {
                            "secretKeyRef": {
                                "name": "odc-admin",
                                "key": "postgres-password",
                            }
                        },
                    },
                    {
                        "name": "AWS_ACCESS_KEY_ID",
                        "valueFrom": {
                            "secretKeyRef": {
                                "name": "processing-landsat-3-aws-creds",
                                "key": "AWS_ACCESS_KEY_ID",
                            }
                        },
                    },
                    {
                        "name": "AWS_SECRET_ACCESS_KEY",
                        "valueFrom": {
                            "secretKeyRef": {
                                "name": "processing-landsat-3-aws-creds",
                                "key": "AWS_SECRET_ACCESS_KEY",
                            }
                        },
                    },
                    {
                        "name": "AWS_DEFAULT_REGION",
                        "valueFrom": {
                            "secretKeyRef": {
                                "name": "processing-landsat-3-aws-creds",
                                "key": "AWS_DEFAULT_REGION",
                            }
                        },
                    },
                ],
            }
        ]
    },
}  # The body or a yaml string (must be valid)

body_filepath = (
    "./k8sjoboperator_test_file.yaml"  # Can be relative to this file, or abs path.
)


with dag:

    job_task = KubernetesJobOperator(
        task_id="failing-testcase",
        image=INDEXER_IMAGE,
        command=["bash", "-c", "datacube product list"],
        namespace="processing",
    )

    job_task_from_body = KubernetesJobOperator(
        task_id="from-body",
        body=body,
        namespace="processing",
    )

    job_task_from_yaml = KubernetesJobOperator(
        task_id="from-yaml",
        body_filepath=body_filepath,
        namespace="processing",
    )

    # Legacy compatibility to KubernetesPodOperator
    legacy_job_task = KubernetesLegacyJobOperator(
        task_id="legacy-image-job",
        image=INDEXER_IMAGE,
        cmds=["bash", "-c", 'echo "all ok"'],
        is_delete_operator_pod=True,
        namespace="processing",
    )

    job_task_from_body >> job_task_from_yaml

    """K8s pod operator that says hello."""
    logging_cmd = [
        "bash",
        "-c",
        dedent(
            """
            echo "echo from bash"
            python - << EOF
            import logging
            logger = logging.getLogger(__name__)
            logger.setLevel(logging.DEBUG)
            logger.info('hello from Python')
            logger.debug('debug log from Python')
            logger.warning('warning from Python')
            print('Print from Python')
            EOF
            """
        ),
    ]

    pod_hello_w = KubernetesPodOperator(
        image=WATERBODIES_UNSTABLE_IMAGE,
        name="testing-python-logging-hello-pod-waterbodies-image",
        arguments=logging_cmd,
        image_pull_policy="IfNotPresent",
        labels={"app": "test-python-logging"},
        get_logs=True,
        is_delete_operator_pod=True,
        namespace="processing",
        task_id="test-python-logging-pod-waterbodies-image",
    )

    job_hello_w = KubernetesJobOperator(
        task_id="testing-python-logging-hello-job-waterbodies-image",
        image=WATERBODIES_UNSTABLE_IMAGE,
        command=logging_cmd,
        namespace="processing",
    )

    pod_hello_indexer_image = KubernetesPodOperator(
        image=INDEXER_IMAGE,
        name="testing-python-logging-hello-pod-indexer-image",
        arguments=logging_cmd,
        image_pull_policy="IfNotPresent",
        labels={"app": "test-python-logging"},
        get_logs=True,
        is_delete_operator_pod=True,
        namespace="processing",
        task_id="test-python-logging-pod-indexer-image",
    )

    job_hello_indexer_image = KubernetesJobOperator(
        task_id="testing-python-logging-hello-job-indexer-image",
        image=INDEXER_IMAGE,
        command=logging_cmd,
        namespace="processing",
    )
