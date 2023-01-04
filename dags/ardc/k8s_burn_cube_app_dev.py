"""
DEA Burn Cube processing by K8s.

"""
from datetime import datetime, timedelta

# import json

from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)

from airflow.utils.task_group import TaskGroup

from textwrap import dedent

from infra.projects.hnrs import (
    WATERBODIES_DEV_USER_SECRET,
    SECRET_HNRS_DC_ADMIN_NAME,
)


from infra.variables import (
    DB_READER_HOSTNAME,
    AWS_DEFAULT_REGION,
    DB_HOSTNAME,
    DB_PORT,
    SECRET_ODC_READER_NAME,
)

BURN_CUBE_UNSTABLE_IMAGE = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/geoscienceaustralia/burn-cube-app:latest"

# Requested memory. Memory limit is twice this.
BURN_CUBE_POD_MEMORY_MB = "40Gi"
BURN_CUBE_POD_CPU = "8000m"

# DAG CONFIGURATION
SECRETS = {
    "env_vars": {
        "ODC_DB_HOSTNAME": DB_READER_HOSTNAME,
        "HNRS_DB_HOSTNAME": DB_HOSTNAME,
        "DB_PORT": DB_PORT,
        "AWS_DEFAULT_REGION": AWS_DEFAULT_REGION,
        "AWS_NO_SIGN_REQUEST": "YES"
    },
    # Lift secrets into environment variables
    "secrets": [
        Secret("env", "ODC_DB_DATABASE", SECRET_ODC_READER_NAME, "database-name"),
        Secret("env", "ODC_DB_USERNAME", SECRET_ODC_READER_NAME, "postgres-username"),
        Secret("env", "ODC_DB_PASSWORD", SECRET_ODC_READER_NAME, "postgres-password"),
        Secret("env", "HNRS_DC_DB_DATABASE", SECRET_HNRS_DC_ADMIN_NAME, "database-name"),
        Secret("env", "HNRS_DC_DB_USERNAME", SECRET_HNRS_DC_ADMIN_NAME, "postgres-username"),
        Secret("env", "HNRS_DC_DB_PASSWORD", SECRET_HNRS_DC_ADMIN_NAME, "postgres-password"),
        Secret("env", "AWS_ACCESS_KEY_ID", WATERBODIES_DEV_USER_SECRET, "AWS_ACCESS_KEY_ID"),
        Secret("env", "AWS_SECRET_ACCESS_KEY", WATERBODIES_DEV_USER_SECRET, "AWS_SECRET_ACCESS_KEY"),
    ],
}
DEFAULT_ARGS = {
    "owner": "Sai Ma",
    "depends_on_past": False,
    "start_date": datetime(2021, 6, 2),
    "email": ["sai.ma@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "startup_timeout_seconds": 5 * 60,
    **SECRETS,
}

# Keep the Waterbodies EC2 groups for now
# Kubernetes autoscaling group affinity
affinity = {
    "nodeAffinity": {
        "requiredDuringSchedulingIgnoredDuringExecution": {
            "nodeSelectorTerms": [
                {
                    "matchExpressions": [
                        {
                            "key": "nodegroup",
                            "operator": "In",
                            "values": [
                                "r5-4xl-waterbodies",
                            ],
                        }
                    ]
                }
            ]
        }
    }
}

tolerations = [
    {
        "key": "dedicated",
        "operator": "Equal",
        "value": "waterbodies",
        "effect": "NoSchedule",
    }
]

# THE DAG
dag = DAG(
    "k8s_burn_cube_app_dev",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,  # triggered only
    catchup=False,
    concurrency=128,
    tags=["k8s", "landsat", "burn_cube", "integration test"],
)


def k8s_bc_processing(dag, region_name):
    bc_run_processing = [
        "bash",
        "-c",
        dedent(
            """
            echo "Using dea-burn-app image"
            dea-burn-cube burn-cube-run -o s3://dea-public-data-dev/projects/WaterBodies/sai-test/burn-cube-app -r {region_name} -t Dec-21 -v
            """.format(
                region_name=region_name
            )
        ),
    ]
    bc_processing = KubernetesPodOperator(
        image=BURN_CUBE_UNSTABLE_IMAGE,
        name="burn-cube-app-processing-" + region_name,
        arguments=bc_run_processing,
        image_pull_policy="IfNotPresent",
        labels={"app": "burn-cube-app-processing"},
        get_logs=False,
        affinity=affinity,
        is_delete_operator_pod=True,
        resources={
            "request_cpu": BURN_CUBE_POD_CPU,
            "request_memory": BURN_CUBE_POD_MEMORY_MB,
        },
        namespace="processing",
        tolerations=tolerations,
        task_id="burn-cube-app-processing-" + region_name,
    )
    return bc_processing


with dag:

    region_list = ["x45y19", "x46y19"]

    with TaskGroup(group_id="burn_cube_processing") as bc_processings:
        for region in region_list:
            bc_processing = k8s_bc_processing(dag, region_name=region)

    bc_processings
