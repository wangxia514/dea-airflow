import datetime

from airflow import models
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator

secret_volume = Secret(
    deploy_type='volume',
    # Path where we mount the secret as volume
    deploy_target='/',
    # Name of Kubernetes Secret
    secret='REPORTING_DB_DEV_SECRET',
    # Key in the form of service account file name
    key='DB_HOST')

YESTERDAY = datetime.datetime.now() - datetime.timedelta(days=1)

with models.DAG(
        dag_id='composer_sample_kubernetes_pod',
        schedule_interval=datetime.timedelta(days=1),
        start_date=YESTERDAY) as dag:
    JOBS_CHECK_VOLUME = [
        "echo check tmp contents $(date)",
        "ls -lrt /",
    ]
    kubernetes_secret_vars_ex = KubernetesPodOperator(
        task_id='ex-kube-secrets',
        name='ex-kube-secrets',
        namespace='default',
        image='ubuntu',
        startup_timeout_seconds=300,
        secrets=[secret_volume],
    )
    kubernetes_secret_vars_ex
