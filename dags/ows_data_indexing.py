"""
# Sentinel-2 indexing automation

DAG to periodically index Sentinel-2 data. Eventually it could
update explorer and ows schemas in RDS after a given Dataset has been
indexed.

This DAG uses k8s executors and in cluster with relevant tooling
and configuration installed.

"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.kubernetes.volume import Volume
from airflow.kubernetes.volume_mount import VolumeMount
from airflow.contrib.operators.kubernetes_pod_operator import \
    KubernetesPodOperator
from airflow.operators.dummy_operator import DummyOperator

from textwrap import dedent

import kubernetes.client.models as k8s

# ENVIRONMENT CONFIGURATION
OWS_CFG_PATH = "/env/config/ows_cfg.py"
INDEXING_PRODUCTS = "s2a_nrt_granule s2b_nrt_granule"
ARCHIVE_PRODUCTS = INDEXING_PRODUCTS
ARCHIVE_CONDITION = "[$(date -d '-365 day' +%F), $(date -d '-91 day' +%F)]"
UPDATE_EXTENT_PRODUCTS = "s2_nrt_granule_nbar_t"
SQS_QUEUE_NAME = "dea-dev-eks-ows"
INDEXING_ROLE = "dea-dev-eks-orchestration"
SECRET_AWS_NAME = "processing-aws-creds-dev"
SECRET_EXPLORER_NAME = "explorer-db"
SECRET_OWS_NAME = "ows-db"
DB_DATABASE = "ows"

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
        "DB_HOSTNAME": "database-write.local",
        "DB_DATABASE": DB_DATABASE,
        "WMS_CONFIG_PATH": OWS_CFG_PATH,
        "DATACUBE_OWS_CFG": "config.ows_cfg.ows_cfg"
    },
    # Lift secrets into environment variables
    "secrets": [
        Secret("env", "DB_USERNAME", SECRET_OWS_NAME, "postgres-username"),
        Secret("env", "DB_PASSWORD", SECRET_OWS_NAME, "postgres-password"),
        Secret("env", "AWS_DEFAULT_REGION", SECRET_AWS_NAME, "AWS_DEFAULT_REGION"),
        Secret("env", "AWS_ACCESS_KEY_ID", SECRET_AWS_NAME, "AWS_ACCESS_KEY_ID"),
        Secret("env", "AWS_SECRET_ACCESS_KEY", SECRET_AWS_NAME, "AWS_SECRET_ACCESS_KEY"),
    ],
}

EXPLORER_SECRETS = [
    Secret("env", "DB_USERNAME", SECRET_EXPLORER_NAME, "postgres-username"),
    Secret("env", "DB_PASSWORD", SECRET_EXPLORER_NAME, "postgres-password")
]

# IMAGES USED FOR THIS DAG
INDEXER_IMAGE = "opendatacube/datacube-index:0.0.8"

OWS_IMAGE = "opendatacube/ows:1.8.1"
OWS_CONFIG_IMAGE = "geoscienceaustralia/dea-datakube-config:1.5.1"
OWS_CFG_IMAGEPATH = "/opt/dea-config/dev/services/wms/ows/ows_cfg.py"

EXPLORER_IMAGE = "opendatacube/dashboard:2.1.9"

# MOUNT OWS_CFG via init_container
# for main container mount
ows_cfg_mount = VolumeMount('ows-config-volume',
                            mount_path='/env/config',
                            sub_path=None,
                            read_only=False)


ows_cfg_volume_config= {}

ows_cfg_volume = Volume(name='ows-config-volume', configs=ows_cfg_volume_config)


# for init container mount
cfg_image_mount = k8s.V1VolumeMount(
      mount_path='/env/config',
      name='ows-config-volume',
      sub_path=None,
      read_only=False
)

config_container = k8s.V1Container(
        image=OWS_CONFIG_IMAGE,
        command=["cp"],
        args=[OWS_CFG_IMAGEPATH, OWS_CFG_PATH],
        volume_mounts=[cfg_image_mount],
        name="mount-ows-config",
        working_dir="/opt"
    )


# BASH COMMANDS FOR EACH CONTAINER
OWS_BASH_COMMAND = [
    "bash",
    "-c",
    dedent("""
        datacube-ows-update --views;
        for product in %s; do
            datacube-ows-update $product;
        done;
    """)%(UPDATE_EXTENT_PRODUCTS)
]

EXPLORER_BASH_COMMAND = [
    "bash",
    "-c",
    dedent("""
        for product in %s; do
            cubedash-gen --no-init-database --refresh-stats --force-refresh $product;
        done;
    """)%(INDEXING_PRODUCTS)
]

INDEXING_BASH_COMMAND = [
    "bash",
    "-c",
    dedent("""
        for product in %s; do
            sqs-to-dc %s $product;
        done;
    """)%(INDEXING_PRODUCTS, SQS_QUEUE_NAME)
]

ARCHIVE_BASH_COMMAND = [
    "bash",
    "-c",
    dedent("""
        for product in %s; do
            datacube dataset search -f csv "product=$product time in %s" > /tmp/to_kill.csv;
            cat /tmp/to_kill.csv | awk -F',' '{print $1}' | sed '1d' > /tmp/to_kill.list;
            wc -l /tmp/to_kill.list;
            cat /tmp/to_kill.list | xargs datacube dataset archive
        done;
    """)%(ARCHIVE_PRODUCTS, ARCHIVE_CONDITION)
]

# THE DAG
dag = DAG(
    "sentinel-2_nrt_indexing",
    doc_md=__doc__,
    default_args=DEFAULT_ARGS,
    schedule_interval='0 */1 * * *',
    catchup=False,
    tags=["k8s", "sentinel-2"]
)

with dag:
    INDEXING = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        image_pull_policy='IfNotPresent',
        annotations={"iam.amazonaws.com/role": INDEXING_ROLE},
        arguments=INDEXING_BASH_COMMAND,
        labels={"step": "sqs-to-rds"},
        name="datacube-index",
        task_id="indexing-task",
        get_logs=True,
        # is_delete_operator_pod=True,
    )

    ARCHIVE_EXTRANEOUS_DS = KubernetesPodOperator(
        namespace="processing",
        image=INDEXER_IMAGE,
        arguments=ARCHIVE_BASH_COMMAND,
        labels={"step": "ds-arch"},
        name="datacube-dataset-archive",
        task_id="archive-nrt-datasets",
        get_logs=True,
        is_delete_operator_pod=True,
    )

    OWS_UPDATE_EXTENTS = KubernetesPodOperator(
        namespace="processing",
        image=OWS_IMAGE,
        arguments=OWS_BASH_COMMAND,
        labels={"step": "ows-mv"},
        name="ows-update-extents",
        task_id="ows-update-extents",
        get_logs=True,
        volumes=[ows_cfg_volume],
        volume_mounts=[ows_cfg_mount],
        init_containers=[config_container],
        is_delete_operator_pod=True,
    )

    EXPLORER_SUMMARY = KubernetesPodOperator(
        namespace="processing",
        image=EXPLORER_IMAGE,
        arguments=EXPLORER_BASH_COMMAND,
        secrets=EXPLORER_SECRETS,
        labels={"step": "explorer"},
        name="explorer-summary",
        task_id="explorer-summary-task",
        get_logs=True,
        is_delete_operator_pod=True,
    )

    COMPLETE = DummyOperator(task_id="all_done")

    INDEXING >> ARCHIVE_EXTRANEOUS_DS
    ARCHIVE_EXTRANEOUS_DS >> OWS_UPDATE_EXTENTS
    ARCHIVE_EXTRANEOUS_DS >> EXPLORER_SUMMARY
    OWS_UPDATE_EXTENTS >> COMPLETE
    EXPLORER_SUMMARY >> COMPLETE