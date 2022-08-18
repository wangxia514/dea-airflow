"""
Common code needed for reporting dags
"""
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)

NCI_TUNNEL_CMDS = [
    "echo Configuring SSH",
    "mkdir -p ~/.ssh",
    "cat /var/secrets/lpgs/PORT_FORWARDER_KEY > ~/.ssh/identity_file.pem",
    "chmod 0400 ~/.ssh/identity_file.pem",
    "echo Establishing NCI tunnel",
    "ssh -o StrictHostKeyChecking=no -f -N -i ~/.ssh/identity_file.pem -L 54320:$ODC_DB_HOST:$ODC_DB_PORT $NCI_TUNNEL_USER@$NCI_TUNNEL_HOST",
    "echo NCI tunnel established",
]


def k8s_operator(
    dag, image, task_id, cmds, env_vars, secrets=None, task_concurrency=None, xcom=False
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
    )
