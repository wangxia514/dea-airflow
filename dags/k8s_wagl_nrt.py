"""
Run WAGL NRT pipeline in Airflow.
"""
from datetime import datetime, timedelta
import csv
from pathlib import Path
import json
import random

from airflow import DAG
from airflow import configuration

from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.contrib.sensors.aws_sqs_sensor import SQSSensor
from airflow.kubernetes.secret import Secret

default_args = {
    "owner": "Imam Alam",
    "depends_on_past": False,
    "start_date": datetime(2020, 9, 11),
    "email": ["imam.alam@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "secrets": [
        Secret("env", "AIRFLOW_CONN_WAGL_NRT", "wagl-nrt-conn-uri", "connection")
    ],
}

WAGL_IMAGE = "451924316694.dkr.ecr.ap-southeast-2.amazonaws.com/dev/wagl:rc-20190109-5"

TILE_LIST = "assets/S2_aoi.csv"

COPY_SCENE_QUEUE = "https://sqs.ap-southeast-2.amazonaws.com/451924316694/dea-dev-eks-wagl-s2-nrt-copy-scene"

NUM_WORKERS = 1
NUM_MESSAGES_TO_POLL = 1


def australia_region_codes():
    root = Path(configuration.get("core", "dags_folder")).parent

    with open(root / TILE_LIST) as fl:
        reader = csv.reader(fl)
        return {x[0] for x in reader}


def region_code(message):
    body_dict = json.loads(message["Body"])
    msg_dict = json.loads(body_dict["Message"])
    tiles = msg_dict["tiles"]
    assert len(tiles) >= 0
    tile = tiles[0]
    return str(tile["utmZone"]) + tile["latitudeBand"] + tile["gridSquare"]


def filter_scenes(**context):
    task_instance = context["task_instance"]
    all_messages = task_instance.xcom_pull(
        task_ids="copy_scene_queue_sensor", key="messages"
    )["Messages"]

    # australia = australia_region_codes()

    messages = [message for message in all_messages]
    #             in region_code(message) in australia]

    task_instance.xcom_push(key="messages", value=messages)


def copy_scenes(**context):
    task_instance = context["task_instance"]
    index = context["index"]
    all_messages = task_instance.xcom_pull(task_ids="filter_scene", key="messages")

    messages = all_messages[index::NUM_WORKERS]
    for message in messages:
        print("imagine I am now copying this")
        print(message)


pipeline = DAG(
    "k8s_wagl_nrt",
    doc_md=__doc__,
    default_args=default_args,
    description="DEA Sentinel-2 NRT Processing",
    concurrency=2,
    max_active_runs=1,
    catchup=False,
    params={},
    schedule_interval=None,
    tags=["k8s", "dea", "psc", "wagl", "nrt"],
)

with pipeline:
    START = DummyOperator(task_id="start_wagl")

    SENSOR = SQSSensor(
        task_id="copy_scene_queue_sensor",
        sqs_queue=COPY_SCENE_QUEUE,
        aws_conn_id="wagl_nrt_manual",
        max_messages=NUM_MESSAGES_TO_POLL,
    )

    FILTER = PythonOperator(
        task_id="filter_scenes", python_callable=filter_scenes, provide_context=True
    )

    WAGL_RUN = KubernetesPodOperator(
        namespace="processing",
        name="dea-s2-wagl-nrt",
        task_id="dea-s2-wagl-nrt",
        image_pull_policy="IfNotPresent",
        image=WAGL_IMAGE,
        is_delete_operator_pod=True,
        arguments=["--version"],
        labels={"runner": "airflow"},
        get_logs=True,
    )

    END = DummyOperator(task_id="end_wagl")

    START >> SENSOR >> FILTER

    for i in range(NUM_WORKERS):
        COPY = PythonOperator(
            task_id=f"copy_scenes_{i}",
            op_kwargs={"index": i},
            python_callable=copy_scenes,
            execution_timeout=timedelta(hours=20),
            provide_context=True,
        )

        FILTER >> COPY >> END
