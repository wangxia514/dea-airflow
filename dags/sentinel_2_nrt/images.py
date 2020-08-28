"""
# Sentinel-2_nrt process docker images used
"""

# IMAGES USED FOR THIS DAG
INDEXER_IMAGE = "opendatacube/datacube-index:0.0.8"

OWS_IMAGE = "opendatacube/ows:1.8.1"
OWS_CONFIG_IMAGE = "geoscienceaustralia/dea-datakube-config:1.5.1"
OWS_CFG_IMAGEPATH = "/opt/dea-config/dev/services/wms/ows/ows_cfg.py"

EXPLORER_IMAGE = "opendatacube/dashboard:2.1.9"
