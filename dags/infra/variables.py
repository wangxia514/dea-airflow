"""
# Environment shared variables read from airflow variable config, provided by infrastracture
# https://airflow.apache.org/docs/stable/concepts.html?highlight=variable#storing-variables-in-environment-variables
# Variables set using Environment Variables would not appear in the Airflow UI but you will be able to use it in your DAG file
Audit check:
    date: 21/04/2021
"""
from airflow.models import Variable

# secrets name available in processing namespace
C3_LANDSAT_INDEXING_USER_SECRET = Variable.get(
    "c3_landsat_indexing_user_secret", "processing-aws-creds-c3-landsat"
)  # qa
C3_ALCHEMIST_SECRET = Variable.get(
    "alchemist_c3_indexing_user_secret", "alchemist-c3-user-creds"
)  # qa
C3_BA_ALCHEMIST_SECRET = Variable.get(
    "alchemist_s2_c3_nrt_user_creds", "alchemist-s2-c3-user-creds"
)

SECRET_EXPLORER_WRITER_NAME = Variable.get(
    "db_explorer_writer_secret", "explorer-writer"
)  # qa
SECRET_OWS_WRITER_NAME = Variable.get("db_ows_writer_secret", "ows-writer")  # qa
SECRET_ODC_WRITER_NAME = Variable.get("db_odc_writer_secret", "odc-writer")  # qa
SECRET_ODC_READER_NAME = Variable.get("db_odc_reader_secret", "odc-reader")  # qa
SECRET_DBA_ADMIN_NAME = Variable.get("db_dba_admin_secret", "dba-admin")  # qa

SECRET_ODC_ADMIN_NAME = Variable.get("db_odc_admin_secret", default_var="odc-admin")

SECRET_EXPLORER_ADMIN_NAME = Variable.get(
    "db_explorer_admin_secret", default_var="explorer-admin"
)

SECRET_OWS_ADMIN_NAME = Variable.get("db_ows_admin_secret", default_var="ows-admin")

SECRET_EXPLORER_NCI_ADMIN_NAME = Variable.get(
    "db_explorer_nci_admin_secret", "explorer-nci-admin"
)  # qa
SECRET_EXPLORER_NCI_WRITER_NAME = Variable.get(
    "db_explorer_nci_writer_secret", "explorer-nci-writer"
)  # qa

# ARD
S2_NRT_AWS_CREDS = "wagl-nrt-aws-creds"
ARD_NRT_LS_CREDS = "ard-nrt-ls-aws-creds"

# DB config
DB_DATABASE = Variable.get("db_database", "odc")  # qa
DB_HOSTNAME = Variable.get("db_hostname", "db-writer")  # qa
DB_READER_HOSTNAME = Variable.get("db_reader_hostname", "db-reader")  # qa
DB_PORT = Variable.get("db_port", "5432")  # qa

AWS_DEFAULT_REGION = Variable.get("region", "ap-southeast-2")  # qa

SENTINEL_2_ARD_INDEXING_AWS_USER_SECRET = Variable.get(
    "sentinel_2_ard_indexing_aws_user_secret", "sentinel-2-ard-indexing-creds"
)

# automated-reporting
AWS_STORAGE_STATS_POD_COUNT = Variable.get(
    "AWS_STORAGE_STATS_POD_COUNT", default_var="10"
)
REPORTING_DB_DEV_SECRET = Variable.get(
    "reporting_db_dev_secret", default_var="reporting-db-dev"
)
REPORTING_IAM_NEMO_PROD_SECRET = Variable.get(
    "reporting_iam_nemo_prod_secret", default_var="reporting-iam-nemo-production"
)
REPORTING_DB_SECRET = Variable.get("reporting_db_secret", default_var="reporting-db")

STATSD_HOST = Variable.get("statsd_host", default_var="localhost")
STATSD_PORT = Variable.get("statsd_port", default_var="8125")

# dea-access
DEA_ACCESS_RESTO_API_ADMIN_SECRET = Variable.get(
    "dea_access_resto_api_admin_secret", default_var="dea-access-resto-api-admin"
)  # qa
