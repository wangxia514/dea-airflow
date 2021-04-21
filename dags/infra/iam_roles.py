"""
#
# Iamroles supplied by terraform
Audit check:
    date: 21/04/2021
"""
from airflow.models import Variable

# role config
INDEXING_ROLE = Variable.get("processing_indexing_role", "dea-dev-eks-orchestration") #qa
DB_DUMP_S3_ROLE = Variable.get("db_dump_s3_role", "dea-dev-eks-db-dump-to-s3") # qa

# C3_PROCESSING_ROLE = Variable.get(
#     "processing_user_secret", "processing-aws-creds-sandbox"
# ) #qa
C3_ALCHEMIST_ROLE = Variable.get(
    "alchemist_c3_indexing_user_secret", "alchemist-c3-user-creds"
) #qa


# NCI db sync
NCI_DBSYNC_ROLE = Variable.get("nci_dbsync_role", "svc-dea-sandbox-eks-nci-dbsync") #qa
