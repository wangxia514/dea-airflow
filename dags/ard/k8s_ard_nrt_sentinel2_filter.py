"""
Keep only Australian scenes for the Sentinel-2 NRT pipeline.
"""
from datetime import datetime, timedelta
import json
import csv
from pathlib import Path

from airflow import DAG
from airflow import configuration

from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import BranchPythonOperator, PythonOperator
from airflow.providers.amazon.aws.hooks.sqs import SQSHook
from airflow.providers.amazon.aws.hooks.sns import AwsSnsHook
from airflow.kubernetes.secret import Secret
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
    KubernetesPodOperator,
)

from infra.pools import WAGL_TASK_POOL
from infra.s3_buckets import S2_NRT_SOURCE_BUCKET, S2_NRT_TRANSFER_BUCKET
from infra.connections import AWS_WAGL_NRT_CONN
from infra.sqs_queues import ARD_NRT_S2_FILTER_SCENE_QUEUE
from infra.sns_notifications import PUBLISH_S2_NRT_FILTER_SNS
from infra.images import S3_TO_RDS_IMAGE
from infra.variables import S2_NRT_AWS_CREDS

AWS_CONN_ID = AWS_WAGL_NRT_CONN

ESTIMATED_COMPLETION_TIME = 30 * 60

NUM_PARALLEL_PIPELINE = 100

TILE_LIST = "assets/S2_aoi.csv"


default_args = {
    "owner": "Imam Alam",
    "depends_on_past": False,
    "start_date": datetime(2020, 9, 29),
    "email": ["imam.alam@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
    "pool": WAGL_TASK_POOL,
    "secrets": [
        Secret("env", None, S2_NRT_AWS_CREDS),
    ],
}

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


def get_sqs():
    """SQS client."""
    return SQSHook(aws_conn_id=AWS_WAGL_NRT_CONN).get_conn()


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


def australian_region_codes():
    """Set of region codes (MGRS tile IDs) we want to process."""
    root = Path(configuration.get("core", "dags_folder")).parent

    with open(root / TILE_LIST) as fl:
        reader = csv.reader(fl)
        return {x[0] for x in reader}


def decode(message):
    """De-stringify message JSON."""
    body_dict = json.loads(message["Body"])
    msg_dict = json.loads(body_dict["Message"])
    return msg_dict


def region_code(message):
    """Extract region code out of metadata."""
    msg_dict = decode(message)
    tiles = msg_dict["tiles"]

    result = {
        str(tile["utmZone"]) + tile["latitudeBand"] + tile["gridSquare"]
        for tile in tiles
    }
    assert len(result) == 1

    return list(result)[0]


def get_tile_info(msg_dict):
    """Minimal info to be able to run wagl."""
    assert len(msg_dict["tiles"]) == 1, "was not expecting multi-tile granule"
    tile = msg_dict["tiles"][0]

    return dict(
        granule_id=msg_dict["id"],
        path=tile["path"],
        datastrip=tile["datastrip"]["path"],
    )


def copy_cmd_tile(tile_info):
    """The bash scipt to run to copy the tile over to the cache bucket."""
    datastrip = tile_info["datastrip"]
    path = tile_info["path"]
    granule_id = tile_info["granule_id"]

    cmd = f"""
    set -e

    if ! aws s3api head-object --bucket {S2_NRT_TRANSFER_BUCKET} --key {datastrip}/.done 2> /dev/null; then
        mkdir -p /transfer/{granule_id}
        echo sinergise -> disk [datastrip]
        aws s3 sync --only-show-errors --request-payer requester \\
                s3://{S2_NRT_SOURCE_BUCKET}/{datastrip} /transfer/{granule_id}/{datastrip}
        echo disk -> cache [datastrip]
        aws s3 sync --only-show-errors \\
                /transfer/{granule_id}/{datastrip} s3://{S2_NRT_TRANSFER_BUCKET}/{datastrip}
        touch /transfer/{granule_id}/{datastrip}/.done
        aws s3 cp \\
                /transfer/{granule_id}/{datastrip}/.done s3://{S2_NRT_TRANSFER_BUCKET}/{datastrip}/.done
    else
        echo s3://{S2_NRT_TRANSFER_BUCKET}/{datastrip} already exists
    fi

    if ! aws s3api head-object --bucket {S2_NRT_TRANSFER_BUCKET} --key {path}/.done 2> /dev/null; then
        mkdir -p /transfer/{granule_id}
        echo sinergise -> disk [path]
        aws s3 sync --only-show-errors --request-payer requester \\
                s3://{S2_NRT_SOURCE_BUCKET}/{path} /transfer/{granule_id}/{path}
        echo disk -> cache [path]
        aws s3 sync --only-show-errors \\
                /transfer/{granule_id}/{path} s3://{S2_NRT_TRANSFER_BUCKET}/{path}
        touch /transfer/{granule_id}/{path}/.done
        aws s3 cp \\
                /transfer/{granule_id}/{path}/.done s3://{S2_NRT_TRANSFER_BUCKET}/{path}/.done
    else
        echo s3://{S2_NRT_TRANSFER_BUCKET}/{path} already exists
    fi

    rm -rf /transfer/{granule_id}
    """

    return cmd


def filter_scenes(**context):
    """Only select scenes that cover Australia."""
    task_instance = context["task_instance"]
    index = context["index"]

    sqs = get_sqs()
    message = get_message(sqs, ARD_NRT_S2_FILTER_SCENE_QUEUE)

    if message is None:
        return f"nothing_to_do_{index}"

    if region_code(message) not in australian_region_codes():
        sqs.delete_message(
            QueueUrl=ARD_NRT_S2_FILTER_SCENE_QUEUE,
            ReceiptHandle=message["ReceiptHandle"],
        )
        return f"nothing_to_do_{index}"

    msg_dict = decode(message)
    tile_info = get_tile_info(msg_dict)
    cmd = copy_cmd_tile(tile_info)
    task_instance.xcom_push(key="message", value=message)
    task_instance.xcom_push(key="cmd", value=cmd)
    return f"dea-ard-nrt-sentinel2-copy-scene-{index}"


def finish_up(**context):
    """Delete the SQS message to mark completion, broadcast to SNS."""
    task_instance = context["task_instance"]
    index = context["index"]

    message = task_instance.xcom_pull(task_ids=f"filter_scenes_{index}", key="message")

    sqs = get_sqs()
    sqs.delete_message(
        QueueUrl=ARD_NRT_S2_FILTER_SCENE_QUEUE, ReceiptHandle=message["ReceiptHandle"]
    )

    msg_dict = decode(message)
    msg_str = json.dumps(msg_dict)
    sns_hook = AwsSnsHook(aws_conn_id=AWS_WAGL_NRT_CONN)
    sns_hook.publish_to_target(PUBLISH_S2_NRT_FILTER_SNS, msg_dict)


pipeline = DAG(
    "k8s_ard_nrt_sentinel2_filter",
    doc_md=__doc__,
    default_args=default_args,
    description="DEA Sentinel-2 ARD NRT Sentinel-2 scene filter",
    concurrency=NUM_PARALLEL_PIPELINE,
    max_active_runs=1,
    catchup=False,
    params={},
    schedule_interval=timedelta(minutes=3),
    tags=["k8s", "dea", "psc", "ard", "wagl", "nrt", "sentinel-2"],
)


with pipeline:
    for index in range(NUM_PARALLEL_PIPELINE):
        FILTER = BranchPythonOperator(
            task_id=f"filter_scenes_{index}",
            python_callable=filter_scenes,
            op_kwargs={"index": index},
            provide_context=True,
        )

        COPY = KubernetesPodOperator(
            namespace="processing",
            name="dea-ard-nrt-sentinel2-copy-scene",
            task_id=f"dea-ard-nrt-sentinel2-copy-scene-{index}",
            image_pull_policy="IfNotPresent",
            image=S3_TO_RDS_IMAGE,
            affinity=affinity,
            tolerations=tolerations,
            startup_timeout_seconds=600,
            cmds=[
                "bash",
                "-c",
                "{{ task_instance.xcom_pull(task_ids='filter_scenes_"
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

        FINISH = PythonOperator(
            task_id=f"finish_{index}",
            python_callable=finish_up,
            op_kwargs={"index": index},
            provide_context=True,
        )

        NOTHING = DummyOperator(task_id=f"nothing_to_do_{index}")

        FILTER >> NOTHING
        FILTER >> COPY >> FINISH
