"""
# SQS queues required for dags
Audit check:
    date: 21/04/2021
"""
from airflow.models import Variable

# AWS SQS
SQS_QUEUE_NAME = Variable.get("sqs_queue_name", default_var="dea-dev-eks-ows-dag")  # qa
SENTINEL_2_ARD_INDEXING_SQS_QUEUE_NAME_ODC_DB = Variable.get(
    "sentinel_2_ard_indexing_sqs_queue_name_odc_db",
    default_var="dea-dev-eks-sentinel-2-ard-indexing-odc-db",
)  # qa


ARD_NRT_S2_PROCESS_SCENE_QUEUE = "https://sqs.ap-southeast-2.amazonaws.com/451924316694/dea-dev-eks-wagl-s2-nrt-process-scene"
ARD_NRT_S2_PROVISIONAL_PROCESS_SCENE_QUEUE = "https://sqs.ap-southeast-2.amazonaws.com/451924316694/dea-dev-eks-ard-nrt-s2-provisional-process-scene"
ARD_NRT_LS_PROCESS_SCENE_QUEUE = "https://sqs.ap-southeast-2.amazonaws.com/451924316694/dea-dev-eks-wagl-ls-nrt-process-scene"

LS_C3_WO_SUMMARY_QUEUE = (
    "https://sqs.ap-southeast-2.amazonaws.com/451924316694/dea-dev-eks-stats-kk"
)
