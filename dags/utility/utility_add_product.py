"""
# Product Adding and Indexing Utility Tool (Self Serve)

This DAG should be triggered manually and will:

- Add a new Product to the database *(Optional)*
- Index a glob of datasets on S3 *(Optional)*
- Update Datacube Explorer so that you can see the results

## Customisation

There are three configuration arguments:

- `product_definition_uri`: A HTTP/S url to a Product Definition YAML *(Optional)*
- `s3_glob`: An S3 URL or Glob pattern, as recognised by `s3-to-dc` *(Optional)*
- `product_name`: The name of the product

The commands which are executed are:

1. `datacube product add`
2. `s3-to-dc`
3. update explorer


## Sample Configuration

    {
        "product_definition_uri": "https://raw.githubusercontent.com/GeoscienceAustralia/dea-config/master/products/lccs/lc_ls_c2.odc-product.yaml",
        "s3_glob": "s3://dea-public-data/cemp_insar/insar/displacement/alos//**/*.yaml",
        "product_name": "lc_ls_landcover_class_cyear_2_0"
    }

"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.kubernetes.secret import Secret
from airflow.operators.python_operator import PythonOperator, BranchPythonOperator
from airflow.utils.trigger_rule import TriggerRule

from infra.images import INDEXER_IMAGE
from infra.podconfig import (
    ONDEMAND_NODE_AFFINITY,
)
from infra.variables import (
    DB_DATABASE,
    DB_HOSTNAME,
    SECRET_ODC_WRITER_NAME,
    AWS_DEFAULT_REGION,
    DB_PORT,
)
from subdags.subdag_explorer_summary import explorer_refresh_operator

ADD_PRODUCT_TASK_ID = "add-product-task"

INDEXING_TASK_ID = "batch-indexing-task"

DAG_NAME = "utility_add_product_index_dataset_explorer_update"

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
    tags=["k8s", "add-product", "self-service", "index-datasets", "explorer-update"],
)


def parse_dagrun_conf(product_name, **kwargs):
    """
    parse input
    """
    return product_name


def check_dagrun_config(product_definition_uri, s3_glob, **kwargs):
    """
    determine task needed to perform
    """
    if product_definition_uri and s3_glob:
        return [ADD_PRODUCT_TASK_ID, INDEXING_TASK_ID]
    elif product_definition_uri:
        return ADD_PRODUCT_TASK_ID
    elif s3_glob:
        return INDEXING_TASK_ID


SET_REFRESH_PRODUCT_TASK_NAME = "parse_dagrun_conf"
CHECK_DAGRUN_CONFIG = "check_dagrun_config"

with dag:
    TASK_PLANNER = BranchPythonOperator(
        task_id=CHECK_DAGRUN_CONFIG,
        python_callable=check_dagrun_config,
        op_args=[
            "{{ dag_run.conf.product_definition_uri }}",
            "{{ dag_run.conf.s3_glob }}",
        ],
    )

    ADD_PRODUCT = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        image_pull_policy="IfNotPresent",
        labels={"step": "datacube-product-add"},
        cmds=["datacube"],
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

    INDEXING = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        image_pull_policy="IfNotPresent",
        labels={"step": "s3-to-dc"},
        cmds=["s3-to-dc"],
        arguments=[
            # "s3://dea-public-data/cemp_insar/insar/displacement/alos//**/*.yaml",
            # "cemp_insar_alos_displacement",
            # Jinja templates for arguments
            "{{ dag_run.conf.s3_glob }}",
            "{{ dag_run.conf.product_name }}",
            "--no-sign-request",
        ],
        name="datacube-index",
        task_id=INDEXING_TASK_ID,
        get_logs=True,
        affinity=ONDEMAND_NODE_AFFINITY,
        is_delete_operator_pod=True,
        trigger_rule=TriggerRule.NONE_FAILED_OR_SKIPPED,  # Needed in case add product was skipped
    )

    SET_PRODUCTS = PythonOperator(
        task_id=SET_REFRESH_PRODUCT_TASK_NAME,
        python_callable=parse_dagrun_conf,
        op_args=["{{ dag_run.conf.product_name }}"],
    )

    EXPLORER_SUMMARY = explorer_refresh_operator(
        xcom_task_id=SET_REFRESH_PRODUCT_TASK_NAME,
    )

    TASK_PLANNER >> [ADD_PRODUCT, INDEXING]
    ADD_PRODUCT >> INDEXING >> EXPLORER_SUMMARY
    SET_PRODUCTS >> EXPLORER_SUMMARY
