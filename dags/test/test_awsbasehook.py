"""
testing for github action to correctly pick up missing client_type error
"""
from airflow.providers.amazon.aws.hooks.base_aws import AwsBaseHook as AwsHook

from infra.connections import AWS_DEA_PUBLIC_DATA_LANDSAT_3_SYNC_CONN

aws_hook = AwsHook(
    aws_conn_id=AWS_DEA_PUBLIC_DATA_LANDSAT_3_SYNC_CONN, client_type="s3"
)

aws_hook_without_client_type = AwsHook(
    aws_conn_id=AWS_DEA_PUBLIC_DATA_LANDSAT_3_SYNC_CONN
)
