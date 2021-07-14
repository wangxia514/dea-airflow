"""
## Utility Tool (Self Serve)
For indexing more dataset from s3 to an existing established product and ows layers.

## Note
All list of utility dags here: https://github.com/GeoscienceAustralia/dea-airflow/tree/develop/dags/utility, see Readme

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
from airflow.operators.python_operator import PythonOperator
from airflow.kubernetes.secret import Secret
from dea_utils.update_explorer_summaries import explorer_refresh_operator
from dea_utils.update_ows_products import ows_update_operator
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)

from infra.images import INDEXER_IMAGE
from infra.variables import (
    DB_DATABASE,
    DB_HOSTNAME,
    SECRET_ODC_WRITER_NAME,
    AWS_DEFAULT_REGION,
    DB_PORT,
)
from infra.podconfig import (
    ONDEMAND_NODE_AFFINITY,
)

DAG_NAME = "utility_batch_indexing_ows_explorer_update"

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
        "DB_DATABASE": DB_DATABASE,
        "DB_PORT": DB_PORT,
        "AWS_DEFAULT_REGION": AWS_DEFAULT_REGION,
    },
    # Lift secrets into environment variables
    "secrets": [
        Secret("env", "DB_USERNAME", SECRET_ODC_WRITER_NAME, "postgres-username"),
        Secret("env", "DB_PASSWORD", SECRET_ODC_WRITER_NAME, "postgres-password"),
    ],
}


# THE DAG
dag = DAG(
    dag_id=DAG_NAME,
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,
    catchup=False,
    tags=["k8s", "batch-indexing", "web-app-update", "self-service"],
)

with dag:
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
        is_delete_operator_pod=True,
    )

    EXPLORER_SUMMARY = explorer_refresh_operator("{{ dag_run.conf.product }}")

    OWS_UPDATE_EXTENTS = ows_update_operator(
        products="{{ dag_run.conf.product }}", dag=dag
    )

    INDEXING >> OWS_UPDATE_EXTENTS
    INDEXING >> EXPLORER_SUMMARY
