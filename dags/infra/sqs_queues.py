"""
#
# sqs_queues supplied by terraform
#
"""
from airflow.models import Variable

# AWS SQS
NEWDEADATA_SQS_QUEUE_NAME = Variable.get(
    "newdeadata_sqs_queue_name_odc_db", "dea-sandbox-eks-ows-dag"
)
C3_ARCHIVAL_SQS_QUEUE_NAME = Variable.get(
    "landsat_c3_archival_sqs_queue_name_odc_db",
    "dea-sandbox-eks-landsat-3-archiving-odc-db",
)
C3_INDEXING_SQS_QUEUE_NAME = Variable.get(
    "landsat_c3_indexing_sqs_queue_name_odc_db",
    "dea-sandbox-eks-landsat-3-indexing-odc-db",
)
C3_FC_SQS_QUEUE_NAME = Variable.get(
    "landsat_c3_fc_indexing_sqs_queue_name_odc_db",
    "dea-sandbox-eks-alchemist-fc-indexing-wo-odc-db",
)
C3_WO_SQS_QUEUE_NAME = Variable.get(
    "landsat_c3_wo_indexing_sqs_queue_name_odc_db",
    "dea-sandbox-eks-alchemist-c3-indexing-wo-odc-db",
)
