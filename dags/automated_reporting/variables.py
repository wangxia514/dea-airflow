"""
Automated Reporting Variables
"""
from airflow.models import Variable

COP_API_REP_CREDS = "copernicus_api_password"
M2M_API_REP_CREDS = "m2m_api_password"
AWS_STORAGE_STATS_POD_COUNT = Variable.get(
    "AWS_STORAGE_STATS_POD_COUNT", default_var="10"
)

REPORTING_DB_DEV_SECRET = Variable.get(
    "reporting_db_dev_secret", default_var="reporting-db-dev"
)

REPORTING_IAM_DEA_S3_SECRET = Variable.get(
    "reporting_iam_dea_s3_secret", default_var="reporting-iam-dea-s3"
)

REPORTING_IAM_REP_S3_SECRET = Variable.get(
    "reporting_iam_rep_s3_secret", default_var="reporting-iam-rep-s3"
)

REPORTING_ODC_DB_SECRET = Variable.get(
    "reporting_odc_db_secret", default_var="reporting-odc-db"
)

REPORTING_UPTIME_API_SECRET = Variable.get(
    "reporting_uptime_api_secret", default_var="reporting-uptime-api"
)

REPORTING_USGSM2M_API_SECRET = Variable.get(
    "reporting_usgsm2m_api_secret", default_var="reporting-usgsm2m-api"
)

REPORTING_IAM_SQS_SECRET = Variable.get(
    "reporting_iam_sqs_secret", default_var="reporting-iam-sqs"
)
