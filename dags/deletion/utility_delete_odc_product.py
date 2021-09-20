"""
## Utility Tool (Self Serve)
For deleting a product from `OWS`, `explorer` and `odc`

#### Utility customisation
The DAG can be parameterized with run time configuration `product_name`

#### Utility customisation

#### example conf in json format

    {
        "product_name": "cemp_insar_alos_displacement"
    }

"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)

from infra.images import INDEXER_IMAGE
from infra.variables import (
    DB_DATABASE,
    DB_HOSTNAME,
    SECRET_ODC_ADMIN_NAME,
    SECRET_EXPLORER_ADMIN_NAME,
    SECRET_OWS_ADMIN_NAME,
    AWS_DEFAULT_REGION,
    DB_PORT,
)
from infra.podconfig import (
    ONDEMAND_NODE_AFFINITY,
)

DAG_NAME = "deletion_utility_odc_product_ows_explorer"

INDEXER_IMAGE = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/opendatacube/datacube-index:0.0.31"

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
        Secret("env", "DB_USERNAME", SECRET_ODC_ADMIN_NAME, "postgres-username"),
        Secret("env", "DB_PASSWORD", SECRET_ODC_ADMIN_NAME, "postgres-password"),
        Secret(
            "env", "EXPLORER_USERNAME", SECRET_EXPLORER_ADMIN_NAME, "postgres-username"
        ),
        Secret(
            "env", "EXPLORER_PASSWORD", SECRET_EXPLORER_ADMIN_NAME, "postgres-password"
        ),
        Secret("env", "OWS_USERNAME", SECRET_OWS_ADMIN_NAME, "postgres-username"),
        Secret("env", "OWS_PASSWORD", SECRET_OWS_ADMIN_NAME, "postgres-password"),
    ],
}

DELETE_PRODUCT_CMD = [
    "bash",
    "-c",
    dedent(
        """
        export PRODUCT_NAME={{ dag_run.conf.product_name }}
        cd /code/odc-product-delete
        ./delete_product.sh
        """
    ),
]

# THE DAG
dag = DAG(
    dag_id=DAG_NAME,
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,
    catchup=False,
    tags=["k8s", "product-deletion", "deletion", "self-service"],
)

with dag:
    DELETE_PRODUCT = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        image_pull_policy="IfNotPresent",
        labels={"step": "delete-product"},
        arguments=DELETE_PRODUCT_CMD,
        name="delete-product",
        task_id="delete-product",
        get_logs=True,
        affinity=ONDEMAND_NODE_AFFINITY,
        is_delete_operator_pod=True,
    )
