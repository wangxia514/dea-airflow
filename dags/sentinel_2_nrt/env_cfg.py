"""
# Sentinel-2_nrt process env configs read from variables if environment specific
"""

# TODO: The archive condition is for sentinel_2_nrt, set different condition for different products
ARCHIVE_PRODUCTS = "s2a_nrt_granule s2b_nrt_granule"
ARCHIVE_CONDITION = "[$(date -d '-365 day' +%F), $(date -d '-93 day' +%F)]"


# products to be indexed
# TODO: This list need to be split when multiple SQS queues are setup for different products
INDEXING_PRODUCTS = (
    "s2a_nrt_granule",
    "s2b_nrt_granule",
    "ga_s2a_ard_nbar_granule",
    "ga_s2b_ard_nbar_granule",
    "wofs_albers",
    "ls5_fc_albers",
    "ls7_fc_albers",
    "ls8_fc_albers",
    "sentinel2_wofs_nrt",
)
# S3 Record list for indexing products
# TODO: This list need to be split when multiple SQS queues are setup for different products
PRODUCT_RECORD_PATHS = (
    "L2/sentinel-2-nrt/S2MSIARD/*/*/ARD-METADATA.yaml",
    "L2/sentinel-2-nbar/S2MSIARD_NBAR/*/*/ARD-METADATA.yaml",
    "WOfS/WOFLs/v2.1.5/combined/*/*/*/*/*/*.yaml",
    "fractional-cover/fc/v2.2.1/*/*/*/*/*/*/*.yaml",
    "WOfS/nrt/v2.1.6/s2/combined/*/*/*.yaml",
)

# batch indexing s3 paths
S2_NRT_S3_PATHS = "s3://dea-public-data/L2/sentinel-2-nrt/S2MSIARD/**/ARD-METADATA.yaml"
