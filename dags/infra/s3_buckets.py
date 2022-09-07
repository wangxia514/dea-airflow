"""
# S3 buckets
Audit check:
    date: 07/09/2022
lines commented with qa has been checked in infrastracture
helm setup
"""
from airflow.models import Variable

# S3 buckets
DB_DUMP_S3_BUCKET = Variable.get("db_dump_s3_bucketname", default_var="dea-dev-odc-db-dump")  # qa

S2_NRT_SOURCE_BUCKET = "sentinel-s2-l1c"
S2_NRT_TRANSFER_BUCKET = "dea-dev-eks-nrt-scene-cache"
