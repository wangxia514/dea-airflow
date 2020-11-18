"""
Check dead queues for entries and alert Alex if any are found.

Todo: create specific creds.
"""
import logging
from collections import namedtuple
from datetime import datetime
from textwrap import dedent

from airflow import DAG, AirflowException
from airflow.contrib.sensors.aws_sqs_sensor import SQSHook
from airflow.operators.python_operator import PythonOperator

default_args = {
    "owner": "Alex Leith",
    "start_date": datetime(2020, 6, 15),
    "email": ["alex.leith@ga.gov.au"],
    "email_on_failure": True,
    "aws_account": "processing-aws-creds-sandbox",
}

Queue = namedtuple("Queue", ["title", "name"])

DEAD_QUEUES = [
    Queue(
        "Collection 3 Water Observations",
        "dea-sandbox-eks-alchemist-c3-processing-wo-deadletter",
    ),
    Queue(
        "Collection 3 Fractional Cover",
        "dea-sandbox-eks-alchemist-c3-processing-fc-deadletter",
    ),
]


def _check_queues(aws_conn):
    sqs_hook = SQSHook(aws_conn_id=default_args["aws_account"])
    sqs = sqs_hook.get_resource_type("sqs")

    bad_queues = []

    for queue in DEAD_QUEUES:
        queue = sqs.get_queue_by_name(QueueName=queue.name)
        queue_size = int(queue.attributes.get("ApproximateNumberOfMessages"))

        if queue_size > 0:
            print(f"{queue.title} queue '{queue.name}' has {queue_size} items on it.")
            bad_queues.append(queue)

    message = dedent(
        f"""
        Found {len(bad_queues)} dead queues that have messages on them.
        These are the culprits:
        {', '.join(q.name for q in DEAD_QUEUES)}
        """
    )

    if len(bad_queues) > 0:
        raise AirflowException(message)


dag = DAG(
    dag_id="aws_check_dead_queues",
    catchup=False,
    default_args=default_args,
    schedule_interval="@daily",
    default_view="tree",
    tags=["aws"],
    doc_md=__doc__,
)

with dag:
    CHECK_QUEUES = PythonOperator(
        task_id="check_queues",
        python_callable=_check_queues,
        op_kwargs=dict(aws_conn="sandbox_aws"),
    )
