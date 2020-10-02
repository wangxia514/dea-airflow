"""
Keep only Australian scenes for the Sentinel-2 wagl NRT pipeline.
"""
from datetime import datetime, timedelta
import json
import csv
from pathlib import Path

from airflow import DAG
from airflow import configuration

from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.subdag_operator import SubDagOperator
from airflow.contrib.sensors.aws_sqs_sensor import SQSSensor
from airflow.contrib.hooks.aws_sqs_hook import SQSHook


AWS_CONN_ID = "wagl_nrt_manual"

FILTER_SCENE_QUEUE = "https://sqs.ap-southeast-2.amazonaws.com/451924316694/dea-dev-eks-wagl-s2-nrt-filter-scene"
PROCESS_SCENE_QUEUE = "https://sqs.ap-southeast-2.amazonaws.com/451924316694/dea-dev-eks-wagl-s2-nrt-process-scene"

# unfortunately this is the max
NUM_MESSAGES_TO_POLL = 10

TILE_LIST = "assets/S2_aoi.csv"


default_args = {
    "owner": "Imam Alam",
    "depends_on_past": False,
    "start_date": datetime(2020, 9, 29),
    "email": ["imam.alam@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def australian_region_codes():
    root = Path(configuration.get("core", "dags_folder")).parent

    with open(root / TILE_LIST) as fl:
        reader = csv.reader(fl)
        return {x[0] for x in reader}


def decode(message):
    body_dict = json.loads(message["Body"])
    msg_dict = json.loads(body_dict["Message"])
    return msg_dict


def region_code(message):
    msg_dict = decode(message)
    tiles = msg_dict["tiles"]

    result = {
        str(tile["utmZone"]) + tile["latitudeBand"] + tile["gridSquare"]
        for tile in tiles
    }
    assert len(result) == 1

    return list(result)[0]


def filter_scenes(**context):
    task_instance = context["task_instance"]
    index = context["index"]
    all_messages = task_instance.xcom_pull(
        task_ids=f"filter_scene_queue_sensor_{index}", key="messages"
    )["Messages"]

    australia = australian_region_codes()

    messages = [
        message for message in all_messages if region_code(message) in australia
    ]

    sqs_hook = SQSHook(aws_conn_id=AWS_CONN_ID)

    for message in messages:
        message_body = json.dumps(decode(message))
        print("sending message")
        print(message_body)
        sqs_hook.send_message(PROCESS_SCENE_QUEUE, message_body)


def subdag():
    result = DAG(
        dag_id="k8s_wagl_nrt_filter.filter_subdag",
        default_args=default_args,
        schedule_interval=None,
    )

    with result:
        for index in range(50):
            SENSOR = SQSSensor(
                task_id=f"filter_scene_queue_sensor_{index}",
                sqs_queue=FILTER_SCENE_QUEUE,
                aws_conn_id=AWS_CONN_ID,
                max_messages=NUM_MESSAGES_TO_POLL,
            )

            FILTER = PythonOperator(
                task_id=f"filter_scenes_{index}",
                python_callable=filter_scenes,
                op_kwargs={"index": index},
                provide_context=True,
            )

            SENSOR >> FILTER

    return result


pipeline = DAG(
    "k8s_wagl_nrt_filter",
    doc_md=__doc__,
    default_args=default_args,
    description="DEA Sentinel-2 NRT scene filter",
    concurrency=50,
    max_active_runs=1,
    catchup=False,
    params={},
    schedule_interval=timedelta(minutes=15),
    tags=["k8s", "dea", "psc", "wagl", "nrt"],
)


with pipeline:
    START = DummyOperator(task_id="start")

    FILTER_SUBDAG = SubDagOperator(task_id="filter_subdag", subdag=subdag())

    END = DummyOperator(task_id="end")

    START >> FILTER_SUBDAG >> END
