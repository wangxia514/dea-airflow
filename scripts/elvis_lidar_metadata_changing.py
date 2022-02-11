# This script aims to
# 1. get a S3 prefix URI which under s3://elvis-stac, return relative S3 objects URIs
# 2. use these S3 object URIs to load relative STAC metadata files (JSON format)
# 3. run transform script to these metadata files
# 4. dump the new metadata files to s3://dea-public-data-dev/projects/elvis-lidar (keep original hierarchy)
# Note: the dea-public-data-dev writer credentials will be passed by K8s secret


import json
import boto3

from botocore import UNSIGNED
from botocore.config import Config


def modify_json_content(old_metadata_content: dict) -> dict:
    # assume all JSON files follow the same schema to save development time
    collection = old_metadata_content['collection']
    old_metadata_content['properties']['odc:collection'] = collection
    return old_metadata_content


def main():

    # the following values would be passed by Airflow, but consider it is a temp solution, let us
    # leave the hard-code values here to pass the test
    original_bucket_name = "elvis-stac"
    original_prefix = "Collarenebri201210/Collarenebri201210-LID1-AHD_6486724_55_0002_0002_1m/"

    new_bucket_name = "dea-public-data-dev"
    new_prefix = "projects/elvis-lidar/"

    s3_conn = boto3.client('s3', config=Config(signature_version=UNSIGNED))
    s3_result = s3_conn.list_objects_v2(Bucket=original_bucket_name, Prefix=original_prefix, Delimiter="/")

    original_file_list = []

    for key in s3_result['Contents']:
        original_file_list.append(key['Key'])

    for original_file_key in original_file_list:

        # it is a loop, so unsign when load the orignal metadata file
        s3_conn = boto3.client('s3', config=Config(signature_version=UNSIGNED))

        content_object = s3_conn.get_object(Bucket=original_bucket_name, Key=original_file_key)
        new_json_content = modify_json_content(json.loads(content_object["Body"].read()))

        # turn on the sign-in cause we will upload to a private bucket
        s3_conn = boto3.client('s3')

        s3_conn.put_object(
            Body=json.dumps(new_json_content),
            Bucket=new_bucket_name,
            Key=new_prefix + original_file_key
        )


if __name__ == "__main__":
    main()