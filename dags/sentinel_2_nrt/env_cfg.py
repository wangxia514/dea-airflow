"""
# Sentinel-2_nrt process env configs read from variables if environment specific
# - ows pod setup configurations
# - SQS name
# - Process configuration
# - - archival
# - - - product names and archival condition
# - - indexing
# - - - product names and indexing condition
# - - web application mv updates
# - - - explorer update product names
# - - - ows update product names
"""


# TODO: The archive condition is for sentinel_2_nrt, set different condition for different products
ARCHIVE_PRODUCTS = "s2a_nrt_granule s2b_nrt_granule ga_s2am_ard_provisional_3 ga_s2bm_ard_provisional_3 ga_ls8c_ard_provisional_3 ga_ls7e_ard_provisional_3"
ARCHIVE_CONDITION = "[$(date -d '-365 day' +%F), $(date -d '-93 day' +%F)]"


# products to be indexed
# TODO: This list need to be split when multiple SQS queues are setup for different products
INDEXING_PRODUCTS = (
    "s2a_nrt_granule",
    "s2b_nrt_granule",
    "ga_s2am_ard_provisional_3",
    "ga_s2bm_ard_provisional_3",
    "ga_ls8c_ard_provisional_3",
    "ga_ls7e_ard_provisional_3",
)
# S3 Record list for indexing products
# TODO: This list need to be split when multiple SQS queues are setup for different products
PRODUCT_RECORD_PATHS = (
    "L2/sentinel-2-nrt/S2MSIARD/*/*/ARD-METADATA.yaml",
    "baseline/ga_s2am_ard_provisional_3/*/*/*/*/*/*/*.odc-metadata.yaml",
    "baseline/ga_s2bm_ard_provisional_3/*/*/*/*/*/*/*.odc-metadata.yaml",
    "baseline/ga_ls8c_ard_provisional_3/*/*/*/*/*/*.odc-metadata.yaml",
    "baseline/ga_ls7e_ard_provisional_3/*/*/*/*/*/*.odc-metadata.yaml",
)

# batch indexing s3 paths
S2_NRT_S3_PATHS = "s3://dea-public-data/L2/sentinel-2-nrt/S2MSIARD/**/ARD-METADATA.yaml"
