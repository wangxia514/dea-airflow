"""
Test DAG please ignore
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator, BranchPythonOperator

from airflow.contrib.hooks.aws_hook import AwsHook

PROCESS_SCENE_QUEUE = "https://sqs.ap-southeast-2.amazonaws.com/451924316694/dea-dev-eks-wagl-s2-nrt-process-scene"
DEADLETTER_SCENE_QUEUE = "https://sqs.ap-southeast-2.amazonaws.com/451924316694/dea-dev-eks-wagl-s2-nrt-process-scene-deadletter"

AWS_CONN_ID = "wagl_nrt_manual"

ESTIMATED_COMPLETION_TIME = 60


default_args = {
    "owner": "Imam Alam",
    "depends_on_past": False,
    "start_date": datetime(2021, 3, 3),
    "email": ["imam.alam@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 0,
}


dag = DAG(
    "k8s_wagl_test",
    doc_md=__doc__,
    default_args=default_args,
    description="test dag please ignore",
    catchup=False,
    params={},
    concurrency=1,
    max_active_runs=1,
    schedule_interval=None,
    tags=["k8s", "dea", "psc", "dev", "wagl"],
)


def get_sqs():
    return AwsHook(aws_conn_id=AWS_CONN_ID).get_session().client("sqs")


def get_message(sqs, url):
    response = sqs.receive_message(
        QueueUrl=url, VisibilityTimeout=ESTIMATED_COMPLETION_TIME, MaxNumberOfMessages=1
    )

    messages = response["Messages"]
    print(messages)

    if len(messages) == 0:
        return None
    else:
        return messages[0]


def receive_task(**context):
    sqs = get_sqs()
    message = get_message(sqs, PROCESS_SCENE_QUEUE)

    if message is None:
        print("no messages")
        return "dont_it"
    else:
        print("received message")
        print(message)

        task_instance = context["task_instance"]
        task_instance.xcom_push(
            key="message_desc",
            value={
                "Id": message["MessageId"],
                "ReceiptHandle": message["ReceiptHandle"],
            },
        )
        return "do_it"


def do_it(**context):
    task_instance = context["task_instance"]
    message_desc = task_instance.xcom_pull(task_ids="receive_task", key="message_desc")
    print("deleting", message_desc)

    sqs = get_sqs()
    sqs.delete_messages(Entries=[message_desc])


with dag:
    BRANCH = BranchPythonOperator(
        task_id="branch", python_callable=receive_task, provide_context=True
    )

    DONT_IT = DummyOperator(task_id="dont_it")

    DO_IT = PythonOperator(
        task_id="do_it", python_callable="do_it", provide_context=True
    )

    BRANCH >> DO_IT
