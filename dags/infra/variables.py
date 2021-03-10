"""
# Environment shared variables read from airflow variable config, provided by infrastracture
# https://airflow.apache.org/docs/stable/concepts.html?highlight=variable#storing-variables-in-environment-variables
# Variables set using Environment Variables would not appear in the Airflow UI but you will be able to use it in your DAG file
"""
from airflow.models import Variable

# role config
INDEXING_ROLE = Variable.get("processing_indexing_role", "dea-dev-eks-orchestration")
DB_DUMP_S3_ROLE = Variable.get("db_dump_s3_role", "dea-dev-eks-db-dump-to-s3")

# secrets name available in processing namespace
SECRET_AWS_NAME = Variable.get("processing_user_secret", "indexing-aws-creds-sandbox")

# DB Users / Roles
SECRET_EXPLORER_WRITER_NAME = Variable.get(
    "db_explorer_writer_secret", "explorer-writer"
)
SECRET_OWS_WRITER_NAME = Variable.get("db_ows_writer_secret", "ows-writer")
SECRET_ODC_WRITER_NAME = Variable.get("db_odc_writer_secret", "odc-writer")
SECRET_DBA_ADMIN_NAME = Variable.get("db_dba_admin_secret", "dba_admin")

# S3 buckets
DB_DUMP_S3_BUCKET = Variable.get("db_dump_s3_bucketname", "dea-dev-odc-db-dump")

# DB config
DB_DATABASE = Variable.get("db_database", "ows")
DB_HOSTNAME = Variable.get("db_hostname", "db-writer")

# AWS SQS
SQS_QUEUE_NAME = Variable.get("sqs_queue_name", "dea-dev-eks-ows-dag")

# Task Pools
WAGL_TASK_POOL = Variable.get("wagl_task_pool", "wagl_processing_pool")
DEA_NEWDATA_PROCESSING_POOL = Variable.get(
    "newdata_indexing_pool", "NewDeaData_indexing_pool"
)
C3_INDEXING_POOL = Variable.get("c3_indexing_pool", "c3_indexing_pool")
