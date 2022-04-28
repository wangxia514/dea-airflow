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
    "CecilPlains2010Twn",
    "BungunyatoToobeah2012Rgn",
    "Dirranbandi2011Twn",
    "Hebel2011Twn",
    "Talwood2011Twn",
    "Nindigully2012Twn",
    "StGeorge2011Twn",
    "Surat2011Twn",
    "Thallon2011Twn",
    "Applethorpe2012Twn",
    "AuchmahSwamp2013Prj",
    "Clifton2014Twn",
    "Clifton2010Twn",
    "Condamine2011Twn",
    "Dalby2010Twn",
    "EastGreenmount2014Twn",
    "Goondiwindi2011Twn",
    "CondamineRivTwmba2014Prj",
    "Inglewood2011Twn",
    "Jandowae2010Twn",
    "Jimbour2012Twn",
    "Kaimkillenbun2012Twn",
    "LowerBalonne2018Prj",
    "Macalister2013Twn",
    "MaryvaletoGoomburra2012Rgn",
    "Pittsworth2010Twn",
    "SpringCkNthBiddeston2014Prj",
    "SpringCkSthWestbrook2014Prj",
    "SquaretopKaimkillenbun2013Prj",
    "Stanthorpe2011Twn",
    "Texas2011Twn",
    "TheSummittoDalveen2013Prj",
    "Tummaville2010Loc",
    "Tummaville2011Loc",
    "Wallangarra2013Twn",
    "Warra2011Twn",
    "Yelarbon2011Twn",
    "Brookstead2012Twn",
    "Chinchilla2010Twn",
    "MyallCkToowoomba2014Prj",
    "SouthernDowns2010Rgn",
    "Toowoomba2010Prj",
    "Toowoomba2011Prj",
    "Toowoomba2010Rgn",
    "Toowoomba2015Prj",
    "BaanBaa201401",
    "Bathurst201104",
    "Bathurst201907",
    "Bellata201207",
    "Bellata201401",
    "Blayney201307",
    "Bellata202008",
    "Blayney201704",
    "Blayney201709",
    "BoganGate201304",
    "BoganGate201511",
    "BoganGate201906",
    "Boorowa201709",
    "Bourke201501",
    "Brewarrina201501",
    "Burrenbar201501",
    "Burrenbar201805",
    "Burrenbar201911",
    "Canonba201503",
    "Carinda201511",
    "Cobbora201407",
    "Collarenebri201210",
    "Condobolin201403",
    "Cowra201107",
    "Cowra201311",
    "Cowra201709",
    "Crookwell201709",
    "Dubbo201407",
    "Dubbo201507",
    "Dubbo201512",
    "Dungalear201207",
    "Geera201511",
    "Gongolgon201511",
    "Hermidon201305",
    "Hillston201610",
    "Mendooran201407",
    "Merriwagga201610",
    "Moree201207",
    "Moree202008",
    "MountHarris201503",
    "Mudgee201407",
    "Narrabri201401",
    "Narrabri201406",
    "Narromine201105",
    "Nyngan201105",
    "Orange201305",
    "Orange201704",
    "Orange201907",
    "Parkes201108",
    "Parkes201304",
    "Parkes201511",
    "Parkes201906",
    "PeakHill201410",
    "Pilliga201410",
    "Quambone201503",
    "Thallon201501",
    "Thallon201805",
    "Thallon201911",
    "Walgett201207",
    "Walgett201511",
    "Warren201105",
    "WeeWaa201207",
    "Wellington200910",
    "Wellington201507",
    "Bathurst201510",
    "Bunarba201506",
    "Carinda201705",
    "Cobbora201510",
    "Cumborah201705",
    "Dungalear201705",
    "Geera201705",
    "Gulgong201510",
    "Hermidon201705",
    "Mudgee201510",
    "Mudgee201612",
    "Oberon201510",
    "Quambone201705",
    "Walgett201705",
    "Bellata201106",
    "Paika201303",
    "Para201410",
    "BoganGate202104",
    "BoonaMount202104",
    "Bourke202011",
    "Brewarrina202011",
    "Moree201411",
    "Moree201506",
    "Cargelligo202103",
    "Cargelligo202104",
    "Cargelligo202107",
    "Geera202011",
    "Grenfell201108",
    "Gindoono202104",
    "Gongolgon202011",
    "Grenfell202104",
    "Merriwagga202103",
    "Marsden202104",
    "Mossgiel202103",
    "Narran202011",
    "BoganGate201502",
    "Hillston202103",
    "Parkes202104",
    "RankinsSprings202103",
    "Tullibigeal202104",
    "Warraweena202011",
    "Willandra202103",
    "LowerLila202011",
    "Condobolin202104",
    "Boomi201501",
    "Blayney201407",
    "Blackville201406",
    "Boggabri201401",
    "Boggabri201911",
    "Curlewis201401",
    "Curlewis201406",
    "Drake201506",
    "Goondiwindi201501",
    "Goondiwindi201911",
    "Manilla201910",
    "Manilla201911",
    "Murrurundi201406",
    "Nundle201911",
    "Tamworth201401",
    "Tamworth201406",
    "Yetman201911",
    "Drake200906",
    "Blackville201109",
    "Boggabri201604",
    "Curlewis201605",
    "Drake201709",
    "Coolah201108",
    "Narrabri201209",
    "TambarSprings201108",
    "Thallon200907",
    "BoganGate201509",
    "Blackville201108",
    "Boggabri201108",
    "Clive201711",
    "CroppaCreek200908",
    "Curlewis201108",
    "GlenInnes201712",
    "Gravesend200907",
    "Nundle201305",
    "Horton201209",
    "Inverell201110",
    "Manilla201210",
    "Murrurundi201111",
    "Tamworth201602",
    "Ashford201110",
    "Stanthorpe201108",
    "Texas201109",
    "Yetman201108",
    "Goondiwindi201506",
    "Yallaroi201412",
    "BaanBaa201605",
    "Bobadah201601",
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
    "Cobbora201208",
    "Collarenebri200908",
    "Condobolin201309",
    "Paika202105",
    "Coolah201109",
    "Cowra201404",
    "Crookwell201411",
    "Cumborah200908",
    "Dandaloo201208",
    "Dubbo201301",
    "Dungalear201703",
    "Dunumbral200908",
    "Oxley202105-z54",
    "Oxley202105-z55",
    "Euchareena201409",
    "Geera201703",
    "Gindoono201601",
    "Glenariff201505",
    "Gongolgon201507",
    "Grenfell201702",
    "Hillston201511",
    "Kilparney201408",
    "LightningRidge201801",
    "Louth201704",
    "LowerLila201508",
    "Marsden201502",
    "Mendooran201109",
    "Merriwagga201202",
    "MogilMogil200907",
    "Molong201308",
    "Molong201403",
    "Mossgiel201512",
    "MountHarris201304",
    "MountOxley201507",
    "Muckerumba201202",
    "Narrabri201604",
    "Narran200907",
    "Narromine201510",
    "Nyngan201211",
    "Oberon201311",
    "OneTree201201",
    "Orange201308",
    "Orange201407",
    "Oxley201303",
    "Parkes201509",
    "PeakHill201204",
    "Pilliga201703",
    "Quambone201304",
    "RankinsSprings201602",
    "TambarSprings201605",
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
    "Hermidon201505",
    "Moree200803",
]

ORIGINAL_BUKCET_NAME = "elvis-stac"
NWE_BUCKET_NAME = "dea-public-data-dev"
NEW_PREFIX = "projects/elvis-lidar/"


def modify_json_content(old_metadata_content: dict) -> dict:
    # assume all JSON files follow the same schema to save development time
    collection = old_metadata_content['collection']
    old_metadata_content['properties']['odc:collection'] = collection
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