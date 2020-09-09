"""
# Sentinel-2_nrt process docker images used
"""

# IMAGES USED FOR THIS DAG
INDEXER_IMAGE = "opendatacube/datacube-index:0.0.9-9-g4aacd64"

OWS_IMAGE = "opendatacube/ows:1.8.1"
OWS_CONFIG_IMAGE = "pinjin/ows-config:s2_msiard"


EXPLORER_IMAGE = "opendatacube/dashboard:2.1.9"
