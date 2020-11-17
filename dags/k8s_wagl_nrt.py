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
    "451924316694.dkr.ecr.ap-southeast-2.amazonaws.com/dev/wagl:patch-20201021-12"
)
S3_TO_RDS_IMAGE = "geoscienceaustralia/s3-to-rds:0.1.1-unstable.36.g1347ee8"

PROCESS_SCENE_QUEUE = "https://sqs.ap-southeast-2.amazonaws.com/451924316694/dea-dev-eks-wagl-s2-nrt-process-scene"
DEADLETTER_SCENE_QUEUE = "https://sqs.ap-southeast-2.amazonaws.com/451924316694/dea-dev-eks-wagl-s2-nrt-process-scene-deadletter"
PUBLISH_S2_NRT_SNS = "arn:aws:sns:ap-southeast-2:451924316694:dea-dev-eks-wagl-s2-nrt"

SOURCE_BUCKET = "sentinel-s2-l1c"
TRANSFER_BUCKET = "dea-dev-nrt-scene-cache"

BUCKET_REGION = "ap-southeast-2"
S3_PREFIX = "s3://dea-public-data-dev/L2/sentinel-2-nrt/S2MSIARD/"

AWS_CONN_ID = "wagl_nrt_manual"

# each DAG instance should process one scene only
# TODO so this should be 1 in production
NUM_MESSAGES_TO_POLL = 10

# TODO then this should be 30
NUM_PARALLEL_PIPELINE = 3

MAX_ACTIVE_RUNS = 10

AWS_CONN_ID = "wagl_nrt_manual"

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
    return "aws s3 sync --only-show-errors " + " ".join(args)


def copy_cmd_tile(tile_info):
    datastrip = tile_info["datastrip"]
    path = tile_info["path"]
    granule_id = tile_info["granule_id"]

    return [
        "echo sinergise -> disk [datastrip]",
        sync(
            "--request-payer requester",
            f"s3://{SOURCE_BUCKET}/{datastrip}",
            f"/ancillary/transfer/{granule_id}/{datastrip}",
        ),
        "echo disk -> cache [datastrip]",
        sync(
            f"/ancillary/transfer/{granule_id}/{datastrip}",
            f"s3://{TRANSFER_BUCKET}/{datastrip}",
        ),
        "echo sinergise -> disk [tile]",
        sync(
            "--request-payer requester",
            f"s3://{SOURCE_BUCKET}/{path}",
            f"/ancillary/transfer/{granule_id}/{path}",
        ),
        "echo disk -> cache [tile]",
        sync(
            f"/ancillary/transfer/{granule_id}/{path}", f"s3://{TRANSFER_BUCKET}/{path}"
        ),
        f"rm -rf /ancillary/transfer/{granule_id}",
    ]


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
    task_instance.xcom_push(key="cmd", value=" &&\n".join(copy_cmd_tile(tile_info)))
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

    msg_str = json.dumps(msg)

    sns_hook = AwsSnsHook(aws_conn_id=AWS_CONN_ID)
    sns_hook.publish_to_target(PUBLISH_S2_NRT_SNS, msg_str)


# this is a hack
# as of airflow 1.10.11, setting resources key seems to have a bug
# https://github.com/apache/airflow/issues/9827
# it adds superfluous keys to the specs with nulls as values and k8s does not like that
# it probably was fixed here: https://github.com/apache/airflow/pull/10084
# once we upgrade airflow, this hack will not be need anymore
class PatchedResources(Resources):
    def to_k8s_client_obj(self):
        result = dict(requests={}, limits={})

        if self.request_memory is not None:
            result["requests"]["memory"] = self.request_memory
        if self.request_cpu is not None:
            result["requests"]["cpu"] = self.request_cpu

        if self.limit_memory is not None:
            result["limits"]["memory"] = self.limit_memory
        if self.limit_cpu is not None:
            result["limits"]["cpu"] = self.limit_cpu

        return k8s.V1ResourceRequirements(**result)


# so we patch the operator with the fixed version of `Resources`
def _set_resources(self, resources):
    if not resources:
        return []
    return [PatchedResources(**resources)]


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

        # # apply monkey patch to fix `Resources`
        # _set_resources_backup = KubernetesPodOperator._set_resources
        # KubernetesPodOperator._set_resources = _set_resources

        copyResource = {
            "request_cpu": "100m",
            "request_memory": "2Gi",
        }
        COPY = KubernetesPodOperator(
            namespace="processing",
            name="dea-s2-wagl-nrt-copy-scene",
            task_id=f"dea-s2-wagl-nrt-copy-scene-{index}",
            image_pull_policy="IfNotPresent",
            image=S3_TO_RDS_IMAGE,
            affinity=affinity,
            startup_timeout_seconds=300,
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
            resources=copyResource,
            get_logs=True,
            is_delete_operator_pod=True,
        )

        runResource = {
            request_cpu="100m",
            request_memory="6Gi",
        }
        RUN = KubernetesPodOperator(
            namespace="processing",
            name="dea-s2-wagl-nrt",
            task_id=f"dea-s2-wagl-nrt-{index}",
            image_pull_policy="IfNotPresent",
            image=WAGL_IMAGE,
            affinity=affinity,
            startup_timeout_seconds=300,
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
            resources=runResource,
            volumes=[ancillary_volume],
            volume_mounts=[ancillary_volume_mount],
            retries=2,
            execution_timeout=timedelta(minutes=150),
            do_xcom_push=True,
            is_delete_operator_pod=True,
        )

        # unapply monkey patch
        # KubernetesPodOperator._set_resources = _set_resources_backup

        # this is meant to mark the success failure of the whole DAG
        END = PythonOperator(
            task_id=f"dag_result_{index}",
            python_callable=dag_result,
            retries=0,
            op_kwargs={"index": index},
            provide_context=True,
            trigger_rule=TriggerRule.ALL_FAILED,
        )

        # TODO this should send out the SNS notification
        SNS = PythonOperator(
            task_id=f"sns_broadcast_{index}",
            python_callable=sns_broadcast,
            op_kwargs={"index": index},
            provide_context=True,
        )

        SENSOR >> CMD >> COPY >> RUN >> SNS >> END
