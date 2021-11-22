"""
# Product Adding and Indexing Utility Tool (Self Serve)

This DAG should be triggered manually and will:

- Add a new Product to the database *(Optional)*
- Index a glob of datasets on S3 *(Optional)*
- Update Datacube Explorer so that you can see the results

## Note
All list of utility dags here: https://github.com/GeoscienceAustralia/dea-airflow/tree/develop/dags/utility, see [Readme](https://github.com/GeoscienceAustralia/dea-airflow/tree/develop/dags/utility)

## Customisation

There are three configuration arguments:

- `product_definition_uri`: A HTTP/S url to a Product Definition YAML *(Optional)*
- `s3_glob`: An S3 URL or Glob pattern, as recognised by `s3-to-dc` *(Optional)* example valid s3_glob can be find here [https://github.com/opendatacube/odc-tools/blob/3b2c4856147eba5ee5ae5337d763e2311737dcd5/apps/cloud/odc/apps/cloud/s3_find.py#L19-L43](https://github.com/opendatacube/odc-tools/blob/3b2c4856147eba5ee5ae5337d763e2311737dcd5/apps/cloud/odc/apps/cloud/s3_find.py#L19-L43)
- `product_name`: The name of the product
- `flags`: Flag, if passesd in config, linage will be skipped in indexing *(Optional)* valid flags can be find here: [https://github.com/opendatacube/odc-tools/blob/218ef9c85e5ebcbea00efb1297f7ed073f58d706/apps/dc_tools/README.md#s3-to-dc](https://github.com/opendatacube/odc-tools/blob/218ef9c85e5ebcbea00efb1297f7ed073f58d706/apps/dc_tools/README.md#s3-to-dc)

The commands which are executed are:

1. `datacube product add`
2. `s3-to-dc --no-sign-request` (no iamrole provided)
3. update explorer


### Sample Configuration

Usecase A: Need to add a product then index its' datasets.

    {
        "product_definition_uri": "https://raw.githubusercontent.com/GeoscienceAustralia/dea-config/master/products/lccs/lc_ls_c2.odc-product.yaml",
        "s3_glob": "s3://dea-public-data/cemp_insar/insar/displacement/alos/**/*.yaml",
        "product_name": "lc_ls_landcover_class_cyear_2_0"
    }

Usecase B: Only needs to index additional datasets to an existing product.

    {
        "s3_glob": "s3://dea-public-data/cemp_insar/insar/displacement/alos/**/*.yaml",
        "product_name": "lc_ls_landcover_class_cyear_2_0"
    }

Usecase C: Only need to add a product in this run, no datasets are ready for indexing.

    {
        "product_definition_uri": "https://raw.githubusercontent.com/GeoscienceAustralia/dea-config/master/products/lccs/lc_ls_c2.odc-product.yaml",
        "product_name": "lc_ls_landcover_class_cyear_2_0"
    }

### Flags

Indexing with s3-to-dc cli flags, `--no-sign-request` flag is provided by default works for usecase where indexing is performed, for details of all the available flag options https://github.com/opendatacube/odc-tools/blob/218ef9c85e5ebcbea00efb1297f7ed073f58d706/apps/dc_tools/README.md#s3-to-dc

    {
        "s3_glob": "s3://dea-public-data/cemp_insar/insar/displacement/alos/**/*.yaml",
        "flags": "--skip-lineages",
        "product_name": "lc_ls_landcover_class_cyear_2_0"
    }

"""

from datetime import datetime, timedelta

from airflow import DAG
from textwrap import dedent

from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)
from airflow.kubernetes.secret import Secret
from airflow.operators.python_operator import BranchPythonOperator
from airflow.utils.trigger_rule import TriggerRule

from infra.images import INDEXER_IMAGE
from infra.podconfig import (
    ONDEMAND_NODE_AFFINITY,
)
from infra.variables import (
    DB_DATABASE,
    DB_HOSTNAME,
    SECRET_ODC_WRITER_NAME,
    SECRET_ODC_ADMIN_NAME,
    AWS_DEFAULT_REGION,
    DB_PORT,
)
from dea_utils.update_explorer_summaries import explorer_refresh_operator
from dea_utils.s3_find_check import s3_find_operator

INDEXER_IMAGE = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/opendatacube/datacube-index:0.0.21"

ADD_PRODUCT_TASK_ID = "add-product-task"

S3_GLOB_VALIDATOR_TASK_ID = "s3-glob-validator-task"

INDEXING_TASK_ID = "batch-indexing-task"

DAG_NAME = "utility_add_product_index_dataset_explorer_update"

DEFAULT_ARGS = {
    "owner": "Pin Jin",
    "depends_on_past": False,
    "start_date": datetime(2020, 6, 14),
    "email": ["pin.jin@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
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

S3_TO_DC_CMD = [
    "bash",
    "-c",
    dedent(
        """
        s3-to-dc --no-sign-request {% if dag_run.conf.get('flags') %} {{ dag_run.conf.flags }}{% endif %} {{ dag_run.conf.s3_glob }} {{ dag_run.conf.product_name }}
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
    tags=["k8s", "add-product", "self-service", "index-datasets", "explorer-update"],
)


def check_dagrun_config(product_definition_uri, s3_glob, **kwargs):
    """
    determine task needed to perform
    """
    if product_definition_uri and s3_glob:
        return [ADD_PRODUCT_TASK_ID, S3_GLOB_VALIDATOR_TASK_ID]
    elif product_definition_uri:
        return ADD_PRODUCT_TASK_ID
    elif s3_glob:
        return S3_GLOB_VALIDATOR_TASK_ID


CHECK_DAGRUN_CONFIG = "check_dagrun_config"

with dag:
    TASK_PLANNER = BranchPythonOperator(
        task_id=CHECK_DAGRUN_CONFIG,
        python_callable=check_dagrun_config,
        op_kwargs={
            "product_definition_uri": "{% if dag_run.conf.get('product_definition_uri') %} {{ dag_run.conf.product_definition_uri }} {% endif %}",
            "s3_glob": "{% if dag_run.conf.get('s3_glob') %} {{ dag_run.conf.s3_glob }} {% endif %}",
        },
    )

    ADD_PRODUCT = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        image_pull_policy="IfNotPresent",
        labels={"step": "datacube-product-add"},
        cmds=["datacube"],
        secrets=[
            Secret("env", "DB_USERNAME", SECRET_ODC_ADMIN_NAME, "postgres-username"),
            Secret("env", "DB_PASSWORD", SECRET_ODC_ADMIN_NAME, "postgres-password"),
        ],
        arguments=[
            "product",
            "add",
            "{{ dag_run.conf.product_definition_uri }}",
        ],
        name="datacube-add-product",
        task_id=ADD_PRODUCT_TASK_ID,
        get_logs=True,
        affinity=ONDEMAND_NODE_AFFINITY,
        is_delete_operator_pod=True,
    )

    S3_GLOB_VALIDATOR = s3_find_operator("{{ dag_run.conf.s3_glob }}")

    INDEXING = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        image_pull_policy="IfNotPresent",
        labels={"step": "s3-to-dc"},
        arguments=S3_TO_DC_CMD,
        name="datacube-index",
        task_id=INDEXING_TASK_ID,
        get_logs=True,
        affinity=ONDEMAND_NODE_AFFINITY,
        is_delete_operator_pod=True,
        trigger_rule=TriggerRule.NONE_FAILED_OR_SKIPPED,  # Needed in case add product was skipped
    )

    EXPLORER_SUMMARY = explorer_refresh_operator("{{ dag_run.conf.product_name }}")

    TASK_PLANNER >> [ADD_PRODUCT, S3_GLOB_VALIDATOR]
    ADD_PRODUCT >> S3_GLOB_VALIDATOR >> INDEXING >> EXPLORER_SUMMARY
