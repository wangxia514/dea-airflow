"""
Run wagl NRT pipeline in Airflow.
"""
from datetime import datetime, timedelta
import random
from urllib.parse import urlencode, quote_plus
import json

from airflow import DAG

from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.contrib.operators.kubernetes_pod_operator import Resources
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.contrib.sensors.aws_sqs_sensor import SQSSensor
from airflow.contrib.hooks.aws_sns_hook import AwsSnsHook
from airflow.kubernetes.secret import Secret
from airflow.kubernetes.volume import Volume
from airflow.kubernetes.volume_mount import VolumeMount
from airflow.hooks.S3_hook import S3Hook
from airflow.contrib.hooks.aws_sqs_hook import SQSHook
from airflow.utils.trigger_rule import TriggerRule

import kubernetes.client.models as k8s

from infra.variables import WAGL_TASK_POOL


default_args = {
    "owner": "Imam Alam",
    "depends_on_past": False,
    "start_date": datetime(2020, 9, 11),
    "email": ["imam.alam@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "secrets": [Secret("env", None, "wagl-nrt-aws-creds")],
}

WAGL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/dev/wagl:patch-20210330-1"
)
S3_TO_RDS_IMAGE = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/geoscienceaustralia/s3-to-rds:0.1.2"

PROCESS_SCENE_QUEUE = "https://sqs.ap-southeast-2.amazonaws.com/451924316694/dea-dev-eks-wagl-s2-nrt-process-scene"
DEADLETTER_SCENE_QUEUE = "https://sqs.ap-southeast-2.amazonaws.com/451924316694/dea-dev-eks-wagl-s2-nrt-process-scene-deadletter"
PUBLISH_S2_NRT_SNS = "arn:aws:sns:ap-southeast-2:451924316694:dea-dev-eks-wagl-s2-nrt"

SOURCE_BUCKET = "sentinel-s2-l1c"
TRANSFER_BUCKET = "dea-dev-eks-nrt-scene-cache"

BUCKET_REGION = "ap-southeast-2"
S3_PREFIX = "s3://dea-public-data-dev/L2/sentinel-2-nrt/S2MSIARD/"

AWS_CONN_ID = "wagl_nrt_manual"

# each DAG instance should process one scene only
# TODO so this should be 10 in dev
NUM_MESSAGES_TO_POLL = 1

# TODO then this should be 3 in dev
NUM_PARALLEL_PIPELINE = 30

MAX_ACTIVE_RUNS = 15

AWS_CONN_ID = "wagl_nrt_manual"

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


ancillary_volume_mount = VolumeMount(
    name="wagl-nrt-ancillary-volume",
    mount_path="/ancillary",
    sub_path=None,
    read_only=False,
)


ancillary_volume = Volume(
    name="wagl-nrt-ancillary-volume",
    configs={"persistentVolumeClaim": {"claimName": "wagl-nrt-ancillary-volume"}},
)


def decode(message):
    return json.loads(message["Body"])


def copy_cmd_tile(tile_info):
    datastrip = tile_info["datastrip"]
    path = tile_info["path"]
    granule_id = tile_info["granule_id"]

    cmd = f"""
    set -e

    if ! aws s3api head-object --bucket {TRANSFER_BUCKET} --key {datastrip}/.done 2> /dev/null; then
        mkdir -p /transfer/{granule_id}
        echo sinergise -> disk [datastrip]
        aws s3 sync --only-show-errors --request-payer requester \\
                s3://{SOURCE_BUCKET}/{datastrip} /transfer/{granule_id}/{datastrip}
        echo disk -> cache [datastrip]
        aws s3 sync --only-show-errors \\
                /transfer/{granule_id}/{datastrip} s3://{TRANSFER_BUCKET}/{datastrip}
        touch /transfer/{granule_id}/{datastrip}/.done
        aws s3 sync --only-show-errors \\
                /transfer/{granule_id}/{datastrip}/.done s3://{TRANSFER_BUCKET}/{datastrip}/.done
    else
        echo s3://{TRANSFER_BUCKET}/{datastrip} already exists
    fi

    if ! aws s3api head-object --bucket {TRANSFER_BUCKET} --key {path}/.done 2> /dev/null; then
        mkdir -p /transfer/{granule_id}
        echo sinergise -> disk [path]
        aws s3 sync --only-show-errors --request-payer requester \\
                s3://{SOURCE_BUCKET}/{path} /transfer/{granule_id}/{path}
        echo disk -> cache [path]
        aws s3 sync --only-show-errors \\
                /transfer/{granule_id}/{path} s3://{TRANSFER_BUCKET}/{path}
        touch /transfer/{granule_id}/{path}/.done
        aws s3 sync --only-show-errors \\
                /transfer/{granule_id}/{path}/.done s3://{TRANSFER_BUCKET}/{path}/.done
    else
        echo s3://{TRANSFER_BUCKET}/{path} already exists
    fi

    rm -rf /transfer/{granule_id}
    """

    return cmd


def get_tile_info(msg_dict):
    assert len(msg_dict["tiles"]) == 1, "was not expecting multi-tile granule"
    tile = msg_dict["tiles"][0]

    return dict(
        granule_id=msg_dict["id"],
        path=tile["path"],
        datastrip=tile["datastrip"]["path"],
    )


def tile_args(tile_info):
    path = tile_info["path"]
    datastrip = tile_info["datastrip"]

    return dict(
        granule_id=tile_info["granule_id"],
        granule_url=f"s3://{TRANSFER_BUCKET}/{path}",
        datastrip_url=f"s3://{TRANSFER_BUCKET}/{datastrip}",
    )


def fetch_sqs_message(context):
    task_instance = context["task_instance"]
    index = context["index"]
    all_messages = task_instance.xcom_pull(
        task_ids=f"process_scene_queue_sensor_{index}", key="messages"
    )

    if all_messages is None:
        raise KeyError("no messages")

    messages = all_messages["Messages"]
    # assert len(messages) == 1
    return messages[0]


def copy_cmd(**context):
    message = fetch_sqs_message(context)

    msg_dict = decode(message)
    tile_info = get_tile_info(msg_dict)

    # forward it to the copy and processing tasks
    task_instance = context["task_instance"]
    task_instance.xcom_push(key="cmd", value=copy_cmd_tile(tile_info))
    task_instance.xcom_push(key="args", value=tile_args(tile_info))


def dag_result(**context):
    try:
        message = fetch_sqs_message(context)
    except KeyError:
        # no messages, success
        return

    sqs_hook = SQSHook(aws_conn_id=AWS_CONN_ID)
    message_body = json.dumps(decode(message))
    sqs_hook.send_message(DEADLETTER_SCENE_QUEUE, message_body)
    raise ValueError(f"processing failed for {message_body}")


def sns_broadcast(**context):
    task_instance = context["task_instance"]
    index = context["index"]
    msg = task_instance.xcom_pull(
        task_ids=f"dea-s2-wagl-nrt-{index}", key="return_value"
    )

    assert "dataset" in msg
    if msg["dataset"] == "exists":
        # dataset already existed, did not get processed by this DAG
        return

    msg_str = json.dumps(msg)

    sns_hook = AwsSnsHook(aws_conn_id=AWS_CONN_ID)
    sns_hook.publish_to_target(PUBLISH_S2_NRT_SNS, msg_str)


pipeline = DAG(
    "k8s_wagl_nrt",
    doc_md=__doc__,
    default_args=default_args,
    description="DEA Sentinel-2 NRT processing",
    concurrency=MAX_ACTIVE_RUNS * NUM_PARALLEL_PIPELINE,
    max_active_runs=MAX_ACTIVE_RUNS,
    catchup=False,
    params={},
    schedule_interval=timedelta(minutes=30),
    tags=["k8s", "dea", "psc", "wagl", "nrt"],
)

with pipeline:
    for index in range(NUM_PARALLEL_PIPELINE):
        SENSOR = SQSSensor(
            task_id=f"process_scene_queue_sensor_{index}",
            sqs_queue=PROCESS_SCENE_QUEUE,
            aws_conn_id=AWS_CONN_ID,
            max_messages=NUM_MESSAGES_TO_POLL,
            retries=0,
            execution_timeout=timedelta(minutes=1),
        )

        CMD = PythonOperator(
            task_id=f"copy_cmd_{index}",
            python_callable=copy_cmd,
            op_kwargs={"index": index},
            provide_context=True,
        )

        COPY = KubernetesPodOperator(
            namespace="processing",
            name="dea-s2-wagl-nrt-copy-scene",
            task_id=f"dea-s2-wagl-nrt-copy-scene-{index}",
            image_pull_policy="IfNotPresent",
            image=S3_TO_RDS_IMAGE,
            pool=WAGL_TASK_POOL,
            affinity=affinity,
            tolerations=tolerations,
            startup_timeout_seconds=600,
            volumes=[ancillary_volume],
            volume_mounts=[ancillary_volume_mount],
            cmds=[
                "bash",
                "-c",
                "{{ task_instance.xcom_pull(task_ids='copy_cmd_"
                + str(index)
                + "', key='cmd') }}",
            ],
            labels={
                "runner": "airflow",
                "product": "Sentinel-2",
                "app": "nrt",
                "stage": "copy-scene",
            },
            resources={
                "request_cpu": "1000m",
                "request_memory": "2Gi",
            },
            get_logs=True,
            is_delete_operator_pod=True,
        )

        RUN = KubernetesPodOperator(
            namespace="processing",
            name="dea-s2-wagl-nrt",
            task_id=f"dea-s2-wagl-nrt-{index}",
            image_pull_policy="IfNotPresent",
            image=WAGL_IMAGE,
            affinity=affinity,
            tolerations=tolerations,
            pool=WAGL_TASK_POOL,
            startup_timeout_seconds=600,
            # this is the wagl_nrt user in the wagl container
            security_context=dict(runAsUser=10015, runAsGroup=10015, fsGroup=10015),
            cmds=["/scripts/process-scene.sh"],
            arguments=[
                "{{ task_instance.xcom_pull(task_ids='copy_cmd_"
                + str(index)
                + "', key='args')['granule_url'] }}",
                "{{ task_instance.xcom_pull(task_ids='copy_cmd_"
                + str(index)
                + "', key='args')['datastrip_url'] }}",
                "{{ task_instance.xcom_pull(task_ids='copy_cmd_"
                + str(index)
                + "', key='args')['granule_id'] }}",
                BUCKET_REGION,
                S3_PREFIX,
            ],
            labels={
                "runner": "airflow",
                "product": "Sentinel-2",
                "app": "nrt",
                "stage": "wagl",
            },
            env_vars=dict(
                bucket_region=BUCKET_REGION,
                datastrip_url="{{ task_instance.xcom_pull(task_ids='copy_cmd_"
                + str(index)
                + "', key='args')['datastrip_url'] }}",
                granule_url="{{ task_instance.xcom_pull(task_ids='copy_cmd_"
                + str(index)
                + "', key='args')['granule_url'] }}",
                granule_id="{{ task_instance.xcom_pull(task_ids='copy_cmd_"
                + str(index)
                + "', key='args')['granule_id'] }}",
                s3_prefix=S3_PREFIX,
            ),
            get_logs=True,
            resources={
                "request_cpu": "1000m",
                "request_memory": "12Gi",
            },
            volumes=[ancillary_volume],
            volume_mounts=[ancillary_volume_mount],
            retries=2,
            execution_timeout=timedelta(minutes=180),
            do_xcom_push=True,
            is_delete_operator_pod=True,
        )

        # this is meant to mark the success failure of the whole DAG
        END = PythonOperator(
            task_id=f"dag_result_{index}",
            python_callable=dag_result,
            retries=0,
            op_kwargs={"index": index},
            provide_context=True,
            trigger_rule=TriggerRule.ALL_FAILED,
        )

        SNS = PythonOperator(
            task_id=f"sns_broadcast_{index}",
            python_callable=sns_broadcast,
            op_kwargs={"index": index},
            provide_context=True,
        )

        SENSOR >> CMD >> COPY >> RUN >> SNS >> END
