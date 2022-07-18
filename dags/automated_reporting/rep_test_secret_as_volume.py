import datetime
from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from infra.variables import REPORTING_NCI_ODC_DB_SECRET, REPORTING_LPGS_PORT_FORWARDER_SECRET

YESTERDAY = datetime.datetime.now() - datetime.timedelta(days=1)

default_args = {
    "owner": "Ramkumar Ramagopalan",
    "depends_on_past": True,
    "start_date": YESTERDAY,
    "email": ["ramkumar.ramagopalan@ga.gov.au"],
    "email_on_failure": True,
    "email_on_retry": False,
    "secrets": [
        Secret("env", "DB_HOST", REPORTING_NCI_ODC_DB_SECRET, "DB_HOST"),
        Secret("env", "DB_NAME", REPORTING_NCI_ODC_DB_SECRET, "DB_NAME"),
        Secret("env", "DB_PORT", REPORTING_NCI_ODC_DB_SECRET, "DB_PORT"),
        Secret("env", "DB_USER", REPORTING_NCI_ODC_DB_SECRET, "DB_USER"),
        Secret("env", "DB_PASSWORD", REPORTING_NCI_ODC_DB_SECRET, "DB_PASSWORD"),
        Secret("env", "PORT_FORWARDER_KEY", REPORTING_LPGS_PORT_FORWARDER_SECRET, "PORT_FORWARDER_KEY"),
    ],
}

dag = DAG(
    "composer_sample_kubernetes_pod",
    description="composer_sample_kubernetes_pod ",
    tags=["reporting_dev"],
    default_args=default_args,
    schedule_interval=None,
)

with dag:
    JOBS_SSH_CONN = [
        "echo try ssh tunnel $(date)",
        "apt update -y",
        "apt install -y openssh-server",
        "apt install -y ca-certificates",
        "apt-get install -y postgresql-client",
        "mkdir -p ~/.ssh",
        "echo $PORT_FORWARDER_KEY > ~/.ssh/identity_file.pem",
        "chmod 0400 ~/.ssh/identity_file.pem",
        "ssh -o StrictHostKeyChecking=no -f -N -i ~/.ssh/identity_file.pem -L 54320:$DB_HOST:$DB_PORT lpgs@gadi.nci.org.au",
        "echo tunnel established",
        "PGPASSWORD=$DB_PASSWORD psql -h localhost -p 54320 -U $DB_USER $DB_NAME -c 'select count(*) from agdc.dataset_type'",
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
        get_logs=True,
    )
    kubernetes_secret_vars_ex
