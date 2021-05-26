"""
# Sentinel-2_nrt process docker images used
"""

# IMAGES USED FOR THIS DAG
INDEXER_IMAGE = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/opendatacube/datacube-index:0.0.18"

OWS_IMAGE = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/opendatacube/ows:latest"
OWS_CONFIG_IMAGE = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/geoscienceaustralia/dea-datakube-config:latest"

EXPLORER_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/opendatacube/explorer:2.5.1"
)

S3_TO_RDS_IMAGE = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/geoscienceaustralia/s3-to-rds:0.1.4"

WAGL_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/dev/wagl:release-20210526a"
)

# UNSTABLE IMAGES
EXPLORER_UNSTABLE_IMAGE = "opendatacube/explorer:2.5.0-3-gd9f5a67"

# TODO: Use Skopeo to automatically fetch tags at runtime
# https://www.mankier.com/1/skopeo-list-tags
