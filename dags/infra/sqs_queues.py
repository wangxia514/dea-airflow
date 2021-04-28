"""
# SQS queues required for dags
Audit check:
    date: 21/04/2021
"""
from airflow.models import Variable

# AWS SQS
SQS_QUEUE_NAME = Variable.get("sqs_queue_name", "dea-dev-eks-ows-dag") #qa
SENTINEL_2_ARD_INDEXING_SQS_QUEUE_NAME_ODC_DB = Variable.get(
    "sentinel_2_ard_indexing_sqs_queue_name_odc_db",
    "dea-dev-eks-sentinel-2-ard-indexing-odc-db",
) #qa