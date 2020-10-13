"""
# Environment shared variables read from airflow variable config, provided by infrastracture
# https://airflow.apache.org/docs/stable/concepts.html?highlight=variable#storing-variables-in-environment-variables
# Variables set using Environment Variables would not appear in the Airflow UI but you will be able to use it in your DAG file
"""
from airflow.models import Variable

# role config
INDEXING_ROLE = Variable.get("processing_indexing_role", "dea-dev-eks-orchestration")

# secrets name available in processing namespace
SECRET_AWS_NAME = Variable.get("processing_user_secret", "indexing-aws-creds-sandbox")
SECRET_EXPLORER_WRITER_NAME = Variable.get(
    "db_explorer_writer_secret", "explorer-writer"
)
SECRET_OWS_WRITER_NAME = Variable.get("db_ows_writer_secret", "ows-writer")
SECRET_ODC_WRITER_NAME = Variable.get("db_odc_writer_secret", "odc-writer")

# DB config
DB_DATABASE = Variable.get("db_database", "ows")
DB_HOSTNAME = Variable.get("db_hostname", "db-writer")

# AWS SQS
SQS_QUEUE_NAME = Variable.get("sqs_queue_name", "dea-sandbox-eks-ows-dag")
