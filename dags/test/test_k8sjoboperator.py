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
from airflow_kubernetes_job_operator.kubernetes_job_operator import KubernetesJobOperator
from airflow_kubernetes_job_operator.kubernetes_legacy_job_operator import KubernetesLegacyJobOperator
from airflow.utils.dates import days_ago
from infra.images import INDEXER_IMAGE

default_args = {"owner": "Pin Jin", "start_date": days_ago(2), "retries": 0}
dag = DAG("test_k8sjoboperator", default_args=default_args, description="Test base job operator", schedule_interval=None)

job_task = KubernetesJobOperator(
    task_id="from-image",
    dag=dag,
    image=INDEXER_IMAGE,
    command=["bash", "-c", 'echo "all ok"'],
)

body = {"kind": "Pod"}  # The body or a yaml string (must be valid)
job_task_from_body = KubernetesJobOperator(dag=dag, task_id="from-body", body=body)

# body_filepath = "./my_yaml_file.yaml"  # Can be relative to this file, or abs path.
# job_task_from_yaml = KubernetesJobOperator(dag=dag, task_id="from-yaml", body_filepath=body_filepath)

# Legacy compatibility to KubernetesPodOperator
legacy_job_task = KubernetesLegacyJobOperator(
    task_id="legacy-image-job",
    image=INDEXER_IMAGE,
    cmds=["bash", "-c", 'echo "all ok"'],
    dag=dag,
    is_delete_operator_pod=True,
)
