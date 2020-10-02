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
S3_TO_RDS_IMAGE = "geoscienceaustralia/s3-to-rds:0.1.1-unstable.36.g1347ee8"

PROCESS_SCENE_QUEUE = "https://sqs.ap-southeast-2.amazonaws.com/451924316694/dea-dev-eks-wagl-s2-nrt-process-scene"

SOURCE_BUCKET = "sentinel-s2-l1c"
TRANSFER_BUCKET = "dea-dev-nrt-scene-cache"

# each DAG instance should process one scene only
# so NUM_WORKERS = NUM_MESSAGES_TO_POLL
# TODO take care of workers with no task with PythonBranchOperator?
NUM_MESSAGES_TO_POLL = 1

AWS_CONN_ID = "wagl_nrt_manual"

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
    return json.loads(message["Body"])


def sync(*args):
    return "aws s3 sync " + " ".join(args)
    # return "aws s3 sync --only-show-errors " + " ".join(args)


def copy_cmd_tile(msg_id, tile):
    datastrip = tile["datastrip"]["path"]
    path = tile["path"]

    return [
        "aws sts get-caller-identity",
        "echo sinergise -> disk [datastrip]",
        sync(
            "--request-payer requester",
            f"s3://{SOURCE_BUCKET}/{datastrip}",
            f"/transfer/{msg_id}/{datastrip}",
        ),
        "echo disk -> cache [datastrip]",
        sync(f"/transfer/{msg_id}/{datastrip}", f"s3://{TRANSFER_BUCKET}/{datastrip}"),
        "echo sinergise -> disk [tile]",
        sync(
            "--request-payer requester",
            f"s3://{SOURCE_BUCKET}/{path}",
            f"/transfer/{msg_id}/{path}",
        ),
        "echo disk -> cache [tile]",
        sync(f"/transfer/{msg_id}/{path}", f"s3://{TRANSFER_BUCKET}/{path}"),
    ]


def copy_cmd(**context):
    task_instance = context["task_instance"]
    # index = context["index"]
    all_messages = task_instance.xcom_pull(
        task_ids="process_scene_queue_sensor", key="messages"
    )["Messages"]

    messages = all_messages  # TODO take care of index
    assert len(messages) == 1
    message = messages[0]
    msg_dict = decode(message)

    cmd = []
    for tile in msg_dict["tiles"]:
        cmd += copy_cmd_tile(msg_dict["id"], tile)

    # forward it to the copy task
    task_instance.xcom_push(key="cmd", value=" &&\n".join(cmd))


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

    CMD = PythonOperator(
        task_id="copy_cmd",
        python_callable=copy_cmd,
        provide_context=True,
    )

    COPY = KubernetesPodOperator(
        namespace="processing",
        name="dea-s2-wagl-nrt-copy-scene",
        task_id="dea-s2-wagl-nrt-copy-scene",
        image_pull_policy="IfNotPresent",
        image=S3_TO_RDS_IMAGE,
        # TODO: affinity=affinity,
        cmds=[
            "bash",
            "-c",
            "{{ task_instance.xcom_pull(task_ids='copy_cmd', key='cmd') }}",
        ],
        labels={"runner": "airflow"},
        get_logs=True,
        is_delete_operator_pod=True,
    )

    # WAGL_RUN = KubernetesPodOperator(
    #     namespace="processing",
    #     name="dea-s2-wagl-nrt",
    #     task_id="dea-s2-wagl-nrt",
    #     image_pull_policy="IfNotPresent",
    #     image=WAGL_IMAGE,
    #     # TODO: affinity=affinity,
    #     arguments=["--version"],
    #     labels={"runner": "airflow"},
    #     get_logs=True,
    #     volumes=[ancillary_volume],
    #     volume_mounts=[ancillary_volume_mount],
    #     is_delete_operator_pod=True,
    # )

    END = DummyOperator(task_id="end")

    # START >> SENSOR >> COPY >> WAGL_RUN >> END
    START >> SENSOR >> CMD >> COPY >> END
