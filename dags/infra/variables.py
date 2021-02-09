"""
# Environment shared variables read from airflow variable config, provided by infrastracture
# https://airflow.apache.org/docs/stable/concepts.html?highlight=variable#storing-variables-in-environment-variables
# Variables set using Environment Variables would not appear in the Airflow UI but you will be able to use it in your DAG file
"""
from airflow.models import Variable

# role config
INDEXING_ROLE = Variable.get("processing_indexing_role", "dea-dev-eks-orchestration")
DB_DUMP_S3_ROLE = Variable.get("db_dump_s3_role", "dea-dev-eks-db-dump-to-s3")

C3_PROCESSING_ROLE = Variable.get(
    "processing_user_secret", "processing-aws-creds-sandbox"
)
C3_ALCHEMIST_ROLE = Variable.get(
    "alchemist_c3_indexing_user_secret", "alchemist-c3-user-creds"
)

# secrets name available in processing namespace
SECRET_AWS_NAME = Variable.get("processing_user_secret", "indexing-aws-creds-sandbox")
SECRET_EXPLORER_WRITER_NAME = Variable.get(
    "db_explorer_writer_secret", "explorer-writer"
)
SECRET_OWS_WRITER_NAME = Variable.get("db_ows_writer_secret", "ows-writer")
SECRET_ODC_WRITER_NAME = Variable.get("db_odc_writer_secret", "odc-writer")
SECRET_DBA_ADMIN_NAME = Variable.get("db_dba_admin_secret", "dba-admin")

# S3 buckets
DB_DUMP_S3_BUCKET = Variable.get("db_dump_s3_bucketname", "dea-dev-odc-db-dump")

# DB config
DB_DATABASE = Variable.get("db_database", "odc")
DB_HOSTNAME = Variable.get("db_hostname", "db-writer")

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
