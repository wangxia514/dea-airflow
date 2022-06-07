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
    'Applethorpe2012Twn',
    'AuchmahSwamp2013Prj',
    'BaanBaa201401',
    'Bathurst201104',
    'Bathurst201907',
    'Bellata201207',
    'Bellata201401',
    'Bellata202008',
    'BendigoRegion2013',
    'Blackville201406',
    'Blayney201307',
    'Blayney201704',
    'Blayney201709',
    'BoganGate201304',
    'BoganGate201511',
    'BoganGate201906',
    'BoganGate202104',
    'Boggabri201401',
    'Boggabri201911',
    'BoonaMount202104',
    'Boorowa201709',
    'Bourke201501',
    'Bourke202011',
    'Brewarrina201501',
    'Brewarrina202011',
    'BrokenHill2009',
    'Brookstead2012Twn',
    'BungunyatoToobeah2012Rgn',
    'BurnieDevonportLauncestonLiDAR2013',
    'Burrenbar201501',
    'Burrenbar201805',
    'Burrenbar201911',
    'Canonba201503',
    'Cargelligo202103',
    'Cargelligo202104',
    'Cargelligo202107',
    'Carinda201511',
    'CecilPlains2010Twn',
    'Chinchilla2010Twn',
    'Clifton2010Twn',
    'Clifton2014Twn',
    'Cobbora201407',
    'Collarenebri201210',
    'Condamine2011Twn',
    'CondamineRivTwmba2014Prj',
    'Condobolin201403',
    'Condobolin202104',
    'Cowra201107',
    'Cowra201311',
    'Cowra201709',
    'Crookwell201709',
    'Curlewis201401',
    'Curlewis201406',
    'Dalby2010Twn',
    'DarlingBourke2009',
    'Dirranbandi2011Twn',
    'Drake201506',
    'Dubbo201407',
    'Dubbo201507',
    'Dubbo201512',
    'Dungalear201207',
    'EastGreenmount2014Twn',
    'Geera201511',
    'Geera202011',
    'Gindoono202104',
    'Gongolgon201511',
    'Gongolgon202011',
    'Goondiwindi2011Twn',
    'Goondiwindi201501',
    'Goondiwindi201911',
    'GreaterHobartLiDAR2013',
    'Grenfell201108',
    'Grenfell202104',
    'Gwydir2008',
    'GwydirValley2013',
    'Hebel2011Twn',
    'Hermidon201305',
    'Hillston201610',
    'Hillston202103',
    'HuonRiverValleyLiDAR2013',
    'Inglewood2011Twn',
    'Jandowae2010Twn',
    'Jimbour2012Twn',
    'Kaimkillenbun2012Twn',
    'LakeGeorgeLidar2014',
    'LowerBalonne2018Prj',
    'LowerDarling2013',
    'LowerLila202011',
    'Macalister2013Twn',
    'MacquarieMarshes2008',
    'Manilla201910',
    'Manilla201911',
    'Marsden202104',
    'MaryvaletoGoomburra2012Rgn',
    'Mendooran201407',
    'Merriwagga201610',
    'Merriwagga202103',
    'Moree201207',
    'Moree201411',
    'Moree201506',
    'Moree202008',
    'Mossgiel202103',
    'MountHarris201503',
    'MountOxley202011',
    'MountWellingtonRiverDerwent2010',
    'Muckerumba202103',
    'Mudgee201407',
    'MurrumbidgeeLidar2009',
    'Murrurundi201406',
    'MyallCkToowoomba2014Prj',
    'Narrabri201401',
    'Narrabri201406',
    'Narran202011',
    'Narromine201105',
    'Nindigully2012Twn',
    'Nundle201911',
    'Nyngan201105',
    'OneTree202105',
    'Orange201305',
    'Orange201704',
    'Orange201907',
    'Oxley202105-z54',
    'Oxley202105-z55',
    'Paika202105',
    'Parkes201108',
    'Parkes201304',
    'Parkes201511',
    'Parkes201906',
    'Parkes202104',
    'PeakHill201410',
    'Pilliga201410',
    'Pittsworth2010Twn',
    'Quambone201503',
    'RankinsSprings202103',
    'SouthernDowns2010Rgn',
    'SpringCkNthBiddeston2014Prj',
    'SpringCkSthWestbrook2014Prj',
    'SquaretopKaimkillenbun2013Prj',
    'StGeorge2011Twn',
    'Stanthorpe2011Twn',
    'Surat2011Twn',
    'Talwood2011Twn',
    'Tamworth201401',
    'Tamworth201406',
    'Texas2011Twn',
    'Thallon2011Twn',
    'Thallon201501',
    'Thallon201805',
    'Thallon201911',
    'TheSummittoDalveen2013Prj',
    'Toowoomba2010Prj',
    'Toowoomba2010Rgn',
    'Toowoomba2011Prj',
    'Toowoomba2015Prj',
    'Tullibigeal202104',
    'Tummaville2010Loc',
    'Tummaville2011Loc',
    'VictorHarbor2011',
    'Walgett201207',
    'Walgett201511',
    'Wallangarra2013Twn',
    'Warra2011Twn',
    'Warraweena202011',
    'Warren201105',
    'WeeWaa201207',
    'Wellington200910',
    'Wellington201507',
    'Willandra202103',
    'Yelarbon2011Twn',
    'Yetman201911']

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