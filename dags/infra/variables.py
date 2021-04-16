"""
# Environment shared variables read from airflow variable config, provided by infrastracture
# https://airflow.apache.org/docs/stable/concepts.html?highlight=variable#storing-variables-in-environment-variables
# Variables set using Environment Variables would not appear in the Airflow UI but you will be able to use it in your DAG file
"""
from airflow.models import Variable

# secrets name available in processing namespace
SECRET_AWS_NAME = Variable.get("processing_user_secret", "indexing-aws-creds-sandbox")

# DB Users / Roles
SECRET_EXPLORER_WRITER_NAME = Variable.get(
    "db_explorer_writer_secret", "explorer-writer"
)
SECRET_OWS_WRITER_NAME = Variable.get("db_ows_writer_secret", "ows-writer")
SECRET_ODC_WRITER_NAME = Variable.get("db_odc_writer_secret", "odc-writer")
SECRET_DBA_ADMIN_NAME = Variable.get("db_dba_admin_secret", "dba_admin")

SECRET_EXPLORER_NCI_ADMIN_NAME = Variable.get("db_explorer_nci_admin_secret", "explorer-nci-admin")
SECRET_EXPLORER_NCI_WRITER_NAME = Variable.get("db_explorer_nci_admin_secret", "explorer-nci-writer")

# DB config
DB_DATABASE = Variable.get("db_database", "odc")
DB_HOSTNAME = Variable.get("db_hostname", "db-writer")
DB_PORT = Variable.get("db_port", "5432")

AWS_DEFAULT_REGION = Variable.get("region", "ap-southeast-2")

# dea-access
DEA_ACCESS_RESTO_API_ADMIN_SECRET = Variable.get("dea_access_resto_api_admin_secret", "dea-access-resto-api-admin")
