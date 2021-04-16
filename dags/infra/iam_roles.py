"""
# IAM ROLES FOR airflow dags kubernetespodsoperators
"""
from airflow.models import Variable

# role config
INDEXING_ROLE = Variable.get("processing_indexing_role", "dea-dev-eks-orchestration")

DB_DUMP_S3_ROLE = Variable.get("db_dump_s3_role", "dea-dev-eks-db-dump-to-s3")

# NCI db sync
NCI_DBSYNC_ROLE = Variable.get("nci_dbsync_role", "svc-dea-dev-eks-nci-dbsync")
