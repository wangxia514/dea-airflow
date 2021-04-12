"""
#
# Iamroles supplied by terraform
#
"""
from airflow.models import Variable

# role config
INDEXING_ROLE = Variable.get("processing_indexing_role", "dea-dev-eks-orchestration")
DB_DUMP_S3_ROLE = Variable.get("db_dump_s3_role", "dea-dev-eks-db-dump-to-s3")

C3_PROCESSING_ROLE = Variable.get(
    "processing_user_secret", "processing-aws-creds-sandbox"
)
C3_ALCHEMIST_ROLE = Variable.get(
    "alchemist_c3_indexing_user_secret", "alchemist-c3-user-creds"
)


# NCI db sync
NCI_DBSYNC_ROLE = Variable.get("nci_dbsync_role", "svc-dea-sandbox-eks-nci-dbsync")
