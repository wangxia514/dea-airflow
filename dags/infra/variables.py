"""
# Environment shared variables read from airflow variable config, provided by infrastracture
# https://airflow.apache.org/docs/stable/concepts.html?highlight=variable#storing-variables-in-environment-variables
# Variables set using Environment Variables would not appear in the Airflow UI but you will be able to use it in your DAG file
Audit check:
    date: 21/04/2021
"""
from airflow.models import Variable

# secrets name available in processing namespace
INDEXING_USER_SECRET = Variable.get(
    "processing_user_secret", "indexing-aws-creds-sandbox"
)  # qa

# DB Users / Roles
SECRET_EXPLORER_WRITER_NAME = Variable.get(
    "db_explorer_writer_secret", "explorer-writer"
)  # qa
SECRET_OWS_WRITER_NAME = Variable.get("db_ows_writer_secret", "ows-writer")  # qa
SECRET_ODC_WRITER_NAME = Variable.get("db_odc_writer_secret", "odc-writer")  # qa
SECRET_ODC_READER_NAME = Variable.get("db_odc_reader_secret", "odc-reader")  # qa
SECRET_DBA_ADMIN_NAME = Variable.get("db_dba_admin_secret", "dba_admin")  # qa

SECRET_EXPLORER_NCI_ADMIN_NAME = Variable.get(
    "db_explorer_nci_admin_secret", "explorer-nci-admin"
)  # qa
SECRET_EXPLORER_NCI_WRITER_NAME = Variable.get(
    "db_explorer_nci_writer_secret", "explorer-nci-writer"
)  # qa

# DB config
DB_DATABASE = Variable.get("db_database", "odc")  # qa
DB_HOSTNAME = Variable.get("db_hostname", "db-writer")  # qa
DB_READER_HOSTNAME = Variable.get("db_reader_hostname", "db-reader")
DB_PORT = Variable.get("db_port", "5432")  # qa

AWS_DEFAULT_REGION = Variable.get("region", "ap-southeast-2")  # qa

# dea-access
DEA_ACCESS_RESTO_API_ADMIN_SECRET = Variable.get(
    "dea_access_resto_api_admin_secret", "dea-access-resto-api-admin"
)  # qa

# c3 alchemist deriveritves
ALCHEMIST_C3_USER_SECRET = Variable.get(
    "alchemist_c3_user_secret", "alchemist-c3-user-creds"
)

LANDSAT_C3_AWS_USER_SECRET = Variable.get(
    "landsat_c3_aws_user_secret", "processing-landsat-3-aws-creds"
)

SENTINEL_2_ARD_INDEXING_AWS_USER_SECRET = Variable.get(
    "sentinel_2_ard_indexing_aws_user_secret", "sentinel-2-ard-indexing-creds"
)

S2_NRT_AWS_CREDS = "wagl-nrt-aws-creds"

COP_API_REP_CREDS = "copernicus_api_creds"

WATERBODIES_DEV_USER_SECRET = Variable.get(
    'waterbodies_dev_user_secret', 'waterbodies-dev-user-creds'
)
