"""
Run wagl NRT pipeline in Airflow.
"""
from datetime import datetime, timedelta
import random
from urllib.parse import urlencode, quote_plus
import json

from airflow import DAG

from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.contrib.sensors.aws_sqs_sensor import SQSSensor
from airflow.kubernetes.secret import Secret
from airflow.kubernetes.volume import Volume
from airflow.kubernetes.volume_mount import VolumeMount
from airflow.hooks.S3_hook import S3Hook

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

WAGL_IMAGE = "451924316694.dkr.ecr.ap-southeast-2.amazonaws.com/dev/wagl:rc-20190109-5"
S3_TO_RDS_IMAGE = "geoscienceaustralia/s3-to-rds:0.1.1-unstable.26.g5ffb384"

PROCESS_SCENE_QUEUE = "https://sqs.ap-southeast-2.amazonaws.com/451924316694/dea-dev-eks-wagl-s2-nrt-process-scene"

SOURCE_BUCKET = "sentinel-s2-l1c"
TRANSFER_BUCKET = "dea-dev-nrt-scene-cache"

# each DAG instance should process one scene only
NUM_MESSAGES_TO_POLL = 1

AWS_CONN_ID = "wagl_nrt_manual"

SYNC_CMD = "aws s3 sync --only-show-errors"

# TODO use this
affinity = {
    "nodeAffinity": {
        "requiredDuringSchedulingIgnoredDuringExecution": {
            "nodeSelectorTerms": [
                {
                    "matchExpressions": [
                        {
                            "key": "nodetype",
                            "operator": "In",
                            "values": [
                                "spot",
                            ],
                        }
                    ]
                }
            ]
        }
    }
}


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
    body_dict = json.loads(message["Body"])
    msg_dict = json.loads(body_dict["Message"])
    return msg_dict


def copy_tile(client, tile, safe_tags):
    datastrips = client.list_objects_v2(
        Bucket=SOURCE_BUCKET,
        Prefix=tile["datastrip"]["path"],
        RequestPayer="requester",
    )

    for obj in datastrips["Contents"]:
        print("copying", obj["Key"], "from", SOURCE_BUCKET, "to", TRANSFER_BUCKET)
        client.copy_object(
            ACL="bucket-owner-full-control",
            CopySource={"Bucket": SOURCE_BUCKET, "Key": obj["Key"]},
            Bucket=TRANSFER_BUCKET,
            TaggingDirective="REPLACE",
            Tagging=safe_tags,
            StorageClass="STANDARD",
            Key=obj["Key"],
            RequestPayer="requester",
        )

    tiles = client.list_objects_v2(
        Bucket=SOURCE_BUCKET, Prefix=tile["path"], RequestPayer="requester"
    )

    for obj in tiles["Contents"]:
        print("copying", obj["key"], "from", SOURCE_BUCKET, "to", TRANSFER_BUCKET)
        client.copy_object(
            ACL="bucket-owner-full-control",
            CopySource={"Bucket": SOURCE_BUCKET, "Key": obj["Key"]},
            Bucket=TRANSFER_BUCKET,
            Key=obj["Key"],
            TaggingDirective="REPLACE",
            Tagging=safe_tags,
            StorageClass="STANDARD",
            RequestPayer="requester",
        )


def copy_scenes(**context):
    task_instance = context["task_instance"]
    index = context["index"]
    all_messages = task_instance.xcom_pull(task_ids="filter_scenes", key="messages")

    s3_hook = S3Hook(aws_conn_id=AWS_CONN_ID)
    client = s3_hook.get_conn()

    print("s3_hook", s3_hook, type(s3_hook))
    print("client", client, type(client))

    # tags to assign to objects
    safe_tags = urlencode({}, quote_via=quote_plus)

    messages = all_messages[index]
    for message in messages:
        msg_dict = decode(message)
        for tile in msg_dict["tiles"]:
            copy_tile(client, tile, safe_tags)

    task_instance.xcom_push(key="messages", value=all_messages)


pipeline = DAG(
    "k8s_wagl_nrt",
    doc_md=__doc__,
    default_args=default_args,
    description="DEA Sentinel-2 NRT processing",
    concurrency=2,
    max_active_runs=1,
    catchup=False,
    params={},
    schedule_interval=None,
    tags=["k8s", "dea", "psc", "wagl", "nrt"],
)

with pipeline:
    START = DummyOperator(task_id="start")

    SENSOR = SQSSensor(
        task_id="process_scene_queue_sensor",
        sqs_queue=PROCESS_SCENE_QUEUE,
        aws_conn_id=AWS_CONN_ID,
        max_messages=NUM_MESSAGES_TO_POLL,
    )

    COPY = PythonOperator(
        task_id=f"copy_scenes",
        python_callable=copy_scenes,
        execution_timeout=timedelta(hours=2),
        provide_context=True,
    )

    WAGL_RUN = KubernetesPodOperator(
        namespace="processing",
        name="dea-s2-wagl-nrt",
        task_id="dea-s2-wagl-nrt",
        image_pull_policy="IfNotPresent",
        image=WAGL_IMAGE,
        # TODO: affinity=affinity,
        arguments=["--version"],
        labels={"runner": "airflow"},
        get_logs=True,
        volumes=[ancillary_volume],
        volume_mounts=[ancillary_volume_mount],
        is_delete_operator_pod=True,
    )

    END = DummyOperator(task_id="end")

    START >> SENSOR >> COPY >> WAGL_RUN >> END
