"""
Run ARD NRT provisional pipeline for Sentinel-2 in Airflow.
"""
import logging
from datetime import datetime, timedelta

from kubernetes.client.models import V1Volume, V1VolumeMount
from kubernetes.client import models as k8s

from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)

from infra.images import WAGL_IMAGE_POC
from infra.pools import WAGL_TASK_POOL
from infra.sns_topics import PUBLISH_ARD_NRT_S2_PROVISIONAL_SNS
from infra.sqs_queues import ARD_NRT_S2_PROVISIONAL_PROCESS_SCENE_QUEUE
from infra.variables import S2_NRT_AWS_CREDS
from infra.s3_buckets import S2_NRT_TRANSFER_BUCKET

_LOG = logging.getLogger()

default_args = {
    "owner": "Imam Alam",
    "depends_on_past": False,
    "start_date": datetime(2021, 8, 24),
    "email": ["imam.alam@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
    "retry_delay": timedelta(minutes=5),
    "pool": WAGL_TASK_POOL,
    "secrets": [
        Secret("env", None, S2_NRT_AWS_CREDS),
        Secret("env", None, "modtran-key"),
    ],
}

ESTIMATED_COMPLETION_TIME = 3 * 60 * 60

S3_PREFIX = "s3://dea-public-data-dev/baseline/"
EXPLORER_URL = "https://explorer.dev.dea.ga.gov.au"

MAX_ACTIVE_RUNS = 12

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
                                "memory-optimised-wagl-s2-nrt-r5-l",
                            ],
                        }
                    ]
                }
            ]
        }
    }
}

tolerations = [
    {"key": "dedicated", "operator": "Equal", "value": "wagl", "effect": "NoSchedule"}
]

ancillary_volume_mount = V1VolumeMount(
    name="wagl-nrt-ancillary-volume",
    mount_path="/ancillary",
    sub_path=None,
    read_only=False,
)

ancillary_volume = V1Volume(
    name="wagl-nrt-ancillary-volume",
    persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(
        claim_name="wagl-nrt-ancillary-volume"
    ),
)

pipeline = DAG(
    "k8s_ard_nrt_sentinel2_provisional",
    doc_md=__doc__,
    default_args=default_args,
    description="DEA Sentinel-2 ARD NRT processing (provisional)",
    concurrency=MAX_ACTIVE_RUNS,
    max_active_runs=MAX_ACTIVE_RUNS,
    catchup=False,
    params={},
    schedule_interval=timedelta(minutes=1),
    tags=["k8s", "dea", "psc", "ard", "wagl", "nrt", "sentinel-2", "provisional"],
)

with pipeline:
    RUN = KubernetesPodOperator(
        namespace="processing",
        name="dea-ard-nrt-sentinel2-provisional",
        task_id="dea-ard-nrt-sentinel2-provisional",
        image_pull_policy="IfNotPresent",
        image=WAGL_IMAGE_POC,
        affinity=affinity,
        tolerations=tolerations,
        startup_timeout_seconds=600,
        cmds=["/scripts/aws-process-scene-sentinel-2.sh"],
        arguments=[
            ARD_NRT_S2_PROVISIONAL_PROCESS_SCENE_QUEUE,
            S2_NRT_TRANSFER_BUCKET,
            S3_PREFIX,
            PUBLISH_ARD_NRT_S2_PROVISIONAL_SNS,
            EXPLORER_URL,
        ],
        labels={
            "runner": "airflow",
            "product": "Sentinel-2",
            "app": "nrt",
            "stage": "wagl",
        },
        env_vars=dict(
            MODTRAN_DATA="/ancillary/MODTRAN6.0.2.3G/DATA",
        ),
        get_logs=True,
        resources={
            "request_cpu": "1000m",
            "request_memory": "12Gi",
        },
        volumes=[ancillary_volume],
        volume_mounts=[ancillary_volume_mount],
        execution_timeout=timedelta(minutes=180),
        is_delete_operator_pod=True,
    )
