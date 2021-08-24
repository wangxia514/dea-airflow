"""
## Utility Tool (Self Serve)
For indexing datasets from s3 into an existing product and OWS layer/s.

#### Utility customisation
The DAG can be parameterized with run time configuration `product` and `s3_glob`

dag_run.conf format:

#### example conf in json format

    {
        "s3_glob": "s3://dea-public-data/cemp_insar/insar/displacement/alos//**/*.yaml",
        "product": "cemp_insar_alos_displacement"
    }

"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from airflow.kubernetes.secret import Secret

from dea_utils.update_explorer_summaries import explorer_sandboxdb_forcerefresh_operator

from infra.iam_roles import INDEXING_ROLE
from infra.images import INDEXER_IMAGE
from infra.podconfig import (
    ONDEMAND_NODE_AFFINITY,
)
from infra.variables import (
    DB_SANDBOX_DATABASE,
    DB_HOSTNAME,
    DB_SANDBOX_USER_SECRET,
    DB_PORT,
    AWS_DEFAULT_REGION,
)

DAG_NAME = "utility_indexing_annual_explorer_update_sandbox"

# DAG CONFIGURATION
DEFAULT_ARGS = {
    "owner": "Pin Jin",
    "depends_on_past": False,
    "start_date": datetime(2020, 6, 14),
    "email": ["pin.jin@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "env_vars": {
        # TODO: Pass these via templated params in DAG Run
        "DB_HOSTNAME": DB_HOSTNAME,
        "DB_DATABASE": DB_SANDBOX_DATABASE,
        "DB_PORT": DB_PORT,
        "AWS_DEFAULT_REGION": AWS_DEFAULT_REGION,
    },
    # Lift secrets into environment variables
    "secrets": [
        Secret("env", "DB_USERNAME", DB_SANDBOX_USER_SECRET, "postgres-username"),
        Secret("env", "DB_PASSWORD", DB_SANDBOX_USER_SECRET, "postgres-password"),
    ],
}

# THE DAG
with DAG(
    dag_id=DAG_NAME,
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,
    catchup=False,
    tags=["k8s", "annual", "batch-indexing", "self-service", "sandbox"],
) as dag:

    INDEXING = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        image_pull_policy="IfNotPresent",
        labels={"step": "s3-to-rds"},
        cmds=["s3-to-dc"],
        arguments=[
            # "s3://dea-public-data/cemp_insar/insar/displacement/alos//**/*.yaml",
            # "cemp_insar_alos_displacement",
            # Jinja templates for arguments
            "--skip-lineage",
            "{{ dag_run.conf.s3_glob }}",
            "{{ dag_run.conf.product }}",
            "--no-sign-request",
        ],
        name="datacube-index",
        task_id="batch-indexing-task",
        get_logs=True,
        affinity=ONDEMAND_NODE_AFFINITY,
        annotations={"iam.amazonaws.com/role": INDEXING_ROLE},
        is_delete_operator_pod=True,
    )

    EXPLORER_SUMMARY = explorer_sandboxdb_forcerefresh_operator(
        "{{ dag_run.conf.product }}", dag=dag
    )

    INDEXING >> EXPLORER_SUMMARY
