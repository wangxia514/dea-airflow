"""
#
# s3_buckets supplied by terraform or global
#
"""
from airflow.models import Variable

# S3 buckets
DB_DUMP_S3_BUCKET = Variable.get("db_dump_s3_bucketname", "dea-dev-odc-db-dump")
