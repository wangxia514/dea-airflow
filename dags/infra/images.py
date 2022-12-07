"""
# IMAGES USED FOR DAGs
"""
# STABLE IMAGES
INDEXER_IMAGE = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/opendatacube/datacube-index:latest"

OWS_IMAGE = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/opendatacube/ows:latest"
OWS_CONFIG_IMAGE = "geoscienceaustralia/dea-datakube-config:latest"  # do not pull from ECR, to avoid delay in ecr sync

EXPLORER_IMAGE = (
    "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/opendatacube/explorer:latest"
)

S3_TO_RDS_IMAGE = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/geoscienceaustralia/s3-to-rds:0.1.4"

WAGL_IMAGE = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/geoscienceaustralia/dea-wagl-docker:0.1.35"

STAT_IMAGE = "538673716275.dkr.ecr.ap-southeast-2.amazonaws.com/opendatacube/datacube-statistician:0.3.31"

WAGL_IMAGE_S2_C3 = "geoscienceaustralia/dea-wagl-docker:0.1.30-15-gec8281a"
WAGL_IMAGE_LS9 = "geoscienceaustralia/dea-wagl-docker:0.1.34"

S5CMD_IMAGE = "peakcom/s5cmd:v1.4.0"

# UNSTABLE IMAGES
EXPLORER_UNSTABLE_IMAGE = "opendatacube/explorer:2.5.0-3-gd9f5a67"

WATERBODIES_UNSTABLE_IMAGE = "geoscienceaustralia/dea-waterbodies:1.1.5-47-gea919a5"
CONFLUX_UNSTABLE_IMAGE = "geoscienceaustralia/dea-conflux:0.1.12-1-g0eb520d"
CONFLUX_WIT_IMAGE = "geoscienceaustralia/dea-conflux:0.1.13-13-ge2de28e"
CONFLUX_DEV_IMAGE = "geoscienceaustralia/dea-conflux:latest"
CONFLUX_WATERBODIES_IMAGE = "geoscienceaustralia/dea-conflux:0.1.12-109-g8643fb4"
