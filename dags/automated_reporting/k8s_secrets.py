"""
Kubernetes Secrets used in Reporting Dags
"""
from airflow.kubernetes.secret import Secret

s3_automated_operation_bucket = [
    Secret("env", "S3_BUCKET", "reporting-automated-operation-bucket", "BUCKET"),
]

s3_db_dump_bucket = [
    Secret("env", "S3_BUCKET", "reporting-db-dump-bucket", "BUCKET"),
]

s3_server_access_log_bucket = [
    Secret("env", "S3_BUCKET", "reporting-server-access-log-bucket", "BUCKET"),
]

s3_public_data_inventory_bucket = [
    Secret("env", "S3_BUCKET", "reporting-public-data-inventory-bucket", "BUCKET"),
]

iam_dea_dev_secrets = [
    Secret("env", "ACCESS_KEY", "reporting-iam-dea-dev", "ACCESS_KEY"),
    Secret("env", "SECRET_KEY", "reporting-iam-dea-dev", "SECRET_KEY"),
]

iam_dea_secrets = [
    Secret("env", "ACCESS_KEY", "reporting-iam-dea-s3", "ACCESS_KEY"),
    Secret("env", "SECRET_KEY", "reporting-iam-dea-s3", "SECRET_KEY"),
]

iam_rep_secrets = [
    Secret("env", "ACCESS_KEY", "reporting-airflow", "ACCESS_KEY"),
    Secret("env", "SECRET_KEY", "reporting-airflow", "SECRET_KEY"),
]

iam_nemo_production_secrets = [
    Secret("env", "ACCESS_KEY", "reporting-iam-nemo-production", "ACCESS_KEY"),
    Secret("env", "SECRET_KEY", "reporting-iam-nemo-production", "SECRET_KEY"),
]

uptime_robot_secret = [
    Secret("env", "API_KEY", "reporting-uptime-api", "UPTIME_KEY"),
]

aws_odc_secrets = [
    Secret("env", "ODC_DB_HOST", "reporting-odc-db", "DB_HOST"),
    Secret("env", "ODC_DB_NAME", "reporting-odc-db", "DB_NAME"),
    Secret("env", "ODC_DB_PORT", "reporting-odc-db", "DB_PORT"),
    Secret("env", "ODC_DB_USER", "reporting-odc-db", "DB_USER"),
    Secret("env", "ODC_DB_PASSWORD", "reporting-odc-db", "DB_PASSWORD"),
]

aws_odc_secrets = [
    Secret("env", "ODC_DB_HOST", "reporting-odc-db", "DB_HOST"),
    Secret("env", "ODC_DB_NAME", "reporting-odc-db", "DB_NAME"),
    Secret("env", "ODC_DB_PORT", "reporting-odc-db", "DB_PORT"),
    Secret("env", "ODC_DB_USER", "reporting-odc-db", "DB_USER"),
    Secret("env", "ODC_DB_PASSWORD", "reporting-odc-db", "DB_PASSWORD"),
]

nci_odc_secrets = [
    Secret("volume", "/var/secrets/lpgs", "lpgs-port-forwarder", "PORT_FORWARDER_KEY"),
    Secret("env", "NCI_TUNNEL_HOST", "reporting-nci-tunnel", "NCI_HOST"),
    Secret("env", "NCI_TUNNEL_USER", "reporting-nci-tunnel", "NCI_USER"),
    Secret("env", "ODC_DB_HOST", "reporting-nci-odc-db", "DB_HOST"),
    Secret("env", "ODC_DB_NAME", "reporting-nci-odc-db", "DB_NAME"),
    Secret("env", "ODC_DB_PORT", "reporting-nci-odc-db", "DB_PORT"),
    Secret("env", "ODC_DB_USER", "reporting-nci-odc-db", "DB_USER"),
    Secret("env", "ODC_DB_PASSWORD", "reporting-nci-odc-db", "DB_PASSWORD"),
]

nci_command_secrets = [
    Secret(
        "volume", "/var/secrets/lpgs", "reporting-lpgs-commands", "LPGS_COMMAND_KEY"
    ),
    Secret("env", "NCI_TUNNEL_HOST", "reporting-nci-tunnel", "NCI_HOST"),
    Secret("env", "NCI_TUNNEL_USER", "reporting-nci-tunnel", "NCI_USER"),
]

reporting_master_db_secrets_for_backup = [
    Secret("env", "DB_HOST", "reporting-db-master", "DB_HOST"),
    Secret("env", "DB_NAME", "reporting-db-master", "DB_NAME"),
    Secret("env", "DB_PORT", "reporting-db-master", "DB_PORT"),
    Secret("env", "DB_USER", "reporting-db-master", "DB_USER"),
    Secret("env", "PGPASSWORD", "reporting-db-master", "DB_PASSWORD"),
]

reporting_db_dev_secrets = [
    Secret("env", "DB_HOST", "reporting-db-dev", "DB_HOST"),
    Secret("env", "DB_NAME", "reporting-db-dev", "DB_NAME"),
    Secret("env", "DB_PORT", "reporting-db-dev", "DB_PORT"),
    Secret("env", "DB_USER", "reporting-db-dev", "DB_USER"),
    Secret("env", "DB_PASSWORD", "reporting-db-dev", "DB_PASSWORD"),
]

m2m_api_secrets = [
    Secret("env", "M2M_USER", "reporting-usgsm2m-api", "M2M_USER"),
    Secret("env", "M2M_PASSWORD", "reporting-usgsm2m-api", "M2M_PASSWORD"),
]

sqs_secrets = [
    Secret("env", "ACCESS_KEY", "reporting-iam-sqs", "ACCESS_KEY"),
    Secret("env", "SECRET_KEY", "reporting-iam-sqs", "SECRET_KEY"),
]

reporting_dev_db_secret = [
    Secret("env", "REP_DB_URI", "reporting-dev-db", "REP_DB_URI"),
]

reporting_master_db_secret = [
    Secret("env", "REP_DB_URI", "reporting-master-db", "REP_DB_URI"),
]

google_analytics_secret = [
    Secret(
        "env",
        "GOOGLE_ANALYTICS_CREDS",
        "reporting-asb-analytics-api",
        "ASB_ANALYTICS_KEY",
    ),
]

scihub_secrets = [
    Secret("env", "SCIHUB_USER", "reporting-scihub-api", "SCIHUB_USER"),
    Secret("env", "SCIHUB_PASSWORD", "reporting-scihub-api", "SCIHUB_PASSWORD"),
]


def db_secrets(env):
    """
    Helper to get db secrets based on environment
    """
    return reporting_master_db_secret if env == "prod" else reporting_dev_db_secret
