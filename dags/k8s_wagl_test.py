"""
Test DAG please ignore
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
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


def my_callable(**context):
    sqs = get_sqs()
    print(type(sqs))
    print(sqs)
    message = get_message(sqs, PROCESS_SCENE_QUEUE)
    print(message)


with dag:
    TASK = PythonOperator(
        task_id="the_task", python_callable=my_callable, provide_context=True
    )
