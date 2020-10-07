"""
# Sentinel-2_nrt process env configs read from variables if environment specific
"""

# OWS pod specific configuration
OWS_CFG_PATH = "/env/config/ows_cfg.py"
OWS_CFG_MOUNT_PATH = "/env/config"
OWS_CFG_PATH = OWS_CFG_MOUNT_PATH + "/ows_cfg.py"
OWS_CFG_IMAGEPATH = "/opt/dea-config/prod/services/wms/ows/ows_cfg.py"

# Process specific for sentinel indexing process
ARCHIVE_PRODUCTS = "s2a_nrt_granule s2b_nrt_granule"
ARCHIVE_CONDITION = "[$(date -d '-365 day' +%F), $(date -d '-91 day' +%F)]"
SQS_QUEUE_NAME = "dea-sandbox-eks-ows-dag"

# products to be indexed
INDEXING_PRODUCTS = (
    "s2a_nrt_granule",
    "s2b_nrt_granule",
    "ga_s2a_ard_nbar_granule",
    "ga_s2b_ard_nbar_granule",
    "wofs_albers",
    "ls5_fc_albers",
    "ls7_fc_albers",
    "ls8_fc_albers",
)
# S3 Record list for indexing products
PRODUCT_RECORD_PATHS = (
    "L2/sentinel-2-nrt/S2MSIARD/*/*/ARD-METADATA.yaml",
    "L2/sentinel-2-nbar/S2MSIARD_NBAR/*/*/ARD-METADATA.yaml",
    "WOfS/WOFLs/v2.1.5/combined/*/*/*/*/*/*.yaml",
    "fractional-cover/fc/v2.2.1/*/*/*/*/*/*/*.yaml",
)
# ows layer product to be updated
UPDATE_EXTENT_PRODUCTS = (
    "s2_nrt_granule_nbar_t",
    "wofs_albers",
    "fc_albers_combined"
)