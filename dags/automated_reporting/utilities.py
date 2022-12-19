"""
Common code needed for reporting dags
"""
from datetime import timedelta
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)

REPORTING_OWNERS = "Tom McAdam, Ramkumar Ramagopalan"
REPORTING_ADMIN_EMAILS = ["tom.mcadam@ga.gov.au", "ramkumar.ramagopalan@ga.gov.au"]


def configure_ssh_cmds(secret_key_name):
    """
    Common cmds for confiuring ssh key from kubernetes volume secret
    """

    return [
        "echo Configuring SSH",
        "mkdir -p ~/.ssh",
        f"cat /var/secrets/lpgs/{secret_key_name} > ~/.ssh/identity_file.pem",
        "chmod 0400 ~/.ssh/identity_file.pem",
        "echo SSH Key Generated",
    ]


NCI_TUNNEL_CMDS = configure_ssh_cmds("PORT_FORWARDER_KEY") + [
    "echo Establishing NCI tunnel",
    "ssh -o StrictHostKeyChecking=no -f -N -i ~/.ssh/identity_file.pem -L 54320:$ODC_DB_HOST:$ODC_DB_PORT $NCI_TUNNEL_USER@$NCI_TUNNEL_HOST",
    "echo NCI tunnel established",
    "parse-uri ${REP_DB_URI} /tmp/env; source /tmp/env",
]


def k8s_operator(
    dag,
    image,
    task_id,
    cmds,
    env_vars=None,
    secrets=None,
    task_concurrency=None,
    xcom=False,
    labels=None,
):
    """
    A helper function to save a few lines of code on the common kwargs for KubernetesPodOperator
    """
    return KubernetesPodOperator(
        namespace="processing",
        image=image,
        arguments=["bash", "-c", " &&\n".join(cmds)],
        name=task_id,
        is_delete_operator_pod=True,
        in_cluster=True,
        task_id=task_id,
        get_logs=True,
        do_xcom_push=xcom,
        task_concurrency=task_concurrency,
        env_vars=env_vars,
        secrets=secrets,
        labels=labels,
        execution_timeout=timedelta(minutes=30),
    )
