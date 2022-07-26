"""
Dev Dag
"""
import datetime
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)

YESTERDAY = datetime.datetime.now() - datetime.timedelta(days=1)

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": True,
    "start_date": YESTERDAY,
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
}

secret_volume = Secret(
    deploy_type="volume",
    # Path where we mount the secret as volume
    deploy_target="/var/secrets/lpgs",
    # Name of Kubernetes Secret
    secret="lpgs-port-forwarder",
    # Key in the form of service account file name
    key="PORT_FORWARDER_KEY",
)


dag = DAG(
    "rep_test_ssh_on_pod",
    description="test_ssh_output",
    tags=["reporting_dev"],
    default_args=default_args,
    schedule_interval=None,
)

with dag:
    JOBS_SSH_CONN = [
        "echo run lquota and save in pod dir $(date)",
        "apt update -y",
        "apt install -y openssh-server",
        "apt install -y ca-certificates",
        "apt-get install -y postgresql-client",
        "mkdir -p ~/.ssh",
        "cat /var/secrets/lpgs/PORT_FORWARDER_KEY > ~/.ssh/identity_file.pem",
        "chmod 0400 ~/.ssh/identity_file.pem",
        "ssh -o StrictHostKeyChecking=no -f -N -i ~/.ssh/identity_file.pem\
             -L 54320:$DB_HOST:$DB_PORT $NCI_TUNNEL_USER@$NCI_TUNNEL_HOST",
        "cat /tmp/a.txt",
    ]
    kubernetes_secret_vars_ex = KubernetesPodOperator(
        namespace="processing",
        image="python:3.8-slim-buster",
        arguments=["bash", "-c", " &&\n".join(JOBS_SSH_CONN)],
        name="checksecret",
        do_xcom_push=False,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id="check_secret",
        secrets=[secret_volume],
        get_logs=True,
    )
    kubernetes_secret_vars_ex
