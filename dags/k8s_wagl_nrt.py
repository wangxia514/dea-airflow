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
from airflow.operators.python_operator import PythonOperator, BranchPythonOperator
from airflow.contrib.sensors.aws_sqs_sensor import SQSSensor
from airflow.contrib.hooks.aws_sns_hook import AwsSnsHook
from airflow.contrib.hooks.aws_hook import AwsHook
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
    "retries": 0,
    "retry_delay": timedelta(minutes=5),
    "pool": WAGL_TASK_POOL,
    "secrets": [Secret("env", None, "wagl-nrt-aws-creds")],
}

WAGL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/dev/wagl:patch-20210330-1"
)
S3_TO_RDS_IMAGE = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/geoscienceaustralia/s3-to-rds:0.1.2"

PROCESS_SCENE_QUEUE = "https://sqs.ap-southeast-2.amazonaws.com/060378307146/dea-sandbox-eks-wagl-s2-nrt-process-scene"
DEADLETTER_SCENE_QUEUE = "https://sqs.ap-southeast-2.amazonaws.com/060378307146/dea-sandbox-eks-wagl-s2-nrt-process-scene-deadletter"
PUBLISH_S2_NRT_SNS = (
    "arn:aws:sns:ap-southeast-2:060378307146:dea-sandbox-eks-wagl-s2-nrt"
)

ESTIMATED_COMPLETION_TIME = 3 * 60 * 60

SOURCE_BUCKET = "sentinel-s2-l1c"
TRANSFER_BUCKET = "dea-sandbox-eks-nrt-scene-cache"

BUCKET_REGION = "ap-southeast-2"
S3_PREFIX = "s3://dea-public-data-dev/L2/sentinel-2-nrt/S2MSIARD/"

AWS_CONN_ID = "wagl_nrt_manual"

NUM_PARALLEL_PIPELINE = 5
MAX_ACTIVE_RUNS = 15

# this should be 10 in dev for 10% capacity
# then it would just discard the other 9 messages polled
NUM_MESSAGES_TO_POLL = 1

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
    """ Decode stringified message. """
    return json.loads(message["Body"])


def copy_cmd_tile(tile_info):
    """ The bash scipt to run to copy the tile over to the cache bucket. """
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
        aws s3 cp \\
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
        aws s3 cp \\
                /transfer/{granule_id}/{path}/.done s3://{TRANSFER_BUCKET}/{path}/.done
    else
        echo s3://{TRANSFER_BUCKET}/{path} already exists
    fi

    rm -rf /transfer/{granule_id}
    """

    return cmd


def get_tile_info(msg_dict):
    """ Minimal info to be able to run wagl. """
    assert len(msg_dict["tiles"]) == 1, "was not expecting multi-tile granule"
    tile = msg_dict["tiles"][0]

    return dict(
        granule_id=msg_dict["id"],
        path=tile["path"],
        datastrip=tile["datastrip"]["path"],
    )


def tile_args(tile_info):
    """ Arguments to the wagl container. """
    path = tile_info["path"]
    datastrip = tile_info["datastrip"]

    return dict(
        granule_id=tile_info["granule_id"],
        granule_url=f"s3://{TRANSFER_BUCKET}/{path}",
        datastrip_url=f"s3://{TRANSFER_BUCKET}/{datastrip}",
    )


def get_sqs():
    """ SQS client. """
    return AwsHook(aws_conn_id=AWS_CONN_ID).get_session().client("sqs")


def get_message(sqs, url):
    """ Receive one message with an estimated completion time set. """
    response = sqs.receive_message(
        QueueUrl=url, VisibilityTimeout=ESTIMATED_COMPLETION_TIME, MaxNumberOfMessages=1
    )

    print("response")
    print(response)

    if "Messages" not in response:
        return None

    messages = response["Messages"]

    if len(messages) == 0:
        return None
    else:
        return messages[0]


def receive_task(**context):
    """ Receive a task from the task queue. """
    task_instance = context["task_instance"]
    index = context["index"]

    sqs = get_sqs()
    message = get_message(sqs, PROCESS_SCENE_QUEUE)

    if message is None:
        print("no messages")
        return f"nothing_to_do_{index}"
    else:
        print("received message")
        print(message)

        task_instance.xcom_push(key="message", value=message)

        msg_dict = decode(message)
        tile_info = get_tile_info(msg_dict)

        task_instance.xcom_push(key="cmd", value=copy_cmd_tile(tile_info))
        task_instance.xcom_push(key="args", value=tile_args(tile_info))

        return f"dea-s2-wagl-nrt-copy-scene-{index}"


def finish_up(**context):
    """ Delete the SQS message to mark completion, broadcast to SNS. """
    task_instance = context["task_instance"]
    index = context["index"]

    message = task_instance.xcom_pull(task_ids=f"receive_task_{index}", key="message")
    sqs = get_sqs()

    print("deleting", message["ReceiptHandle"])
    sqs.delete_message(
        QueueUrl=PROCESS_SCENE_QUEUE, ReceiptHandle=message["ReceiptHandle"]
    )

    msg = task_instance.xcom_pull(
        task_ids=f"dea-s2-wagl-nrt-{index}", key="return_value"
    )

    assert "dataset" in msg
    if msg["dataset"] == "exists":
        print("dataset already existed, did not get processed by this DAG")
        return

    msg_str = json.dumps(msg)

    print(f"publishing to SNS: {msg_str}")
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
    schedule_interval=timedelta(minutes=5),
    tags=["k8s", "dea", "psc", "wagl", "nrt"],
)

with pipeline:
    for index in range(NUM_PARALLEL_PIPELINE):
        SENSOR = BranchPythonOperator(
            task_id=f"receive_task_{index}",
            python_callable=receive_task,
            op_kwargs={"index": index},
            provide_context=True,
        )

        COPY = KubernetesPodOperator(
            namespace="processing",
            name="dea-s2-wagl-nrt-copy-scene",
            task_id=f"dea-s2-wagl-nrt-copy-scene-{index}",
            image_pull_policy="IfNotPresent",
            image=S3_TO_RDS_IMAGE,
            affinity=affinity,
            tolerations=tolerations,
            startup_timeout_seconds=600,
            volumes=[ancillary_volume],
            volume_mounts=[ancillary_volume_mount],
            cmds=[
                "bash",
                "-c",
                "{{ task_instance.xcom_pull(task_ids='receive_task_"
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
            startup_timeout_seconds=600,
            # this is the wagl_nrt user in the wagl container
            security_context=dict(runAsUser=10015, runAsGroup=10015, fsGroup=10015),
            cmds=["/scripts/process-scene.sh"],
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
                datastrip_url="{{ task_instance.xcom_pull(task_ids='receive_task_"
                + str(index)
                + "', key='args')['datastrip_url'] }}",
                granule_url="{{ task_instance.xcom_pull(task_ids='receive_task_"
                + str(index)
                + "', key='args')['granule_url'] }}",
                granule_id="{{ task_instance.xcom_pull(task_ids='receive_task_"
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
            execution_timeout=timedelta(minutes=180),
            do_xcom_push=True,
            is_delete_operator_pod=True,
        )

        FINISH = PythonOperator(
            task_id=f"finish_{index}",
            python_callable=finish_up,
            op_kwargs={"index": index},
            provide_context=True,
        )

        NOTHING = DummyOperator(task_id=f"nothing_to_do_{index}")

        SENSOR >> COPY >> RUN >> FINISH
        SENSOR >> NOTHING
