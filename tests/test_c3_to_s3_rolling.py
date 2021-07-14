from pathlib import Path

import boto3
import moto
import pytest
from scripts.c3_to_s3_rolling import upload_s3_resource


@moto.mock_s3
def test_upload_with_and_without_content_type(local_stac):
    """
    Do some simple tests with putting an object on S3 with appropriate content_types.
    """
    bucket_name = "fake-bucket"
    key_json = "path/to/file.json"
    key_txt = "path/to/file.txt"

    client = boto3.client("s3")
    client.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": "ap-southeast-2"},
    )

    content = local_stac.read_bytes()

    upload_s3_resource(
        bucket_name,
        key_json,
        content,
        content_type="application/json",
    )

    upload_s3_resource(
        bucket_name,
        key_txt,
        content,
    )

    s3 = boto3.resource("s3")

    json_s3 = s3.Object(bucket_name, key_json)
    json_s3.load()

    assert json_s3.content_type == "application/json"

    txt_s3 = s3.Object(bucket_name, key_txt)
    txt_s3.load()

    assert txt_s3.content_type == "binary/octet-stream"


@pytest.fixture
def local_stac():
    return Path("tests/data/ga_ls8c_ard_3-1-0_095075_2019-07-28_final.stac-item.json")
