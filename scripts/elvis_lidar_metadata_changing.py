# This script aims to
# 1. get a S3 prefix URI which under s3://elvis-stac, return relative S3 objects URIs
# 2. use these S3 object URIs to load relative STAC metadata files (JSON format)
# 3. run transform script to these metadata files
# 4. dump the new metadata files to s3://dea-public-data-dev/projects/elvis-lidar (keep original hierarchy)
# Note: the dea-public-data-dev writer credentials will be passed by K8s secret


import json
import boto3
from urllib.parse import urlparse

from botocore import UNSIGNED
from botocore.config import Config


# these collection items will map to S3 URI
# s3://elvis-stac/{collection_name}/collection.json
COLLECTION_LIST = ["Collarenebri201210", "Bellata201207", "Bellata201401"]
ORIGINAL_BUKCET_NAME = "elvis-stac"
NWE_BUCKET_NAME = "dea-public-data-dev"
NEW_PREFIX = "projects/elvis-lidar/"


def modify_json_content(old_metadata_content: dict) -> dict:
    # assume all JSON files follow the same schema to save development time
    collection = old_metadata_content['collection']
    old_metadata_content['properties']['odc:collection'] = collection
    return old_metadata_content


def get_metadata_path(collection_name):
    collection_key = f"{collection_name}/collection.json"

    s3_conn = boto3.client('s3', config=Config(signature_version=UNSIGNED))
    collection_content = s3_conn.get_object(Bucket=ORIGINAL_BUKCET_NAME, Key=collection_key)
    return [e['href'] for e in json.loads(collection_content["Body"].read())['links'] if e['rel'] == 'item']


def main():

    # the following values would be passed by Airflow, but consider it is a temp solution, let us
    # leave the hard-code values here to pass the test
    for collection_name in COLLECTION_LIST:
        original_file_list = get_metadata_path(collection_name)

        for original_file in original_file_list:

            original_file_key = urlparse(original_file).path[1:]

            # it is a loop, so unsign when load the orignal metadata file
            s3_conn = boto3.client('s3', config=Config(signature_version=UNSIGNED))

            content_object = s3_conn.get_object(Bucket=ORIGINAL_BUKCET_NAME, Key=original_file_key)
            old_metadata_content = json.loads(content_object["Body"].read())
            try:
                product_name = old_metadata_content['properties']['odc:product']
                new_json_content = modify_json_content(old_metadata_content)

                # turn on the sign-in cause we will upload to a private bucket
                s3_conn = boto3.client('s3')

                s3_conn.put_object(
                    Body=json.dumps(new_json_content),
                    Bucket=NWE_BUCKET_NAME,
                    Key=NEW_PREFIX + product_name + "/" + original_file_key
                )
            except KeyError:
                print(f"{original_file_key} cannot parse its product name")
            except:
                print(f"{original_file_key} cannot modify its content and dump to temp S3 bucket")


if __name__ == "__main__":
    main()