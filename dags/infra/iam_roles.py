"""
# IAM ROLES FOR airflow dags kubernetespodsoperators
Audit check:
    date: 21/04/2021
"""
from airflow.models import Variable

# role config
INDEXING_ROLE = Variable.get("processing_indexing_role", default_var="dea-dev-eks-orchestration")  # qa

DB_DUMP_S3_ROLE = Variable.get("db_dump_s3_role", default_var="dea-dev-eks-db-dump-to-s3")  # qa

# NCI db sync
NCI_DBSYNC_ROLE = Variable.get("nci_dbsync_role", default_var="svc-dea-dev-eks-nci-dbsync")  # qa
