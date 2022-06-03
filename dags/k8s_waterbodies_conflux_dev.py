"""
DEA Waterbodies processing using Conflux.

Supported configuration arguments:

shapefile
    Default "s3://dea-public-data-dev/projects/WaterBodies/c3_shp/ga_ls_wb_3_v2_dev.shp"

outdir
    Default "s3://dea-public-data-dev/projects/WaterBodies/integration_testing/timeseries_pq_v2"

product
    Default "ga_ls_wo_3".

cmd
    Datacube query to run. Default "'time in [2021-01-01, 2099-01-01]'"
    https://datacube-core.readthedocs.io/en/stable/ops/tools.html#datacube-dataset-search
    e.g. "'lat in [-36.006, -34.671]' 'lon in [142.392, 144.496]' 'gqa_mean_x in [-1, 1]'"

plugin
    Plugin to drill with. Default "waterbodies_c3".

queue_name
    Amazon SQS queue name to save processing tasks. Default "waterbodies_conflux_dev_sqs"

csvdir
    Default "s3://dea-public-data-dev/projects/WaterBodies/integration_testing/timeseries"

flags
    Other flags to pass to Conflux.

"""
from datetime import datetime, timedelta

# import json

from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)

from textwrap import dedent

from infra.images import CONFLUX_DEV_IMAGE

from infra.variables import (
    DB_DATABASE,
    DB_READER_HOSTNAME,
    AWS_DEFAULT_REGION,
    DB_HOSTNAME,
    DB_PORT,
    WATERBODIES_DEV_USER_SECRET,
    SECRET_ODC_READER_NAME,
    WATERBODIES_DB_WRITER_SECRET,
)

# Default config parameters.
DEFAULT_PARAMS = dict(
    shapefile="s3://dea-public-data-dev/projects/WaterBodies/c3_shp/ga_ls_wb_3_v2_dev.shp",
    outdir="s3://dea-public-data-dev/projects/WaterBodies/integration_testing/timeseries_pq_v2",
    product="ga_ls_wo_3",
    # this will break in 2100
    # good luck y'all future folks
    cmd="'time in [2021-01-01, 2099-01-01]'",
    plugin="waterbodies_c3",
    queue_name="waterbodies_conflux_dev_sqs",
    csvdir="s3://dea-public-data-dev/projects/WaterBodies/integration_testing/timeseries",
)

# Requested memory. Memory limit is twice this.
CONFLUX_POD_MEMORY_MB = 6000

# DAG CONFIGURATION
SECRETS = {
    "env_vars": {
        "DB_HOSTNAME": DB_READER_HOSTNAME,
        "DB_DATABASE": DB_DATABASE,
        "DB_PORT": DB_PORT,
        "AWS_DEFAULT_REGION": AWS_DEFAULT_REGION,
        "WATERBODIES_DB_HOST": DB_HOSTNAME,
        "WATERBODIES_DB_PORT": DB_PORT,
    },
    # Lift secrets into environment variables
    "secrets": [
        Secret("env", "WATERBODIES_DB_NAME", WATERBODIES_DB_WRITER_SECRET, "database-name"),
        Secret("env", "WATERBODIES_DB_USER", WATERBODIES_DB_WRITER_SECRET, "postgres-username"),
        Secret("env", "WATERBODIES_DB_PASS", WATERBODIES_DB_WRITER_SECRET, "postgres-password"),
        Secret("env", "DB_USERNAME", SECRET_ODC_READER_NAME, "postgres-username"),
        Secret("env", "DB_PASSWORD", SECRET_ODC_READER_NAME, "postgres-password"),
        Secret(
            "env",
            "AWS_ACCESS_KEY_ID",
            WATERBODIES_DEV_USER_SECRET,
            "AWS_ACCESS_KEY_ID",
        ),
        Secret(
            "env",
            "AWS_SECRET_ACCESS_KEY",
            WATERBODIES_DEV_USER_SECRET,
            "AWS_SECRET_ACCESS_KEY",
        ),
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
    "k8s_waterbodies_conflux_dev",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval=None,  # triggered only
    catchup=False,
    concurrency=128,
    tags=["k8s", "landsat", "waterbodies", "conflux", "Work In Progress"],
)


def k8s_makecsvs(dag):
    makecsvs_cmd = [
        "bash",
        "-c",
        dedent(
            """
            echo "Using dea-conflux image {image}"
            dea-conflux db-to-csv --output {{{{ dag_run.conf.get("csvdir", "{csvdir}") }}}} --shapefile {{{{ dag_run.conf.get("shapefile", "{shapefile}") }}}} --jobs 128 --verbose -b 0 -e 80000
            """.format(
                image=CONFLUX_DEV_IMAGE,
                csvdir=DEFAULT_PARAMS['csvdir'],
                shapefile=DEFAULT_PARAMS['shapefile'],
            )
        ),
    ]
    makecsvs = KubernetesPodOperator(
        image=CONFLUX_DEV_IMAGE,
        name="waterbodies-conflux-makecsvs",
        arguments=makecsvs_cmd,
        image_pull_policy="IfNotPresent",
        labels={"app": "waterbodies-conflux-makecsvs"},
        get_logs=False,
        affinity=affinity,
        is_delete_operator_pod=True,
        resources={
            "request_cpu": "10000m",
            "request_memory": "8192Mi",
        },
        namespace="processing",
        tolerations=tolerations,
        task_id="waterbodies-conflux-makecsvs",
    )
    return makecsvs


with dag:
    cmd = '{{{{ dag_run.conf.get("cmd", "{cmd}") }}}}'.format(
        cmd=DEFAULT_PARAMS['cmd'],
    )

    makecsvs = k8s_makecsvs(dag)
