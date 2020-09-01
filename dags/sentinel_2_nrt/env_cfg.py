"""
# Sentinel-2_nrt process env configs read from variables if environment specific
"""
from airflow.models import Variable

# For testing
foo = Variable.get("bar", "bar")

# OWS pod specific configuration
OWS_CFG_PATH = "/env/config/ows_cfg.py"
OWS_CFG_MOUNT_PATH = "/env/config"
OWS_CFG_PATH = OWS_CFG_MOUNT_PATH + "/ows_cfg.py"
OWS_CFG_IMAGEPATH = "/opt/dea-config/dev/services/wms/ows/ows_cfg.py"

# Process specific for sentinel indexing process
INDEXING_PRODUCTS = "s2a_nrt_granule s2b_nrt_granule"
ARCHIVE_PRODUCTS = INDEXING_PRODUCTS
ARCHIVE_CONDITION = "[$(date -d '-365 day' +%F), $(date -d '-91 day' +%F)]"
UPDATE_EXTENT_PRODUCTS = "s2_nrt_granule_nbar_t"


# Environment shared variables read from airflow variable config
SQS_QUEUE_NAME =  Variable.get("sqs_queue_name", "dea-dev-eks-ows-dag")
INDEXING_ROLE = Variable.get("indexing_role", "dea-dev-eks-orchestration")

SECRET_AWS_NAME = Variable.get("secret_aws_name", "processing-aws-creds-dev")
SECRET_EXPLORER_NAME = Variable.get("secret_explorer_name", "explorer-db")
SECRET_OWS_NAME = Variable.get("secret_ows_name", "ows-db")
DB_DATABASE = Variable.get("db_database", "ows")
DB_HOSTNAME = Variable.get("db_hostname", "db-writer")
