"""
# SQS queues required for dags
Audit check:
    date: 21/04/2021
"""
from airflow.models import Variable

# AWS SQS
SQS_QUEUE_NAME = Variable.get("sqs_queue_name", "dea-dev-eks-ows-dag") #qa
