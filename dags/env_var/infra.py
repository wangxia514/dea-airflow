"""
# Environment shared variables read from airflow variable config, provided by infrastracture
# https://airflow.apache.org/docs/stable/concepts.html?highlight=variable#storing-variables-in-environment-variables
# Variables set using Environment Variables would not appear in the Airflow UI but you will be able to use it in your DAG file
"""
from airflow.models import Variable

# role config
INDEXING_ROLE = Variable.get("indexing_role", "dea-dev-eks-orchestration")

# secrets name available in processing namespace
SECRET_AWS_NAME = Variable.get("secret_aws_name", "processing-aws-creds-dev")
SECRET_EXPLORER_NAME = Variable.get("secret_explorer_name", "explorer-db")
SECRET_OWS_NAME = Variable.get("secret_ows_name", "ows-db")

# DB config
DB_DATABASE = Variable.get("db_database", "ows")
DB_HOSTNAME = Variable.get("db_hostname", "db-writer")
