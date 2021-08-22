"""
Run ARD NRT pipeline for Sentinel-2 (provisional) in Airflow.
"""
import json
import logging
from datetime import datetime, timedelta

from kubernetes.client.models import V1Volume, V1VolumeMount
from kubernetes.client import models as k8s

from airflow import DAG
from airflow.kubernetes.secret import Secret
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator, BranchPythonOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.amazon.aws.hooks.sqs import SQSHook
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)

from infra.connections import AWS_WAGL_NRT_CONN
from infra.images import WAGL_IMAGE_POC
from infra.pools import WAGL_TASK_POOL
from infra.s3_buckets import S2_NRT_SOURCE_BUCKET, S2_NRT_TRANSFER_BUCKET
from infra.sns_notifications import PUBLISH_ARD_NRT_S2_PROVISIONAL_SNS
from infra.sqs_queues import ARD_NRT_S2_PROVISIONAL_PROCESS_SCENE_QUEUE
from infra.variables import S2_NRT_AWS_CREDS

_LOG = logging.getLogger()

default_args = {
    "owner": "Imam Alam",
    "depends_on_past": False,
    "start_date": datetime(2021, 6, 1),
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

# a bit unsure about this and the frequency
NUM_PARALLEL_PIPELINE = 1
MAX_ACTIVE_RUNS = 12

# this should be 10 in dev for 10% capacity
# then it would just discard the other 9 messages polled
NUM_MESSAGES_TO_POLL = 1

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


def setup_logging():
    """ """
    _LOG.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    _LOG.addHandler(handler)


setup_logging()


def decode(message):
    """Decode stringified message."""
    return json.loads(message["Body"])


def get_tile_info(msg_dict):
    """Minimal info to be able to run wagl."""
    assert len(msg_dict["tiles"]) == 1, "was not expecting multi-tile granule"
    tile = msg_dict["tiles"][0]

    return dict(
        granule_id=msg_dict["id"],
        path=tile["path"],
        datastrip=tile["datastrip"]["path"],
    )


def tile_args(tile_info):
    """Arguments to the wagl container."""
    path = tile_info["path"]
    datastrip = tile_info["datastrip"]

    return dict(
        granule_id=tile_info["granule_id"],
        granule_url=f"s3://{S2_NRT_TRANSFER_BUCKET}/{path}",
        datastrip_url=f"s3://{S2_NRT_TRANSFER_BUCKET}/{datastrip}",
    )


def get_sqs():
    """SQS client."""
    return SQSHook(aws_conn_id=AWS_WAGL_NRT_CONN).get_conn()


def get_s3():
    """S3 client."""
    return S3Hook(aws_conn_id=AWS_WAGL_NRT_CONN).get_conn()


def get_message(sqs, url):
    """Receive one message with an estimated completion time set."""
    response = sqs.receive_message(
        QueueUrl=url, VisibilityTimeout=ESTIMATED_COMPLETION_TIME, MaxNumberOfMessages=1
    )

    if "Messages" not in response:
        return None

    messages = response["Messages"]

    if len(messages) == 0:
        return None
    else:
        return messages[0]


def receive_task(**context):
    """Receive a task from the task queue."""
    task_instance = context["task_instance"]
    index = context["index"]

    sqs = get_sqs()
    message = get_message(sqs, ARD_NRT_S2_PROVISIONAL_PROCESS_SCENE_QUEUE)

    if message is None:
        _LOG.info("no messages")
        return f"nothing_to_do_{index}"
    else:
        _LOG.info("received message")
        _LOG.info("%r", message)

        task_instance.xcom_push(key="message", value=message)

        msg_dict = decode(message)
        tile_info = get_tile_info(msg_dict)

        task_instance.xcom_push(key="args", value=tile_args(tile_info))

        return f"dea-s2-wagl-nrt-copy-scene-{index}"


def finish_up(**context):
    """Delete the SQS message to mark completion, broadcast to SNS."""
    task_instance = context["task_instance"]
    index = context["index"]

    message = task_instance.xcom_pull(task_ids=f"receive_task_{index}", key="message")
    sqs = get_sqs()

    _LOG.info("deleting %s", message["ReceiptHandle"])
    sqs.delete_message(
        QueueUrl=ARD_NRT_S2_PROVISIONAL_PROCESS_SCENE_QUEUE,
        ReceiptHandle=message["ReceiptHandle"],
    )


pipeline = DAG(
    "k8s_ard_nrt_sentinel2_provisional",
    doc_md=__doc__,
    default_args=default_args,
    description="DEA Sentinel-2 ARD NRT processing (provisional)",
    concurrency=MAX_ACTIVE_RUNS * NUM_PARALLEL_PIPELINE,
    max_active_runs=MAX_ACTIVE_RUNS,
    catchup=False,
    params={},
    schedule_interval=None,
    tags=["k8s", "dea", "psc", "ard", "wagl", "nrt", "sentinel-2", "provisional"],
)

with pipeline:
    for index in range(NUM_PARALLEL_PIPELINE):
        SENSOR = BranchPythonOperator(
            task_id=f"receive_task_{index}",
            python_callable=receive_task,
            op_kwargs={"index": index},
            provide_context=True,
        )

        RUN = KubernetesPodOperator(
            namespace="processing",
            name="dea-s2-wagl-nrt",
            task_id=f"dea-s2-wagl-nrt-{index}",
            image_pull_policy="Always",
            # image_pull_policy="IfNotPresent",
            image=WAGL_IMAGE_POC,
            affinity=affinity,
            tolerations=tolerations,
            startup_timeout_seconds=600,
            # this is the wagl_nrt user in the wagl container
            # security_context=dict(runAsUser=10015, runAsGroup=10015, fsGroup=10015),
            cmds=["/scripts/process-scene-sentinel-2.sh"],
            arguments=[
                "{{ task_instance.xcom_pull(task_ids='receive_task_"
                + str(index)
                + "', key='args')['granule_url'] }}",
                "{{ task_instance.xcom_pull(task_ids='receive_task_"
                + str(index)
                + "', key='args')['datastrip_url'] }}",
                "{{ task_instance.xcom_pull(task_ids='receive_task_"
                + str(index)
                + "', key='args')['granule_id'] }}",
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

        FINISH = PythonOperator(
            task_id=f"finish_{index}",
            python_callable=finish_up,
            op_kwargs={"index": index},
            provide_context=True,
        )

        NOTHING = DummyOperator(task_id=f"nothing_to_do_{index}")

        SENSOR >> RUN >> FINISH
        SENSOR >> NOTHING
