"""
testing for github action to correctly pick up missing client_type error
"""
from airflow.providers.amazon.aws.hooks.base_aws import AwsBaseHook as AwsHook
from airflow import DAG
from datetime import datetime, timedelta
import pendulum

from infra.connections import AWS_DEA_PUBLIC_DATA_LANDSAT_3_SYNC_CONN

local_tz = pendulum.timezone("Australia/Canberra")

default_args = {
    "owner": "Pin Jin",
    "start_date": datetime(2021, 3, 1, tzinfo=local_tz),
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
    "email": "pin.jin@ga.gov.au",
}

dag = DAG(
    "test_awsbasehook",
    doc_md=__doc__,
    default_args=default_args,
    catchup=False,
    schedule_interval=None,
    max_active_runs=4,
    default_view="tree",
    tags=["test", "AwsBaseHook"],
)
with dag:

    AwsHook(aws_conn_id=AWS_DEA_PUBLIC_DATA_LANDSAT_3_SYNC_CONN, client_type="s3")

    AwsHook(aws_conn_id=AWS_DEA_PUBLIC_DATA_LANDSAT_3_SYNC_CONN)
