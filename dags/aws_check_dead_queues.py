"""
Check whether our SQS dead-letter queues are empty.

If they're not, send email notifications that there have been processing failures.

Todo: create specific creds.
"""
import logging
from collections import namedtuple
from datetime import datetime
from textwrap import dedent

from airflow import DAG, AirflowException
from airflow.providers.amazon.aws.hooks.sqs import SQSHook
from airflow.operators.python_operator import PythonOperator
from infra.connections import AWS_DEAD_LETTER_QUEUE_CHECKER_CONN

default_args = {
    "owner": "Damien Ayers",
    "start_date": datetime(2020, 6, 15),
    "email": ["kieran.ricardo@ga.gov.au", "damien.ayers@ga.gov.au"],
    "email_on_failure": True,
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
    Queue(
        "Collection 3 Landsat Indexing",
        "dea-sandbox-eks-landsat-3-indexing-deadletter",
    ),
    Queue(
        "Collection 3 Landsat Archiving",
        "dea-sandbox-eks-landsat-3-archiving-deadletter",
    ),
]


def check_deadletter_queues(aws_conn):
    """Ensure all releant dead-letter queues are empty or raise an Exception"""
    print(f"Connecting using {aws_conn}")
    sqs_hook = SQSHook(aws_conn)
    sqs = sqs_hook.get_resource_type("sqs")

    bad_queues = []

    for queue in DEAD_QUEUES:
        try:
            sqs_queue = sqs.get_queue_by_name(QueueName=queue.name)
            queue_size = int(sqs_queue.attributes.get("ApproximateNumberOfMessages"))
        except Exception as e:
            logging.info(f"{queue} failed with error: {e}")
            bad_queues.append(queue)
            continue

        if queue_size > 0:
            print(f"{queue.title} queue '{queue.name}' has {queue_size} items on it.")
            bad_queues.append(queue)

    bad_queues_str = "\n".join(f" * {q.name}" for q in bad_queues)
    message = dedent(
        f"""
        Found {len(bad_queues)} dead queues that have messages on them.
        These are the culprits:
        {bad_queues_str}
        """
    )

    if len(bad_queues) > 0:
        raise AirflowException(message)


with DAG(
    dag_id="aws_check_dead_queues",
    catchup=False,
    default_args=default_args,
    schedule_interval="@daily",
    default_view="graph",
    tags=["aws", "landsat_c3"],
    doc_md=__doc__,
) as dag:
    CHECK_QUEUES = PythonOperator(
        task_id="check_queues",
        python_callable=check_deadletter_queues,
        op_kwargs=dict(aws_conn=AWS_DEAD_LETTER_QUEUE_CHECKER_CONN),
    )
