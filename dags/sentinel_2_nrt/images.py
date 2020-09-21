"""
# Sentinel-2_nrt process docker images used
"""

# IMAGES USED FOR THIS DAG
INDEXER_IMAGE = "opendatacube/datacube-index:0.0.9-9-g4aacd64"

OWS_IMAGE = "opendatacube/ows:1.8.1"
OWS_CONFIG_IMAGE = "geoscienceaustralia/dea-datakube-config:1.5.1"

CREATION_DT_PATCHER_IMAGE = (
    "geoscienceaustralia/dea-k8s-data:0.2.7-unstable.12.g2e8431d"
)
EXPLORER_IMAGE = "opendatacube/dashboard:2.1.9"
