# This script aims to
# 1. get a S3 prefix URI which under s3://elvis-stac, return relative S3 objects URIs
# 2. use these S3 object URIs to load relative STAC metadata files (JSON format)
# 3. run transform script to these metadata files
# 4. dump the new metadata files to s3://dea-public-data-dev/projects/elvis-lidar (keep original hierarchy)
# Note: the dea-public-data-dev writer credentials will be passed by K8s secret


import json
import boto3
from urllib.parse import urlparse
import logging
import os

# these collection items will map to S3 URI
# s3://elvis-stac/{product_name}/{collection_name}/collection.json
PRODUCT_LIST = ["dem_1m", "dem_2m", "dem_5m"]

COLLECTION_LIST = [
    "Ashford201110",
    "BaanBaa201605",
    "Bellata201106",
    "Blackville201108",
    "Blackville201109",
    "Blayney201407",
    "Bobadah201601",
    "BoganGate201502",
    "BoganGate201509",
    "Boggabri201108",
    "Boggabri201604",
    "Booligal201310",
    "BoonaMount201204",
    "Boorowa201501",
    "Bourke201507",
    "Brewarrina201506",
    "Bundemar201206",
    "BunnaBunna201604",
    "Burrenbar201108",
    "Canonba201505",
    "Cargelligo201602",
    "Clive201711",
    "Cobbora201208",
    "Collarenebri200908",
    "Condobolin201309",
    "Coolah201108",
    "Coolah201109",
    "Cowra201404",
    "Crookwell201411",
    "CroppaCreek200908",
    "Cumborah200908",
    "Curlewis201108",
    "Curlewis201605",
    "Dandaloo201208",
    "Dubbo201301",
    "Dungalear201703",
    "Dunumbral200908",
    "Euchareena201409",
    "Geera201703",
    "Gindoono201601",
    "GlenInnes201712",
    "Glenariff201505",
    "Gongolgon201507",
    "Gravesend200907",
    "Grenfell201702",
    "Hermidon201505",
    "Hillston201511",
    "Horton201209",
    "Inverell201110",
    "Kilparney201408",
    "LightningRidge201801",
    "Louth201704",
    "LowerLila201508",
    "Manilla201210",
    "Marsden201502",
    "Mendooran201109",
    "Merriwagga201202",
    "MogilMogil200907",
    "Molong201308",
    "Molong201403",
    "Moree200803",
    "Mossgiel201512",
    "MountHarris201304",
    "MountOxley201507",
    "Muckerumba201202",
    "Murrurundi201111",
    "Narrabri201209",
    "Narrabri201604",
    "Narran200907",
    "Narromine201510",
    "Nundle201305",
    "Nyngan201211",
    "Oberon201311",
    "OneTree201201",
    "Orange201308",
    "Orange201407",
    "Oxley201303",
    "Paika201303",
    "Para201410",
    "Parkes201509",
    "PeakHill201204",
    "Pilliga201703",
    "Quambone201304",
    "RankinsSprings201602",
    "Stanthorpe201108",
    "TambarSprings201108",
    "TambarSprings201605",
    "Tamworth201602",
    "Texas201109",
    "Thallon200907",
    "Toorale201507",
    "Tottenham201208",
    "Tullamore201204",
    "Tullibigeal201602",
    "Walgett201309",
    "Warraweena201506",
    "Warren201308",
    "WeeWaa201605",
    "Wellington201409",
    "Willandra201511",
    "Yetman201108",
    "Bathurst201510",
    "Boomi201501",
    "Bunarba201506",
    "Carinda201705",
    "Cobbora201510",
    "Cumborah201705",
    "Drake200906",
    "Drake201709",
    "Dungalear201705",
    "Geera201705",
    "Goondiwindi201506",
    "Gulgong201510",
    "Hermidon201705",
    "Mudgee201510",
    "Mudgee201612",
    "Oberon201510",
    "Quambone201705",
    "Walgett201705",
    "Yallaroi201412"]

ORIGINAL_BUKCET_NAME = "elvis-stac"
NWE_BUCKET_NAME = "dea-public-data-dev"
NEW_PREFIX = "projects/elvis-lidar/"


def modify_json_content(old_metadata_content: dict) -> dict:
    # assume all JSON files follow the same schema to save development time
    collection = old_metadata_content['collection']
    old_metadata_content['properties']['odc:collection'] = collection

    # try to remove the useless pincloud ref
    try:
        old_metadata_content["stac_extensions"].remove("https://stac-extensions.github.io/pointcloud/v1.0.0/schema.json")
        old_metadata_content["links"].remove({'rel': 'derived_from', 'href': 'placeholder.json', 'type': 'application/geojson', 'title': 'Point Cloud'})
        return old_metadata_content
    except:
        return old_metadata_content


def get_metadata_path(product_name, collection_name):
    collection_key = f"{product_name}/{collection_name}/collection.json"
    logging.warning(f"Try to access s3://{ORIGINAL_BUKCET_NAME}/{collection_key}")
    # the read access will come from K8s service account
    s3_conn = boto3.client('s3')
    try:
        collection_content = s3_conn.get_object(Bucket=ORIGINAL_BUKCET_NAME, Key=collection_key)
        return [e['href'] for e in json.loads(collection_content["Body"].read())['links'] if e['rel'] == 'item']
    except:
        return []


def main():

    # the following values would be passed by Airflow, but consider it is a temp solution, let us
    # leave the hard-code values here to pass the test
    for product_name in PRODUCT_LIST:

        for collection_name in COLLECTION_LIST:

            original_file_list = get_metadata_path(product_name, collection_name)

            for original_file in original_file_list:

                original_file_key = urlparse(original_file).path[1:]

                # connect to s3 by elvis-stac creds
                # the read access will come from K8s service account
                s3_conn = boto3.client('s3')

                content_object = s3_conn.get_object(Bucket=ORIGINAL_BUKCET_NAME, Key=original_file_key)
                old_metadata_content = json.loads(content_object["Body"].read())
                try:
                    new_json_content = modify_json_content(old_metadata_content)

                    # turn on the sign-in cause we will upload to a private bucket
                    s3_conn = boto3.client('s3', aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID_WRITE'], aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY_WRITE'])
                    s3_conn.put_object(
                        Body=json.dumps(new_json_content),
                        Bucket=NWE_BUCKET_NAME,
                        Key=NEW_PREFIX + original_file_key
                    )

                except KeyError:
                    logging.warning(f"{original_file_key} cannot parse its product name")
                except:
                    logging.warning(f"{original_file_key} cannot modify its content and dump to temp S3 bucket")


if __name__ == "__main__":
    main()