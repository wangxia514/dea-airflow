"""
This DAG aims index the Burn Cube 4 years GeoMED summary product to private ODC Database.

The Burn Cube 4 years GeoMED summary is still under development. Then we just hard-code the product name and dataset path in this DAG.

We force the user to provide script path before DAG run. In case the Airlfow repo had been hacked and someone can pass any script to run in GA network.

"""

from datetime import datetime, timedelta
from textwrap import dedent

from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)

from infra.podconfig import (
    ONDEMAND_NODE_AFFINITY,
)

from infra.projects.hnrs import (
    SECRET_HNRS_DC_WRITER_NAME,
    SECRET_HNRS_DC_ADMIN_NAME,
    HNRS_DB_DATABASE,
)

from infra.variables import (
    DB_HOSTNAME,
    DB_PORT,
)

INDEXER_IMAGE = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/opendatacube/datacube-index:latest"

# DAG CONFIGURATION
SECRETS = {
    # Lift secrets into environment variables
    "secrets": [
        Secret("env", "DB_USERNAME", SECRET_HNRS_DC_WRITER_NAME, "postgres-username"),
        Secret("env", "DB_PASSWORD", SECRET_HNRS_DC_WRITER_NAME, "postgres-password"),
    ],
}
DEFAULT_ARGS = {
    "owner": "Sai Ma",
    "depends_on_past": False,
    "start_date": datetime(2022, 12, 2),
    "email": ["sai.ma@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "startup_timeout_seconds": 5 * 60,
    "env_vars": {
        "DB_HOSTNAME": DB_HOSTNAME,
        "DB_DATABASE": HNRS_DB_DATABASE,
        "DB_PORT": DB_PORT,
    },
    **SECRETS,
}

# THE DAG
dag = DAG(
    "k8s_burn_cube_4year_gm_indexing",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,  # triggered only
    catchup=False,
    concurrency=128,
    tags=["k8s", "geomed", "burn_cube"],
)


S3_TO_DC_CMD = [
    "bash",
    "-c",
    dedent(
        """
        s3-to-dc s3://dea-public-data-dev/projects/burn_cube/ga_ls8c_nbart_gm_4cyear_3/*/*/*/2018--P4Y/*.odc-metadata.yaml --no-sign-request --skip-lineage ga_ls8c_nbart_gm_4cyear_3
        """
    ),
]


ADD_PRODUCTS_CMD = [
    "bash",
    "-c",
    dedent(
        """
        datacube product add https://raw.githubusercontent.com/GeoscienceAustralia/burn-mapping/feature/Burn_Cube_AWS_app/dea_burn_cube/configs/gm_products/ga_ls8c_nbart_gm_4cyear_3.odc-product.yaml
        """
    ),
]


ADD_METADATA_TYPE_CMD = [
    "bash",
    "-c",
    dedent(
        """
        datacube metadata add https://raw.githubusercontent.com/GeoscienceAustralia/dea-config/a4f39b485b33608a016032d9987251881fec4b6f/workspaces/sandbox-metadata.yaml
        """
    ),
]


def add_metadata_type(dag):
    return KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        image_pull_policy="IfNotPresent",
        labels={"step": "add-metadata-type"},
        arguments=ADD_METADATA_TYPE_CMD,
        name="elvis-lidar-add-metadata-type",
        task_id="elvis-lidar-add-metadata-type",
        get_logs=True,
        affinity=ONDEMAND_NODE_AFFINITY,
        is_delete_operator_pod=True,
        secrets=[
            Secret(
                "env", "DB_USERNAME", SECRET_HNRS_DC_ADMIN_NAME, "postgres-username"
            ),
            Secret(
                "env", "DB_PASSWORD", SECRET_HNRS_DC_ADMIN_NAME, "postgres-password"
            ),
        ],
    )


def add_products(dag):
    return KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        image_pull_policy="IfNotPresent",
        labels={"step": "burn-cube-4year-geomed-add-products"},
        arguments=ADD_PRODUCTS_CMD,
        name="burn-cube-4year-geomed-add-products",
        task_id="burn-cube-4year-geomed-add-products",
        get_logs=True,
        affinity=ONDEMAND_NODE_AFFINITY,
        is_delete_operator_pod=True,
        secrets=[
            Secret(
                "env", "DB_USERNAME", SECRET_HNRS_DC_ADMIN_NAME, "postgres-username"
            ),
            Secret(
                "env", "DB_PASSWORD", SECRET_HNRS_DC_ADMIN_NAME, "postgres-password"
            ),
        ],
    )


def index_dataset(dag):
    return KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        image_pull_policy="IfNotPresent",
        labels={"step": "s3-to-dc"},
        arguments=S3_TO_DC_CMD,
        name="burn-cube-4year-geomed-indexing-metadata",
        task_id="burn-cube-4year-geomed-indexing-metadata",
        get_logs=True,
        affinity=ONDEMAND_NODE_AFFINITY,
        is_delete_operator_pod=True,
    )


with dag:
    add_metadata_type = add_metadata_type(dag)
    add_products = add_products(dag)
    index_dataset = index_dataset(dag)
    add_metadata_type >> add_products >> index_dataset
