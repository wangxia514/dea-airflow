"""
Fetch wagl NRT ancillaries to a S3 bucket.
"""
from datetime import datetime, timedelta
from urllib.parse import urlencode, quote_plus

from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.hooks.S3_hook import S3Hook

AWS_CONN_ID = "wagl_nrt_manual"


default_args = {
    "owner": "Imam Alam",
    "depends_on_past": False,
    "start_date": datetime(2020, 9, 23),
    "email": ["imam.alam@ga.gov.au"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=60),
}


def aws_s3_sync(
    client, src_bucket, src_prefix, dest_bucket, dest_prefix, safe_tags, key_filter=None
):
    to_copy = client.list_objects_v2(
        Bucket=src_bucket,
        Prefix=src_prefix,
    )
    for obj in to_copy["Contents"]:
        src_key = obj["Key"]
        suffix = src_key[len(src_prefix) :]

        if key_filter is not None and not key_filter(suffix):
            continue

        dest_key = dest_prefix + suffix
        print(f"copying {src_key} to {dest_key}")

        extra_args = dict(
            Tagging=safe_tags,
            StorageClass="STANDARD",
            ACL="bucket-owner-full-control",
            TaggingDirective="REPLACE",
        )

        # this can copy >5GB objects
        client.copy(
            CopySource={"Bucket": src_bucket, "Key": src_key},
            Bucket=dest_bucket,
            Key=dest_key,
            ExtraArgs=extra_args,
        )


def copy_ancillaries(**context):
    task_instance = context["task_instance"]

    s3_hook = S3Hook(aws_conn_id=AWS_CONN_ID)
    client = s3_hook.get_conn()

    safe_tags = urlencode({}, quote_via=quote_plus)

    def ga_sentinel_to_cache(src_prefix, dest_prefix, key_filter=None):
        aws_s3_sync(
            client,
            src_bucket="ga-sentinel",
            src_prefix=src_prefix,
            dest_bucket="dea-dev-nrt-scene-cache",
            dest_prefix=dest_prefix,
            safe_tags=safe_tags,
            key_filter=key_filter,
        )

    def dev_to_cache(src_prefix, dest_prefix, key_filter=None):
        aws_s3_sync(
            client,
            src_bucket="dea-dev-bucket",
            src_prefix=src_prefix,
            dest_bucket="dea-dev-nrt-scene-cache",
            dest_prefix=dest_prefix,
            safe_tags=safe_tags,
            key_filter=key_filter,
        )

    ga_sentinel_to_cache(
        src_prefix="ancillary/lookup_tables/ozone",
        dest_prefix="ancillary/ozone",
    )
    ga_sentinel_to_cache(
        src_prefix="ancillary/elevation/tc_aus_3sec",
        dest_prefix="ancillary/dsm",
    )
    ga_sentinel_to_cache(
        src_prefix="ancillary/elevation/world_1deg",
        dest_prefix="ancillary/elevation/world_1deg",
    )
    ga_sentinel_to_cache(
        src_prefix="ancillary/aerosol/AATSR/2.0",
        dest_prefix="ancillary/aerosol",
        key_filter=lambda suffix: suffix == "/aerosol.h5",
    )
    dev_to_cache(src_prefix="s2-wagl-nrt/invariant", dest_prefix="ancillary/invariant")
    dev_to_cache(
        src_prefix="s2-wagl-nrt",
        dest_prefix="ancillary",
        key_filter=lambda suffix: suffix == "/Land_Sea_Rasters.tar.z",
    )


pipeline = DAG(
    "k8s_wagl_nrt_ancillary",
    doc_md=__doc__,
    default_args=default_args,
    description="DEA Sentinel-2 NRT fetch ancillary",
    concurrency=1,
    max_active_runs=1,
    catchup=False,
    params={},
    schedule_interval=None,
    tags=["k8s", "dea", "psc", "wagl", "nrt"],
)

with pipeline:
    START = DummyOperator(task_id="start_wagl")

    COPY = PythonOperator(
        task_id="copy_ancillaries",
        python_callable=copy_ancillaries,
        provide_context=True,
    )

    END = DummyOperator(task_id="end_wagl")

    START >> COPY >> END
