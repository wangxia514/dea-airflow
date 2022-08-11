"""
Kubernetes Secrets used in Reporting Dags
"""
from airflow.kubernetes.secret import Secret

s3_secrets = [
    Secret("env", "S3_ACCESS_KEY", "reporting-airflow", "ACCESS_KEY"),
    Secret("env", "S3_BUCKET", "reporting-airflow", "BUCKET"),
    Secret("env", "S3_SECRET_KEY", "reporting-airflow", "SECRET_KEY"),
]

aws_odc_secrets = [
    Secret("env", "ODC_DB_HOST", "reporting-odc-db", "DB_HOST"),
    Secret("env", "ODC_DB_NAME", "reporting-odc-db", "DB_NAME"),
    Secret("env", "ODC_DB_PORT", "reporting-odc-db", "DB_PORT"),
    Secret("env", "ODC_DB_USER", "reporting-odc-db", "DB_USER"),
    Secret("env", "ODC_DB_PASSWORD", "reporting-odc-db", "DB_PASSWORD"),
]

reporting_db_secrets = [
    Secret("env", "DB_HOST", "reporting-db", "DB_HOST"),
    Secret("env", "DB_NAME", "reporting-db", "DB_NAME"),
    Secret("env", "DB_PORT", "reporting-db", "DB_PORT"),
    Secret("env", "DB_USER", "reporting-db", "DB_USER"),
    Secret("env", "DB_PASSWORD", "reporting-db", "DB_PASSWORD"),
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


def db_secrets(env):
    """
    Helper to get db secrets based on environment
    """
    return reporting_db_secrets if env == "prod" else reporting_db_dev_secrets
