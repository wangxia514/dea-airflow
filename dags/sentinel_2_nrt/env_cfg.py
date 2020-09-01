"""
# Sentinel-2_nrt process env configs read from variables if environment specific
"""
from airflow.models import Variable
foo = Variable.get("db_hostname", "db-writer")

# ENVIRONMENT CONFIGURATION
OWS_CFG_PATH = "/env/config/ows_cfg.py"
INDEXING_PRODUCTS = "s2a_nrt_granule s2b_nrt_granule"
ARCHIVE_PRODUCTS = INDEXING_PRODUCTS
ARCHIVE_CONDITION = "[$(date -d '-365 day' +%F), $(date -d '-91 day' +%F)]"
UPDATE_EXTENT_PRODUCTS = "s2_nrt_granule_nbar_t"
SQS_QUEUE_NAME = "dea-dev-eks-ows-dag"
INDEXING_ROLE = "dea-dev-eks-orchestration"
SECRET_AWS_NAME = "processing-aws-creds-dev"
SECRET_EXPLORER_NAME = "explorer-db"
SECRET_OWS_NAME = "ows-db"
DB_DATABASE = "ows"
DB_HOSTNAME = "db-writer"


OWS_CFG_MOUNT_PATH = "/env/config"
OWS_CFG_PATH = OWS_CFG_MOUNT_PATH + "/ows_cfg.py"
