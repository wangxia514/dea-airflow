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
SECRET_EXPLORER_NAME = Variable.get("explorer_db_secret", "explorer-db")
SECRET_OWS_NAME = Variable.get("ows_db_secret", "ows-db")

# DB config
DB_DATABASE = Variable.get("db_database", "ows_prod_20200827")
DB_HOSTNAME = Variable.get("db_hostname", "db-writer")