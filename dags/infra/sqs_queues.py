"""
#
# sqs_queues supplied by terraform
Audit check:
    date: 21/04/2021
"""
from airflow.models import Variable

# AWS SQS
NEWDEADATA_SQS_QUEUE_NAME = Variable.get(
    "newdeadata_sqs_queue_name_odc_db", "dea-sandbox-eks-ows-dag"
)  # qa
C3_ARCHIVAL_SQS_QUEUE_NAME = Variable.get(
    "landsat_c3_archival_sqs_queue_name_odc_db",
    "dea-sandbox-eks-landsat-3-archiving-odc-db",
)  # qa
C3_INDEXING_SQS_QUEUE_NAME = Variable.get(
    "landsat_c3_indexing_sqs_queue_name_odc_db",
    "dea-sandbox-eks-landsat-3-indexing-odc-db",
)  # qa
C3_FC_SQS_QUEUE_NAME = Variable.get(
    "landsat_c3_fc_indexing_sqs_queue_name_odc_db",
    "dea-sandbox-eks-alchemist-fc-indexing-wo-odc-db",
)  # qa
C3_WO_SQS_QUEUE_NAME = Variable.get(
    "landsat_c3_wo_indexing_sqs_queue_name_odc_db",
    "dea-sandbox-eks-alchemist-c3-indexing-wo-odc-db",
)  # qa
SENTINEL_2_ARD_INDEXING_SQS_QUEUE_NAME_SANDBOX_DB = Variable.get(
    "sentinel_2_ard_indexing_sqs_queue_name_sandbox_db",
    "dea-sandbox-eks-sentinel-2-ard-indexing-sandbox-db",
)  # qa
SENTINEL_2_ARD_INDEXING_SQS_QUEUE_NAME_ODC_DB = Variable.get(
    "sentinel_2_ard_indexing_sqs_queue_name_odc_db",
    "dea-sandbox-eks-sentinel-2-ard-indexing-odc-db",
)  # qa
ARD_NRT_LS_PROCESS_SCENE_QUEUE = (
    "arn:aws:sqs:ap-southeast-2:060378307146:dea-sandbox-eks-wagl-ls-nrt-process-scene"
)
ARD_NRT_S2_PROVISIONAL_PROCESS_SCENE_QUEUE = "https://sqs.ap-southeast-2.amazonaws.com/060378307146/dea-sandbox-eks-ard-nrt-s2-provisional-process-scene"
