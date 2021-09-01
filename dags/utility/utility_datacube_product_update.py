"""
## Utility Tool (Self Serve)
For updating products or updating datasets

datacube command used for `product update`
```
datacube -v product update \
    https://raw.githubusercontent.com/GeoscienceAustralia/digitalearthau/develop/digitalearthau/config/eo3/products-aws/ard_ls7_provisional.odc-product.yaml \
    https://raw.githubusercontent.com/GeoscienceAustralia/digitalearthau/develop/digitalearthau/config/eo3/products-aws/ard_ls8_provisional.odc-product.yaml \
    https://raw.githubusercontent.com/GeoscienceAustralia/digitalearthau/develop/digitalearthau/config/eo3/products-aws/ard_s2a_provisional.odc-product.yaml \
    https://raw.githubusercontent.com/GeoscienceAustralia/digitalearthau/develop/digitalearthau/config/eo3/products-aws/ard_s2b_provisional.odc-product.yaml
```

odc-tools command used for `dataset update`
```
s3-to-dc --allow-unsafe --update-if-exists --no-sign-request \
    s3://dea-public-data-dev/s2be//**/*.yaml s2_barest_earth
```

## Note
All list of utility dags here: https://github.com/GeoscienceAustralia/dea-airflow/tree/develop/dags/utility, see Readme

#### Utility customisation
The DAG can be parameterized with run time configuration `product_definition_urls`

dag_run.conf format is json list, this is designed to improve readability when large number of products definitions need to be updated.

#### example conf in json format

Scenario 1: need to update product definitions ONLY

    {
        "product_definition_urls": [
            "https://raw.githubusercontent.com/GeoscienceAustralia/digitalearthau/develop/digitalearthau/config/eo3/products-aws/ard_ls7_provisional.odc-product.yaml",
            "https://raw.githubusercontent.com/GeoscienceAustralia/digitalearthau/develop/digitalearthau/config/eo3/products-aws/ard_ls8_provisional.odc-product.yaml",
            "https://raw.githubusercontent.com/GeoscienceAustralia/digitalearthau/develop/digitalearthau/config/eo3/products-aws/ard_s2a_provisional.odc-product.yaml",
            "https://raw.githubusercontent.com/GeoscienceAustralia/digitalearthau/develop/digitalearthau/config/eo3/products-aws/ard_s2b_provisional.odc-product.yaml"
        ],
        "s3_glob": "",
        "product": ""
    }

Scenario 2: need to update dataset ONLY

    {
        "product_definition_urls": [],
        "s3_glob": "s3://dea-public-data-dev/s2be/*/*.odc-metadata.yaml",
        "product": "s2_barest_earth"
    }

Scenario 3: need to update product and datasets

    {
        "product_definition_urls": [
            "https://raw.githubusercontent.com/GeoscienceAustralia/digitalearthau/develop/digitalearthau/config/eo3/products-aws/ard_ls7_provisional.odc-product.yaml",
            "https://raw.githubusercontent.com/GeoscienceAustralia/digitalearthau/develop/digitalearthau/config/eo3/products-aws/ard_ls8_provisional.odc-product.yaml",
            "https://raw.githubusercontent.com/GeoscienceAustralia/digitalearthau/develop/digitalearthau/config/eo3/products-aws/ard_s2a_provisional.odc-product.yaml",
            "https://raw.githubusercontent.com/GeoscienceAustralia/digitalearthau/develop/digitalearthau/config/eo3/products-aws/ard_s2b_provisional.odc-product.yaml"
        ],
        "s3_glob": "s3://dea-public-data-dev/s2be/*/*.odc-metadata.yaml",
        "product": "s2_barest_earth"
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
        {% if dag_run.conf['product_definition_urls'] %}
            {% for product in dag_run.conf.product_definition_urls %}datacube -v product update --allow-unsafe {{product}}
            {% endfor %}
        {% endif %}
        {% if dag_run.conf['s3_glob'] and dag_run.conf['product'] %}
            s3-to-dc --allow-unsafe --update-if-exists --no-sign-request {{ dag_run.conf.s3_glob}} {{dag_run.conf.product}}
        {% endif %}
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
    Product_or_dataset_update = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        image_pull_policy="IfNotPresent",
        labels={"step": "datacube-product-update"},
        arguments=PRODUCT_UPDATE_CMD,
        name="datacube-product-or-dataset-update",
        task_id="datacube-product-or-dataset-update",
        get_logs=True,
        affinity=ONDEMAND_NODE_AFFINITY,
        is_delete_operator_pod=True,
    )