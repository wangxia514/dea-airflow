"""
#
# sns topics supplied by terraform
Audit check:
    date: 27/04/2021
"""
from airflow.models import Variable

SENTINEL_2_ARD_TOPIC_ARN = Variable.get(
    "sentinel_2_ard_sns_topic_arn",
    "arn:aws:sns:ap-southeast-2:538673716275:dea-public-data-sentinel-2-ard",
)

PUBLISH_ARD_NRT_LS_SNS = (
    "arn:aws:sns:ap-southeast-2:060378307146:dea-sandbox-eks-wagl-ls-nrt"
)

PUBLISH_ARD_NRT_S2_PROVISIONAL_SNS = (
    "arn:aws:sns:ap-southeast-2:060378307146:dea-sandbox-eks-ard-nrt-s2-provisional"
)
