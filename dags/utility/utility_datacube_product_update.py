"""
## Utility Tool (Self Serve)
For updating products

```
datacube -v product update \
    https://raw.githubusercontent.com/GeoscienceAustralia/digitalearthau/develop/digitalearthau/config/eo3/products-aws/ard_ls7_provisional.odc-product.yaml \
    https://raw.githubusercontent.com/GeoscienceAustralia/digitalearthau/develop/digitalearthau/config/eo3/products-aws/ard_ls8_provisional.odc-product.yaml \
    https://raw.githubusercontent.com/GeoscienceAustralia/digitalearthau/develop/digitalearthau/config/eo3/products-aws/ard_s2a_provisional.odc-product.yaml \
    https://raw.githubusercontent.com/GeoscienceAustralia/digitalearthau/develop/digitalearthau/config/eo3/products-aws/ard_s2b_provisional.odc-product.yaml
```
## Note
All list of utility dags here: https://github.com/GeoscienceAustralia/dea-airflow/tree/develop/dags/utility, see Readme

#### Utility customisation
The DAG can be parameterized with run time configuration `product_definition_urls`

dag_run.conf format:

#### example conf in json format

    {
        "product_definition_urls": [
            "https://raw.githubusercontent.com/GeoscienceAustralia/digitalearthau/develop/digitalearthau/config/eo3/products-aws/ard_ls7_provisional.odc-product.yaml",
            "https://raw.githubusercontent.com/GeoscienceAustralia/digitalearthau/develop/digitalearthau/config/eo3/products-aws/ard_ls8_provisional.odc-product.yaml",
            "https://raw.githubusercontent.com/GeoscienceAustralia/digitalearthau/develop/digitalearthau/config/eo3/products-aws/ard_s2a_provisional.odc-product.yaml",
            "https://raw.githubusercontent.com/GeoscienceAustralia/digitalearthau/develop/digitalearthau/config/eo3/products-aws/ard_s2b_provisional.odc-product.yaml"
        ]
    }

"""
from datetime import datetime, timedelta

from airflow import DAG
from textwrap import dedent

from airflow.kubernetes.secret import Secret

from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from infra.images import INDEXER_IMAGE
from infra.variables import (
    DB_DATABASE,
    DB_HOSTNAME,
    SECRET_ODC_ADMIN_NAME,
    AWS_DEFAULT_REGION,
    DB_PORT,
)
from infra.podconfig import (
    ONDEMAND_NODE_AFFINITY,
)

DAG_NAME = "utility_datacube_product_update"

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
    ],
}

PRODUCT_UPDATE_CMD = [
        "bash",
        "-c",
        dedent(
            """
            {% for product in dag_run.conf.product_definition_urls }}
                datacube -v product update --allow-unsafe {{product}}{% endfor %}
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
    tags=["k8s", "datacube-product-update", "self-service"],
)


with dag:
    Product_update = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        image_pull_policy="IfNotPresent",
        labels={"step": "datacube-product-update"},
        arguments=PRODUCT_UPDATE_CMD,
        name="datacube-product-update",
        task_id="datacube-product-update",
        get_logs=True,
        affinity=ONDEMAND_NODE_AFFINITY,
        is_delete_operator_pod=True,
    )
