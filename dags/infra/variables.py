"""
# Environment shared variables read from airflow variable config, provided by infrastracture
# https://airflow.apache.org/docs/stable/concepts.html?highlight=variable#storing-variables-in-environment-variables
# Variables set using Environment Variables would not appear in the Airflow UI but you will be able to use it in your DAG file
Audit check:
    date: 21/04/2021
"""
from airflow.models import Variable

# DB Users / Roles
SECRET_EXPLORER_WRITER_NAME = Variable.get(
    "db_explorer_writer_secret", default_var="explorer-writer"
)  # qa
SECRET_OWS_WRITER_NAME = Variable.get(
    "db_ows_writer_secret", default_var="ows-writer"
)  # qa
SECRET_ODC_WRITER_NAME = Variable.get(
    "db_odc_writer_secret", default_var="odc-writer"
)  # qa
SECRET_ODC_READER_NAME = Variable.get(
    "db_odc_reader_secret", default_var="odc-reader"
)  # qa
SECRET_DBA_ADMIN_NAME = Variable.get(
    "db_dba_admin_secret", default_var="dba_admin"
)  # qa

SECRET_ODC_ADMIN_NAME = Variable.get("db_odc_admin_secret", default_var="odc-admin")

SECRET_EXPLORER_ADMIN_NAME = Variable.get(
    "db_explorer_admin_secret", default_var="explorer-admin"
)

SECRET_OWS_ADMIN_NAME = Variable.get("db_ows_admin_secret", default_var="ows-admin")

SECRET_EXPLORER_NCI_ADMIN_NAME = Variable.get(
    "db_explorer_nci_admin_secret", default_var="explorer-nci-admin"
)  # qa
SECRET_EXPLORER_NCI_WRITER_NAME = Variable.get(
    "db_explorer_nci_writer_secret", default_var="explorer-nci-writer"
)  # qa

# DB config
DB_DATABASE = Variable.get("db_database", default_var="odc")  # qa
DB_HOSTNAME = Variable.get("db_hostname", default_var="db-writer")  # qa
DB_READER_HOSTNAME = Variable.get("db_reader_hostname", default_var="db-reader")
DB_PORT = Variable.get("db_port", default_var="5432")  # qa

# HNRS ((Hydrometric Networks and Remote Sensing) DB config
# Note: this DB run within same DB cluster as odc, so reuse
# the odc db hostname and port. 
HNRS_DB_DATABASE = Variable.get("hnrs_db_database", default_var="hnrs_dc") 
SECRET_HNRS_DC_ADMIN_NAME = Variable.get(
    "db_hnrs_dc_admin_secret", default_var="hnrs-dc-admin"
)

SECRET_HNRS_DC_WRITER_NAME = Variable.get(
    "db_hnrs_dc_writer_secret", default_var="hnrs-dc-writer"
) 

AWS_DEFAULT_REGION = Variable.get("region", default_var="ap-southeast-2")  # qa

# dea-access
DEA_ACCESS_RESTO_API_ADMIN_SECRET = Variable.get(
    "dea_access_resto_api_admin_secret", default_var="dea-access-resto-api-admin"
)  # qa

# c3 alchemist deriveritves
ALCHEMIST_C3_USER_SECRET = Variable.get(
    "alchemist_c3_user_secret", default_var="alchemist-c3-user-creds"
)

ALCHEMIST_S2_C3_WO_NRT_USER_SECRET = Variable.get(
    "alchemist_s2_c3_wo_nrt_user_secret", default_var="alchemist-s2-c3-nrt-wo-user-creds"
)

LANDSAT_C3_AWS_USER_SECRET = Variable.get(
    "landsat_c3_aws_user_secret", default_var="processing-landsat-3-aws-creds"
)

SENTINEL_2_ARD_INDEXING_AWS_USER_SECRET = Variable.get(
    "sentinel_2_ard_indexing_aws_user_secret",
    default_var="sentinel-2-ard-indexing-creds",
)

S2_NRT_AWS_CREDS = "wagl-nrt-aws-creds"
ARD_NRT_LS_CREDS = "ard-nrt-ls-aws-creds"

COP_API_REP_CREDS = "copernicus_api_password"

WATERBODIES_DEV_USER_SECRET = Variable.get(
    "waterbodies_dev_user_secret", default_var="waterbodies-dev-user-creds"
)
ELVIS_DEV_USER_SECRET = Variable.get(
    "processing_aws_creds_elvis", default_var="processing-aws-creds-elvis"
)
WIT_DEV_USER_SECRET = Variable.get(
    "wit_dev_user_secret", default_var="wit-dev-user-creds"
)
WATERBODIES_DB_WRITER_SECRET = Variable.get(
    "waterbodies_writer", default_var="waterbodies-writer"
)

# stats
PROCESSING_STATS_USER_SECRET = Variable.get(
    "processing_stats_user_secret", default_var="processing-aws-creds-stats"
)

# automated-reporting
AWS_STATS_SECRET = Variable.get(
    "aws_stats_secret", default_var="aws-stats"
)  # qa
AWS_STORAGE_STATS_POD_COUNT = Variable.get("AWS_STORAGE_STATS_POD_COUNT", default_var="10")

SARA_HISTORY_SECRET = Variable.get(
    "sara_history_secret", default_var="sara-history"
)  # qa
ARCHIE_SECRET = Variable.get(
    "archie_secret", default_var="archie"
)
UPTIME_ROBOT_SECRET = Variable.get("uptime_robot_secret", default_var="uptime-robot")

REPORTING_ASB_ANALYTICS_API_SECRET = Variable.get("reporting_asb_analytics_api_secret", default_var="reporting-asb-analytics-api")

REPORTING_DB_DEV_SECRET = Variable.get("reporting_db_dev_secret", default_var="reporting-db-dev")

REPORTING_IAM_DEA_S3_SECRET = Variable.get("reporting_iam_dea_s3_secret", default_var="reporting-iam-dea-s3")

REPORTING_IAM_REP_S3_SECRET = Variable.get("reporting_iam_rep_s3_secret", default_var="reporting-iam-rep-s3")

REPORTING_ODC_DB_SECRET = Variable.get("reporting_odc_db_secret", default_var="reporting-odc-db")

REPORTING_SCIHUB_API_SECRET = Variable.get("reporting_scihub_api_secret", default_var="reporting-scihub-api")

REPORTING_UPTIME_API_SECRET = Variable.get("reporting_uptime_api_secret", default_var="reporting-uptime-api")

REPORTING_USGSM2M_API_SECRET = Variable.get("reporting_usgsm2m_api_secret", default_var="reporting-usgsm2m-api")
