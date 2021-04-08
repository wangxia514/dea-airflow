"""
# SQS queues required for dags
"""
from airflow.models import Variable

# AWS SQS
SQS_QUEUE_NAME = Variable.get("sqs_queue_name", "dea-dev-eks-ows-dag")
